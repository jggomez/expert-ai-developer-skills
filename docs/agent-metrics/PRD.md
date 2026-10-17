# PRD: `agent-meter` — Token, Cost & Latency Metrics for AI Coding Agents

| Field | Value |
| :--- | :--- |
| Status | Draft v1, for `architect-engineer` (ADR-001) and Track 11 implementers |
| Source of scope | `PLAN.md` § Track 11 (user decisions recorded 2026-10-16). That section wins if this PRD conflicts with it. |
| Hosts | Claude Code (`claude-code`), Antigravity CLI (`antigravity-cli`), Antigravity IDE (`antigravity-ide`) |
| Milestones | **A**: Local (DuckDB, console summary, HTML report). **B**: Cloud (BigQuery `devhack-3f0c2`, Looker Studio) |

## 1. Problem

A freelance developer runs AI coding agents (often multi-subagent DAGs) across three hosts on several client projects. Today they can't answer:
- How many tokens did project X use this month, and what would that cost at API prices, across all hosts?
- How long do tasks take (P50/P95), and how much of that is the agent working versus waiting?
- For a single prompt that fans out to subagents, which agents cost the most, and did parallel fan-out actually save time?
- What share of what I bill client Z is AI cost?

Each host writes transcripts to disk, but in different, partly undocumented formats. Naively adding up Claude Code transcript lines overcounts by about 1.8x. Neither host reports per-project, cross-host or per-client numbers.

## 2. Personas

| Persona | Description | Needs |
| :--- | :--- | :--- |
| **P1 — Freelancer (primary)** | Spanish-speaking developer in Colombia. Uses all three hosts with this repo's DAG plugins. Bills clients hourly or at a fixed price, some in COP. Has the GCP project `devhack-3f0c2`. | Per-project and per-client cost, cost vs billable value, per-task rollups with subagents, a cloud dashboard |
| **P2 — Standalone developer** | Uses Claude Code and/or Antigravity, with **none** of this repo's plugins. May have no cloud account. | Install one CLI, answer a short wizard, see metrics locally. Existing hooks stay untouched. Clean uninstall. |

## 3. Goals and Non-Goals

**Goals**
- G1: Accurate (deduplicated) tokens, API-equivalent cost, latency and active time for each project, across all three hosts.
- G2: A per-task rollup that includes every subagent, nested ones too.
- G3: Client-level economics: cost per client, and AI cost vs billable value.
- G4: $0 to run. Option A works fully offline. Option B stays inside the BigQuery free tier.
- G5: Opt-in and fully decoupled. Users who don't install it see zero change, and everything it adds can be reversed.

**Non-Goals (v1)**: team or multi-developer aggregation; Windows scheduler; real-time streaming; OpenTelemetry export; invoicing or time-tracker integrations; cost per commit; guaranteed recovery of legacy IDE `.pb` history; i18n of CLI text (English only; `es` is a candidate for v1.x); storing any prompt, code or tool content.

## 4. Glossary (normative)

| Term | Definition |
| :--- | :--- |
| **Project** | One code repository, identified by its normalized git `origin` remote, else its git root path, else its working directory path. Worktrees resolve to their main repository. |
| **Session** | One Claude Code session or one Antigravity top-level conversation (not a subagent conversation). |
| **Task** | One user prompt plus everything it triggers until the next user prompt, including all subagents. The latency metrics call this a "turn". |
| **Agent run** | The main thread (`spawn_depth = 0`) or one subagent execution (recursive, `spawn_depth >= 1`). |
| **Active time** | Union of the intervals where any agent run is producing LLM calls or tool executions. Gaps longer than `idle_threshold` (default 120 s) are excluded. |
| **Wall-clock** | Time from the first event to the last event of a task or session. |
| **Equivalent cost** | Tokens by type × the versioned public API price for that model on the call date. Always labelled "≈" / "API-equivalent". It is **not** what a subscription user actually paid. |
| **Work item** | A user-defined group of tasks, created with an explicit tag (`agent-meter tag`). |

## 5. Business Rules (BR)

