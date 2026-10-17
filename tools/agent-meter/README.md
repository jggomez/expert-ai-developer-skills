# agent-meter

Local-first token, **API-equivalent** cost and latency metrics for AI coding agents —
Claude Code and Antigravity (CLI, IDE and "Antigravity 2.0" app) — per project, client,
task and agent (including nested subagents).

- **Option A (local, default):** a DuckDB file, a session summary after each task or
  session, and a static offline HTML report. No network, no cloud account.
- **Option B (cloud, opt-in):** a BigQuery replica (`pip install "agent-meter[bigquery]"`)
  for Looker Studio dashboards, using load jobs only (free tier).

agent-meter only **reads** the transcripts and databases the hosts already write. It never
stores prompts, assistant text, code, tool inputs/outputs or file paths (privacy rule BR-16).
Every cost is labelled `≈` (API-equivalent). It is not what a subscription plan bills you.

## Install

Requires Python ≥ 3.11 (`uv` installs a managed interpreter for you).

```bash
uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
# or
pipx install --python python3.12 "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

agent-meter setup            # interactive: hosts, hooks and/or scheduler, backfill
agent-meter setup --local --yes   # non-interactive, zero network calls
```

Runtime dependencies are `duckdb`, `PyYAML` and `pytz`. DuckDB needs `pytz` to return
`TIMESTAMPTZ` values to Python. Every store connection runs with `TimeZone = 'UTC'`, so
fetched timestamps are timezone-aware UTC. Local-day bucketing happens in the SQL views
using the configured `timezone`.

## Everyday commands

| Command | What it does |
| :--- | :--- |
| `agent-meter collect [--host H] [--since D] [--full]` | Incremental ingest. Unchanged sessions are skipped and re-runs are idempotent |
| `agent-meter last [--project P] [--json]` | Last session summary, with today and month-to-date for the project across all hosts |
| `agent-meter tasks [--last [N]] [--session S] [--project P] [--tag T] [--since D] [--json]` | Per-task rollups with every subagent |
| `agent-meter report [--open] [--out F] [--month YYYY-MM] [--from D --to D] [--project P] [--client C]` | Self-contained HTML report |
| `agent-meter projects list [--json]` · `projects set <p> --name --client --billing hourly\|fixed --rate --price --currency` · `projects merge <a> <b>` | Projects and clients (`projects.yaml`) |
| `agent-meter hours set <p> <YYYY-MM-DD\|YYYY-MM> <h>` · `hours unset` · `hours list` | Manual dev-hours overrides. A manual value always wins |
| `agent-meter tag "<name>" [--last N] [--project P]` · `tag --clear` | Group tasks into a work item |
| `agent-meter pricing list\|unpriced\|add\|set\|alias\|remove\|validate` | Price table. Edits re-price history immediately, with no re-ingest |
| `agent-meter doctor [--json] [--cloud]` | Health check (hooks, scheduler, formats, unpriced models, untracked history) |
| `agent-meter config show\|get <k>\|set <k> <v>\|edit` | `config.toml`, e.g. `config set timezone America/Bogota` |
| `agent-meter verify --reconcile [--from D --to D] [--host H] [--cloud]` | Store vs a fresh independent re-read of the transcripts, or local vs BigQuery |
| `agent-meter sync [--full-reload] [--dry-run]` | Upload to BigQuery (Option B) |
| `agent-meter uninstall [--keep-scheduler] [--purge --yes]` | Remove hooks and scheduler and restore settings. Data is kept unless `--purge` |

Global flags: `--home <dir>` (or `$AGENT_METER_HOME`, default `~/.agent-meter`) and `--quiet`.
`--json` output is `json.dumps(obj, default=str, sort_keys=True)`.

Exit codes: `0` ok · `1` error · `2` usage · `3` doctor FAIL · `4` store busy · `5`
reconcile found a difference. **`hook` always exits 0.**

Task labels (a ≤ 40-character prompt excerpt) are shown **only** when `tasks` writes to an
interactive terminal. They are never written to the store, `last-summary.txt`, notifications,
the report or the cloud. Turn them off with `config set show_task_labels false`.

