# agent-meter: Token, Cost and Latency Metrics for AI Coding Agents

`agent-meter` gives a developer visibility, per project, into what their AI coding agents cost and how they perform. It covers **Claude Code** and **Antigravity** (CLI, IDE and app), including when the same project moves between hosts from one day to the next. It is local-first, runs at **$0**, and is entirely **optional**.

> **User guides:** step-by-step install and usage for both options (local and BigQuery + Looker Studio) live in
> [`tools/agent-meter/README.md`](../../tools/agent-meter/README.md) (English) and
> [`tools/agent-meter/README.es.md`](../../tools/agent-meter/README.es.md) (español). This page is the design overview.

It reads the transcripts and databases that the hosts already write in real time, so nothing is lost on a crash or an unclean exit. It is an **idempotent, incremental collector**: running it twice never double-counts. The local store is the source of truth, and the cloud is only a replica.

| Metric | Why it matters |
| :--- | :--- |
| API-equivalent cost (`≈ USD`) per project, client, host, model and day | Margins, plan choice, monthly invoices |
| Tokens by type (input / output / cache write / cache read) and cache hit ratio | The real cost drivers. Cache reads dominate raw totals |
| Task latency P50 / P95 / P99, active time vs wall-clock | Normal experience vs stuck or looping tasks |
| Per-task rollup: subagents by type, max spawn depth, parallelism, critical path, retries | What a multi-agent run costs and where its time goes |
| AI cost vs billable value per client and month | "AI cost was 4% of what I billed client Z" |
| Tool-call counts and files touched (counts only) | What the agent did, with no content stored |

## Option A vs Option B

| | **Option A: Local** (default, always on) | **Option B: Cloud** (opt-in, on top of A) |
| :--- | :--- | :--- |
| Audience | Anyone, with no cloud account | Developers with a GCP project |
| Storage | DuckDB at `~/.agent-meter/meter.duckdb` | A + BigQuery dataset `agent_metrics` (load jobs only) |
| Visualization | Summary after each task or session, `agent-meter last` / `tasks`, offline HTML report (`agent-meter report --open`) | Looker Studio dashboard with drill-down project → session → task → agent run → call |
| Network | None. `setup --local --yes` makes zero network calls | BigQuery load jobs. Offline periods queue in a local outbox and upload later |
| Cost | $0 | $0 within the BigQuery free tier |
| Modes | — | `billing` (billing linked, optional $1 budget alert that notifies but **does not cap** spend) or `sandbox` (no billing, 60-day table expiry, weekly full reload) |

Looker Studio shows **the same totals** as the local report: `agent-meter verify --reconcile --cloud` must report 0 differences.

## Install Channels

The CLI is the product. Both plugins are optional ways to register its hooks.

| Channel | For | How |
| :--- | :--- | :--- |
| **1. Standalone CLI** (primary) | Anyone, with or without this repo's plugins | `uv tool install` or `pipx install`, then `agent-meter setup`. With consent, it registers the hooks in `~/.claude/settings.json` and `~/.gemini/config/hooks.json` (backed up and merged, never overwritten) and/or a scheduler (`launchd` on macOS, `systemd`/`cron` on Linux, Task Scheduler `schtasks` on Windows) |
| **2. Optional `agent-metrics` plugin** | Marketplace users who prefer plugins | [Claude Code plugin](../../plugins/claude/agent-metrics/README.md) or [Antigravity plugin](../../plugins/antigravity/agent-metrics/README.md). It ships the hooks and a setup skill. The hooks do nothing (exit 0, one stderr hint) if the CLI is missing |
| **3. No hooks at all** | Users who do not want any host hook | Scheduler only (every 15 min), or a manual `agent-meter collect`. Summaries come from `agent-meter last` / `agent-meter tasks --last` |

```bash
# macOS, Linux or Windows (PowerShell/CMD or WSL2, %USERPROFILE%\.local\bin) — Python ≥ 3.11 (uv installs a managed interpreter for you)
uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
# or
pipx install --python python3.12 "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

agent-meter setup --local                                         # Option A
agent-meter setup --cloud --gcp-project <project> --mode billing  # Option B (needs the [bigquery] extra)
agent-meter doctor
```

No existing plugin or skill in this repository depends on agent-meter, references it, or behaves differently because of it. The package imports nothing from `plugins/`, `skills/` or `scripts/`. `tests/structure/test_agent_meter_decoupling.py` enforces both rules.