| ID | Rule |
| :--- | :--- |
| BR-01 | **Cost semantics.** Every cost shown is API-equivalent and labelled `≈`. The HTML report, Looker and `docs` explain that subscription plans (Claude Pro/Max, Gemini plans) are not billed per token. v1 does not model subscription fees (see OQ-2). |
| BR-02 | **Unpriced is never $0.** A call whose model has no price for its date gets cost `NULL` and the flag `unpriced`. Any total that includes unpriced calls is shown as a partial lower bound, e.g. `≥ $4.10 (312 calls unpriced: gemini-x)`. `doctor` lists unpriced models. |
| BR-03 | **Price versioning.** The price applied is the `pricing.yaml` row with the latest `effective_from <= call date`. A correction to `pricing.yaml` must show up in historical costs on the next report and sync (cost is derivable, not frozen). Local and BigQuery totals must stay identical. |
| BR-04 | **Inferred model.** If the Antigravity model can't be resolved from `gen_metadata`, the configured `default_model` is used with `model_inferred = true`. The report flags affected totals with `*`. |
| BR-05 | **Dedup.** Claude Code calls are deduplicated by `requestId`. Antigravity calls are deduplicated by `conversation_id + step_index`, read from exactly one source per conversation. `<synthetic>` model entries are excluded from cost. |
| BR-06 | **Day and month buckets.** Calls are bucketed by **their own timestamp** in the configured timezone (default: system timezone, overridable with `config set timezone America/Bogota`). It is not bucketed by session start. A session that spans midnight or a month end splits its cost across both days or months. Tasks and sessions are counted on their **start** day. |
| BR-07 | **Project identity.** SSH and HTTPS forms of the same remote are one project. Worktrees map to the main repo. A moved directory with the same remote keeps its project. A repo with no remote is keyed by its path; after a move it shows up as a new project until it is merged with `projects merge`. |
| BR-08 | **No-project sessions.** Sessions whose directory is `$HOME`, `/` or a temp directory, or isn't a git repo and isn't listed in `projects.yaml`, go to the bucket `(unassigned)`. They are never silently dropped. |
| BR-09 | **Cross-host concurrency.** The same project can be open in two or more hosts at once. Costs add up (they never overlap). Developer hours use the **union** of time intervals per project per day, never the sum (see BR-11). |
| BR-10 | **Clients and rates.** Each project can belong to at most one client. Billing is `hourly` (rate + currency) or `fixed` (price + currency). Money is stored in USD. Display currency uses the single fixed `usd_rate` in `config.toml`. Changing that rate re-renders history (no FX history in v1). The rate in effect at report time applies to all periods (no rate history in v1, see OQ-3). |
| BR-11 | **Cost vs billable value.** Hourly: `AI cost ÷ (rate × dev hours)` per client, project and month. Fixed: `cumulative AI cost ÷ fixed_price` over the project's lifetime. Dev hours default to the session wall-clock union (BR-09). `hours set` overrides a day or month and the manual value always wins. A project with no client or rate shows `—`, never `0%`. |
| BR-12 | **Active vs wall-clock.** Time spent waiting for the user or a permission prompt (gap > `idle_threshold`) counts toward wall-clock but not active time. Parallelism factor = Σ agent-run active time ÷ task active time. It is shown only when there is at least one subagent. |
| BR-13 | **Retries.** A retry is a second or later run of the same `agent_type` within one task (for example `code-implementer` after a failed `qa-tester`), shown as `N retries <from>→<to>`. |
| BR-14 | **Open and crashed sessions.** A task with no terminal event is shown as `in progress`. If nothing new arrives for 24 h, it is closed at its last event. A later ingest **updates** it and never duplicates it. |
| BR-15 | **Retention beyond host cleanup.** Hosts may delete old transcripts (for example Claude Code `cleanupPeriodDays`). The local store keeps ingested data permanently. Deleting a transcript never deletes rows. Backfill only covers what the hosts still retain, and `doctor` prints the earliest available date per host. |
| BR-16 | **Privacy (hard).** Only numeric fields and metadata are stored: no prompts, assistant text, code, tool inputs or outputs, file paths, or subagent descriptions (always stored as a salted hash; the `store_agent_descriptions` key is reserved for v2 and currently ignored). Tool usage is stored as counts by tool name plus a count of files touched. Transcripts are opened read-only. |
| BR-17 | **Cloud anonymization.** `anonymize_projects = true` replaces **both project and client names** (and repo URLs) with stable salted hashes before upload. The local store keeps the clear names. The salt never leaves the machine. |
| BR-18 | **Consent before host edits.** `setup` shows the exact JSON it will add to each host settings file, asks for confirmation (or `--yes`), backs the file up, and merges without changing existing keys or hooks. If a settings file is invalid JSON or is managed (enterprise or policy file), `setup` refuses to edit it and offers scheduler-only. |
| BR-19 | **Uninstall safety.** `uninstall` restores the backup byte-for-byte **only if** the settings file hasn't changed since `setup`. Otherwise it removes only the entries agent-meter added, keeps the user's later edits, and leaves the backup in place. |
| BR-20 | **Zero agent overhead.** Hooks never write to stdout in a way the host would inject into agent context. They always exit 0, finish within the hard timeout, and never block the host. |
| BR-21 | **Work-item tags.** A tag is scoped to a project. `tag "<name>"` applies to every **new** task in that project, from any host, until `tag --clear` or another tag is set. `tag "<name>" --last N` tags tasks after the fact. Tags live only in the agent-meter store. |
| BR-22 | **Untracked history.** IDE `.pb` conversations and files whose format changed are counted and reported as "untracked" (count + date range). They are never estimated and never shown as zero usage. |

