---
name: agent-metrics
description: Use when the user wants to install, set up, check or remove agent-meter (token, API-equivalent cost and latency metrics for Claude Code and Antigravity per project, client, task and subagent), asks "how much did this task / project / client cost", "why is my agent slow or expensive", wants a local report or a BigQuery + Looker Studio dashboard, needs to fix unpriced models with "agent-meter pricing", or wants ad-hoc DuckDB / BigQuery queries over the collected metrics.
---

# AI Coding Metrics Skill (`agent-metrics`)

## Overview
`agent-meter` is an **optional, standalone CLI** that reads the transcripts Claude Code and Antigravity (CLI, IDE and app) already write to disk and turns them into per-project, per-client, per-task and per-subagent metrics: tokens by type, API-equivalent cost (`≈`), cache hit ratio, task latency P50/P95/P99, active time vs wall-clock, parallelism, retries and tool-call counts.

- **Option A — Local (default)**: a DuckDB file at `~/.agent-meter/meter.duckdb`, a summary after each task or session, and an offline HTML report. No network, no cloud account.
- **Option B — Cloud (opt-in, on top of A)**: a BigQuery replica (dataset `agent_metrics`) loaded with free-tier load jobs, plus a Looker Studio dashboard. The local store stays the source of truth.

It only stores numbers and metadata: never prompts, assistant text, code, tool inputs/outputs or file paths. Every cost is **API-equivalent**: it is not what a subscription plan bills.

This skill guides the user through installing and configuring the CLI, reading its output and querying the data. It never edits host settings files by hand: `agent-meter setup` does that with consent, a backup and a reversible `agent-meter uninstall`.

## When to Use
### Trigger Scenarios
- The user asks to install or configure agent-meter, or to "track how much my agents cost".
- The user asks what a task, session, project or client cost, or why a task was slow or expensive.
- The user wants a report (local HTML) or a cloud dashboard (BigQuery + Looker Studio).
- `agent-meter doctor` or a summary reports unpriced models, a stale scheduler, missing hooks or a cloud backlog.
- The user wants an ad-hoc question answered from the metrics (e.g. "cost per subagent type this month").

### When NOT to Use
- **Billing disputes with a provider**: agent-meter shows API-equivalent cost, not invoices.
- **Reading prompt or code content**: agent-meter never stores it; do not try to recover it from transcripts.
- **Users who did not ask for metrics**: agent-meter is opt-in. Never install it or register hooks unprompted.

## Process
### Phase 1: Install the CLI (Python ≥ 3.11; `uv` provisions it)
```bash
uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
# or
pipx install --python python3.12 "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
# Option B also needs the BigQuery extra:
uv tool install --force "agent-meter[bigquery] @ git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
agent-meter --help
```
If `agent-meter` is not found afterwards, the tool bin directory (usually `~/.local/bin`) is missing from `PATH`: run `uv tool update-shell` and open a new terminal.

### Phase 2: Choose local or cloud and run the wizard
Ask the user which option they want before running anything. Explain each wizard prompt as it appears:

1. **Hosts detected**: Claude Code (`~/.claude/`), Antigravity CLI (`~/.gemini/antigravity-cli/`), Antigravity IDE (`~/.gemini/antigravity/`), with how much history exists.
2. **Backfill**: imports existing history once. Re-running is idempotent (nothing is double-counted).
3. **Triggers**: `hooks` (a summary after every task / session), `scheduler` (every 15 min via `launchd` / systemd user timer / cron), both, or none (manual `agent-meter collect`). The wizard shows the exact JSON it will add, backs up the settings file and never overwrites existing hooks. If the optional `agent-metrics` plugin is installed, the wizard skips user-level hooks because the plugin already registers them.
4. **Privacy**: anonymize project names before cloud upload, store subagent descriptions (defaults: no / no).
5. **Projects and clients**: projects are discovered from the imported history; set display names, clients and rates afterwards with `agent-meter projects set`.

**Option A — local only** (zero network calls):
```bash
agent-meter setup --local            # interactive
agent-meter setup --local --yes      # accept the defaults
```