## Hooks (registered by `setup`, or by the optional `agent-metrics` plugin)

| Host | File | Command |
| :--- | :--- | :--- |
| Claude Code `SessionEnd` | `~/.claude/settings.json` | `<abs>/agent-meter hook --host claude-code --event session-end` (timeout 10) |
| Claude Code `Stop` | `~/.claude/settings.json` | `<abs>/agent-meter hook --host claude-code --event task-end` (timeout 10) |
| Antigravity `Stop` (CLI, IDE, app) | `~/.gemini/config/hooks.json` (named hook `agent-meter`) | `<abs>/agent-meter hook --host antigravity --event task-end` (timeout 10) |

The hook fast path reads at most 64 KiB of stdin and keeps only allowlisted keys. It spawns
a detached `hook-worker` and returns within an internal 2 s watchdog. For Claude Code it
prints nothing to stdout; for Antigravity it prints exactly `{}`. It never imports `duckdb`.
The worker ingests that one session, writes `~/.agent-meter/last-summary.txt` and sends a
desktop notification according to `config notify` (`auto`, `session`, `long-tasks` or `off`).

## Files

`~/.agent-meter/` (mode 0700) holds the following:

| File | Contents |
| :--- | :--- |
| `meter.duckdb` | The store (schema v1, `sql/duckdb/`) |
| `config.toml` | Configuration |
| `projects.yaml` | Projects and clients |
| `pricing.local.yaml` | Local price overrides and additions |
| `secret` | Local salt (never uploaded) |
| `state/snapshot.json` | Snapshot used when the store is busy |
| `last-summary.txt` | The last session summary |
| `logs/` | Exception class names only |
| `install.json`, `backups/` | Undo data for `uninstall` |
| `.agent-meter-home` | Marker proving agent-meter created this directory |

The directory gets mode 0700 only when agent-meter creates it (or it holds the marker).
Pointing `--home` at an existing directory never changes that directory's permissions.

`uninstall --purge` deletes only the entries listed above, plus `report.html`,
`meter.duckdb.wal` and `.*.tmp` leftovers, and then removes the directory. It refuses with
exit 2 and changes nothing when the directory is `/`, your home directory, an ancestor of
your home directory, a mount point or a symbolic link, or when it holds any other entry.
The marker is required. The one exception is a home created by an earlier build without
the marker: it is accepted when it holds only known entries.

The `store_agent_descriptions` config key is reserved for v2 and is currently ignored.
Subagent descriptions are always stored as salted hashes, and `setup` does not ask about them.

## Development

```bash
cd tools/agent-meter
uv run --python 3.11 --extra dev pytest -q                       # unit + contract + integration
uv run --python 3.11 --extra dev pytest -q -m bigquery           # live BigQuery (opt-in)
uv run --python 3.11 --extra dev ruff check src tests
uv run --python 3.11 --extra dev mypy --strict src
```

By default the suite skips the `bigquery`, `e2e` and `perf` markers. The integration tests
(`tests/integration/`) drive the CLI end to end over synthetic hosts in a temporary `HOME`,
with the network blocked. They assert that a privacy canary planted in every content slot
of the fixtures never reaches the store, snapshot, summary, report, logs or command output.

### Notes on the v1 behaviour

- **Reconciliation:** `verify --reconcile` compares the store with an independent
  in-memory re-read of the transcripts that still exist (deduplicated by call id, lowest
  owner rank wins), per host and local day. It does not shell out to `npx ccusage`, because
  the local mode must stay offline. Transcripts the host has already deleted (BR-15) show up
  as store-only differences.
- **Session ends:** `SessionEnd`, and Antigravity `Stop` with `fullyIdle`, are kept as
  markers in the store `meta` table. Later full re-reads therefore keep the last task `done`
  instead of reverting it to `in progress`.
- **Invalid local prices:** if `pricing.local.yaml` is invalid, the last valid price table
  stays in use. `doctor` reports the file as `FAIL`.
