# shared-context

> Cross-agent working memory: captures and restores architecture decisions across AI sessions, for Claude Code.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-orange?style=flat-square)](../../../docs/claude-code-installation.md)

`shared-context` keeps a plain-Markdown memory in the repo's `context/` directory, committed with git.
Claude Code and Google Antigravity read and write the same files, so one tool can pick up where the other stopped.
A session reads the short index `context/memory/MEMORY.md` at start and updates it when a task ships.
An optional session archive stores detailed snapshots, compressed as `tar.xz`.

## Requirements

| Needs | For | Required |
| :--- | :--- | :--- |
| `python3` on `PATH` | The `context_*.py` scripts and the MCP server | Yes |
| `node` on `PATH` | The three hooks | Yes; without it the hooks do nothing, the rest still works |
| `uv` on `PATH` | Starting the MCP server with no manual install | Recommended; otherwise `pip install "mcp<2"` |

## Installation

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install shared-context@expert-ai-developer-skills
```

Updates, per-project settings, local development and limitations: [Claude Code installation guide](../../../docs/claude-code-installation.md).

## Quick start

```text
Read context/memory/MEMORY.md and architecture.md before planning this feature.
```

```text
We're done. Update context/memory/ with the new architectural decisions and a log entry.
```

```text
Use the context-keeper agent to archive a full session snapshot and roll up decisions.
```

## What's included

### Agents

| Agent | Role | Model |
| :--- | :--- | :--- |
| `context-keeper` | Maintains `context/memory/` and the session archive in its own context window, so the main agent spends no tokens on bookkeeping | `haiku` |

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `SessionStart` (`startup`, `resume`, `clear`) | `hooks/session-start-context.js` | If `context/memory/MEMORY.md` exists, tells the agent to read it silently. Otherwise, if archived sessions exist, tells the agent to ask you what to load. At most once every 4 hours per repo. |
| `PostToolUse` (`Write`, `Edit`, `Bash`) | `hooks/post-tool-autosave.js` | Counts tool calls once `context/` exists. Silent when `MEMORY.md` exists; with the archive only, nudges a checkpoint after 25 calls or 10 minutes. Never blocks. |
| `Stop` | `hooks/stop-flush.js` | If `context/` exists and the session used tools, reminds the agent to update `context/memory/` (or flush the archive). Never blocks. |

### MCP servers

| Server | Command | Purpose |
| :--- | :--- | :--- |
| `shared-context` | `sh ${CLAUDE_PLUGIN_ROOT}/mcp/run-server.sh` (stdio) | `context_list`, `context_snapshot`, `context_read`, `context_write`, `context_pack`, `context_unpack`, `context_rollup`, `context_search` |

The launcher uses `uv run --with 'mcp<2'` when `uv` exists. Otherwise it uses a Python that already has the v1 MCP SDK. If neither works it exits with a hint; the scripts under `skills/context-*/scripts/` still work without it.

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`context-restore`** | Reads `context/memory/MEMORY.md` at session start and opens topic pages on demand; lists archived sessions with `context_list.py` and loads them only after you confirm |
| **`context-capture`** | Updates `context/memory/` when a task ships; redacts secrets; archives sessions with `context_snapshot.py`, `context_pack.py` and `context_rollup.py` |

## How it works

The `context/` directory is created in your repo on first capture. It is not shipped with the plugin.

```text
context/
├── memory/
│   ├── MEMORY.md            # short index read at session start
│   ├── architecture.md      # durable architecture decisions
│   ├── conventions.md       # coding conventions and stack rules
│   └── log/YYYY-MM-DD.md    # one short block per shipped milestone
├── .contextrc.json          # autosave, compression, retention, redaction
└── YYYY-MM-DD/<session>/    # optional archive: manifest.json, summary.md, decisions.md, detail.tar.xz
```

Only `MEMORY.md` is read up front. Topic pages and the archive are opened when a task needs them.
Updates happen when a task ships or when you ask to save context, not on every turn.
Records are redacted on write, but this is not a secret store: keep credentials out.

## Configuration

| Setting | Default | Effect |
| :--- | :--- | :--- |
| `SHARED_CONTEXT_DIR` | `./context` | Location of the store, for the MCP server and scripts |
| `SHARED_CONTEXT_PYTHON` | unset | Python the launcher tries first when `uv` is missing |
| `SHARED_CONTEXT_AGENT`, `SHARED_CONTEXT_MODEL`, `SHARED_CONTEXT_USER` | unset | Provenance recorded in archived session manifests |
| `context/.contextrc.json` `autosave` | `everyNToolCalls: 25`, `everyMinutes: 10` | Checkpoint nudge thresholds for the archive |
| `context/.contextrc.json` `restore.askBeforeLoad` | `true` | Ask before loading archived sessions |

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `shared-context: MCP server not started` | Neither `uv` nor a Python with the v1 MCP SDK is available (mcp 2.x renamed `FastMCP`) | Install `uv`, or `pip install "mcp<2"` |
| No memory prompt at session start | No `context/memory/MEMORY.md` yet, or it already fired in the last 4 hours | Create the store with `context-capture`; wait for the debounce |
| Hooks do nothing | `node` is not on `PATH` | Install Node.js |
| Stop reminder never appears | No `context/` directory, or no tool calls this session | Expected; it only fires after work in a repo with a store |

## Related plugins

- [`senior-dev`](../senior-dev/README.md), [`senior-data-engineer`](../senior-data-engineer/README.md) and [`sql-query-optimizer`](../sql-query-optimizer/README.md) bundle the same two skills.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