## 6. User Stories and Acceptance Criteria

Priority: M = Must, S = Should, C = Could. Milestone in brackets.

### US-01 Session-end summary — Scenario 1 (M) [A]
As P1, I want a summary when I exit a session, so that I can see what it cost right away.
- **Given** a hook is registered for Antigravity CLI and I worked in project X, **when** I exit, **then** within 3 s (P95) stderr and a macOS notification show: session tokens by type, cache hit %, ≈ cost, task P50/P95, and **today and month-to-date for X across all hosts**. The same text is written to `~/.agent-meter/last-summary.txt`.
- **Given** macOS notifications are disabled or unavailable (Linux), **when** the hook runs, **then** the summary still goes to stderr and the last-summary file, with no error.
- **Given** the store is locked by the scheduler for more than 3 s, **when** the hook runs, **then** it skips ingestion, prints totals from the current store with the note `(collecting… run 'agent-meter last' in a minute)`, and exits 0.

### US-02 Cross-host project totals — Scenario 2 (M) [A]
- **Given** project X was used yesterday in Antigravity CLI and today in Claude Code from the same repo (or a worktree of it), **when** the Claude Code session ends, **then** X's month-to-date equals the sum of both hosts, with a per-host breakdown.
- **Given** X is open in Claude Code and the Antigravity IDE at the same time, **when** both are ingested, **then** costs add up and dev hours use the time union (BR-09).

### US-03 Crash and open sessions — Scenario 3 (M) [A]
- **Given** a session is still open or the terminal was killed, **when** the 15-min scheduler runs, **then** all complete transcript lines are ingested, the partial last line is not, and the task shows `in progress`.
- **Given** the same files are ingested again by the hook, the scheduler or `collect`, **when** totals are computed, **then** they're identical (idempotent, no double counting).
- **Given** the machine slept or rebooted, **when** it wakes, **then** the scheduler resumes on its own and catches up.

### US-04 Separate projects — Scenario 4 (M) [A]
- **Given** I work on project Y in a different repo, **when** I open the report, **then** Y appears as its own project. A session in a non-repo directory goes to `(unassigned)` (BR-08).

### US-05 Local HTML report — Scenario 5 (M) [A]
- **Given** data exists, **when** I run `agent-meter report --open`, **then** a single static HTML file opens offline, with no external `http(s)://` assets. It shows cost and tokens by project, client, host, model and day; P50/P95/P99 task latency; cache efficiency; context size; error rate; and a tasks table with agent breakdown.
- **Given** the store is empty, **when** I run `report`, **then** a valid page renders with "No data yet — run `agent-meter collect`".
- Unpriced, inferred-model and untracked data are visibly flagged (BR-02, BR-04, BR-22).

### US-06 Per-task rollup with subagents — Scenario 7 (M) [A]
As P1, when one prompt fans out to N subagents, I want one rollup, so that I know what the whole DAG cost and how long it took.
- **Given** a task with 3 parallel subagents and 1 nested subagent, **when** it finishes (Claude Code `Stop` or the host equivalent, or the next ingest), **then** `agent-meter tasks --last` shows: wall-clock vs active time, total cost, cost, calls and tool counts per agent type, number of agents and max depth, parallelism factor, retries, and files touched (count). The task cost equals the sum of its calls exactly.
- **Given** a task is still running, **when** I run `tasks --last`, **then** it shows `in progress` with its partial totals.
- **Given** a host doesn't fire a per-task event, **then** the rollup is still available from `tasks --last` after the next ingest.

