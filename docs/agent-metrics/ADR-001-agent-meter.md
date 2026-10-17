# ADR-001: `agent-meter` — local-first, idempotent usage collector for Claude Code and Antigravity

| Field | Value |
| :--- | :--- |
| Status | **Proposed** (ratification by orchestrator/user) |
| Date | 2026-10-16 |
| Author | `architect-engineer` (Track 11, State 1) |
| Inputs | `PLAN.md` § Track 11 (wins on conflict), `PRD.md`, `spike-notes.md` §1–6, `pricing-sources.md` |
| Companion | `contracts.md` (module signatures, dataclasses, store views, NDJSON outbox) — normative for Tracks 11A–11D |

## 1. Context

A freelancer needs deduplicated tokens, API-equivalent cost, latency and active time per project, task and agent across Claude Code and three Antigravity products, at $0 and with zero host overhead. Every host already writes durable files in real time, so the problem is **read-only, idempotent ETL over undocumented local formats**, not telemetry capture. The spike (`spike-notes.md` §6) settled the facts this ADR depends on:

- **Antigravity canonical usage = conversation DB.** `conversations/<id>.db` → `gen_metadata` is a strict superset of transcript usage. On the 25,267 overlapping steps it matches the transcripts exactly (0 mismatches). CLI transcripts only carry token fields since **2026-10-02**: 146 older conversations have transcripts without tokens. The "2.4x" gap is a coverage difference, not phantom calls. Rows copied between DBs are prefix imports declared in `parent_references`. The dedup key is `(trajectory_id, last_step_index)`.
- The DB `steps` table has the full step timeline. `step_type` 14 = `USER_INPUT`, 15 = `PLANNER_RESPONSE`, 17 = `ERROR_MESSAGE`, and `metadata.1.1` = epoch seconds (133,290/133,290 equal to transcript `created_at`). Transcripts are needed only for tool names.
- **Three Antigravity data roots**, not two: `~/.gemini/antigravity-cli/` (CLI), `~/.gemini/antigravity-ide/` (IDE: 45 `.db`, 5,573 calls) and `~/.gemini/antigravity/` ("Antigravity 2.0" per the CLI's embedded docs: 12 `.db`). Legacy `.pb` files have ~8.0 bits/byte entropy and no magic, so they are encrypted or compressed and **not recoverable**.
- **Hooks.** Antigravity (all products) supports `SessionStart`, `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation` and `Stop`, with **no session-end event**. `Stop` fires at the end of every execution loop (per task). Hooks run synchronously and must print a JSON object on stdout. User-level hooks live in `~/.gemini/config/hooks.json` (named-hook format; a top-level string such as `"description"` makes the whole file fail to parse). Claude Code has `SessionEnd` and `Stop`.
- **Claude Code.** `promptId` sits on every `user` line, including tool results, and never on `assistant` lines. A subagent run belongs to the prompt that **spawned** it: 100/102 runs' first `promptId` equals the spawn prompt, while 51 later carry newer prompt ids. Streaming duplicates grow `output_tokens`, so "first line wins" dedup undercounts output by **15.6%**. 83 `requestId`s are copied across files (resumed sessions, forks).

## 2. Quality attribute scenarios (SEI 6-part)

| ID | Source | Stimulus | Artifact | Environment | Response | Response measure |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| QA-1 Host latency | Host (Claude Code / Antigravity) | `Stop`/`SessionEnd` hook fires | `agent-meter hook` | Normal use, store possibly locked | Parse ≤ 64 KiB stdin, spawn detached worker, print `""` (Claude) / `{}` (Antigravity), exit 0 | Host-blocking time **P95 ≤ 300 ms**, hard cap 2 s, exit code 0 in 100% of HK tests |
| QA-2 Summary freshness | User | Ends a task/session | worker → summary | Lock free | Ingest that unit, write `last-summary.txt`, notify | **P95 ≤ 3 s** from hook start to summary file written (NFR-01) |
| QA-3 Idempotency | Hook + scheduler + manual `collect` | Same files ingested N times, concurrently | Store | Any | One writer at a time; upserts by natural key | Totals byte-identical after N ∈ {1,2,5} runs; 0 duplicate PKs (ST-01, ST-04) |
| QA-4 Backfill | `setup` | Imports full history (~373 MB Claude Code + 3.5 GB Antigravity DBs; only small blob fields decoded) | Collector | Cold start, M-series laptop | Unit-by-unit ingest, one transaction per batch of units | **≤ 2 min**, peak RSS **≤ 300 MB**; no-change incremental **≤ 2 s** (stat only) |
| QA-5 Accuracy | `verify --reconcile` | Frozen date range | Readers + views | Real data, read-only | Compare against independent counts | Claude Code input/cache tokens and request count = independent dedup **exactly**. Antigravity calls/tokens = independent `gen_metadata` count exactly and = transcript usage on transcript-covered steps. Cloud = local exactly (BQ-08) |
| QA-6 Format drift | Host update | Unknown fields / protobuf layout / DB schema | Readers | Any | Skip the affected unit/row, never write 0 tokens, record diagnostic | 0 crashes on RD-10/11/15 fixtures; `doctor` FAIL/WARN within 1 run |
| QA-7 Privacy | Fixture with canary `AGENT-METER-CANARY-7f3a` | Full pipeline incl. sync | Store, logs, outbox, HTML, BigQuery test dataset | L1–L4 | Allowlist extraction only | Canary occurrences = **0** (PV-01) |
| QA-8 Cost | Sync | 15-min scheduler for a month | BigQuery sink | `billing` mode | Load jobs only; views scan small tables | $0; BQ-04 static check finds 0 streaming/DML calls. Free-tier numbers **to verify at L4** |

## 3. Decision

### 3.1 Shape: one local package, ports and adapters only where hosts differ

A single Python package, `tools/agent-meter/`, is a modular monolith with no daemon. The data flow is **readers (one adapter per host format) → canonical records → DuckDB store (source of truth) → SQL views → {summary, HTML report, BigQuery replica}**. The only abstraction introduced is the `HostReader` protocol, because hosts differ. Store, report and sink are concrete modules.

```
tools/agent-meter/
  pyproject.toml            # name "agent-meter", hatchling, requires-python >=3.11, PyPI-ready metadata
  README.md  LICENSE
  src/agent_meter/
    __init__.py  __main__.py
    model.py                # dataclasses + enums (contracts.md §2) — 11A
    timeline.py             # active time, union, critical path, retries (pure) — 11A
    project_resolver.py     # git root / remote normalisation / worktrees — 11A
    pricing.py  pricing.yaml # load/merge/validate/write; resolve_price() oracle — 11A
    readers/{__init__,base,_protowire,claude_code,antigravity}.py   # 11A
    paths.py  config.py  locking.py  store.py  collector.py  summary.py  notify.py  hook.py  cli.py   # 11B
    sql/duckdb/{schema_v1.sql,views.sql}                              # 11B
    scheduler/{__init__,launchd,systemd,cron}.py  setup/{wizard,settings_merge,install_manifest,gcp_checks}.py  # 11B
    report/{__init__,build.py,template.html,style.css,app.js}         # 11C
    sinks/{__init__,outbox,bigquery}.py  sql/bigquery/{tables.sql,views.sql}   # 11D
  tests/{unit,contract,integration}/...  tests/fixtures/builder.py   # see §6 (moved from repo tests/)
```

- **Python ≥ 3.11** for `tomllib`, `datetime.fromisoformat("…Z")` and `ExceptionGroup`. System Python here is 3.10.8, so `uv tool install` provisions a managed interpreter and docs show `pipx install --python python3.12`.
- **Runtime deps: `duckdb>=1.1,<2` and `PyYAML>=6.0`** (safe_load/safe_dump only). PyYAML is the single addition to "duckdb + stdlib": PLAN fixes user-edited files as YAML (`pricing.yaml`, `pricing.local.yaml`, `projects.yaml`), and the CLI must write them. `config.toml` is read with `tomllib` and written by a small fixed-schema serializer in `config.py`. **Extra `[bigquery]`: `google-cloud-bigquery>=3.20`** (it brings `google-auth`). Option A imports nothing from it: `sinks/bigquery.py` imports lazily and DC tests assert this.
- Protobuf decoding uses a ~80-line stdlib wire-format walker (`readers/_protowire.py`, no `protobuf` dependency) that is allowlist-driven (§3.4).
- Imports nothing from `plugins/`, `skills/` or `scripts/` (NFR-09). SQL files ship as package data (`importlib.resources`).

### 3.2 Hosts and sources

| `host` value | Root (override env) | Usage source | Timeline source | Tools source | Project source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `claude-code` | `$CLAUDE_CONFIG_DIR` or `~/.claude` → `projects/*/<sid>.jsonl` + `<sid>/subagents/agent-*.{jsonl,meta.json}` | `assistant.message.usage`, one per `requestId` | line `timestamp`; `system/turn_duration` | `tool_use` blocks | line `cwd` (first of session) |
| `antigravity-cli` | `~/.gemini/antigravity-cli` | `conversations/<id>.db` `gen_metadata` | `steps` (`step_type`, `metadata.1.1`) | `brain/<id>/…/transcript_full.jsonl` `tool_calls[].name` | `conversation_summaries.workspace_uris[0]`, else blob `trajectory_metadata_blob.1.1` |
| `antigravity-ide` | `~/.gemini/antigravity-ide` | same | same | same, if present | blob `1.1` (no summaries DB) |
| `antigravity-app` *(new)* | `~/.gemini/antigravity` ("Antigravity 2.0") | same | same | same | blob `1.1` |

`antigravity-app` is proposed as a 4th host value (PLAN/PRD assumed `~/.gemini/antigravity/` was the IDE). Conversation ids found in more than one Antigravity root (100 legacy `.pb` ids exist in both `antigravity/` and `antigravity-ide/`) are counted once in untracked history. Agent-meter **never reads** `cli.log` (it contains user prompt text) or any `*.pb`.

### 3.3 Reading model: session units, full re-parse on change

A **unit** is the set of files that together describe one session:
- **Claude Code**: the main file plus its `subagents/` directory.
- **Antigravity CLI**: a root conversation plus all descendants (from `conversation_summaries.parent_conversation_id`, falling back to the `gen_metadata` key `parent_cascade_id`), covering each member's `.db`, `.db-wal`, transcript and `subagents/*.json`.
- **IDE/app**: one conversation.

`discover()` only stats files. A unit's fingerprint is the SHA-256 of `(relpath, size, mtime_ns, inode)` over its files. If it equals the stored fingerprint the unit is skipped, which keeps the no-change incremental run ≤ 2 s. Otherwise the **whole unit is re-parsed** and upserted.

Measured cost supports this: all Claude Code transcripts parse in 2.5 s and the largest (187 MB) in 0.86 s. This removes byte offsets, carry state and additive counters. Every derived value is recomputed from complete inputs, so re-ingestion is idempotent by construction.

- **Partial line rule**: JSONL is read only up to the last `\n`. An invalid final line is ignored, not committed. SQLite is opened with `file:…?mode=ro` and `PRAGMA query_only=1; busy_timeout=2000`, with no `immutable=1`, so WAL content is visible.
- **Retention (BR-15)**: if a unit's main file disappears, the unit is not re-read and stored rows are kept. The store never deletes ingested rows, except through explicit `--purge` or `projects merge`, which re-key rows by upsert.
- **Robustness**: each unit is parsed inside a `try`. A failure yields a `Diagnostic(kind="corrupt"|"format_changed", …)`, carrying only the exception class name and never its message, and the run continues.

### 3.4 Antigravity decoding contract (`gen_metadata.data`, protobuf)

| Path | Field | Rule |
| :--- | :--- | :--- |
| `1.20` repeated `{1:key,2:value}` | `trajectory_id`, `last_step_index` (required), `parent_cascade_id`, `request_id` (optional, 90% coverage, **not** a key) | Missing either required key → row skipped, `Diagnostic format_changed` |
| `1.4` | usage message | Absent → tokens `NULL` (never 0). If present, absent subfields = 0 (proto3 default) |
| `1.4.2` / `1.4.5` / `1.4.3` | input / cache read / output (output **includes** thinking) | verified 25,267/25,267 |
| `1.4.9` / `1.4.10` | thinking / visible output; `1.4.3 = 1.4.9 + 1.4.10` on 53,950/53,950 rows | `thinking_tokens` stored, informational only (never added to cost) |
| `1.19` / `1.21` | model id / display label | empty → `model = NULL` (inferred at query time, BR-04) |
| `1.11` `{1:s,2:ns}` | total call latency | stored as `latency_ms`. Evidence: the next call never starts before `1.9.4 + 1.11` (8,422/8,422 pairs) |
| `1.12` | unknown (≤ `1.11` in 94%, p50 0.06 s) | **not exposed** |

- The call is attached to step `last_step_index + 1`. `ts` = `steps.metadata.1.1` of that step, or `1.9.4.1` when the step is absent.
- **Dedup and ownership**: `call_id = "<host>:<trajectory_id>:<last_step_index>"`. A row is **owned** by the DB whose `trajectory_meta.trajectory_id` equals the key's `trajectory_id`, with `owner_rank "0"`. Copies in other DBs get `owner_rank "1:<conversation_id>"` and can only win when the owner DB does not exist (observed: 1 deleted trajectory, 830 calls). Per-DB `trajectory_meta` has exactly 1 row (463/463), and `cascade_id == conversation_id`.
- **Fallback**: if a conversation has no `.db` but its transcript has token fields, usage comes from `PLANNER_RESPONSE` steps (`call_id` = `"<host>:conv:<conversation_id>:<step_index>"`, model NULL). If a `.db` exists, transcript tokens are only a contract cross-check (RD-14).

### 3.5 Segmentation (task, agent run)

**Claude Code**
1. `task_id = "claude-code:<promptId>"`. A task starts at the first `user` line carrying that `promptId` and is labelled from that line at render time only.
2. A main-thread `assistant` line belongs to the `promptId` of its nearest `parentUuid` ancestor of type `user` with a `promptId`. If the chain breaks, use the last `promptId` seen in file order. If none exists yet, use the synthetic `"claude-code:<sid>:pre"`. On current data, chain and file order agree on 15,475/15,475 lines.
3. Subagent `agentId` → `agent_run_id = "claude-code:agent:<agentId>"`. Its **task** is the resolved `promptId` of the `assistant` line containing `tool_use.id == meta.toolUseId`, searched in the main file and sibling subagent files; fallback is the first `promptId` in the subagent file. **All of its calls roll up to that task**, whatever later `promptId`s its lines carry. `parent_agent_run_id` = `meta.parentAgentId`, else the owner of `toolUseId`, else the task's main run. `spawn_depth = meta.spawnDepth`.
4. Main run: `agent_run_id = task_id + ":main"`, `spawn_depth 0`, `agent_type "main"`.
5. Calls: one per `requestId` (fallback `message.id`). Take the line with **max `output_tokens`** (input and cache are identical across lines), with `ts` = its first line. `<synthetic>` is skipped. `usage.iterations[]` entries whose `type != "message"` produce a `Diagnostic unknown_usage_iteration` and are not priced.
6. `owner_rank = "<0 main|1 subagent>:<file first timestamp ISO>:<session_id>"`, so resumed-session and fork copies keep the original attribution.

**Antigravity**
1. Steps come from the DB `steps` table ordered by `idx`. `USER_INPUT` (`step_type 14`) steps open tasks: `task_id = "<host>:<conversation_id>:<user_input_idx>"`. Calls on steps before the first `USER_INPUT` (inherited prefixes) join the first task.
2. Child conversation → `agent_run_id = "<host>:agent:<child_conversation_id>"`, `agent_type = conversation_summaries.agent_name`. Its task is the parent task containing `subagents/<id>.json.spawnStepIndex`, falling back to the parent task active at the child's first step `ts`. Nested children inherit the root task, and `parent_agent_run_id` is the parent conversation's run. All calls of the child roll up there.
3. `ERROR_MESSAGE` steps count into `agent_runs.errors`. Tool counts come from transcript `tool_calls[].name`; with no transcript, `tool_uses` is empty and `agent_runs.tools_untracked = true`.

**Task status (BR-14)**:
- `done` when a later task exists in the session, or the host signalled end (`SessionEnd`, Antigravity `Stop` with `fullyIdle` recorded).
- `closed_stale` when there has been no event for 24 h; `ended_at` is then the last event.
- Otherwise `in_progress`.

A later ingest updates the row in place (same PK).

### 3.6 Time metrics (`timeline.py`, host-independent, pure)

- Each agent run's events are the sorted timestamps of every line or step it owns. Antigravity calls also contribute an interval `[ts, ts + latency_ms]`.
- **Run active time**: the union over consecutive events where `gap ≤ idle_threshold_s` (default 120), plus the latency intervals. Gaps longer than that are idle (BR-12).
- **Task active time**: the union of all its runs' active intervals.
- **Wall-clock**: last event minus first event across all runs.
- `reported_ms` = Claude Code `turn_duration.durationMs` reached by the `parentUuid` chain (last one wins). `duration_source = 'reported'` if present, else `'derived'`. Latency percentiles use `COALESCE(reported_ms, wall_clock_ms)`.
- **Parallelism factor**: Σ run `active_ms` ÷ task `active_ms`, shown only if `agent_runs > 1`.
- **Critical path**: the longest chain of runs ordered by `a.ended_at ≤ b.started_at`, weighted by `active_ms` (O(n²) DP, n ≤ ~100). Stored as `critical_path_ms` plus `critical_path` (agent types joined by `→`).
- **Retries (BR-13)**: for each `agent_type` with k > 1 runs in a task, k − 1 retries. `retry_summary` lists `<previous agent_type>→<agent_type>` by start order.
- **Derived dev hours (OQ-1)**: per project and local day, merge task intervals across sessions and hosts where the gap is ≤ 30 min, then sum, splitting at local midnight. These are written to table `dev_hours_derived` and recomputed on every collect, so cloud parity comes from uploading the table rather than re-deriving it in SQL.

Sensitivity: `idle_threshold_s` controls active time and parallelism. A single LLM call or tool longer than the threshold (e.g. a 5-min `pytest`) counts as idle in Claude Code because its request start time is not logged. This is documented, and a threshold change applies after `collect --full`.

### 3.7 Project resolution (`project_resolver.py`, BR-07/08)

1. **Input**: an absolute directory path, either Claude Code `cwd` or an Antigravity `file://` URI after URL-unquoting.
2. **Unassigned**: `$HOME`, `/`, a temp root (`/tmp`, `/private/tmp`, `/var/folders`, `$TMPDIR`), or a path matched by `projects.yaml` `ignore:` resolves to `(unassigned)`.
3. **Existing directory**: run `git -C <p> rev-parse --path-format=absolute --git-common-dir --show-toplevel` (timeout 2 s). For worktrees the main repo is `dirname(git-common-dir)`. Then read `git -C <main> remote get-url origin`.
4. **Missing directory** (56/139 observed): first try the stored `path_map` via `sha256(path)`. Then, if the path contains a `/.claude/worktrees/`, `/.worktrees/` or `/worktrees/` segment, resolve the prefix before it. Otherwise fall back to a path id.
5. **Remote normalisation**: strip scheme, `userinfo@` (credentials are never stored), port and trailing `.git`/`/`; convert `git@host:owner/repo` to `host/owner/repo`; lowercase the host only. The result looks like `github.com/jggomez/expert-ai-developer-skills`.
6. **Identifiers**: `project_id = "git:" + sha256(normalized)[:16]`, or `"path:" + sha256(realpath)[:16]`, or `"(unassigned)"`. `display_name` = repo basename, overridable in `projects.yaml`.
7. **Path cache**: the store keeps only `path_map(path_hash → project_id)` and **no clear-text workspace paths** (BR-16).
8. **Overrides**: `projects.yaml` `paths:` aliases and `merge` re-key project ids.

### 3.8 Pricing (ratifies PLAN "Configurable pricing" and `pricing-sources.md`)

- **Files**: shipped `agent_meter/pricing.yaml`, seeded **only** from `pricing-sources.md`, plus user `~/.agent-meter/pricing.local.yaml`. They are merged at load and **local wins** per `(model, effective_from, min_prompt_tokens)` row and per alias. The format is in `contracts.md` §5.
- **Windows**: a call uses the row with the latest `effective_from ≤ local call date` and the highest `min_prompt_tokens ≤ prompt_tokens`, where `prompt_tokens = input + cache_read + cache_write_5m + cache_write_1h`. Tiers cover Haiku 5.5 > 100K and Gemini 3.1 Pro > 200K.
- **Aliases** are single-hop: `alias → model`, `estimated: bool`. Chains and cycles are rejected by `validate` (PC-09).
- **Adopted alias seed** (from `pricing-sources.md` §3):
  - exact: `claude-haiku-4-5-20251001 → claude-haiku-4-5`
  - estimated: `gemini-3.8-flash-n → gemini-3.8-flash`, `gemini-flash-3.6-high-control → gemini-3.6-flash`
  - left **unpriced** (no defensible mapping): `gemini-3.7-flash*`, `gemini-default`, `gemini-pro-default`, `agy-demo-*`, `gemini-3-flash-a/-b`, `gemini-3-flash-medium-a`
  - not in `pricing-sources.md`, so unpriced until the orchestrator fetches them: `claude-opus-4-6-thinking`
- **Variants**: `usage.speed == "fast"` resolves to model key `<model>:fast` if such a row exists, else to the base row with `estimated`. `inference_geo` is stored and ignored in v1, which is documented.
- **Cost is computed at query time** in view `v_calls`, never persisted:
  - `cost_usd = ROUND((in*p_in + out*p_out + cw5*p_cw5 + cw1h*p_cw1h + cr*p_cr) / 1000000, 9)`
  - prices are `DECIMAL(12,6)` USD/MTok
  - DuckDB computes in `DECIMAL(38,12)`; BigQuery uses `BIGNUMERIC` then `ROUND(…, 9)` (half away from zero in both)
  - totals are sums of per-call rounded values, so local equals cloud
  - Python never does float money (NFR-04)
- **Unpriced** (BR-02): no row → `cost_usd NULL`, `unpriced = true`. Totals render `≥ $X (N calls unpriced: m1, m2)`, and `doctor`/summary print the exact `agent-meter pricing add <model> --input … --output … --cache-read … --effective-from …`.
- **Inferred model** (BR-04): `model IS NULL` resolves via `host_defaults.default_model` from `config.toml`. Flags propagate as `*` for estimated and `†` for inferred.
- **Price data at query time**: `pricing`, `pricing_aliases` and `host_defaults` are tables fully replaced from files at the start of every store-opening command (tiny). Editing a price changes history on the next report or sync with **no re-ingestion** (PC-08).
- **Python oracle**: `pricing.resolve_price()` (contracts §3.4) mirrors the SQL. Store tests assert view == oracle on fixtures (guards drift between the two).

### 3.9 Store (DuckDB) and concurrency

- One file, `~/.agent-meter/meter.duckdb`. Schema v1 DDL is in `contracts.md` §4, and `meta.schema_version` drives forward-only migrations (`store.migrate()`, ST-06).
- **Writes**: each batch of units goes into temporary staging tables (via `executemany`, or for large batches a temp NDJSON file loaded with `read_json`) and is then merged in one transaction:
  - `INSERT OR REPLACE … SELECT s.* FROM staging s LEFT JOIN target t USING(pk) WHERE t.pk IS NULL OR s.owner_rank < t.owner_rank OR (s.owner_rank = t.owner_rank AND s.row_hash <> t.row_hash)`
  - `row_hash` = SHA-256 of the business columns
  - `ingest_seq = nextval('ingest_seq')` is assigned only to changed rows, so unchanged re-reads do not re-upload
  - `tool_uses` for agent runs present in the batch are replaced wholesale
  - unit fingerprints commit in the same transaction
- **Locking** (`locking.py`, `fcntl.flock` on `~/.agent-meter/lock`):
  - writers (`collect`, hook worker, `sync`, `tag`, `hours`, `projects`) take `LOCK_EX`
  - readers (`report`, `tasks`, `last`, `doctor`) take `LOCK_SH` and open DuckDB `read_only=True`
  - DuckDB itself forbids a reader while another process writes, hence the shared advisory lock
  - wait budgets: hook worker 3 s, scheduler 60 s (then skip the cycle), interactive commands 30 s with a message
- **Snapshot**: after each successful write, `~/.agent-meter/state/snapshot.json` is written atomically. It holds today and MTD per project and host, plus the last 20 session summaries. When the lock is busy, the hook worker renders from it plus an in-memory parse of the current unit, with the note `(collecting… run 'agent-meter last' in a minute)` (US-01).

### 3.10 Triggers: hooks, scheduler, manual

**Hook wrapper contract (BR-20)**:
- `agent-meter hook --host <h> --event session-end|task-end`
- reads ≤ 64 KiB of stdin JSON and extracts **only** the allowlisted keys:
  - Claude Code: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `reason`, `stop_hook_active`
  - Antigravity: `conversationId`, `transcriptPath`, `workspacePaths`, `terminationReason`, `fullyIdle`, `executionNum`
  - everything else, e.g. `last_assistant_message`, is discarded unread and never logged
- spawns `agent-meter hook-worker …` detached (`start_new_session=True`, stdio to `/dev/null`, args via argv, never a shell)
- stdout: writes nothing (Claude Code) or exactly `{}\n` (Antigravity requires a JSON object; `{}` allows the stop)
- exits **0** on every path, including exceptions and the internal 2 s watchdog (`signal.alarm`)
- the host-side `timeout` is set to 10 s as a backstop
- the worker ingests only that unit, writes `last-summary.txt`, and notifies according to `notify` policy (`session`, the default for Claude Code `SessionEnd`; `long-tasks` ≥ 120 s, the default for `Stop` on both hosts; `off`)
- Antigravity `Stop` from a child conversation, or with `fullyIdle=false`, ingests and does not notify
- the inline `systemMessage` display for Claude Code is **off** (`claude_inline_summary = false`) until verified at L6 that it is user-only and not model context

**Registration**:

| Host | File | Entry |
| :--- | :--- | :--- |
| Claude Code | `~/.claude/settings.json` (`$CLAUDE_CONFIG_DIR`) | `hooks.SessionEnd[] += {hooks:[{type:"command",command:"<abs>/agent-meter hook --host claude-code --event session-end",timeout:10}]}`, and `hooks.Stop[]` likewise with `--event task-end` |
| Antigravity (CLI, IDE, app) | `~/.gemini/config/hooks.json` | named hook `"agent-meter": {"enabled": true, "Stop": [{"type":"command","command":"<abs>/agent-meter hook --host antigravity --event task-end","timeout":10}]}`. Host is detected from the `transcriptPath` root (`antigravity-cli/`, `antigravity-ide/`, `antigravity/`). **No top-level non-object keys.** |

Antigravity has no session-exit event, so US-01 for Antigravity is met **per task** (`Stop`). The session view is `agent-meter last`, and the scheduler closes stale sessions. `~/.gemini/settings.json` belongs to **Gemini CLI** (`BeforeTool`/`run_shell_command`), is not an Antigravity file, and is never edited (the `rtk` hook is untouched by construction).

**Settings merger** (`setup/settings_merge.py`, BR-18/19):
- **Read**: resolve `realpath` (edit the symlink target). Refuse on invalid JSON, a non-object root, a file not owned by the user, or a managed policy present (`/Library/Application Support/ClaudeCode/managed-settings.json` or `/etc/claude-code/managed-settings.json` with `allowManagedHooksOnly`). On refusal, offer scheduler-only.
- **Backup**: copy the original bytes, or an `absent` marker, to `~/.agent-meter/backups/<host>-<UTC>.json` (mode 0600) **before** any write.
- **Merge**: append our entries only if an identical `command` string is not already present, which keeps the merge idempotent (SU-01). Write atomically (temp file in the same directory, `fsync`, `os.replace`, original mode preserved) with `indent=2`. Record `{file, backup, post_sha256, entries}` in `~/.agent-meter/install.json`.
- **Uninstall**: if the current SHA-256 equals `post_sha256`, restore the backup byte-for-byte, or delete the file if it was absent. Otherwise remove exactly our recorded entries, drop containers we created that are now empty, keep the user's edits and leave the backup in place (BR-19).
- **Plugin overlap**: if the optional `agent-metrics` plugin is detected (`enabledPlugins` / `~/.gemini/config/plugins/agent-metrics`), setup does not add user-level hooks. Double firing is harmless anyway (idempotent), and notifications are deduped by `state/notified.json` keyed by `(unit, task_id, event)`.

**Scheduler** (`scheduler/`): runs `<abs>/agent-meter collect --scheduled --quiet` every 900 s. `--scheduled` also runs `sync` when the cloud sink is enabled, and a weekly `--full-reload` in sandbox mode.
- **macOS**: `~/Library/LaunchAgents/dev.agentmeter.collect.plist` with `StartInterval 900`, `RunAtLoad true`, `ProcessType Background`, `LowPriorityIO true`, `Nice 10` and stdout/stderr to `~/.agent-meter/logs/scheduler.log`. Installed via `launchctl bootstrap gui/<uid>` and removed via `bootout`; launchd runs a missed interval once after wake (PF-05).
- **Linux**: `~/.config/systemd/user/agent-meter-collect.{service,timer}` (`OnBootSec=2min`, `OnUnitActiveSec=15min`, `Persistent=true`), enabled with `systemctl --user enable --now`. Without user systemd, a crontab line `*/15 * * * * <abs>/agent-meter collect --scheduled --quiet # agent-meter` is managed by marker.

### 3.11 BigQuery sink (Option B, 11D)

- **Logical outbox**: there is no second copy of the data. Rows with `ingest_seq > meta['bq_watermark:<table>']` form the outbox. At sync time they are materialised to `~/.agent-meter/outbox/<table>/<batch_id>.ndjson` (`contracts.md` §7). A **load job** (`NEWLINE_DELIMITED_JSON`, explicit schema, `WRITE_APPEND`) runs per file, and the watermark advances only after the job is `DONE` without errors, in the same lock. On failure, or when offline or holding expired ADC, files and watermark stay put and are retried next cycle; `doctor` shows lag and backlog (US-15, BQ-05/06/07). The outbox is deleted after success.
- **Tables**:
  - fact tables: `raw_llm_calls`, `raw_tasks`, `raw_agent_runs`, `raw_tool_uses`, `raw_sessions`, all append-only with `ingest_seq` and `_uploaded_at`; partitioned by `TIMESTAMP_TRUNC(ts|started_at, MONTH)` and clustered by `project_id, host`
  - reference tables, with **the same names as in DuckDB**: `projects`, `pricing`, `pricing_aliases`, `host_defaults`, `dev_hours_manual`, `dev_hours_derived`, `task_tags`, `tag_history`, `settings`, `untracked`; small and re-loaded with `WRITE_TRUNCATE` every sync, so price edits propagate (PC-08)
- **Dedup views**: one plain-named view per fact table (`llm_calls`, `tasks`, …), each built as `QUALIFY ROW_NUMBER() OVER (PARTITION BY <pk> ORDER BY ingest_seq DESC) = 1` over `raw_<table>`. The `v_*` views are then written against identical names on both engines, so names and columns mirror the DuckDB views exactly (`contracts.md` §6). Percentiles use `PERCENTILE_CONT` (exact) on both sides.
- `--full-reload` = `WRITE_TRUNCATE` of every table from the local store, which is also the sandbox-mode weekly job.
- **No `insert_rows`, no DML, no streaming** (BQ-04). DDL runs once at setup via `CREATE … IF NOT EXISTS` / `CREATE OR REPLACE VIEW` query jobs.
- **Recommendation**: drop `require_partition_filter`. It breaks dedup views and Looker queries that do not filter the base partition column. Use BQ-09 as a dry-run byte ceiling instead: each view's full-history dry run must be ≤ 1 GiB at 10x the current volume.
- **Anonymisation (BR-17)**: with `anonymize_projects`, `project_id`, `display_name`, `client` and `remote_url` are replaced by `HMAC-SHA256(salt, value)[:16]`. The salt is 32 random bytes in `~/.agent-meter/secret` (0600) and is never uploaded. `verify --reconcile --cloud` maps ids locally.
- **Auth**: ADC via `google.auth.default()`. The project is always passed explicitly (`bigquery.Client(project=cfg.project)`), and tokens are never logged or written.
- **Wizard prerequisite checks** (`setup/gcp_checks.py`): each returns `Check(id, status, message, fix_command, autofix_safe)` and runs `gcloud` with `--project <p>`, `CLOUDSDK_CORE_DISABLE_PROMPTS=1` and a 20 s timeout.

| Check | Probe | Fix printed |
| :--- | :--- | :--- |
| `gcloud` | `gcloud --version` | install URL |
| ADC | `gcloud auth application-default print-access-token` (exit≠0 / "reauth") | `gcloud auth application-default login` (autofix: interactive) |
| project | `gcloud projects describe <p> --format=value(projectNumber)` | list via `gcloud projects list` |
| default-project mismatch | `gcloud config get-value project` ≠ `<p>` | WARN only: "agent-meter always uses `<p>` explicitly" |
| billing | `gcloud billing projects describe <p> --format=value(billingEnabled)` | `gcloud billing projects link <p> --billing-account=<id>` or choose `sandbox` |
| API | `gcloud services list --enabled --project <p> --filter=config.name=bigquery.googleapis.com` | `gcloud services enable bigquery.googleapis.com --project <p>` (autofix safe) |
| IAM | Resource Manager `projects.testIamPermissions` (`bigquery.datasets.create`, `bigquery.tables.create`, `bigquery.tables.updateData`, `bigquery.jobs.create`) with the ADC token | `gcloud projects add-iam-policy-binding <p> --member=user:<adc email> --role=roles/bigquery.dataEditor` and `…/roles/bigquery.jobUser` |
| budget (offer) | — | `gcloud billing budgets create --billing-account=<id> --display-name=agent-meter --budget-amount=1USD --threshold-rule=percent=0.5 --threshold-rule=percent=1.0`, plus the warning "alerts do not cap spend" |

- **Looker Studio**: the Linking API create URL, i.e. `https://lookerstudio.google.com/reporting/create?c.reportId=<template>&ds.ds0.connector=bigQuery&ds.ds0.type=TABLE&ds.ds0.projectId=<p>&ds.ds0.datasetId=<d>&ds.ds0.tableId=v_calls…`. The parameter names, a publicly shared template report and the multi-data-source binding are **to verify at L4**. Manual steps are the fallback.

### 3.12 Summary and HTML report

- `summary.py` renders the PRD text formats from views only. **Task labels** (OQ-4) are read from the transcript at render time and printed **only to an interactive terminal** (`tasks`, `last` when `isatty`). They never reach `last-summary.txt`, notifications, logs, the report or the cloud; opt out with `show_task_labels = false`.
- **Test status**: `Bash`/`run_command` tool calls whose command's first tokens match a fixed allowlist (`pytest`, `python -m pytest`, `uv run pytest`, `npm test`, `npx jest`, `flutter test`, `dart test`, `go test`, `cargo test`). Their `tool_result.is_error` / `error` gives `test_runs` / `test_failures`. The command string is never stored.
- **Report** (`report/build.py`): a single self-contained HTML file. CSS and vanilla JS are inlined from package files, charts are server-rendered inline **SVG** (no chart library), and data is embedded as `<script type="application/json">` with `<`, `>` and `&` escaped as `<`, `>` and `&`. Every text value is HTML-escaped. There are no `http(s)://` references other than optional plain-text doc links (SM-04 asserts the regex `(src|href)=["']https?:` has 0 matches). Pages: Overview, Projects & Clients, Tasks & Agents, Performance, Efficiency, Data Quality (unpriced, inferred, untracked, diagnostics). An empty store renders "No data yet — run `agent-meter collect`".

### 3.13 Privacy enforcement points (BR-16/17, NFR-06)

1. **Readers**:
   - copy only allowlisted keys into the typed dataclasses in `model.py`, never whole dicts
   - free-text-capable fields (`agent_type`, `tool_name`, `model`, `model_label`) must match `^[A-Za-z0-9_.:@/+ ()-]{1,80}$`, otherwise `"(other)"`
   - descriptions are stored as `sha256(salt + text)`
   - file paths touched are hashed in memory per run and only counted
2. **Store**: no column holds prompt, assistant text, tool args/results, file paths or workspace paths (`path_map` holds hashes). `source_units`/`source_files` keep host transcript paths for change detection; they are local-only and never exported or rendered.
3. **Logs and diagnostics**: carry the exception class name, unit id hash, and file kind only.
4. **Hook**: allowlisted stdin keys only (§3.10).
5. **Outbox/BigQuery**: explicit column projection from views and tables (`contracts.md` §7), plus anonymisation.
6. **Never read**: `cli.log`, `*.pb`, `history.jsonl`, `~/.gemini/oauth_creds.json`.
7. **Tests**: the canary is planted in every free-text slot of the fixtures, and PV-01 greps the store dump, outbox, HTML, logs and the BigQuery test dataset.

## 4. ATAM trade-offs

| Trade-off | Choice | Cost accepted |
| :--- | :--- | :--- |
| Simplicity vs incremental efficiency | Full re-parse per changed unit, no byte offsets | A very large active unit (e.g. a 53-child Antigravity DAG) is re-read on every hook. Measured at < 1 s for Claude Code; the Antigravity unit P95 is guarded by PF-03, with per-file caching as a later optimisation if it fails |
| Accuracy vs independent-tool parity | Max-output line per `requestId` | Can differ from tools that keep the first line (−15.6% output tokens observed). NFR-03 is restated in §7 |
| Coverage vs single source | Antigravity DB canonical; transcript only for tool names and the no-DB fallback | Depends on an undocumented protobuf; mitigated by allowlist decoding, contract fixtures, `doctor` "format changed", NULL-not-0 |
| Host responsiveness vs visibility | Detached worker; Claude Code shows no inline text by default | The summary appears via notification, `last-summary.txt` and `agent-meter last`, not in the host UI |
| Query-time cost vs speed | Cost view recomputed per query | Trivial at this data size (~10^5 calls/yr); every price edit is retroactive by design (BR-03) |
| Cloud cost vs guardrails | No `require_partition_filter` | Relies on small tables plus dry-run byte ceiling tests |

**Risks**:
- R1: Antigravity format change (High likelihood over time / Medium impact). Mitigated by contract tests and `doctor`.
- R2: Claude Code `cleanupPeriodDays` (default 30; earliest transcript here is 2026-09-21) limits backfill. Mitigated by the scheduler ingesting continuously, plus BR-15.
- R3: Antigravity hook stdout handling. Mitigated by always printing `{}`, and verified in L6.
- R4: DuckDB ICU timezone functions must be available in wheels. Verified in ST tests; fallback is computing `local_date` in Python and storing `utc_offset_min`.

## 5. Alternatives considered

| Alternative | Rejected because |
| :--- | :--- |
| Antigravity transcripts as usage source | Miss ~60% of calls: no tokens before 2026-10-02, prefixes missing, 36 conversations without a transcript |
| `request_id` / `last_execution_id` / `cascade_id` as Antigravity dedup key | `request_id` is missing on 10% of rows, `last_execution_id` is shared by many calls, and `cascade_id` is per conversation |
| Byte-offset incremental readers with carry state | Measured full parse is cheap. Offsets need cross-chunk state (parentUuid chains, spawn maps, distinct-file sets) and non-idempotent counters |
| SQLite as the local store | Weaker analytics (percentiles, window functions); DuckDB ≈ BigQuery SQL keeps the views symmetrical |
| Physical NDJSON outbox written at ingest | Duplicates data and needs cleanup; a logical outbox with `ingest_seq` watermarks gives the same at-least-once plus dedup guarantees |
| Streaming inserts / `MERGE` into BigQuery | Not free-tier/sandbox safe (NFR-05) |
| OpenTelemetry / Claude Code OTel export | Host-specific, needs a collector, out of scope (v1 non-goal) |
| Hook does the work inline | Antigravity hooks block the agent loop; a 2-min backfill under lock would stall the host |
| TOML for pricing/projects (no PyYAML) | Contradicts the user-decided YAML files; PyYAML is a small, ubiquitous dependency |

## 6. Consequences and follow-ups

- **Positive**: all three Antigravity products are covered from one reader and one decoding contract. Re-ingestion is idempotent by construction, a crash loses nothing, and Option A works fully offline.
- **Negative**:
  - the undocumented protobuf must be re-validated on each Antigravity update (contract fixture per format fingerprint = sorted table/column set + observed `1.20` keys)
  - per-task rather than per-session hooks on Antigravity
  - +1 dependency (PyYAML)
- **Tests**: tests for the package move to `tools/agent-meter/tests/` (DC-03 requires them to pass from a clean venv without the repo). Repo-level `tests/structure/` keeps the decoupling and plugin checks (DC-01/02/04).
- **Runbook**: `uv run --project tools/agent-meter pytest tools/agent-meter/tests`. The existing `pytest tests/` (system Python 3.10) is unaffected.
- **Plugins (11E)**: the Antigravity `agent-metrics/hooks.json` must use the named-hook format with **no top-level `description`**.

## 7. Architectural invariants (for `compliance-verifier` and `qa-tester`)

1. **I-1 Decoupling**: no file outside `tools/agent-meter/`, `plugins/*/agent-metrics/`, `skills/agent-metrics/`, `docs/agent-metrics/` and the marketplace entry mentions `agent-meter`/`agent-metrics`. The package imports nothing from repo folders.
2. **I-2 Optional cloud**: no top-level import of `google.*` anywhere. `python -X importtime -m agent_meter --help` loads no `google` module.
3. **I-3 Read-only hosts**: readers open transcripts in binary read mode only, and SQLite with `mode=ro` + `query_only`. The only host files written are the two settings/hooks files via `settings_merge.py`.
4. **I-4 Hook**: the `hook` subcommand exits 0 on every path. stdout is empty (Claude Code) or `{}` (Antigravity), and it never imports `duckdb` (fast path).
5. **I-5 Money**: no `float` in any cost path. Cost exists only in views (`v_calls.cost_usd`), with no cost column in any table.
6. **I-6 Unpriced**: `cost_usd IS NULL ⇔ unpriced`. No `COALESCE(cost, 0)` in views or report totals, which are always paired with `unpriced_calls`.
7. **I-7 BigQuery**: only `load_table_from_file`/`load_table_from_uri` and DDL query jobs. 0 occurrences of `insert_rows`, `insert_rows_json`, `MERGE`, `UPDATE`, `DELETE`, `INSERT INTO`.
8. **I-8 Privacy**: canary absent everywhere (PV-01). The store contains no columns beyond `contracts.md` §4.
9. **I-9 Natural keys**: `call_id`, `task_id` and `agent_run_id` are deterministic strings from §3.4–3.5. Re-ingesting in any order yields identical tables (attribution decided by `owner_rank`).
10. **I-10 Parity**: `v_daily_project_cost` is identical in DuckDB and BigQuery for the same `settings.timezone` (BQ-08).

**Corrected NFR-03 (recommended)**:
- Claude Code: request count and input/cache-read/cache-write tokens must equal an independent `requestId` dedup exactly. Output tokens are compared with "max line per `requestId`" semantics. `ccusage` differences are reported, not failed: L5 must first establish which line `ccusage` keeps.
- Antigravity: calls and tokens equal an independent `gen_metadata` count using the §3.4 key and ownership rule, and equal transcript `PLANNER_RESPONSE` usage exactly on transcript-covered steps.
