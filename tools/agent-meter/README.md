# agent-meter

> **How much are my AI coding agents costing me, per project, per task and per subagent — and how long do they take?**

`agent-meter` answers that for **Claude Code** and **Antigravity** (CLI, IDE and the "Antigravity 2.0" app). It reads the
transcripts and databases those tools already write on your machine, and turns them into:

- a short **summary after every task or session** (tokens, API-equivalent cost, time, P50/P95),
- an **offline HTML report** you open in your browser,
- and, optionally, a **BigQuery dataset + Looker Studio dashboard** in your own Google Cloud project.

It is **free** (local mode needs no account at all), **read-only** towards your tools, and **private**: it never stores
prompts, code, tool inputs/outputs or file paths.

> 🇪🇸 Guía en español: [README.es.md](README.es.md)

---

## Table of contents

1. [Two ways to use it](#1-two-ways-to-use-it)
2. [Quick start (5 minutes, local)](#2-quick-start-5-minutes-local)
3. [How it works](#3-how-it-works)
4. [Install](#4-install)
5. [Option A — Local (DuckDB + HTML report)](#5-option-a--local-duckdb--html-report)
6. [Option B — Cloud (BigQuery + Looker Studio)](#6-option-b--cloud-bigquery--looker-studio)
7. [Command reference](#7-command-reference)
8. [Understanding the numbers](#8-understanding-the-numbers)
9. [Projects, clients, rates and hours](#9-projects-clients-rates-and-hours)
10. [Prices (configurable)](#10-prices-configurable)
11. [Configuration reference](#11-configuration-reference)
12. [Hooks, scheduler and notifications](#12-hooks-scheduler-and-notifications)
13. [Privacy and files](#13-privacy-and-files)
14. [Supported tools and data sources](#14-supported-tools-and-data-sources)
15. [Troubleshooting / FAQ](#15-troubleshooting--faq)
16. [Uninstall](#16-uninstall)
17. [Development](#17-development)

---

## 1. Two ways to use it

| | **Option A — Local** (default) | **Option B — Cloud** (opt-in, on top of A) |
| :--- | :--- | :--- |
| For | Any developer, no cloud account | Developers with a Google Cloud project |
| Data lives in | `~/.agent-meter/meter.duckdb` on your Mac/Linux/Windows | The same local file **plus** a BigQuery dataset |
| You see it in | Terminal summaries + `agent-meter report` (HTML) | Everything in A **plus** a Looker Studio dashboard |
| Network | Never | Only BigQuery uploads (batch load jobs) |
| Cost | $0 | $0 within the BigQuery free tier for this data volume (load jobs are free); set a budget alert |

Option B is a **replica** of Option A: the local store is always the source of truth, and the cloud copy can be rebuilt
from it at any time (`agent-meter sync --full-reload`).

---

## 2. Quick start (5 minutes, local)

```bash
# 1) Install (needs uv: https://docs.astral.sh/uv/)
uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

# 2) Configure once: detects Claude Code / Antigravity, imports your history
agent-meter setup --local

# 3) Use it
agent-meter last            # summary of your last session
agent-meter tasks --last 5  # the last 5 tasks, with every subagent
agent-meter report --open   # full HTML report in your browser
```

That's it. If you chose hooks or the scheduler during `setup`, new activity is recorded automatically; otherwise run
`agent-meter collect` whenever you want fresh numbers.

> Installing from a branch that is not merged yet, or from a local clone? See [§4 Install](#4-install).

---

## 3. How it works

```
 Claude Code transcripts (~/.claude/projects)          Antigravity databases (~/.gemini/antigravity-*/)
                 │                                                        │
                 └──────────────────┬─────────────────────────────────────┘
                                    ▼
                 agent-meter collect   (incremental, idempotent, read-only)
                                    │   triggered by: hooks (end of task/session), scheduler (every 15 min) or you
                                    ▼
                 ~/.agent-meter/meter.duckdb   ← source of truth (tokens, times, projects, tasks, agents)
                    │                    │                                  │
         agent-meter last / tasks   agent-meter report (HTML)     agent-meter sync  ──►  BigQuery  ──►  Looker Studio
              (terminal)               (offline)                     (Option B only)
```

- **Nothing is lost** if a session crashes or you never close it: the tools keep writing their transcripts, and the next
  `collect` (hook, scheduler or manual) picks up where the last one stopped.
- **Nothing is double counted**: every LLM call has a natural key; re-running `collect` is always safe.
- **Cost is computed when you look at it**, from tokens × the price table. Fixing or adding a price instantly re-prices
  your whole history (locally and in BigQuery after the next sync).

---

## 4. Install

**Requirements:** macOS, Linux or Windows (PowerShell/CMD or WSL2), Python ≥ 3.11 (installed for you by `uv`), and `uv` or `pipx`.

### 4.1 From GitHub (recommended)

```bash
# Local mode only
uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

# Local + BigQuery support (Option B)
uv tool install "agent-meter[bigquery] @ git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

# Same with pipx
pipx install --python python3.12 "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
```

To install from a specific branch (e.g. before it is merged into `main`), add `@<branch>` right after the repository URL:

```bash
uv tool install "agent-meter[bigquery] @ git+https://github.com/jggomez/expert-ai-developer-skills@feature/agent-metrics#subdirectory=tools/agent-meter"
```

### 4.2 From a local clone of this repository

```bash
cd /path/to/expert-ai-developer-skills
uv tool install "./tools/agent-meter"               # local mode
uv tool install "./tools/agent-meter[bigquery]"     # with BigQuery support
```

### 4.3 Check, update, remove the tool

```bash
agent-meter --version            # e.g. agent-meter 0.1.0
uv tool upgrade agent-meter      # update (or: uv tool install --force <same source>)
uv tool uninstall agent-meter    # remove the program (run `agent-meter uninstall` first, see §16)
```

### 4.4 Optional: the `agent-metrics` plugin

If you already use this repository's plugin marketplace, you can register the hooks through the optional plugin instead
of `setup`. **The CLI is still required** (the plugin only calls it).

```text
/plugin marketplace add jggomez/expert-ai-developer-skills
/plugin install agent-metrics@expert-ai-developer-skills
```

No other plugin in this repository depends on agent-meter; installing or removing it changes nothing else.

---

## 5. Option A — Local (DuckDB + HTML report)

### 5.1 Run the setup wizard

```bash
agent-meter setup --local
```

The wizard walks through 8 steps. Every step is safe to re-run; running `setup` twice changes nothing the second time.

| Step | What it asks / does | Recommended answer |
| :--- | :--- | :--- |
| 1. Hosts | Detects Claude Code (`~/.claude`) and Antigravity CLI/IDE/app (`~/.gemini/...`) and how much history each has | Keep all detected hosts |
| 2. Mode | Local or Local + Cloud | Local (you can add Cloud later) |
| 3. Triggers | How new activity gets recorded: **hooks**, **scheduler**, both or none (see below) | `hooks,scheduler` |
| 4. Privacy | Anonymize project names before cloud upload (only matters for Option B) | No for your own project |
| 5. Backfill | Import your existing history now | Yes |
| 6. Projects | Optional: set display names, clients and rates (can be done later, §9) | Skip for now |
| 7. Cloud | Only in Cloud mode (§6) | — |
| 8. Summary | Prints what changed and runs `doctor` | — |

**Triggers — what each option changes on your machine:**

| Trigger | What it does | What it modifies |
| :--- | :--- | :--- |
| `hooks` | A summary right after each task (Claude Code `Stop`/`SessionEnd`, Antigravity `Stop`) | Adds entries to `~/.claude/settings.json` and `~/.gemini/config/hooks.json` — it shows you the exact JSON first, backs the files up, and **never touches your existing hooks** |
| `scheduler` | Collects every 15 minutes, also catching crashed/open sessions; uploads to BigQuery in Option B | Adds a user `launchd` agent (macOS), a systemd user timer / cron entry (Linux), or a Windows Task Scheduler task (`schtasks`) |
| `none` | Nothing automatic; you run `agent-meter collect` yourself | Nothing |

Non-interactive variants:

```bash
agent-meter setup --local --yes                               # accept the defaults, zero network calls
agent-meter setup --local --yes --triggers none               # import history only, change nothing else
agent-meter setup --local --yes --triggers scheduler          # add only the 15-minute scheduler
agent-meter setup --local --yes --hosts claude-code           # only Claude Code
agent-meter setup --local --yes --no-backfill                 # skip the history import
```

### 5.2 Everyday use

```bash
agent-meter last                       # last session summary (+ today / month for that project)
agent-meter last --project webpage-devhack
agent-meter tasks --last 10            # last 10 tasks with per-agent breakdown
agent-meter tasks --since 2026-10-01 --project webpage-devhack
agent-meter collect                    # refresh now (incremental)
agent-meter projects list              # every project with sessions and cost
```

Example session summary:

```
[agent-meter] expert-ai-developer-skills · Claude Code · session 20h 55m (active 2h 47m)
  Tokens 1.7K in · 138.79M cache read · 6.56M cache write · 639K out · cache hit 95%
  Cost ≈ $77.54 · 45 tasks · P50 50s · P95 2h 32m
  expert-ai-developer-skills today ≈ $33.10 (Claude Code $33.10) · month ≥ $89.53
```

Example task with subagents:

```
[agent-meter] proyecto-x · Claude Code · task #12 · 13m 02s (active 11m 40s)
  Cost ≈ $4.10 · 6 agents (max depth 1) · parallelism 2.7x · 1 retry
  main                 $0.40    9 calls
  code-implementer ×2  $2.90  188 calls · 41 Edit · 12 Write
  qa-tester            $0.50   22 calls
  compliance-verifier  $0.30   14 calls
```

### 5.3 The HTML report

```bash
agent-meter report --open                                   # all history, opens the browser
agent-meter report --open --month 2026-10                   # one month
agent-meter report --open --from 2026-10-01 --to 2026-10-15 # a date range
agent-meter report --open --project webpage-devhack         # one project
agent-meter report --open --client "Client A"               # all projects of one client
agent-meter report --out ~/Desktop/ai-costs-oct.html        # write to a specific file
```

The report is a single self-contained file (works offline, no external assets). Light theme by default, dark mode
follows your system. Sections: overview (cost by project/month, Claude Code vs Antigravity), tasks & agents, performance
(P50/P95/P99), efficiency (cache hit, context size), billing (when rates are set) and notices (unpriced/estimated/untracked).
Every chart has a **Table view** toggle.

---

## 6. Option B — Cloud (BigQuery + Looker Studio)

### 6.1 Prerequisites (one time)

| # | What | How |
| :--- | :--- | :--- |
| 1 | `gcloud` CLI | https://cloud.google.com/sdk/docs/install |
| 2 | BigQuery support in agent-meter | Install with the `[bigquery]` extra (§4) |
| 3 | Log in for applications (ADC) | `gcloud auth application-default login` |
| 4 | (Recommended) quota project for ADC | `gcloud auth application-default set-quota-project <PROJECT_ID>` |
| 5 | A GCP project | Use an existing one (ideally a dev/non-production project) |
| 6 | Billing mode | **billing** (recommended): billing linked, stays within the free tier for this volume · **sandbox**: no card, but BigQuery deletes tables after 60 days (agent-meter re-uploads everything weekly) |
| 7 | Permissions | Project **Owner**, or `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` |

You don't need to enable APIs by hand: the wizard checks each prerequisite and prints the exact command to fix anything
missing (`gcloud services enable bigquery.googleapis.com --project …`, IAM bindings, etc.).

> agent-meter **always uses the project you pass**, never your `gcloud` default project.

### 6.2 Connect

```bash
agent-meter setup --cloud --gcp-project <PROJECT_ID> --mode billing
# non-interactive, without touching hooks or the scheduler:
agent-meter setup --cloud --gcp-project <PROJECT_ID> --mode billing --triggers none --yes
```

What happens:

1. Prerequisite checks: `gcloud`, ADC, project, billing, BigQuery API, IAM (`agent-meter doctor --cloud` runs the same checks).
2. **Budget alert (billing mode)**: offers a **$1 budget alert** on the project's billing account (it enables the Budget API
   for you). An alert only emails you at 50% and 100%; it does **not** cap spending.
3. Creates the dataset `agent_metrics` (location `US` by default) with its tables and views.
4. Uploads your full history and checks that BigQuery totals equal the local totals.

### 6.3 What is created in BigQuery

| Kind | Names |
| :--- | :--- |
| Fact tables (monthly partitions) | `raw_llm_calls`, `raw_tasks`, `raw_agent_runs`, `raw_sessions`, `raw_tool_uses` |
| Reference tables | `projects`, `pricing`, `pricing_aliases`, `host_defaults`, `dev_hours_manual`, `dev_hours_derived`, `task_tags`, `tag_history`, `settings`, `untracked` |
| Deduplicated views | `llm_calls`, `tasks`, `agent_runs`, `sessions`, `tool_uses` |
| **Views for dashboards** | `v_daily_project_cost`, `v_calls`, `v_sessions`, `v_tasks`, `v_agent_runs`, `v_agent_type_cost`, `v_task_latency`, `v_tool_counts`, `v_client_month`, `v_dev_hours`, `v_unpriced_models`, `v_untracked`, `v_health` |

Only numbers and metadata are uploaded (tokens, times, model ids, project/client names, agent types, tool names and
counts). Set `agent-meter config set bigquery.anonymize_projects true` to upload project, client, remote and tag names as
salted hashes instead (the salt never leaves your machine).

### 6.4 Keep it updated

```bash
agent-meter sync                 # upload what changed since the last sync (batch load jobs only)
agent-meter sync --dry-run       # show what would be uploaded
agent-meter sync --full-reload   # rebuild every table from the local store (sandbox mode does this weekly)
agent-meter verify --reconcile --cloud --from 2026-10-01 --to 2026-10-31   # local vs BigQuery, exit 5 on any difference
```

With the `scheduler` trigger, every 15-minute run also syncs. Without it, run `agent-meter collect && agent-meter sync`.

Quick check from the terminal:

```bash
bq query --project_id=<PROJECT_ID> --use_legacy_sql=false \
  'SELECT display_name, ROUND(SUM(cost_usd),2) AS cost_usd, SUM(calls) AS calls
   FROM `<PROJECT_ID>.agent_metrics.v_daily_project_cost` GROUP BY 1 ORDER BY 2 DESC LIMIT 10'
```

### 6.5 Build the Looker Studio dashboard

Looker Studio (https://lookerstudio.google.com) is Google's **free** web dashboard tool; you sign in with your Google
account. (It is not "Looker", the paid enterprise product.)

1. **Create → Report → Add data → BigQuery**.
2. Pick **your project → `agent_metrics` → `v_daily_project_cost`** (you can type the project id in *Enter project ID manually*) → **Add**.
3. Looker Studio warns that the data source uses **owner's credentials**: anyone you share the report with could see the
   data. That's fine while the report is only yours. Accept.
4. Add charts. This layout gives a clear, formal dashboard:

| Chart | Type | Dimension | Metric | Tip |
| :--- | :--- | :--- | :--- | :--- |
| Total cost | Scorecard | — | `cost_usd` (Sum, type *Currency USD*) | Duplicate for `calls`, `output_tokens`, `cache_read_tokens` (enable *Compact numbers*) |
| Daily cost | Time series | `local_date` | `cost_usd` | Hide the legend |
| Cost by project | Table with heatmap | `display_name` | `calls`, `cost_usd` | Sort by `cost_usd` descending |
| Cost by tool | Donut | `host` | `cost_usd` | Legend on the right |
| Monthly cost | Column chart | `local_month` | `cost_usd` | Sort by `local_month` ascending, show data labels |
| Period filter | Date range control | — | — | Uses `local_date` |

5. Styling used in the reference dashboard: page background `#EEF2F7`, white cards (radius 12, light border, shadow),
   header band with an indigo→violet gradient (`#312E81` → `#7C3AED`) and white title, font Roboto, chart palette
   `#4F46E5` (indigo), `#14B8A6` (teal), `#F59E0B` (amber), `#EC4899` (pink). Theme and layout → *Customize* sets the
   page background, font, component background and palette for every chart at once.
6. For drill-downs (sessions, tasks, agents, latency, cache efficiency), add data sources for `v_sessions`, `v_tasks`,
   `v_agent_runs`, `v_agent_type_cost` and `v_task_latency`. Page-by-page details: [`docs/agent-metrics/looker-studio.md`](../../docs/agent-metrics/looker-studio.md).

> Clicking a row or a slice applies a **cross-filter** to the whole page. Use **Reset** (top bar) to clear it.

> Looker Studio caches query results; data refreshes after the next `agent-meter sync` and the cache expiry (or *Refresh
> data* in the report menu).

---

## 7. Command reference

Global flags (before the command): `--home <dir>` (or `$AGENT_METER_HOME`; default `~/.agent-meter`) and `--quiet`.
Most read commands accept `--json`.

| Command | Purpose | Most useful flags |
| :--- | :--- | :--- |
| `setup` | Interactive setup (local or cloud) | `--local`/`--cloud`, `--yes`, `--hosts`, `--triggers hooks,scheduler\|hooks\|scheduler\|none`, `--gcp-project`, `--mode billing\|sandbox`, `--no-backfill` |
| `collect` | Incremental import | `--host H`, `--since YYYY-MM-DD`, `--full` (re-read everything, still idempotent) |
| `last` | Last session summary | `--project P`, `--json` |
| `tasks` | Per-task rollups with subagents | `--last [N]`, `--session S`, `--project P`, `--tag T`, `--since D`, `--json` |
| `report` | HTML report | `--open`, `--out F`, `--month YYYY-MM`, `--from D --to D`, `--project P`, `--client C` |
| `projects list` | Projects with sessions and cost | `--json` |
| `projects set <project>` | Name, client, billing | `--name`, `--client`, `--billing hourly\|fixed`, `--rate`, `--price`, `--currency` |
| `projects merge <src> <dst>` | Merge two project ids into one | — |
| `hours set <project> <YYYY-MM-DD\|YYYY-MM> <hours>` · `hours unset` · `hours list` | Manual developer hours (override the automatic estimate) | — |
| `tag "<name>"` | Group tasks into a work item | `--last N`, `--project P`, `--clear` |
| `pricing list\|unpriced\|add\|set\|alias\|remove\|validate` | Price table (§10) | see §10 |
| `config show\|get\|set\|edit` | Configuration (§11) | `config set <key> <value>` |
| `doctor` | Health check (hooks, scheduler, formats, prices, untracked history) | `--cloud`, `--json` |
| `verify --reconcile` | Local store vs an independent re-read (or vs BigQuery with `--cloud`) | `--from`, `--to`, `--host`, `--cloud` |
| `sync` | Upload to BigQuery | `--full-reload`, `--dry-run` |
| `uninstall` | Remove hooks/scheduler, restore settings | `--keep-scheduler`, `--purge --yes` |

Exit codes: `0` ok · `1` error · `2` usage error · `3` doctor found a FAIL · `4` store busy (try again) · `5` reconcile
found differences. The internal `hook` command always exits `0`.

---

## 8. Understanding the numbers

| You see | Meaning |
| :--- | :--- |
| `≈ $77.54` | **API-equivalent cost**: what these tokens would cost at the public API price. If you pay a subscription (Claude Max, Google AI plan), this is the *value* you consumed, not what you were billed |
| `≥ $89.53` | A **lower bound**: some calls in that total have no price or incomplete token data |
| `*` | The price is **estimated** (e.g. an Antigravity internal model id priced as its nearest public model) |
| `†` | The **model was inferred** (the tool did not record it; `hosts.<host>.default_model` was used) |
| Tokens *in / cache read / cache write / out* | Input sent fresh / input served from the prompt cache (cheap) / input written to the cache / generated output (incl. thinking) |
| *cache hit* | `cache read ÷ (input + cache read + cache write)` — higher is cheaper |
| *session 20h 55m (active 2h 47m)* | Wall-clock from first to last event vs time the agents were actually working (gaps > `idle_threshold_s` are idle) |
| *task* | One prompt you sent, including every subagent it spawned |
| *P50 / P95* | Median and 95th-percentile task duration |
| *parallelism 2.7x* | Sum of agent active time ÷ task active time (how much parallel subagents overlapped) |
| *retry* | The same agent type ran again in the same task (e.g. implementer after a failed QA) |

---

## 9. Projects, clients, rates and hours

A **project** is identified by its git repository (remote URL or root), so the same repo opened from Claude Code and from
Antigravity counts as **one** project. Folders that were moved are merged automatically; if two ids still describe the
same project, merge them with `projects merge`.

```bash
agent-meter projects list
agent-meter projects set webpage-devhack --name "DevHack website" --client "DevHack" --billing hourly --rate 45 --currency USD
agent-meter projects set client-app --client "Client A" --billing fixed --price 3000 --currency USD
agent-meter projects merge path:0a4e234a3424dac3 git:1d58476545c17b30
```

Developer hours are estimated from your sessions (gaps longer than `dev_hours_merge_gap_min` are not counted).
Override them when you know the real number:

```bash
agent-meter hours set webpage-devhack 2026-10 32       # 32 hours in October
agent-meter hours set webpage-devhack 2026-10-18 4     # 4 hours on one day
agent-meter hours list
agent-meter hours unset webpage-devhack 2026-10
```

With rates set, the report and `v_client_month` show **AI cost vs billable value** per client and month.

Group several prompts into a **work item** (e.g. a ticket):

```bash
agent-meter tag "TICKET-123"            # tag the current/next tasks
agent-meter tag "TICKET-123" --last 5   # tag the 5 most recent tasks
agent-meter tag --clear
agent-meter tasks --tag "TICKET-123"
```

To show amounts in your currency next to USD: `agent-meter config set currency.display COP` and
`agent-meter config set currency.usd_rate 4100` (units of that currency per 1 USD).

---

## 10. Prices (configurable)

No price is hard-coded. Two layers are merged, and **your local file always wins**:

| File | Maintained by | Contents |
| :--- | :--- | :--- |
| `pricing.yaml` (shipped with agent-meter) | agent-meter releases | Official Anthropic and Google prices with source URL and date windows; aliases for Antigravity internal model ids (marked *estimated*) |
| `~/.agent-meter/pricing.local.yaml` | You | New models, corrections, your own aliases |

Each model can have several **price windows** (`effective_from`), so a price change never rewrites past months.

```bash
agent-meter pricing list                       # every model, window and source
agent-meter pricing unpriced                   # models seen in your data with no price (+ the exact fix command)

# Add a new model (USD per million tokens)
agent-meter pricing add gemini-5-flash --input 1.00 --output 5.00 --cache-read 0.10 --effective-from 2026-11-01 \
  --source-url https://ai.google.dev/gemini-api/docs/pricing

# A price change from a date (all three main prices are required)
agent-meter pricing set claude-sonnet-5 --input 2.00 --output 12.00 --cache-read 0.20 \
  --cache-write-5m 2.50 --cache-write-1h 4.00 --effective-from 2026-12-01

# Map an unknown/internal id to a priced model
agent-meter pricing alias agy-demo-high gemini-3.8-flash --estimated

agent-meter pricing remove --alias agy-demo-high
agent-meter pricing remove --model gemini-5-flash --effective-from 2026-11-01
agent-meter pricing validate                   # check pricing.local.yaml
```

Rules:

- A model with no price is still recorded (tokens are kept) and shown as `≥ $X (N calls unpriced)`, **never as $0**.
- Prices are applied when you query, so `pricing add/set/alias` re-prices history immediately (BigQuery after the next `sync`).
- Tiered prices (e.g. a higher price above a prompt size) use `--min-prompt-tokens`.
- If `pricing.local.yaml` is invalid, the last valid table stays in use and `doctor` reports it.
- Antigravity often omits the model id; such calls are priced as `hosts.<host>.default_model` (default `gemini-3.8-flash`)
  and flagged `†`.

---

## 11. Configuration reference

`agent-meter config show` lists everything; change values with `agent-meter config set <key> <value>`.
The file is `~/.agent-meter/config.toml`.

| Key | Default | Meaning |
| :--- | :--- | :--- |
| `timezone` | your system zone | Day/month boundaries (e.g. `America/Bogota`) |
| `idle_threshold_s` | `120` | Gaps longer than this inside a task count as idle (not active time) |
| `stale_after_h` | `24` | A task with no end event is closed after this many hours of inactivity |
| `dev_hours_merge_gap_min` | `30` | Gaps between tasks longer than this are not counted as developer hours |
| `show_task_labels` | `true` | Show a short prompt excerpt in `tasks` (terminal only, never stored) |
| `notify` | `auto` | Desktop notifications: `auto` (session end + long tasks), `session`, `long-tasks`, `off` |
| `notify_min_task_s` | `120` | Minimum task duration for a "long task" notification |
| `claude_inline_summary` | `false` | Reserved (inline summaries inside Claude Code are off) |
| `store_agent_descriptions` | `false` | Reserved for v2, currently ignored (descriptions are always hashed) |
| `currency.display`, `currency.usd_rate` | — | Show a second currency, e.g. `COP` and `4100` (units per 1 USD) |
| `hosts.<host>.enabled` | `true` | Collect from `claude-code`, `antigravity-cli`, `antigravity-ide`, `antigravity-app` |
| `hosts.<host>.root` | (auto) | Custom data folder for that tool |
| `hosts.<host>.default_model` | `gemini-3.8-flash` for Antigravity | Model assumed when the tool does not record one |
| `bigquery.enabled` | `false` | Turned on by `setup --cloud` |
| `bigquery.project`, `bigquery.dataset`, `bigquery.location` | —, `agent_metrics`, `US` | Where data is uploaded |
| `bigquery.mode` | `billing` | `billing` or `sandbox` |
| `bigquery.anonymize_projects` | `false` | Upload project/client/remote/tag names as salted hashes |
| `bigquery.looker_template_id` | — | Optional template report id for a one-click Looker copy (not required) |

---

## 12. Hooks, scheduler and notifications

**Hooks** (added by `setup` with the `hooks` trigger, or by the optional plugin):

| Tool | File | Event |
| :--- | :--- | :--- |
| Claude Code | `~/.claude/settings.json` | `Stop` (end of each task) and `SessionEnd` |
| Antigravity (CLI, IDE, app) | `~/.gemini/config/hooks.json` (named hook `agent-meter`) | `Stop` (end of each task) |

The hook returns in under ~2 seconds, never blocks your agent, adds **nothing** to the agent's context (zero tokens),
always exits 0, and does the actual import in a detached background process. `~/.gemini/settings.json` (Gemini CLI) is
never modified.

**Scheduler:** every 15 minutes (macOS `launchd` user agent with `RunAtLoad`; Linux systemd user timer with
`Persistent=true`, or cron; Windows Task Scheduler `schtasks` task `com.agent-meter.collect`). It catches sessions that crashed or were never closed, and syncs to BigQuery in Option B.

**Notifications** appear only when useful:

```bash
agent-meter config set notify off               # never
agent-meter config set notify session           # only when a session ends
agent-meter config set notify long-tasks        # only tasks longer than notify_min_task_s
agent-meter config set notify_min_task_s 600    # "long" = 10 minutes
```

The summary is also always saved to `~/.agent-meter/last-summary.txt` (`agent-meter last` prints it).

---

## 13. Privacy and files

**Never stored or uploaded:** prompts, assistant messages, code, tool inputs or outputs, file paths, subagent descriptions
in clear text (salted hashes only), `cli.log`. Transcripts and tool databases are opened **read-only**.

**Stored:** token counts, timestamps, durations, model ids, project/client names (from git), agent types, tool names and
counts, errors as class names.

`~/.agent-meter/` (mode 0700):

| File | Contents |
| :--- | :--- |
| `meter.duckdb` | The local store |
| `config.toml` | Configuration |
| `projects.yaml` | Projects and clients |
| `pricing.local.yaml` | Your prices and aliases |
| `secret` | Local salt for hashes (never uploaded) |
| `last-summary.txt` | Last summary |
| `report.html` | Last report (default location) |
| `state/`, `outbox/`, `logs/`, `lock` | Internal state, BigQuery upload staging, error class names, concurrency lock |
| `install.json`, `backups/` | What `setup` changed, to undo it with `uninstall` |
| `.agent-meter-home` | Marker proving agent-meter created this folder |

---

## 14. Supported tools and data sources

| Tool | Read from | Notes |
| :--- | :--- | :--- |
| Claude Code | `~/.claude/projects/**/*.jsonl` (+ `subagents/`) | Full tokens, model, tasks and nested subagents; responses split over several lines are deduplicated by request id |
| Antigravity CLI | `~/.gemini/antigravity-cli/conversations/*.db` (+ transcripts, `conversation_summaries.db`) | Tokens, model and latency per call; subagents are child conversations |
| Antigravity IDE | `~/.gemini/antigravity-ide/` | Same format as the CLI; no session-end hook, so it relies on the `Stop` hook or the scheduler |
| Antigravity 2.0 app | `~/.gemini/antigravity/` | Older conversations stored as encrypted `.pb` files cannot be read; `doctor` lists them as *untracked history* |

---

## 15. Troubleshooting / FAQ

**Start with `agent-meter doctor`** (add `--cloud` for Option B). It checks hooks, scheduler, data formats, prices,
secret, store and untracked history and prints a fix for every problem.

| Problem | Fix |
| :--- | :--- |
| `agent-meter: command not found` | Make sure `~/.local/bin` (`%USERPROFILE%\.local\bin` on Windows) is on your `PATH` (`uv tool update-shell`), or reinstall (§4) |
| No data / old data | `agent-meter collect` (or check `doctor` for hooks/scheduler) |
| A cost shows `≥ $0.00` | That model has no price: `agent-meter pricing unpriced` shows the exact `pricing add`/`alias` command |
| The same project appears twice | `agent-meter projects merge <src> <dst>` |
| `store busy` (exit 4) | Another import is running (hook or scheduler); retry in a few seconds |
| Too many notifications | `agent-meter config set notify session` or `off` (§12) |
| Cloud: expired credentials | `gcloud auth application-default login` — local collection keeps working meanwhile; the next `sync` uploads the backlog |
| Cloud: "without a quota project" warning | `gcloud auth application-default set-quota-project <PROJECT_ID>` (harmless otherwise) |
| Cloud: missing permissions | Owner, or `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` on the project |
| Cloud: budget alert not created | The account needs Billing Account Administrator/Costs Manager on the billing account; the alert is optional |
| Looker shows old numbers | Run `agent-meter sync`, then *Refresh data* in the report |
| Looker table/donut filters everything | You clicked a row/slice (cross-filter): press **Reset** |
| Totals look wrong | `agent-meter verify --reconcile` (and `--cloud` for BigQuery) |

---

## 16. Uninstall

```bash
agent-meter uninstall                    # remove hooks + scheduler, restore your settings files; keeps your data
agent-meter uninstall --keep-scheduler   # remove only the hooks
agent-meter uninstall --purge --yes      # also delete ~/.agent-meter (only agent-meter's own files)
uv tool uninstall agent-meter            # finally remove the program
```

`uninstall` restores a settings file byte-for-byte only if you did not edit it after `setup`; otherwise it removes only
agent-meter's own entries. `--purge` refuses to delete `/`, your home folder, any folder that contains files
agent-meter did not create, or a folder without its marker.

The BigQuery dataset is **not** deleted automatically. Remove it yourself if you want:
`bq rm -r -d <PROJECT_ID>:agent_metrics`.

---

## 17. Development

```bash
cd tools/agent-meter
uv run --python 3.11 --extra dev pytest -q                    # unit + contract + integration (offline)
AGENT_METER_TEST_GCP_PROJECT=<PROJECT_ID> \
  uv run --python 3.11 --extra dev --extra bigquery pytest -m bigquery tests/cloud -q   # live BigQuery (temporary dataset, auto-deleted)
uv run --python 3.11 --extra dev ruff check .
uv run --python 3.11 --extra dev mypy --strict src
```

Design documents: [`docs/agent-metrics/`](../../docs/agent-metrics/) — PRD, ADR-001, interface contracts, pricing sources,
Looker Studio guide and the compliance report.

Implementation notes:

- `verify --reconcile` compares the store with an independent in-memory re-read of the transcripts that still exist. It
  works offline (it does not call `npx ccusage`). Transcripts the tool already deleted show up as store-only differences.
- Session-end markers (`SessionEnd`, Antigravity `Stop` with `fullyIdle`) are kept in the store, so later full re-reads
  keep the last task `done`.
- BigQuery uploads use batch load jobs only (no streaming inserts, no DML); dedup views expose the latest row per key.