### US-07 Work-item tags — Scenario 8 (S) [A]
- **Given** I run `agent-meter tag "Track 11"` in project X, **when** I then run "execute the plan" and "continue" in any host, **then** `agent-meter tasks --tag "Track 11"` and the report roll up both tasks together. `tag --clear` stops tagging (BR-21).
- **Given** I forgot to tag, **when** I run `agent-meter tag "Track 11" --last 2`, **then** the two most recent tasks of X are tagged.

### US-08 Clients, rates and cost vs billable (M) [A]
- **Given** `projects.yaml` maps X and W to client Z at 80,000 COP/h with `usd_rate` set, **when** I run `report --month 2026-10`, **then** I see cost per client in USD and COP, dev hours, billable value, and `AI cost / billable %` for each client and project.
- **Given** I run `agent-meter hours set X 2026-10-14 6.5`, **when** the report is regenerated, **then** that day uses 6.5 h (source `manual`) instead of the derived hours.
- **Given** a fixed-price project, **then** the ratio is cumulative cost ÷ fixed price (BR-11). **Given** a project with no client, **then** the ratio shows `—`.

### US-09 Antigravity IDE (M) [A]
- **Given** IDE conversations stored as `.db`, **when** they're collected, **then** tokens and model come from `gen_metadata`, host = `antigravity-ide`, and the conversation joins the same project as CLI and Claude sessions in the same workspace.
- **Given** legacy `.pb` conversations, **then** they're reported as untracked (count + date range) in `doctor` and the report (BR-22).
- **Given** the IDE has no exit hook, **then** the IDE relies on the scheduler. A notification for an idle conversation is a Could (US-17).

### US-10 Standalone install — Scenario 9 (M) [A]
- **Given** P2 has no plugins from this repo, **when** they run `uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"` (or `pipx`) and then `agent-meter setup` and choose Local, **then** hooks and/or the scheduler are installed with consent (BR-18), history is backfilled, and the next session prints a summary.
- **Given** `~/.gemini/settings.json` already has an unrelated hook (for example `rtk-hook-gemini.sh`), **then** that hook is preserved byte-for-byte in meaning and keeps firing.
- **Given** `setup --local --yes`, **then** zero network calls are made and no Google libraries are needed.
- **Given** setup is run a second time, **then** it reports "no changes".

### US-11 Clean uninstall — Scenario 11 (M) [A]
- **Given** agent-meter was set up, **when** I run `agent-meter uninstall`, **then** its hooks and scheduler are removed, settings are restored per BR-19, and the DuckDB data is kept. `--purge` also deletes `~/.agent-meter/` after confirmation. Transcripts are never modified.

### US-12 Optional `agent-metrics` plugin (S) [A]
- **Given** a marketplace user installs the plugin but not the CLI, **when** a session ends, **then** the hook exits 0 within its timeout and prints one hint line to stderr (`agent-meter not installed: see <docs url>`).
- **Given** no other plugin in this repo, **then** none of them references or bundles agent-meter (decoupling).

### US-13 Guided cloud setup — Scenario 10 (M) [B]
- **Given** P1 runs `agent-meter setup --cloud`, **when** a prerequisite is missing (no `gcloud`, expired ADC, wrong gcloud default project, billing not linked, BigQuery API disabled, missing `bigquery.dataEditor`/`jobUser`), **then** the wizard names the exact problem and prints the exact fix command, and offers to run it where that's safe.
- **Given** the user picks `devhack-3f0c2` and `billing` mode, **then** the wizard uses that project explicitly (never the gcloud default), offers the $1 budget alert (and states that an alert **does not cap** spend), creates the dataset, tables and views, backfills, verifies that row counts match local, and prints the Looker Studio link.
- **Given** it's run again, **then** nothing is duplicated and it reports "already configured".
- **Given** `sandbox` mode, **then** the wizard explains the 60-day table expiry and schedules a weekly `sync --full-reload`.

### US-14 Looker parity and drill-down — Scenario 6 (M) [B]
- **Given** a sync has completed, **when** I compare Looker with `agent-meter report` for the same range and timezone, **then** totals per project and day match exactly (`verify --reconcile --cloud` reports 0 diff).
- **Then** Looker offers drill-down project → session → task → agent run → call, and a Tasks & Agents page (Gantt of agent runs, cost by agent type).

### US-15 Cloud resilience (M) [B]
- **Given** I'm offline or my credentials have expired, **when** the scheduler runs, **then** local collection continues, the outbox is kept, a clear message appears in `doctor` and the next summary, and the backlog uploads once on reconnect with no loss or duplicates.

