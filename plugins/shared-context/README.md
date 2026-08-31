# `shared-context` Plugin

**Cross-agent working memory for Claude Code and Antigravity CLI.**

The `shared-context` plugin lets different AI coding agents hand off to each
other through a committed `context/` directory in the repo. When an agent
finishes a task — or at a periodic checkpoint — it records *what was done, why,
and how*; the next agent (on either host) is prompted at start-up to load that
context, but only with the user's explicit OK.

Its `agents/`, `skills/`, `hooks.json` (`"hooks"` key), `.mcp.json`, and
`${CLAUDE_PLUGIN_ROOT}` layout follow the **Claude Code plugin format**; the
root `plugin.json`, the `shared-context-relay` group in `hooks.json`,
`mcp_config.json`, and `rules/` cover **Antigravity CLI**. One folder,
`agy plugin install`-safe, loads on both.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of
> `context-capture` and `context-restore` in the root `/skills` catalog. After
> editing either under `/skills`, run `python3 scripts/sync_plugin_skills.py`
> from the repo root. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills`
> fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/shared-context/
├── .claude-plugin/plugin.json   # Claude Code manifest
├── plugin.json                  # Antigravity manifest (same content)
├── README.md
├── .mcp.json                    # Claude Code MCP config (stdio: sh mcp/run-server.sh)
├── mcp_config.json              # Antigravity MCP config (same launcher)
├── hooks.json                   # "hooks" key (Claude Code) + "shared-context-relay" group (Antigravity)
├── hooks/
│   ├── session-start-context.js # start-of-session: prompt to load prior context (CC SessionStart / AGY PreInvocation, debounced)
│   ├── post-tool-autosave.js    # PostToolUse: checkpoint nudge every N tool calls / T minutes (non-blocking)
│   └── stop-flush.js            # Stop: remind to flush + roll up + compress (non-blocking)
├── rules/
│   └── shared-context-rules.md  # Antigravity auto-loads (no SessionStart event there)
├── mcp/
│   ├── run-server.sh           # launcher: `uv run --with 'mcp<2'` (zero manual install), falls back to a local mcp
│   └── mcp_server.py           # stdio MCP: context_list/snapshot/read/write/pack/unpack/rollup/search
├── agents/
│   └── context-keeper.md        # host-neutral subagent: restore + capture + rollup, off the main context window
└── skills/
    ├── context-capture/         # mirror of /skills/context-capture
    └── context-restore/         # mirror of /skills/context-restore
```

The `context/` directory itself is created in the target repo on first capture,
not shipped here. Its layout:

```
context/
├── INDEX.md                     # generated table of all sessions, newest first
├── preferences.md               # long-lived, cross-session user preferences
├── architecture.md              # append-only decision log (built by the rollup)
├── .contextrc.json             # autosave / compression / retention / redaction config
├── .gitattributes              # *.tar.xz marked binary
└── <YYYY-MM-DD>/<HH-MM-SS-host-user>/
    ├── manifest.json            # host, agent, model, git branch/HEAD, status, task   (loose)
    ├── summary.md               # what was done, current state, next steps            (loose)
    ├── decisions.md             # decisions with trade-offs; rolled into architecture (loose)
    └── detail.tar.xz            # flows.md, topics.md, files-touched.json, git-context (packed)
```

Each session keeps `manifest` + `summary` + `decisions` uncompressed so the
store browses and diffs cleanly in a PR; the heavier detail is packed with
`xz` (Python stdlib `tarfile`, no external binary). `context_rollup.py` applies
retention: sessions past `maxSessions` / `maxAgeDays` are fully archived into
`full.tar.xz`.

---

## 2. The Agent

**`context-keeper`** — a host-neutral subagent (`model: inherit`, explicit
`subagent`/`mainAgent`, no `tools` key). It does the restore/capture/rollup
bookkeeping in its own context window so the main agent doesn't spend tokens on
it. Invoke it directly ("use the context-keeper agent to save this session") or
let the main agent delegate to it.

---

## 3. Model Context Protocol (`.mcp.json` / `mcp_config.json`)

Both configs run `sh mcp/run-server.sh`, which starts `mcp/mcp_server.py` — a
stdio MCP server exposing the store with **identical tool names on both hosts**
(no `Bash` vs `run_command` split):

