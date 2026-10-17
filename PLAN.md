# Engineering Execution Plan: Antigravity & Claude Code Plugins

## Track 1: Antigravity Plugins Ecosystem Enhancement (COMPLETED)
- [x] Phase 1: `senior-dev-flutter` (Graph DAG, role boundaries, Plan-First pre-tool gate, `flutter-rules.md`).
- [x] Phase 2: `senior-data-engineer` (`hooks.json`, `data-safety-gate.js`, `data-quality-gate.js`, Lakehouse DAG).
- [x] Phase 3: `python-backend` (`python-backend-orchestrator.md`, `python-backend-rules.md`, Plan-First pre-tool gate).
- [x] Phase 4: `sql-query-optimizer` (`sql-optimization-rules.md`, `sql-safety-gate.js`, dry-run enforcement).
- [x] Phase 5: `git-workflow` (`gitflow-rules.md`, Conventional Commits, `git-clean-stop-gate.js`).
- [x] Phase 6: `docs-and-quality` (`docs-and-quality-rules.md`, Karpathy rules, `anti-lazy-code-gate.js`).
- [x] Phase 7: `multi-agent-ops` & `shared-context` (`context-guard-gate.js`, clean hooks schema).
- [x] Phase 8: Verification & Syntax Validation (`node --check`, `JSON.parse` across all plugins).

---

## Track 2: Claude Code Plugins Ecosystem Enhancement (COMPLETED)
- [x] Phase 1: Architecture & Flutter (`senior-dev-flutter`)
- [x] Phase 2: Python Backend (`python-backend`)
- [x] Phase 3: Data Engineering & SQL (`senior-data-engineer` & `sql-query-optimizer`)
- [x] Phase 4: Git Hygiene & Quality Gates (`git-workflow` & `docs-and-quality`)
- [x] Phase 5: Multi-Agent Coordination & Context (`multi-agent-ops` & `shared-context`)
- [x] Phase 6: Verification & Validation (`node --check`, `JSON.parse`, 48 empirical tests, `APPROVED` audit).

---

## Track 3: Unified Agent Governance & Living Repo Context (COMPLETED)
- [x] Phase 1: Universal `AGENTS.md` Constitution
- [x] Phase 2: Cross-Platform Symlinks (`CLAUDE.md`, `AGENT.md`)
- [x] Phase 3: Living Project Context (`.agents/rules/project-context.md`)
- [x] Phase 4: Empirical Testing (`qa-tester`, 91/91 tests pass)
- [x] Phase 5: Compliance Audit (`compliance-verifier`, `APPROVED`)

---

## Track 4: Skill Synchronization Automation (COMPLETED)
- [x] Phase 1: Updated `scripts/sync_plugin_skills.py` for dual synchronization (`plugins/antigravity` & `plugins/claude`).
- [x] Phase 2: Propagated canonical `/skills` into all 18 plugins.

---

## Track 5: Workflows Modernization with Dual-Runner Support (COMPLETED)
- [x] Phase 1: Updated all 16 workflows with dual-runner delegation (`invoke_subagent` for Antigravity & `Agent` for Claude Code).
- [x] Phase 2: Explicitly codified Inviolable Role Boundaries in `build-workflow.md`, `plan-workflow.md`, etc.

---

## Track 6: Functional Enrichment of Core Skills (COMPLETED)
- [x] Phase 1: `loop-engineering`: Topologies (Manager-Worker, Sequential, Review Committee) and 3-loop cap.
- [x] Phase 2: `guidelines-karpathy`: Anti-Lazy Code policy and Anti-Premature Abstraction.
- [x] Phase 3: `test-driven-development`: Multi-language testing patterns (Python pytest, Flutter widget tests, Dataform assertions).
- [x] Phase 4: `commit-expert`: Conventional Commits standard aligned with lifecycle hooks.

---

## Track 7: All READMEs & Documentation Modernized (COMPLETED)
- [x] Root `README.md` updated with full dual ecosystem architecture, `AGENTS.md`, and 35 skills.
- [x] `skills/README.md` updated with sync runbooks.
- [x] All 18 plugin `README.md` files updated across `plugins/antigravity/` and `plugins/claude/`.

---

## Track 8: Global QA & Verification Suite (COMPLETED)
- [x] `pytest tests/structure/`: 36 passed (100%).
- [x] `pytest tests/unit/`: 55 passed (100%).
- [x] Total: 91 passed in full test suite (`exit code 0`).

---

## Track 9: Senior-Dev LLM Wiki Memory (`context/memory/`), Mandatory Discovery Triage & Parallel DAG Execution (COMPLETED)
- [x] Phase 1: LLM Wiki Memory Architecture in `context-capture` & `context-restore`.
- [x] Phase 2: Senior-Dev Orchestrator DAG Upgrade (Triage Gate + Parallel Fan-Out/Fan-In + Worktrees + Wiki Memory).
- [x] Phase 3: Synchronization & Automated Tests (`99 passed`, `APPROVED`).

---

## Track 10: Ecosystem-Wide Plugin Upgrade (`senior-dev-flutter`, `python-backend`, `senior-data-engineer`, `sql-query-optimizer`, `shared-context`, `multi-agent-ops`) (COMPLETED)

### Discovery & Architecture Triage
| Specialist Node | Triage Verdict | Justification |
| :--- | :--- | :--- |
| **`product-analyst`** | `COMPLETED IN /plan` | User confirmed full scope across all 5 plugin groups and confirmed silent automatic `context/memory/MEMORY.md` loading without 25-tool-call mid-turn autosave nagging. |
| **`architect-engineer`** | `COMPLETED IN /plan` | Designed Track 10A (`senior-dev-flutter` & `python-backend`) and Track 10B (`senior-data-engineer`, `sql-query-optimizer`, `shared-context`, `multi-agent-ops`) with Mode A Disjoint File Partitioning followed by Fan-In dual-ecosystem synchronization. |

### Parallel Execution Tracks
| Track | Subagent | Isolation Mode | Owned Files |
| :--- | :--- | :--- | :--- |
| **Track 10A** | `code-implementer` #1 | Mode A (`Disjoint Files`, `inherit`) | `skills/flutter-senior-orchestration/SKILL.md`, `plugins/antigravity/senior-dev-flutter/**`, `plugins/antigravity/python-backend/**` |
| **Track 10B** | `code-implementer` #2 | Mode A (`Disjoint Files`, `inherit`) | `plugins/antigravity/senior-data-engineer/**`, `plugins/antigravity/sql-query-optimizer/**`, `plugins/antigravity/shared-context/hooks/*.js`, `plugins/antigravity/multi-agent-ops/rules/multi-agent-ops-rules.md` |
| **Track 10C (Fan-In)** | `code-implementer` | Sequential Fan-In | `scripts/sync_plugin_skills.py`, `scripts/sync_agents.py`, `plugins/claude/**`, `tests/**` |

### Phase Checklist
- [x] **Phase 1 (Track 10A)**: Upgrade `senior-dev-flutter` (`flutter-feature-orchestrator.md`, `skills/flutter-senior-orchestration/SKILL.md`, `flutter-rules.md`, `flutter-pre-tool-gate.js`, `README.md`) and `python-backend` (`python-backend-rules.md`, `pre-tool-gate.js`, `README.md`) with `context/memory/` LLM Wiki, Mandatory Triage Gates, and Parallel Fan-Out/Fan-In (`Disjoint Files` vs `Git Worktree`).
- [x] **Phase 2 (Track 10B)**: Upgrade `senior-data-engineer`, `sql-query-optimizer`, `shared-context/hooks/*.js` (silent `context/memory/MEMORY.md` support + zero 25-call mid-turn nagging when `MEMORY.md` is active), and `multi-agent-ops/rules/multi-agent-ops-rules.md`.
- [x] **Phase 3 (Track 10C — Fan-In & Dual-Host Sync)**: Update `scripts/sync_plugin_skills.py` and `scripts/sync_agents.py`, synchronize all `plugins/antigravity/` and `plugins/claude/` plugins, and add automated unit & structural tests.
- [x] **Phase 4 (State 3 & 4 Parallel Verification)**: Run `qa-tester` (`pytest -v tests/` -> `103 passed`, `exit code 0`; `node --check` -> `34/34 passed`) and `compliance-verifier` (`APPROVED` audit) in parallel.
- [x] **Phase 5 (State 5 Ship, README Sync & Git Push)**: Update root `README.md`, `skills/README.md`, `shared-context/README.md`, and `multi-agent-ops/README.md`, update `context/memory/`, commit with Conventional Commits, and push to `origin feature/unified-agent-governance-and-plugins`.

