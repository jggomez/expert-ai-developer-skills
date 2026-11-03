# agent-metrics

> Optional hook that hands each finished task to the `agent-meter` CLI.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Antigravity-4285F4?style=flat-square)](.)

`agent-metrics` is an optional convenience plugin for [`agent-meter`](../../../tools/agent-meter/README.md):
token, API-equivalent cost and latency metrics per project, client, task and subagent. It only registers
one `Stop` hook that calls the CLI. `agent-meter setup` can register the same hook in
`~/.gemini/config/hooks.json` without the plugin. No other plugin depends on it.
Overview and privacy: [docs/agent-metrics/README.md](../../../docs/agent-metrics/README.md).

## Requirements

- Google Antigravity with the `agy` CLI, and `node` on `PATH`.
- The `agent-meter` CLI (Python >= 3.11, installed by `uv`). The plugin does nothing without it.

## Installation

1. Install the CLI:

   ```bash
   uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
   ```

2. Install the plugin:

   ```bash
   agy plugin install ./plugins/antigravity/agent-metrics
   ```

3. Run the setup wizard. It detects the installed plugin (`~/.gemini/config/plugins/agent-metrics`)
   and does not add the user-level named hook, so the event is not registered twice.

   ```bash
   agent-meter setup --local                                         # Option A: local only, no network calls
   agent-meter setup --cloud --gcp-project <project> --mode billing  # Option B: adds BigQuery
   ```

More install options (pipx, BigQuery extra, local clone): [tools/agent-meter/README.md](../../../tools/agent-meter/README.md).

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
| `Stop` | `hooks/agent-meter-hook.js` | Runs `agent-meter hook --host antigravity --event task-end` with the payload on stdin. |

`hooks.json` holds only the named hook object `agent-metrics`. A top-level string key such as
`"description"` would make the Antigravity loader reject the whole file.

## How it works

1. The wrapper runs from the plugin folder with a 10 s host timeout.
2. It looks for `agent-meter` on `PATH`, then in `~/.local/bin`.
3. It always exits 0 and prints exactly `{}` on stdout, which allows the stop.
4. The CLI keeps only allowlisted payload keys (`conversationId`, `transcriptPath`, `workspacePaths`, `terminationReason`, `fullyIdle`, `executionNum`).
5. Antigravity has no session-exit event. The scheduler (every 15 min) closes idle sessions and covers the IDE.
6. A `Stop` from a child conversation, or with `fullyIdle = false`, is ingested without a notification.

## Configuration

| Variable | Default | Effect |
| :--- | :--- | :--- |
| `AGENT_METER_HOOK_TIMEOUT_MS` | `8000` | Wrapper timeout before it kills a hung CLI. Clamped to 100-9000 ms. |

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| stderr shows `agent-meter not installed: see <url>` | CLI not on `PATH` or in `~/.local/bin`. | Install it with `uv tool install` (above); run `uv tool update-shell`. |
| stderr shows `timed out` | CLI ran longer than the wrapper timeout. | Run `agent-meter doctor`; raise `AGENT_METER_HOOK_TIMEOUT_MS` if needed. |
| No data after a task | Hook or scheduler not set up. | Run `agent-meter doctor`, then `agent-meter collect`. |
| A cost shows `≥ $0.00` | The model has no price. | `agent-meter pricing unpriced` prints the fix command. |

## Uninstall

```bash
agy plugin uninstall agent-metrics     # removes the plugin hook
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