| Tool | Purpose |
| :--- | :--- |
| `context_list` | list sessions (read-only); `exists` boolean drives the start-up prompt |
| `context_snapshot` | create / update this session's record + git snapshot |
| `context_read` | read one file from a session or a long-lived file |
| `context_write` | write/append one agent-editable markdown file (redacted on write) |
| `context_pack` / `context_unpack` | compress / restore a session's detail |
| `context_rollup` | decisions → `architecture.md`, regenerate `INDEX.md`, retention |
| `context_search` | case-insensitive regex search across `context/` |

The launcher gets the MCP SDK for you via `uv` (nothing to `pip install`) — see
§7. If it can't, the bundled scripts under `skills/context-*/scripts/` still
work standalone.

---

## 4. Bundled Skills (2 Packaged Modules)

| Skill | Role |
| :--- | :--- |
| **`context-capture`** | How to write a well-formed session record: the schema, the "would another agent be worse off not knowing this?" bar, secret redaction, `tar.xz` compression, and decision rollup. Scripts: `context_snapshot.py`, `context_pack.py`, `context_rollup.py`. |
| **`context-restore`** | How to load prior context at session start: list, rank relevance, **ask the user** which set to load, then adopt decisions/preferences explicitly. Script: `context_list.py`. |

---

## 5. What This Plugin Is *Not*

- Not automatic memory — nothing is loaded without the user's OK.
- Not a secret store — records are redacted on write; still keep credentials out.
- Not cross-repo — the store is per-repo `context/`, shared via git.

---

## 6. Example Prompts

- "Check the shared context and tell me what previous sessions did before we start."
- "We're done — use the context-keeper agent to save this session and roll up the decisions."
- "Checkpoint the shared context now, then keep going."
- "Load only the architecture decisions and preferences, not the full history."

---

## 7. Requirements

| Needs | For | Required? |
| :--- | :--- | :--- |
| **`python3`** on `PATH` | the `context_*.py` scripts and the MCP server | **yes** |
| **`node`** on `PATH` | the three `hooks/*.js` (start prompt, checkpoint nudge, stop flush) | **yes** — without it the hooks are inert; skills + agent + MCP still work |
| **`uv`** on `PATH` | the MCP server, with zero manual install | **recommended** — `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

**The MCP server, made easy.** `.mcp.json` / `mcp_config.json` don't run Python
directly — they run the launcher `mcp/run-server.sh`, which:

1. if **`uv`** is installed → `uv run --no-project --with 'mcp<2' python mcp_server.py`.
   `uv` fetches the MCP SDK into a cached throwaway env the first time and reuses
   it after. **Nothing to install by hand, nothing polluting your Python.**
2. else, if some Python already has the v1 MCP SDK importable
   (`$SHARED_CONTEXT_PYTHON`, then `python3`, then `python`) → use that.
3. else → exit with a one-line hint. The `context_*.py` scripts keep working;
   you only lose the unified MCP tool names (the agent runs the scripts over the
   shell instead).

> **Why `mcp<2`**: this server uses the v1 `FastMCP` API; mcp 2.x renamed it.
> The launcher pins v1 so it keeps working regardless of what's newest.

No `uv` and no way to install it? `pip install "mcp<2"` for the `python3` on
`PATH` also satisfies step 2.

---

## 8. Installation

**Claude Code** — global, copy the plugin folder:
```bash
cp -r ./plugins/shared-context ~/.claude/plugins/shared-context
```
**Claude Code** — project-scoped, no install/copy:
```bash
claude --plugin-dir ./plugins/shared-context
```

**Antigravity CLI** — global, via `agy` (installs the agent, skills, hooks, MCP):
```bash
agy plugin install ./plugins/shared-context
agy plugin list      # confirm
```
**Antigravity CLI** — project-scoped, if you don't want a global plugin install:
```bash
mkdir -p .agents/agents .agents/skills .agents/rules
cp plugins/shared-context/agents/context-keeper.md .agents/agents/
cp -r plugins/shared-context/skills/context-capture plugins/shared-context/skills/context-restore .agents/skills/
cp plugins/shared-context/rules/shared-context-rules.md .agents/rules/
cp -r plugins/shared-context/mcp .agents/shared-context-mcp   # keep run-server.sh next to mcp_server.py
# then merge into .agents/mcp_config.json:
#   "shared-context": { "command": "sh", "args": [".agents/shared-context-mcp/run-server.sh"] }
```

That's it — no `pip install`. Install `uv` once
(`curl -LsSf https://astral.sh/uv/install.sh | sh`) and the launcher handles the
MCP dependency itself (see §7).