### US-16 Health and reconciliation (M doctor [A], S reconcile [A])
- `agent-meter doctor` reports: hosts detected, hooks registered and last fired, scheduler loaded, last ingest, files skipped or corrupt, untracked history, unpriced models, unknown host format versions ("Antigravity format changed"), earliest available transcript date, and cloud lag and auth (B). It exits non-zero if any check is `FAIL`.
- `agent-meter verify --reconcile` compares local totals against independent counts (`npx ccusage` for Claude Code if available, raw transcript counts for Antigravity) over a frozen date range and prints the differences.

### US-17 Could-haves
- C1: macOS notification when an IDE conversation has been idle for 10 min (summary of its tasks).
- C2: `projects merge <a> <b>` and path aliases in `projects.yaml`.
- C3: Per-project budget threshold with a warning in the session summary.
- C4: `es` locale for CLI output (v1.x).

## 7. CLI UX Specification

General: English output. `--json` on all read commands. Exit code 0 on success and non-zero on error, **except `hook`, which always exits 0**. Global flags: `--home <dir>` (`AGENT_METER_HOME`) and `--quiet`. Durations use the format `13m 02s`. Costs are `≈ $4.10`, with display currency in parentheses when configured.

| Command | Purpose | Key flags |
| :--- | :--- | :--- |
| `setup` | Interactive wizard (detect hosts, mode, triggers, privacy, projects and clients, backfill, cloud) | `--local`, `--cloud`, `--yes`, `--hosts claude-code,antigravity-cli,antigravity-ide`, `--triggers hooks,scheduler,none`, `--gcp-project`, `--mode billing\|sandbox`, `--no-backfill` |
| `collect` | Incremental ingest of all hosts | `--host`, `--since <date>`, `--full` (re-scan from offset 0, still idempotent) |
| `hook` | Called by host hooks. Reads stdin payload, ingests that session, writes the summary. Not meant for humans. | `--host <host>`, `--event session-end\|task-end`, `--timeout <s>` (default 3) |
| `last` | Prints the last session summary | `--project` |
| `tasks` | Task rollups | `--last [N]`, `--session <id>`, `--project`, `--tag`, `--since` |
| `report` | Builds the static HTML report | `--open`, `--out <file>`, `--month YYYY-MM`, `--from/--to`, `--project`, `--client` |
| `sync` | Uploads the outbox to BigQuery [B] | `--full-reload`, `--dry-run` |
| `projects` | Lists and edits projects and clients (writes `projects.yaml`) | `list`, `set <id> --name --client --billing hourly\|fixed --rate --price --currency`, `merge <a> <b>` (C) |
| `hours set` | Manual dev hours override | `hours set <project> <YYYY-MM-DD\|YYYY-MM> <hours>`, `hours list`, `hours unset` |
| `tag` | Work-item tagging | `tag "<name>"`, `--last N`, `--clear`, `--project` |
| `doctor` | Health check | `--json`, `--cloud` |
| `config` | Shows and edits `config.toml` | `show`, `get <key>`, `set <key> <value>`, `edit` |
| `uninstall` | Removes hooks and scheduler, restores settings (BR-19) | `--purge`, `--yes`, `--keep-scheduler` |
| `verify --reconcile` | Reconciles against independent sources | `--from/--to`, `--host`, `--cloud` (local vs BigQuery) |

**Session summary (hook / `last`)**
```
[agent-meter] project-x · Antigravity CLI · session 42m 10s (active 18m 05s)
  Tokens 1.21M in · 9.80M cache read · 85K out · cache hit 89%
  Cost ≈ $1.37 · 7 tasks · P50 35s · P95 4m 10s
  project-x today ≈ $3.02 (Claude Code $1.65 · Antigravity $1.37) · month ≈ $41.80 (COP 171,380)
```

**Per-task rollup (`tasks --last`)**, English rendering of the PLAN.md example:
```
[agent-meter] project-x · Claude Code · task "execute the plan" · 13m 02s (active 11m 40s)
  Cost ≈ $4.10 · 6 agents (max depth 1) · parallelism 2.7x · 1 retry qa→impl
  main                 $0.40    9 calls
  code-implementer ×2  $2.90  188 calls · 41 Edit · 12 Write · 7 files
  qa-tester            $0.50   22 calls · pytest ✓
  compliance-verifier  $0.30   14 calls
```
The task label is a **local-only, truncated (≤ 40 chars) display** taken from the prompt at render time. It is never persisted to the store or the cloud (BR-16). If the prompt can't be read, the label is `task #<n>`. `pytest ✓` comes from the exit status of a `Bash` tool call matched by command name only. Whether to keep this is decided in the ADR (OQ-4).

