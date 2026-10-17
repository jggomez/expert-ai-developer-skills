# `agent-metrics` Plugin (Claude Code)

**Optional** convenience plugin for [`agent-meter`](../../../tools/agent-meter/README.md): token, API-equivalent cost and latency metrics for Claude Code and Antigravity, per project, client, task and subagent.

The plugin is opt-in and fully decoupled:

- No other plugin in this repository depends on it, references it or bundles its skill. Installing or removing it changes nothing else.
- `agent-meter` works **without this plugin**: install the CLI and run `agent-meter setup`, which can register the same hooks directly in `~/.claude/settings.json`. The plugin is just another way to register them.
- The hooks are thin wrappers. If the CLI is not installed they do nothing: they exit 0 and print one hint line to stderr.

Overview, options and privacy: [docs/agent-metrics/README.md](../../../docs/agent-metrics/README.md).

---

## 1. What It Installs

```
plugins/claude/agent-metrics/
├── .claude-plugin/plugin.json   # Claude Code manifest ("hooks": "./hooks.json")
├── hooks.json                   # SessionEnd + Stop → hooks/agent-meter-hook.js
├── hooks/
│   └── agent-meter-hook.js      # runs `agent-meter hook …` with the payload on stdin
├── README.md
└── skills/
    └── agent-metrics/           # mirror of /skills/agent-metrics
```

| Event | Command | Timeout |
| :--- | :--- | :---: |
| `SessionEnd` | `node "${CLAUDE_PLUGIN_ROOT}/hooks/agent-meter-hook.js" --host claude-code --event session-end` → `agent-meter hook --host claude-code --event session-end` | 10 s |
| `Stop` (end of every task) | `node "${CLAUDE_PLUGIN_ROOT}/hooks/agent-meter-hook.js" --host claude-code --event task-end` → `agent-meter hook --host claude-code --event task-end` | 10 s |

Wrapper contract:

- It always exits `0` and never blocks Claude Code.
- It writes **nothing to stdout**, so there is zero token overhead: nothing reaches the model context. The CLI's own stdout is discarded.
- It enforces its own timeout (`AGENT_METER_HOOK_TIMEOUT_MS`, default 8000 ms, clamped to 100–9000 ms) below the 10 s host timeout, and kills a hung CLI.
- It looks for `agent-meter` on `PATH`, then in `~/.local/bin` (the default for `uv tool` and `pipx`). If neither has it, it prints `agent-meter not installed: see <docs url>` to stderr and exits 0.
- The CLI keeps only allowlisted payload keys (`session_id`, `transcript_path`, `cwd`, `hook_event_name`, `reason`, `stop_hook_active`). It hands off to a detached worker and returns within about 2 s.

## 2. Install

1. Install the CLI (Python ≥ 3.11; `uv` provisions it):

   ```bash
   uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
   # or: pipx install --python python3.12 "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
   ```

2. Install the plugin:

   ```bash
   /plugin marketplace add jggomez/expert-ai-developer-skills
   /plugin install agent-metrics@expert-ai-developer-skills
   # or from a local checkout:
   claude plugin install plugins/claude/agent-metrics
   ```

3. Run the setup wizard (backfill, scheduler, projects, optional cloud):

   ```bash
   agent-meter setup --local      # Option A: local only, zero network calls
   agent-meter setup --cloud --gcp-project <project> --mode billing   # Option B: + BigQuery
   ```

   The wizard detects the enabled plugin (`enabledPlugins` in `~/.claude/settings.json`) and **does not add user-level hooks**, so events are not registered twice. Even if they were, ingestion is idempotent and notifications are deduplicated.

4. Check the installation with `agent-meter doctor`. After your next task, `agent-meter last` or `agent-meter tasks --last` prints a summary.

## 3. Uninstall

```bash
/plugin uninstall agent-metrics        # removes the plugin hooks
agent-meter uninstall                  # removes the scheduler and any user-level hooks; keeps the data
agent-meter uninstall --purge --yes    # also deletes ~/.agent-meter/
uv tool uninstall agent-meter
```

## 4. Bundled Skills

- **`agent-metrics`**: guides `agent-meter setup` (local vs cloud, billing vs sandbox), explains the metrics, keeps prices correct (`agent-meter pricing`), runs `agent-meter doctor`, and writes ad-hoc DuckDB / BigQuery queries.

> **Maintaining the bundled skill**: `skills/agent-metrics/` is a physical copy of `/skills/agent-metrics`. After editing the canonical file, run `python3 scripts/sync_plugin_skills.py` from the repo root.