**Option B — cloud** (always pass the GCP project explicitly; the wizard never relies on the `gcloud` default project):
```bash
agent-meter setup --cloud --gcp-project devhack-3f0c2 --mode billing
agent-meter setup --cloud --gcp-project my-sandbox-project --mode sandbox
```
- **`billing` mode**: the project has a billing account linked. Load jobs and the free tier keep the cost at $0 for normal volumes. The wizard offers a **$1 budget alert**; tell the user that an alert notifies but **does not cap** spend.
- **`sandbox` mode**: BigQuery sandbox, no billing account. Tables expire after 60 days, so the wizard schedules a weekly `agent-meter sync --full-reload` that re-uploads everything from the local store.
- Prerequisites the wizard checks, each with the exact fix command: `gcloud` installed, Application Default Credentials valid (`gcloud auth application-default login`), billing linked (billing mode), BigQuery API enabled, and the roles `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` on the project. Offer to run a fix only when the wizard marks it safe.
- Running `setup` again is safe: it reports "already configured" instead of duplicating anything.
- After the first sync, follow the Looker Studio guide: [Looker Studio dashboard](https://github.com/jggomez/expert-ai-developer-skills/blob/main/docs/agent-metrics/looker-studio.md).

### Phase 3: Verify the installation
```bash
agent-meter doctor            # config, hooks per host, store, pricing, untracked history, scheduler
agent-meter doctor --cloud    # adds the GCP prerequisite checks and BigQuery lag/backlog
```
Each line is `OK`, `WARN` or `FAIL` with a fix hint. Exit code `3` means at least one `FAIL`.

### Phase 4: Interpret the metrics
```bash
agent-meter last                  # last session + today and month-to-date for the project, all hosts
agent-meter tasks --last 5        # per-task rollups with every subagent
agent-meter report --open         # offline HTML report (by project, host, day, latency, cache)
agent-meter verify --reconcile    # store vs a fresh re-read of the transcripts
```
How to read them:
- **Cost `≈ $X`** is API-equivalent. **`≥ $X`** means some calls are unpriced: fix them (Phase 5) before trusting totals.
- **Cache hit ratio** = `cache_read / (input + cache_read + cache_write)`. A falling ratio means paying more for the same work (context churn, frequent restarts).
- **Active time vs wall-clock**: gaps longer than the idle threshold (default 120 s, e.g. waiting for a permission prompt) count toward wall-clock only. **Parallelism** = Σ subagent active time ÷ task active time; > 1 means fan-out saved time.
- **Retries** count repeated runs of the same subagent type in one task (e.g. implementer → QA → implementer), i.e. the cost of self-correction loops.
- **Cost share by subagent type** shows which role dominates (implementers are usually the largest share).
- **Client view**: `agent-meter projects set <p> --client <c> --billing hourly --rate 40 --currency USD`, then `agent-meter report --client <c>`; correct dev hours with `agent-meter hours set <p> 2026-10 32`.

### Phase 5: Keep prices correct
```bash
agent-meter pricing unpriced                                   # models seen without a price
agent-meter pricing list
agent-meter pricing alias gemini-3.7-flash gemini-3.6-flash --estimated
agent-meter pricing add my-model --input 3 --output 15 --cache-read 0.3 --effective-from 2026-10-01 --source-url https://example.com/pricing
agent-meter pricing validate
```
Prices are USD per million tokens and versioned by `--effective-from`. Edits re-price history immediately, with no re-ingest. Mark aliases `--estimated` when the price is borrowed from another model.

### Phase 6: Ad-hoc queries
**Local (DuckDB)**: open the store read-only. If a collect is running, wait a few seconds and retry.
```bash
duckdb -readonly ~/.agent-meter/meter.duckdb \
  "SELECT local_month, display_name, round(sum(cost_usd), 2) AS usd, sum(unpriced_calls) AS unpriced
   FROM v_daily_project_cost GROUP BY ALL ORDER BY local_month DESC, usd DESC LIMIT 20"
# without the duckdb CLI:
uv run --with duckdb python -c "import duckdb, os; c = duckdb.connect(os.path.expanduser('~/.agent-meter/meter.duckdb'), read_only=True); print(c.sql('SELECT agent_type, round(sum(cost_usd), 2) AS usd FROM v_agent_type_cost GROUP BY ALL ORDER BY usd DESC'))"
```
**Cloud (BigQuery)**: the dataset has views with the same names and columns as DuckDB. Filter on `local_date` / `local_month` to keep scans small.
```bash
bq query --project_id=devhack-3f0c2 --use_legacy_sql=false \
  'SELECT local_month, project_id, ROUND(SUM(cost_usd), 2) AS usd
   FROM agent_metrics.v_daily_project_cost
   WHERE local_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
   GROUP BY 1, 2 ORDER BY usd DESC'
```
Useful views: `v_calls`, `v_daily_project_cost`, `v_sessions`, `v_tasks`, `v_agent_runs`, `v_agent_type_cost`, `v_tool_counts`, `v_task_latency`, `v_dev_hours`, `v_client_month`, `v_unpriced_models`, `v_health`.

### Phase 7: Remove it
```bash
agent-meter uninstall                 # removes hooks + scheduler, restores settings; keeps the data
agent-meter uninstall --purge --yes   # also deletes ~/.agent-meter/
uv tool uninstall agent-meter
```
If the settings file changed after setup, uninstall removes only agent-meter's own entries and keeps the user's later edits.

## Usage
### Example Prompts
- *"Set up agent-meter locally for Claude Code and Antigravity."*
- *"Connect agent-meter to BigQuery in devhack-3f0c2 with a $1 budget alert."*
- *"How much did the last plan execution cost, and which subagent was the most expensive?"*
- *"doctor says there are unpriced models; fix the pricing."*
- *"Query the cost per client for last month from DuckDB."*

### Commands Reference
| Command | Purpose |
| :--- | :--- |
| `agent-meter setup [--local\|--cloud] [--yes] [--hosts …] [--triggers …] [--gcp-project P] [--mode billing\|sandbox]` | Guided, idempotent setup |
| `agent-meter collect [--host H] [--since D] [--full]` | Incremental ingest |
| `agent-meter last` · `agent-meter tasks --last N` · `agent-meter report --open` | Summaries and report |
| `agent-meter projects …` · `agent-meter hours …` · `agent-meter tag "<name>"` | Projects, clients, dev hours, work items |
| `agent-meter pricing list\|unpriced\|add\|set\|alias\|remove\|validate` | Price table |
| `agent-meter doctor [--cloud]` · `agent-meter verify --reconcile [--cloud]` | Health and reconciliation |
| `agent-meter sync [--full-reload] [--dry-run]` | Upload to BigQuery (Option B) |
| `agent-meter config show\|get\|set\|edit` | e.g. `agent-meter config set timezone America/Bogota` |
| `agent-meter uninstall [--purge --yes]` | Clean removal |

## Red Flags
- Installing agent-meter or registering hooks without the user asking for it (it is opt-in).
- Editing `~/.claude/settings.json`, `~/.gemini/config/hooks.json` or `~/.gemini/settings.json` by hand instead of letting `agent-meter setup` / `agent-meter uninstall` do it (the latter file belongs to Gemini CLI and is never touched).
- Relying on the `gcloud` default project instead of passing `--gcp-project` explicitly.
- Presenting `≈` costs as invoiced amounts, or reporting totals while `unpriced_calls > 0` without saying "≥".
- Telling the user a budget alert caps spend (it only notifies).
- Opening `meter.duckdb` read-write for ad-hoc queries while the scheduler or a hook may be writing.
- Trying to extract prompt text, code or file paths from transcripts to "enrich" the metrics.

## Verification
- [ ] The user explicitly chose Option A (local) or Option B (cloud) before `agent-meter setup` ran.
- [ ] `agent-meter doctor` (and `agent-meter doctor --cloud` for Option B) shows no `FAIL`.
- [ ] `agent-meter last` or `agent-meter tasks --last` prints a summary after the next task.
- [ ] `agent-meter pricing unpriced` is empty, or every remaining model is explained to the user.
- [ ] Option B: `agent-meter verify --reconcile --cloud` reports 0 differences before building Looker charts.
- [ ] Costs were presented as API-equivalent (`≈`), never as billed amounts.