**Partial and flagged values**: `Cost ≥ $4.10 (12 calls unpriced: gemini-x)` · `≈ $1.20*` with the footnote `* model inferred`.

**`doctor` (abridged)**
```
OK    claude-code       hook registered · last fired 2026-10-16 18:42 · earliest transcript 2026-09-16
OK    antigravity-cli   scheduler-only · last ingest 4 min ago
WARN  antigravity-ide   100 legacy .pb conversations untracked (2026-05-02 → 2026-06-28)
WARN  pricing           unpriced model: gemini-x (312 calls)
OK    bigquery          devhack-3f0c2.agent_metrics · lag 6 min · outbox 0
```

## 8. Non-Functional Requirements

| ID | Requirement |
| :--- | :--- |
| NFR-01 | Hook end-to-end P95 ≤ 3 s. Hard timeout. Always exits 0. Never writes to stdout in a way that reaches agent context. |
| NFR-02 | Full backfill of current history (~11K Claude requests + ~25K Antigravity calls, ~365 MB) ≤ 2 min. Incremental run with no new data ≤ 2 s. Peak memory ≤ 300 MB. |
| NFR-03 | Accuracy: deduplicated token totals match `ccusage` (Claude Code) and the independent transcript counts (Antigravity) **exactly** over a frozen range. Cloud totals equal local totals exactly. |
| NFR-04 | Money uses `Decimal` and is rounded only at presentation. Costs show 2 decimals in USD, 0 in COP. |
| NFR-05 | Option A: no network, no cloud SDKs (`[bigquery]` is an optional extra). Option B: batch load jobs only (no streaming inserts, no DML), so it stays at $0 in the free tier. |
| NFR-06 | Privacy: a canary string planted in fixtures never appears in the store, outbox, report, logs or the BigQuery test dataset. No credentials are written to config, logs or outbox. |
| NFR-07 | Robustness: corrupt files, unknown fields, new host format versions or a killed process never crash a run or corrupt the store. They show up in `doctor`. |
| NFR-08 | Platforms: macOS (launchd) and Linux (systemd user timer, cron fallback). Python ≥ 3.11 (to be confirmed in the ADR). Package metadata is PyPI-ready from v0.x. |
| NFR-09 | Decoupling: no existing plugin or skill references or depends on agent-meter, and the package imports nothing from `plugins/`, `skills/` or `scripts/`. |

## 9. Prioritization (MoSCoW → Milestone)

| Story | Priority | Milestone |
| :--- | :--- | :--- |
| US-01 Session summary, US-02 Cross-host, US-03 Crash/open, US-04 Separate projects | Must | A |
| US-05 HTML report, US-06 Per-task rollup, US-08 Clients & billable, US-09 Antigravity IDE | Must | A |
| US-10 Standalone install, US-11 Uninstall, US-16 `doctor` | Must | A |
| US-07 Work-item tags, US-12 Optional plugin, US-16 `verify --reconcile` (local) | Should | A |
| US-13 Guided cloud setup, US-14 Looker parity, US-15 Cloud resilience | Must | B |
| US-17 C1–C4 | Could | after B / v1.x |
| PyPI publish as `agent-meter` | Should | v1, after A |

Milestone A ships on its own and is fully usable without B.

## 10. Open Questions (genuinely remaining)

| ID | Question | Recommended default if unanswered |
| :--- | :--- | :--- |
| OQ-1 | **Default dev hours.** The plan says dev hours = session wall-clock. A session left open overnight would inflate hours (and lower the AI-cost %). Should derived hours exclude gaps between tasks longer than X? | Union of session intervals with gaps > 30 min between tasks removed. `hours set` always wins. |
| OQ-2 | **Subscription users.** Should v1 also show an "effective cost" that spreads a monthly plan fee (e.g. Claude Max) across usage, or only API-equivalent? | API-equivalent only in v1. A `[subscriptions]` config is a v1.x Could. |
| OQ-3 | **Rate history.** If a client's hourly rate changes mid-year, do past months need the old rate? | No in v1 (current rate applies). Add optional `effective_from` per rate later. |
| OQ-4 | **Task label and test status in the rollup.** Is showing a truncated prompt label (display only, never stored) acceptable, and is it OK to infer `pytest ✓/✗` from a Bash tool's command name and exit status? Both touch content-adjacent data. | Label: shown locally only, opt-out with `show_task_labels = false`. Test status: Should, matched by command name only. |
