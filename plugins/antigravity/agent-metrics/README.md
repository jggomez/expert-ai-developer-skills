# `agent-metrics` Plugin (Antigravity)

**Optional** convenience plugin for [`agent-meter`](../../../tools/agent-meter/README.md): token, API-equivalent cost and latency metrics for Antigravity (CLI, IDE and app) and Claude Code, per project, client, task and subagent.

The plugin is opt-in and fully decoupled:

- No other plugin in this repository depends on it, references it or bundles its skill. Installing or removing it changes nothing else.
- `agent-meter` works **without this plugin**: install the CLI and run `agent-meter setup`, which can register the same hook directly in `~/.gemini/config/hooks.json` as the named hook `agent-meter`. The plugin is just another way to register it.
- The hook is a thin wrapper. If the CLI is not installed it does nothing: it prints `{}`, exits 0 and writes one hint line to stderr.

Overview, options and privacy: [docs/agent-metrics/README.md](../../../docs/agent-metrics/README.md).

---

## 1. What It Installs

```
plugins/antigravity/agent-metrics/
├── plugin.json                  # Antigravity manifest
├── .claude-plugin/plugin.json   # same name, required by the repo layout
├── hooks.json                   # named hook "agent-metrics": Stop → hooks/agent-meter-hook.js
├── hooks/
│   └── agent-meter-hook.js      # runs `agent-meter hook …` with the payload on stdin
├── README.md
└── skills/
    └── agent-metrics/           # mirror of /skills/agent-metrics
```

`hooks.json` contains **only** the named hook object. It has no top-level `"description"` string, because the Antigravity loader rejects a whole `hooks.json` that has a top-level non-object key (`cannot unmarshal string … JSONHookSpec`).

| Event | Command (run from the plugin folder) | Timeout |
| :--- | :--- | :---: |
| `Stop` (end of every task) | `node ./hooks/agent-meter-hook.js --host antigravity --event task-end` → `agent-meter hook --host antigravity --event task-end` | 10 s |

Antigravity has no session-exit event. The "session" view is `agent-meter last`, and the scheduler closes idle sessions. The Antigravity IDE fires no hook that agent-meter can rely on, so it is covered by the scheduler (every 15 min).

Wrapper contract:

- It always exits `0`. Antigravity runs hooks synchronously, so the wrapper never holds the loop.
- stdout is **exactly `{}`**: Antigravity requires a JSON object, and `{}` allows the stop. The CLI's own stdout is discarded.
- It enforces its own timeout (`AGENT_METER_HOOK_TIMEOUT_MS`, default 8000 ms, clamped to 100–9000 ms) below the 10 s host timeout, and kills a hung CLI.
- It looks for `agent-meter` on `PATH`, then in `~/.local/bin` (the default for `uv tool` and `pipx`). If neither has it, it prints `agent-meter not installed: see <docs url>` to stderr.
- The CLI keeps only allowlisted payload keys (`conversationId`, `transcriptPath`, `workspacePaths`, `terminationReason`, `fullyIdle`, `executionNum`). It hands off to a detached worker and returns within about 2 s. A `Stop` from a child conversation, or with `fullyIdle = false`, is ingested without a notification.

## 2. Install

1. Install the CLI (Python ≥ 3.11; `uv` provisions it):

   ```bash
   uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
   # or: pipx install --python python3.12 "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
   ```

2. Install the plugin:

   ```bash
   agy plugin install ./plugins/antigravity/agent-metrics
   ```

3. Run the setup wizard (backfill, scheduler, projects, optional cloud):

   ```bash
   agent-meter setup --local      # Option A: local only, zero network calls
   agent-meter setup --cloud --gcp-project <project> --mode billing   # Option B: + BigQuery
   ```

   The wizard detects the installed plugin (`~/.gemini/config/plugins/agent-metrics`) and **does not add the user-level named hook**, so the event is not registered twice. Even if it were, ingestion is idempotent and notifications are deduplicated. `~/.gemini/settings.json` belongs to Gemini CLI and is never edited.

4. Check the installation with `agent-meter doctor`. After your next task, `agent-meter last` or `agent-meter tasks --last` prints a summary.

## 3. Uninstall

```bash
agy plugin uninstall agent-metrics     # removes the plugin hook
agent-meter uninstall                  # removes the scheduler and any user-level hooks; keeps the data
agent-meter uninstall --purge --yes    # also deletes ~/.agent-meter/
uv tool uninstall agent-meter
```

## 4. Bundled Skills

- **`agent-metrics`**: guides `agent-meter setup` (local vs cloud, billing vs sandbox), explains the metrics, keeps prices correct (`agent-meter pricing`), runs `agent-meter doctor`, and writes ad-hoc DuckDB / BigQuery queries.

> **Maintaining the bundled skill**: `skills/agent-metrics/` is a physical copy of `/skills/agent-metrics`. After editing the canonical file, run `python3 scripts/sync_plugin_skills.py` from the repo root.