---

## Track 11: `agent-meter` — Token, Cost & Latency Metrics for AI Coding Agents (Claude Code + Antigravity CLI/IDE) (COMPLETED — v0.1, see Phase 5/6 notes)

### Goal
Give a freelance developer per-project visibility into what their AI agents cost and how they perform, across **both hosts** (the same project can be worked on with Antigravity today and Claude Code tomorrow), at **$0 cost**, with two delivery options built on one core:

| Option | Audience | Storage | Visualization | Cost |
| :--- | :--- | :--- | :--- | :--- |
| **A — Local** (always on) | Any developer, no cloud account | DuckDB file `~/.agent-meter/meter.duckdb` | Session-end console summary + static HTML report (`agent-meter report`) | $0, zero servers |
| **B — Cloud** (opt-in, on top of A) | Developers with a GCP project | A + BigQuery dataset `agent_metrics` | Looker Studio dashboard (traceability drill-down) | $0 within BigQuery free tier (load jobs only) |

**Core principle**: both hosts already write transcripts to disk in real time, so data is never lost on crash or unclean exit. `agent-meter` is an **idempotent, incremental collector** over those files; the local store is the source of truth and BigQuery is a replica.

**Opt-in & decoupled (inviolable for this track)**:
- `agent-meter` is an **optional add-on**. No existing plugin (`senior-dev`, `senior-dev-flutter`, `python-backend`, `shared-context`, …) or canonical skill gains a dependency on it, references it, or changes behavior. Users who keep installing the current plugins/skills see zero difference.
- It works **standalone, without any plugin from this repo**: install the CLI, run the setup wizard, done. The `agent-metrics` plugin is just one optional convenience channel for marketplace users.
- Option B is opt-in on top of Option A; Option A never requires a cloud account, `gcloud`, or network access.
- Everything it installs (hooks, scheduler, config) is reversible with `agent-meter uninstall`; collected data is kept unless `--purge`.