## Hooks

| Host | Event | Command | Output |
| :--- | :--- | :--- | :--- |
| Claude Code | `SessionEnd` | `agent-meter hook --host claude-code --event session-end` | nothing on stdout |
| Claude Code | `Stop` (every task) | `agent-meter hook --host claude-code --event task-end` | nothing on stdout |
| Antigravity | `Stop` (every task) | `agent-meter hook --host antigravity --event task-end` | exactly `{}` |

Every hook always exits 0, has a 10 s host timeout and an internal 2 s watchdog, and hands the work to a detached worker. Hooks never write into the agent's context, so they add zero token overhead. Antigravity has no session-exit event, so its session view is `agent-meter last`, and the Antigravity IDE is covered by the scheduler.

## Commands

| Command | What it does |
| :--- | :--- |
| `agent-meter setup [--local\|--cloud] [--yes] [--hosts …] [--triggers …] [--gcp-project P] [--mode billing\|sandbox] [--no-backfill]` | Idempotent wizard: hosts, backfill, triggers, privacy, cloud prerequisites |
| `agent-meter collect [--host H] [--since D] [--full]` | Incremental ingest |
| `agent-meter last` · `agent-meter tasks [--last N]` | Last session summary, per-task rollups |
| `agent-meter report [--open] [--month YYYY-MM] [--project P] [--client C]` | Self-contained offline HTML report |
| `agent-meter projects list\|set\|merge` · `agent-meter hours set\|unset\|list` · `agent-meter tag "<name>"` | Projects and clients, dev-hours overrides, work items |
| `agent-meter pricing list\|unpriced\|add\|set\|alias\|remove\|validate` | Versioned price table. Edits re-price history immediately |
| `agent-meter doctor [--cloud]` | Health check: hooks, scheduler, formats, unpriced models, cloud lag |
| `agent-meter verify --reconcile [--cloud]` | Store vs a fresh re-read of the transcripts, or local vs BigQuery |
| `agent-meter sync [--full-reload] [--dry-run]` | Upload to BigQuery |
| `agent-meter config show\|get\|set\|edit` | `~/.agent-meter/config.toml` |
| `agent-meter uninstall [--purge --yes]` | Removes hooks and scheduler and restores settings. Data is kept unless `--purge`, which deletes only agent-meter's own files and refuses `/`, `$HOME`, its ancestors, mount points and directories with foreign entries |

The full reference is in the [package README](../../tools/agent-meter/README.md).

## Privacy

- **Stored**: only numbers and metadata, such as token counts, timestamps, model ids, tool names with call/error counts, and file counts.
- **Never stored**: prompts, assistant text, code, tool inputs or outputs, file paths, or credentials.
- **Transcripts**: opened read-only and never modified.
- **Hook payloads**: reduced to an allowlist of keys. Everything else, e.g. `last_assistant_message`, is discarded unread.
- **Subagent descriptions**: always stored as salted hashes. The `store_agent_descriptions` key is reserved for v2 and is currently ignored.
- **Task labels**: a short prompt excerpt, shown only on an interactive terminal and never persisted.
- **Cloud upload**: with `anonymize_projects = true`, project names, clients, remote URLs and work-item tags are replaced by salted HMAC hashes before upload. The salt never leaves `~/.agent-meter/secret`.
- **Removal**: `agent-meter uninstall` restores the host settings files byte-for-byte when they are unchanged since setup. Otherwise it removes only its own entries.

## Documents

| Document | Contents |
| :--- | :--- |
| [PRD.md](PRD.md) | Personas, user stories (US-01..US-17), business rules, NFRs |
| [ADR-001-agent-meter.md](ADR-001-agent-meter.md) | Architecture decisions: readers, schema v1, triggers and hooks (§3.10), BigQuery sink (§3.11) |
| [contracts.md](contracts.md) | Interface contracts, DuckDB schema, store views, outbox and BigQuery tables |
| [looker-studio.md](looker-studio.md) | Building the Looker Studio dashboard over the BigQuery views |
| [pricing-sources.md](pricing-sources.md) | Where every seeded price comes from |
| [spike-notes.md](spike-notes.md) | Verified host facts: transcript formats, hook events and payloads |
| [build-notes.md](build-notes.md) | Build-phase notes and accepted deviations |
