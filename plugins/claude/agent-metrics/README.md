# agent-metrics

> Optional hooks that hand each finished task and session to the `agent-meter` CLI.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-orange?style=flat-square)](../../../docs/claude-code-installation.md)

`agent-metrics` is an optional convenience plugin for [`agent-meter`](../../../tools/agent-meter/README.md):
token, API-equivalent cost and latency metrics per project, client, task and subagent. It only registers
two hooks that call the CLI. `agent-meter setup` can register the same hooks without the plugin. No other
plugin depends on it. Overview and privacy: [docs/agent-metrics/README.md](../../../docs/agent-metrics/README.md).

## Requirements

- Claude Code with plugin support and `node` on `PATH`.
- The `agent-meter` CLI (Python >= 3.11, installed by `uv`). The plugin does nothing without it.

## Installation

1. Install the CLI:

   ```bash
   uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
   ```

2. Install the plugin:

   ```bash
   claude plugin marketplace add jggomez/expert-ai-developer-skills
   claude plugin install agent-metrics@expert-ai-developer-skills
   ```

3. Run the setup wizard. It detects the enabled plugin (`enabledPlugins` in `~/.claude/settings.json`)
   and does not add user-level hooks, so events are not registered twice.

   ```bash
   agent-meter setup --local                                         # Option A: local only, no network calls
   agent-meter setup --cloud --gcp-project <project> --mode billing  # Option B: adds BigQuery
   ```

More install options (pipx, BigQuery extra, local clone): [tools/agent-meter/README.md](../../../tools/agent-meter/README.md).
Plugin updates and project scope: [docs/claude-code-installation.md](../../../docs/claude-code-installation.md).

## Quick start

```bash
agent-meter doctor          # check hooks, scheduler, prices
agent-meter last            # summary of your last session
agent-meter tasks --last 5  # the last 5 tasks, with every subagent
```

## What's included

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`agent-metrics`** | Guides `agent-meter setup` (local vs cloud, billing vs sandbox), explains the metrics, fixes prices with `agent-meter pricing`, runs `agent-meter doctor`, writes DuckDB / BigQuery queries. |

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `SessionEnd` | `hooks/agent-meter-hook.js` | Runs `agent-meter hook --host claude-code --event session-end` with the payload on stdin. |
| `Stop` | `hooks/agent-meter-hook.js` | Runs `agent-meter hook --host claude-code --event task-end` with the payload on stdin. |

## How it works

1. Both hooks run the same Node wrapper with a 10 s host timeout.
2. The wrapper looks for `agent-meter` on `PATH`, then in `~/.local/bin`.
3. It always exits 0 and writes nothing to stdout, so nothing reaches the model context.
4. The CLI keeps only allowlisted payload keys (`session_id`, `transcript_path`, `cwd`, `hook_event_name`, `reason`, `stop_hook_active`).
5. The CLI hands off to a detached worker and returns in about 2 s.

## Configuration

| Variable | Default | Effect |
| :--- | :--- | :--- |
| `AGENT_METER_HOOK_TIMEOUT_MS` | `8000` | Wrapper timeout before it kills a hung CLI. Clamped to 100-9000 ms. |

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| stderr shows `agent-meter not installed: see <url>` | CLI not on `PATH` or in `~/.local/bin`. | Install it with `uv tool install` (above); run `uv tool update-shell`. |
| stderr shows `timed out` | CLI ran longer than the wrapper timeout. | Run `agent-meter doctor`; raise `AGENT_METER_HOOK_TIMEOUT_MS` if needed. |
| No data after a task | Hooks or scheduler not set up. | Run `agent-meter doctor`, then `agent-meter collect`. |
| A cost shows `≥ $0.00` | The model has no price. | `agent-meter pricing unpriced` prints the fix command. |

## Uninstall

```bash
/plugin uninstall agent-metrics        # removes the plugin hooks
agent-meter uninstall                  # removes the scheduler and user-level hooks; keeps the data
agent-meter uninstall --purge --yes    # also deletes ~/.agent-meter/
uv tool uninstall agent-meter
```

## Related plugins

- [shared-context](../shared-context/README.md): cross-session memory in `context/`.
- [senior-dev](../senior-dev/README.md): orchestrated SDLC whose subagents the metrics break down.

## Maintenance

`skills/agent-metrics/` is a copy of `/skills/agent-metrics`. After editing it, run
`python3 scripts/sync_plugin_skills.py` from the repo root.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