### Evidence Gathered (2026-10-16, local machine)
| Fact | Claude Code | Antigravity CLI |
| :--- | :--- | :--- |
| Transcript source | `~/.claude/projects/*/*.jsonl` (+ `*/subagents/*.jsonl`) | `~/.gemini/antigravity-cli/brain/<id>/.system_generated/logs/transcript_full.jsonl` (+ `chunks/`) |
| Token fields | `message.usage`: `input_tokens`, `output_tokens`, `cache_creation_input_tokens` (5m/1h split), `cache_read_input_tokens` | `input_tokens`, `cache_read_tokens`, `output_tokens` on `PLANNER_RESPONSE` steps |
| Timing | `system/turn_duration.durationMs` (not emitted in every session → fallback to timestamps) | `created_at` per step (turn duration derived) |
| Project attribution | `cwd`, `gitBranch` on every line | `conversation_summaries.db` → `workspace_uris` |
| Model | `message.model` | Not in the transcript, but **present per LLM call in `conversations/<id>.db` → `gen_metadata.data`** (protobuf): field `1.19` = model id (e.g. `gemini-3.6-flash`), `1.21` = display name, `1.20` key/values incl. `last_step_index`, `used_claude`. Antigravity can run Gemini **and** Claude models, so pricing must cover both |
| `gen_metadata` usage mapping (**verified 2026-10-16**) | — | `1.4.2` = input, `1.4.5` = cache read, `1.4.3` = output; call belongs to step `last_step_index + 1`. Cross-checked against CLI transcripts: **2,244 / 2,244 calls matched, 0 mismatches** (40 conversations). Candidate per-call latency in `1.11` (seconds + nanos; p50 1.9 s / p95 3.6 s on IDE data) — semantics to confirm. Undocumented internal format → guarded by contract tests and `doctor` |
| **Antigravity IDE** (`~/.gemini/antigravity/`) | — | Same layout as the CLI (`brain/`, `conversations/`), but its `transcript_full.jsonl` has **no token fields** → tokens + model come only from `conversations/<id>.db` `gen_metadata` (12 `.db`, Jul 2026: 366 calls, 2.66M input / 23.5M cache read / 0.37M output, all `gemini-3.6-flash`). 100 older conversations are opaque `.pb` files (May–Jun 2026) — format unknown, best effort. No session-exit hook known → IDE relies on the scheduler |
| Timestamp precision | ISO-8601 with sub-second precision | `created_at` to the **second** (fine for P50/P95 in seconds/minutes, not for sub-second latency) |
| Dedup key | `requestId` — naive line summing overcounts **~1.8x** | `conversation_id + step_index` |
| Observed volume | 11,068 requests; P50 turn 35 s, P95 ~16 min | 418 conversations, 25,009 LLM calls |
| Prompt → subagent linkage | Each subagent has `<session>/subagents/agent-<id>.jsonl` whose lines carry the parent `promptId`, plus `agent-<id>.meta.json` with `agentType`, `description`, `toolUseId` (the parent's `Agent` call), `spawnDepth` | Subagents are child conversations: `conversation_summaries.parent_conversation_id`, `agent_name`, `nesting_depth`; parent `brain/<id>/.system_generated/subagents/*.json` has `conversationId` + `spawnStepIndex` (the parent step that spawned it) |
| Example rollup (real data) | One prompt in `flutter-ai`: 315 LLM calls, 2× `flutter-implementer` + 1× `flutter-reviewer`; implementers = 92% of calls. Wall-clock 770 min because it includes idle/wait time → **active time must be measured separately from wall-clock** | 407 of 791 conversations are subagents (`code-implementer` 130, `qa-tester` 67, `compliance-verifier` 66, `architect-engineer` 21, `product-analyst` 11). Real full-DAG task (one `USER_INPUT`): 36.7 min wall-clock, main 28 calls + `product-analyst` 12 + `architect-engineer` 8 + 2× `code-implementer` 69 + `qa-tester` 15 + `compliance-verifier` 7; 53/53 children resolved to a parent task via `spawnStepIndex`, all with their own transcript |

### Metrics Catalog (v1)
| Metric | Definition | Why it matters for a freelancer |
| :--- | :--- | :--- |
| Equivalent cost (USD) | Σ tokens-by-type × versioned price for the model at call date | Billing, margins, plan choice (subscription users see API-equivalent value) |
| Tokens by type | input / output / cache write / cache read | Cost drivers; raw totals are misleading because cache reads dominate |
| Cache hit ratio | `cache_read / (input + cache_read + cache_write)` | Falling ratio = paying more for the same work |
| Context size per call | `input + cache_read + cache_write` | Context bloat drives per-step cost |
| Turn latency P50 / P95 / P99 | Distribution of turn durations | Normal experience vs stuck/looping tasks |
| Session duration & active time | First→last event; Σ turn durations | Agent-hours vs billed hours |
| Calls & output tokens per turn | Per-turn averages | Agent verbosity / loop detection |
| Subagent share | % of cost from sidechain/subagent calls | Cost of multi-agent DAG fan-out |
| Error rate | Errored steps / API errors per session | Reliability per host and project |
| Cost by project / client / host / model / day | Rollups | The core freelance view |
| Agent cost vs billable value | Per client/project/month: AI equivalent cost ÷ (hourly rate × developer hours); developer hours default to session wall-clock and can be corrected with `agent-meter hours set` | "AI cost was 4% of what I billed client Z this month" |
| Cost per client | Σ cost of the client's projects (from `projects.yaml`), shown in USD and the rate's currency (fixed exchange rate in config, e.g. COP) | Monthly invoice support |
| **Task rollup** (per user prompt, incl. all subagents) | Wall-clock, active time, cost, tokens, calls, # subagents by type, max spawn depth | "This plan execution took 13 min, cost $X, ran 4 subagents and did Y" |
| Agent-time vs wall-clock (parallelism factor) | Σ agent active time ÷ task wall-clock | Measures how much parallel fan-out actually saved |
| Critical path | Longest sequential chain of agent runs in the task | What to optimize to make tasks faster |
| Cost share by agent type | % of task cost per `agentType` / `agent_name` | e.g. implementers vs QA vs compliance; which subagent is expensive |
| Retry / loop count | Repeated runs of the same agent type within a task (e.g. `code-implementer` after a failed `qa-tester`) | Cost of the DAG's self-correction loops (max 3) |
| Work done | Tool-call counts by tool name, files edited/created (count), errors | "What it did", without storing any content |

### Functional Scenarios (acceptance)
1. Work on project **X** with Antigravity → exit → console + macOS notification shows: session tokens, cache %, equivalent cost, P50/P95, **today and month-to-date for X across both hosts**.
2. Next day, work on **X** with Claude Code → exit → same summary; X's totals now combine both hosts.
3. Leave a session open or kill the terminal → the scheduler (every 15 min) ingests it; nothing lost, nothing double-counted.
4. Work on project **Y** → appears as a separate project in the report and dashboard.
5. Option A: `agent-meter report --open` renders an offline HTML report (by project, host, day; latency percentiles; cache efficiency).
6. Option B: Looker Studio shows **the same totals as the local report** (zero discrepancy), with drill-down project → session → task → agent run → call.
7. **Per-task rollup**: one prompt (e.g. "execute the plan") that fans out to N subagents in parallel → when it finishes (and in `agent-meter tasks --last`), show: wall-clock vs active time, total cost, cost/tokens per subagent type, # subagents and max depth, parallelism factor, retries, tool-call counts and files touched. Example:
   ```
   [agent-meter] proyecto-x · Claude Code · tarea "ejecuta el plan" · 13m 02s (activo 11m 40s)
     Costo ≈ $4.10 · 6 agentes (máx. profundidad 1) · paralelismo 2.7x · 1 reintento qa→impl
     main                 $0.40   9 llamadas
     code-implementer ×2  $2.90  188 llamadas · 41 Edit · 12 Write · 7 archivos
     qa-tester            $0.50   22 llamadas · pytest ✓
     compliance-verifier  $0.30   14 llamadas
   ```
8. Optional grouping above tasks: a **work item** = several prompts (e.g. "execute plan" + "continue") grouped by an explicit tag (`agent-meter tag "Track 11"`) or a `PLAN.md` track; v1 supports explicit tags only.
9. **Standalone install, no plugins**: a developer who uses none of this repo's plugins runs `uv tool install agent-meter` (or `pipx`) → `agent-meter setup` → chooses Local → metrics start flowing for both hosts. Their existing hooks (e.g. `rtk-hook-gemini.sh` in `~/.gemini/settings.json`) keep working untouched.
10. **Guided cloud setup**: the same developer later runs `agent-meter setup --cloud`; the wizard checks prerequisites, tells them exactly what is missing and how to fix it, creates the BigQuery resources, backfills history and prints the Looker Studio link. Running it again is safe (idempotent).
11. **Clean removal**: `agent-meter uninstall` removes only what it added (hooks, scheduler), restores settings from its backup, and leaves the hosts exactly as before.

### Proposed Architecture (to be ratified by `architect-engineer` ADR in State 1)
```
transcripts (both hosts) ──► readers (adapter per host) ──► canonical schema v1
                                                              │
                         project resolver (git root / origin remote + projects.yaml)
                                                              │
                         pricing (pricing.yaml, effective_from) ─┤
                                                              ▼
               local store: DuckDB (idempotent upsert by natural key, per-file offsets)
                 │                    │                               │
     session summary (hook)   HTML report (Option A)     outbox NDJSON ──► BigQuery load job (Option B)
```
- **Triggers**: (1) session-end hook per host → ingests that session only, prints summary, never blocks the host (always exit 0, hard timeout); (2) `launchd` user agent every 15 min (Linux: systemd user timer / cron fallback) → full incremental ingest + optional BigQuery sync; (3) manual `agent-meter collect | sync | report`.
- **Concurrency**: hook and scheduler can overlap → exclusive file lock (`~/.agent-meter/lock`); the hook skips ingestion if the lock is held > 3 s and reports from the current store.
- **Partial lines**: a line being written (no trailing newline / invalid JSON) is not committed and the offset does not advance past it.
- **Zero token overhead**: hooks never write to the agent's context (no SessionStart stdout injection); display goes to stderr/notification and `~/.agent-meter/last-summary.txt` (`agent-meter last`).
- **Privacy**: only numeric/metadata fields are stored — never prompts, code, tool inputs or outputs. Transcripts are opened read-only. Optional `anonymize_projects = true` hashes project names before upload to BigQuery.

#### Canonical schema v1 (local DuckDB and BigQuery share it)
Hierarchy: **project → session → task (one user prompt) → agent run (main thread or subagent, recursive) → LLM call / tool use**.
- `llm_calls(call_id PK, host, project_id, session_id, task_id, agent_run_id, ts, model, model_inferred BOOL, input_tokens, output_tokens, cache_write_tokens, cache_read_tokens, is_error, schema_version, ingested_at)`
- `tasks(task_id PK, host, project_id, session_id, started_at, ended_at, wall_clock_ms, active_ms, duration_source ENUM('reported','derived'), agent_runs, max_spawn_depth, work_item_tag NULL)` — Claude Code: `promptId`; Antigravity: the `USER_INPUT` step and every step until the next one. A task is what the latency metrics call a "turn".
- `agent_runs(agent_run_id PK, task_id, parent_agent_run_id NULL, host, agent_type, description_hash, spawn_depth, started_at, ended_at, active_ms, status)` — main thread is a run with `spawn_depth = 0`. Claude Code: `agentId` + `meta.json` (`agentType`, `toolUseId`, `spawnDepth`); Antigravity: child conversation (`agent_name`, `parent_conversation_id`, `spawnStepIndex` → parent task). The subagent `description` is free text and may contain client info → stored only as a hash unless `store_agent_descriptions = true`.
- `tool_uses(agent_run_id, tool_name, calls, errors, files_touched)` — aggregated counts only; never tool inputs, outputs or file paths.
- **Active time**: union of intervals where an agent run is producing LLM calls or tool executions; gaps longer than an idle threshold (default 120 s, e.g. waiting for a permission prompt or for the user) count toward wall-clock but not active time. Parallel runs overlap → parallelism factor = Σ `agent_runs.active_ms` ÷ `tasks.active_ms`.
- `sessions` (view): per-session rollups incl. duration, active time, cost, P50/P95 of task duration.
- `task_rollup` (view): per task — cost, tokens, calls, cost share by `agent_type`, parallelism factor, critical path, retry count (repeated `agent_type` runs within the task), tool counts.
- `pricing(model, effective_from, input, output, cache_write_5m, cache_write_1h, cache_read, source_url)` — prices per MTok, filled from official pricing pages at implementation time (never from memory). Unknown model → cost `NULL` + flagged `unpriced`, never silently `0`. Antigravity model is configurable per host (`default_model`) and marked `model_inferred = true` until the spike resolves it.
- `projects(project_id, display_name, client, hourly_rate, rate_currency, billing_model ENUM('hourly','fixed'), fixed_price NULL, repo_root, remote_url)` — sourced from `projects.yaml`; `config.toml` holds `[currency] display = "COP", usd_rate = <fixed>`.
- `dev_hours(project_id, date, hours, source ENUM('session_wall_clock','manual'))` — denominator for cost-vs-billable metrics.
- Host values: `claude-code`, `antigravity-cli`, `antigravity-ide`.

#### Configurable pricing (decided 2026-10-16)
- No price is hard-coded. Two layers, merged at load time: shipped `pricing.yaml` (official Anthropic + Google prices with `source_url` and `fetched_at`, seeded from `docs/agent-metrics/pricing-sources.md`) and the user's `~/.agent-meter/pricing.local.yaml` (new models, overrides, aliases) — **local always wins**.
- Each model has one row per price window (`effective_from`); a call is priced with the row valid at its timestamp, so price changes never rewrite past months unless the user edits that window.
- `aliases` map internal/unknown ids (e.g. Antigravity `agy-demo-high`, `gemini-3.8-flash-n`, dated Claude ids) to a priced model, optionally `estimated: true` (shown with `*`).
- **Cost is computed at query time** (tokens × price view), never persisted per call → adding/correcting a price recalculates all history locally and in BigQuery (the merged pricing table is uploaded with each sync so Looker Studio matches).
- CLI: `agent-meter pricing list | unpriced | add | set | alias | remove | validate`; unseen models are still ingested (tokens kept), shown as `≥ $X (N calls unpriced)`, and surfaced by the session summary and `doctor` with the exact `pricing add` command.
- No automatic scraping of pricing pages in v1 (format drift could silently produce wrong prices); shipped prices are refreshed per release.

#### Option B — BigQuery specifics
- Dataset `agent_metrics`: `raw_llm_calls`, `raw_tasks`, `raw_agent_runs`, `raw_tool_uses` partitioned by date and clustered by `project_id, host`; dedup views using `QUALIFY ROW_NUMBER() OVER (PARTITION BY <pk> ORDER BY ingested_at DESC) = 1`; rollup views `v_sessions`, `v_task_rollup`, `v_agent_type_cost`, `v_daily_project_cost`, `v_latency_percentiles`.
- Tasks still running when a sync happens are re-uploaded with a newer `ingested_at` once they finish; the dedup views always expose the latest version.
- Pipeline uses **batch load jobs only** (no streaming inserts, no DML) so it works in both modes:
  - `mode = "billing"` (recommended): billing enabled, stays in free tier; append-only loads; documented $1 budget alert.
  - `mode = "sandbox"`: no card; tables expire after 60 days → weekly `sync --full-reload` (`WRITE_TRUNCATE` from the local store, which retains full history).
  - Free-tier limits and sandbox restrictions must be re-verified against current GCP docs during State 1.
- Auth via Application Default Credentials (`gcloud auth application-default login`); config in `~/.agent-meter/config.toml` (`[sinks.bigquery] enabled, project, dataset, location, mode`).
- **This developer's target (decided 2026-10-16)**: GCP project **`devhack-3f0c2`** (the `dev` alias in `webpage-devhack/.firebaserc`, keeping metrics out of the production `devhack-web` project), `mode = "billing"` with a **$1 budget alert**, dataset `agent_metrics` (production) and ephemeral `agent_metrics_test_<run_id>` datasets for automated cloud tests. Prerequisites to confirm in State 1: billing is linked to `devhack-3f0c2`, the ADC account has `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` on it (local `gcloud` token was expired on 2026-10-16 and the active configuration points at a different project, so the wizard must select the project explicitly, never rely on the gcloud default).
- Looker Studio: documented data-source setup + 5 pages (Overview, Traceability, **Tasks & Agents** — per-task timeline/Gantt of agent runs and cost by agent type, Performance, Efficiency) in `docs/agent-metrics/looker-studio.md`.

#### Installation channels & setup wizard (opt-in)
| Channel | For whom | What it does |
| :--- | :--- | :--- |
| **1. Standalone CLI** (primary) | Anyone, with or without this repo's plugins | `uv tool install` / `pipx install` the `agent-meter` package → `agent-meter setup` registers hooks directly in the hosts' user settings (with consent) and/or the scheduler |
| **2. Optional `agent-metrics` plugin** | Marketplace users who prefer plugins | Ships the session/task-end hooks + a setup skill; the hooks are thin wrappers that no-op (exit 0, one-line hint) if the CLI is not installed. Not bundled into or required by any other plugin |
| **3. No hooks at all** | Users who do not want any host hook | Scheduler only (every 15 min) or manual `agent-meter collect`; summaries via `agent-meter last` / `agent-meter tasks --last` |

**`agent-meter setup`** (interactive, re-runnable, every step idempotent; non-interactive flags for CI/scripts, e.g. `--local --yes`):
1. **Detect** installed hosts (Claude Code `~/.claude/`, Antigravity CLI `~/.gemini/antigravity-cli/`, Antigravity IDE `~/.gemini/antigravity/`) and report how much history exists.
2. **Choose mode**: `Local` (Option A) or `Local + Cloud` (Option B).
3. **Choose triggers**: hooks per host (shows the exact JSON it will add; backs up the settings file; merges without touching existing hooks — never overwrites), scheduler (`launchd` / systemd user timer), or none.
4. **Privacy defaults**: anonymize project names for cloud upload? store subagent descriptions? (default: no / no).
5. **Projects & clients** (runs after step 6 backfill): auto-discover projects from history (across all three hosts), group them into clients, and set display name, client, billing model (hourly / fixed price), rate and currency (e.g. COP with a fixed USD rate) in `projects.yaml`; editable later with `agent-meter projects`.
6. **Backfill**: import existing history now (default yes).
7. **Cloud only — guided prerequisites**, each checked and explained with the exact fix command when missing:
   - `gcloud` installed → link to install docs if not.
   - Application Default Credentials → offers to run `gcloud auth application-default login`.
   - GCP project → list existing projects or create one.
   - Billing linked? → explains `billing` (recommended, $1 budget alert offered) vs `sandbox` (60-day expiry, weekly full reload) and lets the user pick.
   - BigQuery API enabled → offers `gcloud services enable bigquery.googleapis.com`.
   - Create dataset (location choice), tables and views from `sql/bigquery/*.sql`; test load; verify row counts match the local store.
   - Looker Studio: print a one-click link that copies the template report bound to the user's dataset (Linking API, to be verified in the spike), plus manual fallback steps.
8. **Summary** of what was configured + `agent-meter doctor` result.

Supporting commands: `agent-meter doctor` (health check: hooks registered and firing, scheduler loaded, last ingest time, cloud auth/quota, lag between local and BigQuery), `agent-meter config` (show/edit), `agent-meter uninstall [--purge]`.

#### Proposed repository layout
| Path | Contents |
| :--- | :--- |
| `tools/agent-meter/` | **Self-contained, independently installable** Python package (`pyproject.toml`, `src/agent_meter/`): `readers/{claude_code,antigravity_cli}.py`, `model.py`, `project_resolver.py`, `pricing.py` + `pricing.yaml`, `store.py`, `summary.py`, `report/`, `sinks/bigquery.py` (extra `[bigquery]`, so Option A installs without Google libraries), `scheduler/`, `setup/` (wizard, host-settings merger with backup/restore, GCP prerequisite checks), `cli.py`, `sql/bigquery/*.sql`. Imports nothing from `plugins/`, `skills/` or `scripts/` |
| `plugins/claude/agent-metrics/` (optional) | `.claude-plugin/plugin.json`, `hooks.json` (`SessionEnd`, `Stop`), `hooks/session-end-meter.js` (thin wrapper → `agent-meter hook --host claude-code`; no-op if CLI absent), `README.md`, bundled setup skill |
| `plugins/antigravity/agent-metrics/` (optional) | `plugin.json`, `hooks.json` (event confirmed by spike), `hooks/session-end-meter.js`, `README.md`, bundled setup skill |
| `skills/agent-metrics/SKILL.md` | Canonical skill: guides the user through `agent-meter setup` (runs the CLI, explains each prompt), interprets metrics, ad-hoc DuckDB/BigQuery queries. **Bundled only into the `agent-metrics` plugin** — `scripts/sync_plugin_skills.py` must not add it to any other plugin |
| `docs/agent-metrics/` | `README.md` (A and B setup), `looker-studio.md`, `ADR-001-agent-meter.md` |
| `tests/unit/agent_meter/`, `tests/integration/agent_meter/` | Synthetic sanitized fixtures for both hosts |

### ADR-001 Ratified Deltas (2026-10-16) — supersede the draft sections above where they differ
Normative sources for State 2: `docs/agent-metrics/ADR-001-agent-meter.md`, `docs/agent-metrics/contracts.md` (wins over this plan for signatures, schema and file ownership), `docs/agent-metrics/PRD.md`, `docs/agent-metrics/pricing-sources.md`, `docs/agent-metrics/spike-notes.md` §6.
1. **Hosts/roots**: `claude-code` (`~/.claude/projects/`), `antigravity-cli` (`~/.gemini/antigravity-cli/`), `antigravity-ide` (**`~/.gemini/antigravity-ide/`**, 45 `.db`, 5,573 calls), `antigravity-app` (`~/.gemini/antigravity/`, "Antigravity 2.0"; legacy `.pb` there are encrypted/compressed → reported as untracked). One reader `readers/antigravity.py` (+ `readers/_protowire.py`) serves all three Antigravity roots.
2. **Antigravity canonical usage = `conversations/<id>.db`**: usage/model/latency from `gen_metadata`, step timeline from `steps` (`metadata.1.1` timestamp), transcripts only for tool names and as fallback when no DB exists. The 2.4x gap was coverage (transcripts carry tokens only since 2026-10-02), not phantom calls; tokens match 25,267/25,267 where both exist. Dedup key `(trajectory_id, last_step_index)`; ownership = DB whose `trajectory_meta.trajectory_id` matches; copies (from `parent_references`, continued/forked conversations) dropped; deterministic `owner_rank` keeps orphaned copies once. `1.4.3` = total output incl. thinking (`1.4.9` thinking + `1.4.10` visible); `1.11` = call latency; `1.12` not exposed.
3. **Claude Code**: dedup per `requestId` keeps the line with **max output tokens** (first-line would undercount output by 15.6%); 83 requests are copied across files (resume/fork) → global dedup. Task = `promptId` resolved via `parentUuid` chain; subagent run belongs to the prompt that spawned it; nesting via `parentAgentId`.
4. **Triggers**: Antigravity has no session-end event — `Stop` fires per task (payload `conversationId`, `workspacePaths`, `transcriptPath`, `terminationReason`, `fullyIdle`), user-level file `~/.gemini/config/hooks.json` (named-hook format), stdout must be exactly `{}`; `~/.gemini/settings.json` belongs to Gemini CLI and is never edited. Claude Code: `Stop` per task + `SessionEnd`, stdout empty. Notification policy prevents per-task spam.
5. **Reading model**: per-session "unit fingerprints" with full re-parse of a changed unit (replaces per-file offsets; ST-02/ST-03 reworded accordingly, RD-02 still holds).
6. **Schema v1** per contracts §4: no cost column anywhere (cost only in `v_calls` view); cache-write 5m/1h split, `thinking_tokens`, `latency_ms`, `speed`, `inference_geo`, `owner_rank`, `row_hash`, `ingest_seq`; tables `sessions`, `tag_history`, `task_tags`, `dev_hours_manual`/`dev_hours_derived`, `untracked`, `path_map` (hashes only), `source_units`, `format_versions`, `diagnostics`, `settings`; **no clear-text paths stored**.
7. **Pricing**: configurable design ratified; price windows + prompt-size tiers, priced on the call's local date. Additional observed ids needing alias/price: `claude-opus-4-6-thinking`, `gemini-3-flash-a`/`-b`, `gemini-3-flash-medium-a`, `gemini-3.7-flash*` (unpriced until aliased).
8. **BigQuery**: no `require_partition_filter` (breaks dedup views/Looker) → monthly partitions + dry-run byte ceiling (BQ-09 reworded); logical outbox = rows past an `ingest_seq` watermark serialized to NDJSON at sync time.
9. **Privacy**: task labels only in interactive terminal output — never in `last-summary.txt`, notifications or reports. agent-meter never reads `cli.log` (contains prompt text).
10. **Layout/deps**: tests live in `tools/agent-meter/tests/` (unit, contract, integration, cloud); `sql/` is package data under `src/agent_meter/sql/`; extra modules `timeline`, `collector`, `locking`, `paths`, `config`, `notify`, `hook`, `readers/_protowire`, `sinks/outbox`. Runtime deps: `duckdb`, `PyYAML`; Python ≥ 3.11 (use `uv`); `google-cloud-bigquery` only in extra `[bigquery]`. Repo-level `tests/structure/` keeps the decoupling tests (DC-01/02/04).
11. **Baselines**: L5 Antigravity reconciliation compares DB vs transcript only for dates ≥ 2026-10-02; Claude `ccusage` output-token differences are reported, not failed (ADR §7).
12. **Out-of-track bug found (Track 12, pending user approval)**: every `plugins/antigravity/*/hooks.json` has a top-level `"description"` string that Antigravity rejects ("cannot unmarshal string … JSONHookSpec", logged >1,900 times) → none of those plugins' hooks run in Antigravity; same for the installed `~/.gemini/config/plugins/shared-context/hooks.json`. The new `agent-metrics` Antigravity `hooks.json` must not have that key. Also to verify in Track 12 (found by 11E): Claude Code plugins load hooks from `hooks/hooks.json` by default, while the existing Claude plugins keep `hooks.json` at the plugin root without a manifest `"hooks"` pointer — their hooks may not load either (`agent-metrics` sets the pointer explicitly). `claude plugin validate` / `agy plugin validate --strict` are the checks to use (`agy` reports `hooks 0` for shared-context today).

### Discovery & Architecture Triage
| Specialist Node | Triage Verdict | Justification |
| :--- | :--- | :--- |
| **`product-analyst`** | `MUST INVOKE` | New user-facing feature with unstated edge cases (open/crashed sessions, cross-host project identity, subscription vs API cost semantics, privacy of client code). Produce PRD from this plan + open questions below. |
| **`architect-engineer`** | `MUST INVOKE` | New package, new data schema (local + BigQuery), new external dependencies (`duckdb`, `google-cloud-bigquery`), new plugin in both ecosystems, crosses hooks/scheduler/cloud layers. Deliver `ADR-001-agent-meter.md`, ratify schema v1 and layout, and run the **Antigravity spike** (below). |

Discovery runs **sequentially** (`product-analyst` → `architect-engineer`) because the ADR depends on the PRD's answers to the open questions.

#### State 1 spike (architect-engineer, read-only investigation)
- [ ] Antigravity CLI: which hook event fires on session exit, and its stdin payload (conversation id, workspace path?).
- [x] Antigravity: model + tokens per call decoded from `gen_metadata` (verified 2026-10-16, 2,244/2,244 matches); keep the `default_model` fallback if a call cannot be mapped.
- [ ] Antigravity: confirm `1.11` / `1.12` duration semantics (total generation latency vs time-to-first-token) and `1.4.9` / `1.4.10` (thinking tokens?) before exposing them.
- [ ] Antigravity IDE: legacy `.pb` conversations — determine if usage is recoverable; if not, report them as "untracked history" in `doctor` and the report.
- [ ] Antigravity IDE: any hook/extension point for a session-end summary; otherwise scheduler + macOS notification when a conversation goes idle.
- [x] Confirm `brain/<id>` == `conversation_summaries.conversation_id` (verified 2026-10-16: parent and all 53 children resolved).
- [ ] Claude Code: confirm `SessionEnd` payload (`session_id`, `transcript_path`, `cwd`, `reason`) and which output channel is visible to the user after exit.
- [ ] Re-verify BigQuery free tier & sandbox limits and Looker Studio connector behavior.
- [ ] Claude Code task segmentation: confirm which main-thread lines carry `promptId` and how to assign assistant lines in between (`parentUuid` chain vs. propagation); confirm `promptId` on nested subagents (`spawnDepth >= 2`).
- [x] Antigravity task segmentation: `spawnStepIndex` maps each child to the parent `USER_INPUT` range (verified on real data).
- [ ] Antigravity double counting: children's token steps live in their own `brain/<child-id>/` transcript and the parent range showed only its own 28 calls — confirm the parent never repeats child usage.
- [ ] Standalone hook registration without a plugin: Claude Code `~/.claude/settings.json` `hooks` merge; Antigravity CLI — which file registers user-level hooks (`~/.gemini/antigravity-cli/settings.json` vs `~/.gemini/settings.json`) and which events exist; fallback to scheduler-only if none.
- [ ] `devhack-3f0c2`: billing linked, BigQuery API enabled, ADC account IAM (`bigquery.dataEditor`, `bigquery.jobUser`), chosen dataset location; create the $1 budget alert.
- [ ] Looker Studio Linking API: confirm a template report can be copied and bound to the user's BigQuery dataset via URL.
- [ ] Decide the per-task display trigger: Claude Code `Stop` hook (fires at the end of every task, not only session end) vs. `SubagentStop`; Antigravity equivalent.

#### Open questions for the user
1. ~~GCP project to use for Option B, and `billing` vs `sandbox` mode.~~ **Resolved 2026-10-16**: `devhack-3f0c2`, `billing` + $1 budget alert.
2. ~~Track Antigravity IDE in v1?~~ **Resolved 2026-10-16: yes** — `.db` conversations fully supported (tokens/model via `gen_metadata`); legacy `.pb` conversations best effort.
3. ~~Client + hourly rate in `projects.yaml`?~~ **Resolved 2026-10-16: yes** — adds cost-per-client and cost-vs-billable metrics.
4. ~~Distribution?~~ **Resolved 2026-10-16**: v0.x installs from this repo (`uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"` or `pipx`); publish to PyPI as `agent-meter` at v1 (after Milestone A), automatable via GitHub Actions. Package metadata must be PyPI-ready from day one.

#### PRD open questions — defaults adopted by the orchestrator (2026-10-16, reversible)
- OQ-1: developer hours default = session wall-clock **minus gaps > 30 min between tasks**; manual `hours set` overrides.
- OQ-2: v1 shows **API-equivalent cost only** (no subscription amortization).
- OQ-3: no rate history in v1 (current rate applies to all periods; documented).
- OQ-4: per-task label = truncated prompt shown **only in the live local summary, never persisted or uploaded**, opt-out via config; test-status inference (`pytest ✓`) is a Should (exit status + command name only).
- PRD BR-19 accepted: uninstall restores byte-for-byte only if the settings file is unchanged since setup; otherwise removes only agent-meter's own entries.

### Parallel Execution Tracks (Mode A — Disjoint Files; **Owned Files are exactly `contracts.md` §1**, the paths below are the original draft)
| Track | Subagent | Owned Files | Depends on |
| :--- | :--- | :--- | :--- |
| **11A — Readers & Domain** | `code-implementer` #1 | `tools/agent-meter/src/agent_meter/{readers/{claude_code,antigravity_cli,antigravity_ide,antigravity_pb}.py,model.py,project_resolver.py,pricing.py,pricing.yaml}`, `tests/unit/agent_meter/test_readers*.py`, `test_project_resolver.py`, `test_pricing.py`, fixtures | ADR schema v1 |
| **11B — Store, CLI, Summary, Scheduler & Setup Wizard** | `code-implementer` #2 | `tools/agent-meter/src/agent_meter/{store.py,summary.py,cli.py,scheduler/,setup/}`, `tools/agent-meter/pyproject.toml`, `tests/unit/agent_meter/test_store.py`, `test_summary.py`, `test_cli.py`, `test_scheduler.py`, `test_setup_*.py` | ADR schema v1 (codes against model interfaces) |
| **11C — HTML Report (Option A)** | `code-implementer` #3 | `tools/agent-meter/src/agent_meter/report/`, `tests/unit/agent_meter/test_report.py` | Store view contract from ADR |
| **11D — BigQuery Sink & Looker (Option B)** | `code-implementer` #4 | `tools/agent-meter/src/agent_meter/sinks/`, `tools/agent-meter/sql/bigquery/`, `docs/agent-metrics/looker-studio.md`, `tests/unit/agent_meter/test_bigquery_sink.py` (mocked client) | Schema v1 |
| **11E — Fan-In: Plugins, Skill & Sync** | `code-implementer` (sequential) | `plugins/{claude,antigravity}/agent-metrics/**`, `skills/agent-metrics/**`, `.claude-plugin/marketplace.json`, `docs/agent-metrics/README.md`, `tests/integration/agent_meter/`, `tests/structure/` additions | 11A–11D merged |

Delivery order: **Milestone A** (11A + 11B + 11C + 11E without the BigQuery sink) ships first and is usable on its own; **Milestone B** (11D + 11E BigQuery wiring) follows.

### Test Plan

#### Strategy & levels
| Level | Scope | Runner / marker | Runs | Network |
| :--- | :--- | :--- | :--- | :--- |
| **L1 Unit** | Readers, resolver, pricing, store, task rollup, summary, setup merger, sink request builders | `pytest tests/unit/agent_meter` | Every change (TDD) | Blocked (socket guard fixture) |
| **L2 Contract** | One fixture set per host **format version** (Claude Code `version`, Antigravity CLI build); a new host version without a fixture fails loudly in `doctor`, not silently | `pytest -m contract` | Every change | Blocked |
| **L3 Integration (local)** | Full CLI flows in a temp `HOME` + temp `AGENT_METER_HOME`: setup → hook → collect → summary → report → uninstall | `pytest tests/integration/agent_meter` | Every change | Blocked |
| **L4 Cloud integration** | Real BigQuery in `devhack-3f0c2`, ephemeral dataset `agent_metrics_test_<run_id>` (default table expiration 1 day as safety net, deleted in teardown) | `pytest -m bigquery` with `AGENT_METER_TEST_GCP_PROJECT=devhack-3f0c2` | Before Milestone B ship and on sink/SQL changes | Allowed (BigQuery only) |
| **L5 Reconciliation (real data, read-only)** | Totals from the developer's real transcripts vs independent sources | `agent-meter verify --reconcile` + `pytest -m e2e` | Before each milestone ship | Optional |
| **L6 E2E acceptance** | Functional scenarios 1–11 with the real hosts (Claude Code + Antigravity CLI) on a scratch project | Scripted checklist in `docs/agent-metrics/acceptance.md` | Before each milestone ship | Allowed |
| **L7 Non-functional** | Performance, resilience, privacy, security | `pytest -m perf` / `-m privacy` + manual | Before each milestone ship | Mixed |
| **L8 Regression & structure** | Existing suite (`pytest tests/`, currently 103), `node --check` on all hooks, JSON validation, decoupling invariants | Repo runbooks §4.1–4.3 | Every change | Blocked |

Default `pytest` run excludes `bigquery`, `e2e` and `perf` markers so the existing runbook stays offline and fast.

#### Test data & environment rules
- Fixtures are **synthetic**, produced by a fixture builder in `tests/unit/agent_meter/fixtures/` that emits host-shaped JSONL / SQLite; **no real transcript content is ever committed**.
- Every fixture embeds a **canary string** (`AGENT-METER-CANARY-7f3a`) inside prompts, tool inputs/outputs, file paths and subagent descriptions — used by the privacy tests.
- Automated tests never read the real `~/.claude` or `~/.gemini`; only L5/L6 do, read-only, and only when invoked explicitly.
- Times are fixed (frozen clock) and timezone-explicit; day/month boundaries use the developer's local timezone (tests run under `UTC` and `America/Bogota`).

#### Test case catalog
**RD — Readers (both hosts)**
- RD-01 Claude: duplicated `requestId` lines count once (fixture reproduces the observed ~1.8x duplication).
- RD-02 Partial trailing line (no newline / invalid JSON) is not ingested and the offset does not advance; ingested after completion.
- RD-03 Missing `turn_duration` → derived duration with `duration_source = 'derived'`.
- RD-04 Subagent linkage via `promptId` + `meta.json` (`agentType`, `toolUseId`, `spawnDepth`); RD-05 nested subagent (`spawnDepth = 2`) attaches to the correct parent run.
- RD-06 Antigravity: token fields read from `PLANNER_RESPONSE` steps only; RD-07 `spawnStepIndex` maps each child to the parent `USER_INPUT` range.
- RD-08 Antigravity: `transcript_full.jsonl` and `logs/chunks/**` describe the same steps — only one source is read (no double count).
- RD-09 Model unresolved → `model_inferred = true` with configured `default_model`; resolved from `gen_metadata` when available.
- RD-13 Antigravity IDE reader: tokens/model from `gen_metadata`, steps/timestamps from `transcript_full.jsonl`, host = `antigravity-ide`; same project as CLI/Claude when the workspace matches.
- RD-14 **`gen_metadata` contract test**: decoded tokens equal transcript tokens for CLI fixtures (field mapping `1.4.2/1.4.5/1.4.3`, step = `last_step_index + 1`); L5 re-runs this on real data (baseline 2,244/2,244).
- RD-15 Unknown protobuf layout (missing/renamed fields) → tokens `NULL` + `doctor` warning "Antigravity format changed", never `0`, never crash; legacy `.pb` files counted as untracked.
- RD-10 Unknown/new fields are ignored (forward compatibility); RD-11 a corrupt file is skipped with a warning and `doctor` reports it — the run never crashes; RD-12 `<synthetic>` model entries are excluded from cost.

**PR — Project resolution**
- PR-01 Same repo opened from Claude Code (`cwd`) and Antigravity (`workspace_uris` as `file://` URI) → same `project_id`.
- PR-02 SSH and HTTPS `origin` URLs normalize to the same project; PR-03 **git worktrees** (used by the DAG's Mode B) map to their main repo's project.
- PR-04 Non-git directory → path-based fallback id; PR-05 `projects.yaml` overrides display name/client; PR-06 a moved/renamed directory with the same remote keeps the same project.

**PC — Pricing**
- PC-07 `pricing.local.yaml` overrides a shipped price and adds a new model; invalid YAML or negative/missing fields are rejected by `pricing validate` with a clear error and the previous valid table stays in use.
- PC-08 Adding a price for a previously unpriced model recalculates historical cost (local views and BigQuery views after sync) with no re-ingestion.
- PC-09 Alias resolution: alias → model → window; alias chains/cycles rejected; `estimated` propagates to the displayed total.
- PC-06 Cost-vs-billable: hourly and fixed-price projects, manual `dev_hours` override wins over session wall-clock, currency conversion with the configured fixed rate, project without client/rate → metric omitted (not 0%).
- PC-01 Price chosen by `effective_from` at call time (boundary on the exact change date); PC-02 cache write 5 m vs 1 h priced separately; PC-03 unknown model → cost `NULL` + `unpriced` flag (never `0`); PC-04 Gemini and Claude models priced for Antigravity; PC-05 `Decimal` arithmetic, rounding only at presentation.

**ST — Store & idempotency**
- ST-01 Ingesting the same files twice yields identical rows; ST-02 offsets persist across runs; ST-03 truncated/replaced file (inode or size shrink) is re-read safely; ST-04 hook and scheduler running concurrently → lock held by one, the other skips within 3 s, no corruption; ST-05 process killed mid-ingest → transaction rolled back, next run completes; ST-06 schema migration v1 → v2 preserves data.

**TK — Tasks & agent runs**
- TK-01 Task cost = Σ its calls (exact); TK-02 overlapping runs → parallelism factor > 1; TK-03 idle gap > threshold excluded from active time; TK-04 critical path on a known DAG fixture; TK-05 `code-implementer` after failed `qa-tester` counts as 1 retry; TK-06 a task still running at sync time is updated (not duplicated) when it finishes; TK-07 tool counts and files-touched counts match the fixture.

**SM — Summary & HTML report (Option A)**
- SM-01 Session/task summary shows today and month-to-date per project across both hosts; SM-02 day boundary in local timezone; SM-03 report renders with empty store; SM-04 report has **no external network references** (no `http(s)://` assets) and opens offline; SM-05 P50/P95/P99 match a reference calculation on the fixture.

**HK — Hooks**
- HK-01 Always exit 0, even with malformed stdin, missing CLI, locked store or exceptions; HK-02 hard timeout respected; HK-03 **nothing written to stdout** that the host would inject into the agent's context (zero token overhead); HK-04 Antigravity and Claude payload variants handled.

**SU — Setup / uninstall**
- SU-01 Wizard idempotent (second run = no changes); SU-02 settings merge preserves an unrelated pre-existing hook (`BeforeTool` → `rtk-hook-gemini.sh` fixture) and writes a backup; SU-03 `uninstall` restores original settings byte-for-byte; SU-04 `setup --local --yes` performs zero network calls; SU-05 one test per missing cloud prerequisite (no `gcloud`, expired ADC, wrong default project, billing not linked, API disabled, missing IAM role) asserts the exact guidance message and fix command; SU-06 wizard always uses the explicitly chosen project (`devhack-3f0c2`), ignoring the gcloud default project.

**BQ — Cloud sink (Option B)**
- BQ-01 Outbox → load job (NDJSON, `WRITE_APPEND`) built correctly (unit, mocked); BQ-02 dedup views return exactly one row per PK after re-uploads (L4); BQ-03 `--full-reload` uses `WRITE_TRUNCATE`; BQ-04 static check: no `insert_rows`/streaming or DML statements in the sink; BQ-05 upload failure keeps the outbox and retries next cycle; BQ-06 expired credentials → clear message, local collection continues unaffected; BQ-07 offline for N cycles → backlog uploads once on reconnect, no loss/duplicates; BQ-08 **reconciliation**: totals per project/day in BigQuery equal the local store exactly; BQ-09 cost guard: tables use `require_partition_filter`, and views/queries are dry-run checked to stay under a byte budget.

**PV — Privacy & security**
- PV-01 Canary string absent from DuckDB, outbox files, BigQuery test dataset, HTML report and logs; PV-02 project-name anonymization hash is stable and irreversible (salted); PV-03 transcripts opened read-only (mtime/hash unchanged after a run); PV-04 no credentials or tokens written to config, logs or outbox; PV-05 subagent descriptions stored only as hashes unless opted in.

**DC — Decoupling** (L8)
- DC-01 No file outside `tools/agent-meter/`, `plugins/*/agent-metrics/`, `skills/agent-metrics/`, `docs/agent-metrics/` references `agent-meter`/`agent-metrics` (except the marketplace entry); DC-02 `agent-metrics` skill bundled in no other plugin after `sync_plugin_skills.py`; DC-03 `tools/agent-meter` installs and passes L1–L3 in a clean venv without the repo; DC-04 existing plugins' files unchanged (`git diff --stat` scoped check).

**PF — Performance & resilience** (L7, targets to be ratified in ADR)
- PF-01 Full backfill of current history (~11K Claude requests + ~25K Antigravity calls, ~365 MB of transcripts) ≤ 2 min; PF-02 incremental run with no new data ≤ 2 s; PF-03 hook end-to-end P95 ≤ 3 s; PF-04 peak memory ≤ 300 MB; PF-05 scheduler survives reboot (launchd `RunAtLoad`) and sleep/wake.

#### L5 reconciliation (real data)
- Claude Code: per-day token totals vs `npx ccusage` for the same date range — tokens must match exactly after dedup; cost differences only explained by pricing-table differences (documented).
- Antigravity CLI: per-conversation call and token counts vs an independent count over `transcript_full.jsonl` (baseline 2026-10-16: 418 conversations, 25,009 LLM calls, 211.1M input / 2,635.0M cache-read / 15.6M output tokens; compare on a frozen date range since history keeps growing).
- Task rollups: the two real tasks inspected during planning (Claude `flutter-ai` prompt with 2× `flutter-implementer` + 1× `flutter-reviewer`; Antigravity full-DAG task with 6 subagents, 36.7 min) reproduce the same agent counts and per-agent call counts.

#### Traceability (scenario → tests)
| Scenario | Tests |
| :--- | :--- |
| 1–2 Session summary, cross-host project | PR-01..06, SM-01..02, HK-01..04, L6 |
| 3 Crash / open session | RD-02, ST-01..05, PF-05, L6 |
| 4 Separate projects | PR-01..06, SM-01 |
| 5 Local HTML report | SM-03..05, PC-01..05 |
| 6 Looker = local totals | BQ-02, BQ-08, L4, L6 |
| 7 Per-task rollup | RD-04..08, TK-01..07, L5 |
| 8 Work-item tags | ST-01, SM-01 (tag rollup) |
| 9 Standalone install | DC-01..04, SU-01..04 |
| 10 Guided cloud setup | SU-05..06, BQ-01..09, L4 |
| 11 Clean removal | SU-03, PV-03 |

#### Entry / exit criteria
- **Entry (per milestone)**: ADR-001 ratified; fixtures for every supported host format version exist; L4 only after billing + IAM on `devhack-3f0c2` are confirmed.
- **Exit Milestone A**: L1–L3, L7 privacy and L8 green (`exit code 0`); L5 reconciliation within criteria; L6 scenarios 1–5, 7–9, 11 passed and recorded in `docs/agent-metrics/acceptance.md`.
- **Exit Milestone B**: Milestone A criteria + L4 green against `devhack-3f0c2` + BQ-08 exact reconciliation + L6 scenarios 6 and 10 passed; ephemeral test datasets confirmed deleted.
- Any failure loops back to State 2 (max 3 iterations, then escalate to the user).

### Phase Checklist
- [x] **Phase 0 (State 0)**: Restore `context/memory/MEMORY.md`; create branch `feature/agent-metrics` from the current base (done 2026-10-16).
- [x] **Phase 1 (State 1 — Discovery)**: `product-analyst` PRD (`docs/agent-metrics/PRD.md`) → `architect-engineer` ADR-001 + contracts + spike results (`docs/agent-metrics/`); deltas recorded above (done 2026-10-16).
- [x] **Phase 2 (State 2 — Build, Milestone A)**: Tracks 11A, 11B, 11C in parallel (TDD red→green→refactor). 11A **done** 2026-10-16 (241 tests, exit 0). 11B split into 11B-core and 11B-setup (see `docs/agent-metrics/build-notes.md`); 11B-core, 11B-setup, 11C and 11D (Milestone B) launched in parallel. 11C **done** 2026-10-16 (87 tests, exit 0; verified against 11B's real store/views, canary absent, zero external URLs). 11B-setup **done** 2026-10-16 (124 tests; full package suite 660 passed, exit 0). Accepted deviations: wizard runs backfill before project configuration (projects are discovered from imported history); `MergePlan.target`, `PlanStale`, `run_checks(http=, mode=)`; systemd timer uses `OnCalendar=*:0/15` + `Persistent=true`. 11D **done** 2026-10-17 (96 unit tests, exit 0; 6 L4 cloud tests collected and skipped until ADC is valid). Accepted backward-compatible contract additions: `now=` on `materialize`/`sync`, `ensure_dataset(default_table_expiration_days=)`, `reconcile(anonymizer=)`, `BigQueryGateway` protocol instead of a raw client, structural Protocol parameter types, meta key `bq_last_sync_at`, cloud `v_health` with `unknown_formats`/`diagnostics_7d` = NULL. Known limit: local deletions (`--purge`, vanished `tool_uses`) reach BigQuery only on `--full-reload`.
  - Verify: ingesting the same fixtures twice yields identical row counts; duplicated `requestId` lines are counted once; a truncated trailing line is not ingested until complete; missing `turn_duration` falls back to derived durations; unknown model yields `unpriced`, not `0`.
  - Verify (tasks): a fixture prompt with 3 parallel subagents + 1 nested subagent rolls up to exactly one task whose cost equals the sum of its calls; overlapping agent runs give a parallelism factor > 1; an idle gap > threshold is excluded from active time; a repeated `code-implementer` run after `qa-tester` counts as 1 retry; no tool input, output, file path or prompt text appears anywhere in the store.
- [x] **Phase 3 (State 2 — Build, Milestone B)**: Track 11D. 11B-core **done** 2026-10-17; orchestrator re-ran: `tools/agent-meter` `pytest` → 726 passed, 6 deselected, exit 0; `ruff check` clean; `mypy --strict src` 47 files clean; `pytest -m bigquery tests/cloud` → 6 skipped (ADC expired); repo `pytest tests/` → 103 passed, exit 0.
  - Verify: outbox → load-job request built correctly (mocked); dedup views return one row per PK; `--full-reload` uses `WRITE_TRUNCATE`; no streaming/DML calls anywhere in the sink.
- [x] **Phase 4 (State 2 — Fan-In)**: Track 11E done 2026-10-17: repo suite 142 passed (exit 0) incl. 39 new structure/decoupling tests; `agy plugin validate --strict` and `claude plugin validate` pass; canonical slug `jggomez/expert-ai-developer-skills`; `scripts/sync_agents.py` gained the `agent-metrics` description and now preserves extra manifest keys (`hooks`), verified idempotent; DC-04 implemented as per-commit + working-tree checks because `merge-base main` predates two unmerged governance commits; run `python3 scripts/sync_agents.py && python3 scripts/sync_plugin_skills.py`.
  - Verify: hooks pass `node --check`, always exit 0 within timeout even if `agent-meter` is missing; no Claude tool names in Antigravity plugin and vice versa; all JSON valid.
  - Verify (decoupling): structural test asserts no file outside `tools/agent-meter/`, `plugins/*/agent-metrics/`, `skills/agent-metrics/` and `docs/agent-metrics/` references `agent-meter`/`agent-metrics`; `agent-metrics` skill is bundled in no other plugin; `git diff` shows zero changes to existing plugins except the marketplace entry; `tools/agent-meter` installs and its tests pass in a clean venv with no repo checkout dependencies.
  - Verify (setup): wizard is idempotent (second run makes no changes); settings merge preserves pre-existing hooks (fixture with an unrelated `BeforeTool` hook) and creates a backup; `uninstall` restores the original files byte-for-byte; `setup --local --yes` never touches the network; cloud prerequisite checks are tested with mocked `gcloud`/BigQuery responses for each missing-prerequisite case.
- [x] **Phase 5 (States 3 & 4) — closed short at the user's request (2026-10-17)**: compliance audit 1 = REJECTED (H-1 unsafe `--purge`); remediation loop 1 fixed H-1, M-1, M-2(a), L-2, L-3, L-4, L-9 with tests. Real-data demo fixes: Antigravity internal model ids priced as estimated aliases (`pricing unpriced` → "Every call is priced"), moved-folder duplicate projects merged, modern light report redesign (dataviz palette validated). Final gates: `tools/agent-meter` pytest 836 passed + 1 xfailed, ruff + mypy --strict clean; repo `pytest tests/` 144 passed, 1 skipped (DC-03 clean-venv install now opt-in via `AGENT_METER_RUN_DC03=1` — disk-heavy). **Not done (user chose to stop the long process):** compliance re-audit, QA-1/QA-2 reports, L4 BigQuery live tests (ADC expired), interactive acceptance (real hook firing, `setup` on the real machine, Looker), PF-02 perf (incremental collect ≈ 11–14 s vs 2 s target), `ruff format` (L-1). Original Phase 5 plan kept below for reference.
- [ ] ~~**Phase 5 (States 3 & 4 — parallel)**~~: `qa-tester` executes the **Test Plan** (L1–L3 + L8 `pytest -v tests/` exit 0; L4 `pytest -m bigquery` against `devhack-3f0c2`; L5 reconciliation incl. `npx ccusage`; L6 acceptance checklist; L7 perf) — can fan out as parallel `qa-tester` instances per level ‖ `compliance-verifier` (PV-01..05 privacy audit, DC-01..04 decoupling, ADC/secrets handling, OWASP review of the settings merger; `APPROVED` verdict). Max 3 correction loops.
- [ ] **Phase 6 (State 5 — Ship)**: Mark tasks complete, update `context/memory/` (MEMORY.md, architecture.md, daily log), update root `README.md` plugin catalog, Conventional Commit on `feature/agent-metrics`.

### Phase 5 — real-data demo findings & decisions (2026-10-17)
Orchestrator ran the CLI read-only on the developer's real history (throwaway `--home` in the session scratchpad): `collect`, `last`, `tasks --last`, `projects list`, `pricing unpriced`, `report` all work; session summary and 448 KB report produced.
- **Unpriced Antigravity internal model ids** (`agy-demo-high` 6,646 calls, `gemini-3-flash-a`, `gemini-3.7-flash(-control)`, `gemini-default`, `gemini-pro-default`, `agy-demo-medium`, `gemini-3-flash-medium-a`, `gemini-3.8-flash-tiered`, `gemini-3.1-pro-low`, `claude-opus-4-6-thinking`, "no model") → **user decision: price them as estimated aliases of `gemini-3.8-flash`** (Gemini Pro-labelled ids → `gemini-3.1-pro-preview`, Claude-labelled ids → their Claude base model), shown with `*`; `hosts.<antigravity>.default_model = gemini-3.8-flash` (estimated).
- **Bug: duplicate projects** for the same folder name (`agent-ux-ui`, `agente-santory`, `ai-rag-docs` appear twice with different `path:` ids) → cross-host/path normalization defect to root-cause and fix.
- **Perf gap**: no-change incremental `collect` ≈ 14 s on real data vs PF-02 target 2 s → optimize.
- **Report redesign** (user request): modern light-default theme following the dataviz skill (validated palette, KPI tiles, tooltips, table views, dark mode as its own steps).

### Out of Scope (v1)
Guaranteed recovery of legacy Antigravity IDE `.pb` conversations (best effort only), integration with external time trackers/invoicing tools (manual `dev_hours` in v1), Windows scheduler, real-time streaming, multi-developer/team aggregation, OpenTelemetry export, cost-per-commit attribution (candidate for v2: join `git log` within session windows).
