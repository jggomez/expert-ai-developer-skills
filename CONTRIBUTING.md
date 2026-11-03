# Contributing

Thanks for helping improve Expert AI Developer Skills. This guide covers how the repository is organized, how to make a change, and what a pull request must pass.

## Where to make changes

| You want to change | Edit | Then run |
| :--- | :--- | :--- |
| A skill | `skills/<skill>/` | `python3 scripts/sync_plugin_skills.py` |
| An agent, Antigravity hook or plugin manifest | `plugins/antigravity/<plugin>/` | `python3 scripts/sync_agents.py` |
| Claude Code-only behavior (tool names, models, dependencies, preloaded skills) | `scripts/claude_sync_config.py` | `python3 scripts/sync_agents.py` |
| A Claude Code hook | `plugins/claude/<plugin>/hooks/` and `hooks.json` | — |
| The shared hook library (both hosts) | `scripts/hook-lib/gate-utils.js` | `python3 scripts/sync_agents.py` |
| A plugin README | `plugins/<host>/<plugin>/README.md` (both hosts) | — |

Do not hand-edit generated files under `plugins/claude/<plugin>/agents/` or `skills/`; the sync scripts overwrite them.

## Workflow

1. Create a branch from `main`: `feat/<slug>`, `fix/<slug>`, `docs/<slug>` or `chore/<slug>`. Never commit to `main` directly.
2. Write or update a test first when you change behavior (hooks, sync scripts, structure rules).
3. Make the change in the canonical source, then run the sync scripts listed above.
4. Run the checks below.
5. Commit with [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <description>`, imperative and lowercase, no trailing period. Stage files explicitly (`git add <file>`), not `git add .`.
6. Open a pull request against `main` describing what changed and how you verified it.

## Checks

```bash
pytest tests/                       # structure, unit and behavioral tests
claude plugin validate .            # marketplace and plugin manifests
for hook in plugins/*/*/hooks/*.js; do node --check "$hook" || exit 1; done
```

All three must pass. `claude plugin validate .` warns that plugins have no `version`; that is intentional (see below).

## Conventions

- **Host isolation.** Antigravity files use Antigravity tool names; Claude Code files use Claude Code tool names. A test fails if Antigravity tool names appear under `plugins/claude/`.
- **No plugin versions.** Claude Code plugins omit `version` so each commit is a new version for users who installed from GitHub.
- **Plugin dependencies.** In Claude Code, plugins that reuse `senior-dev` agents declare `"dependencies": ["senior-dev"]` instead of copying them.
- **The metrics add-on stays decoupled.** The optional metrics plugin and its CLI under `tools/` may only be mentioned in the paths allowed by the decoupling test in `tests/structure/`, and commits that touch them must not touch other plugins.
- **READMEs.** Keep the structure used across plugins: tagline, requirements, installation, quick start, what's included, troubleshooting, license. Document only what the plugin's files actually contain.

## Reporting issues

Open a GitHub issue with the plugin name, host (Claude Code or Antigravity) and version, steps to reproduce, and the hook or agent output.
