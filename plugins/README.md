# Plugins

> One set of engineering plugins, packaged for Claude Code and Google Antigravity.

Each plugin exists twice: `antigravity/<plugin>/` is the source of truth, and `claude/<plugin>/` is generated from it by `scripts/sync_agents.py`, with Claude Code tool names, plugin dependencies and Claude-specific hooks.

## Catalog

| Plugin | What it does | Claude Code | Antigravity |
| :--- | :--- | :--- | :--- |
| `senior-dev` | SDLC orchestrator and the shared specialist subagents. | [README](claude/senior-dev/README.md) | [README](antigravity/senior-dev/README.md) |
| `senior-dev-flutter` | Flutter and Dart architecture, profiling and release engineering. | [README](claude/senior-dev-flutter/README.md) | [README](antigravity/senior-dev-flutter/README.md) |
| `python-backend` | FastAPI/Django backends, migrations, CI/CD gates. | [README](claude/python-backend/README.md) | [README](antigravity/python-backend/README.md) |
| `senior-data-engineer` | Google Cloud lakehouse, CDC and BigQuery modeling. | [README](claude/senior-data-engineer/README.md) | [README](antigravity/senior-data-engineer/README.md) |
| `sql-query-optimizer` | SQL diagnosis from real execution plans. | [README](claude/sql-query-optimizer/README.md) | [README](antigravity/sql-query-optimizer/README.md) |
| `shared-context` | Working memory shared across sessions and hosts. | [README](claude/shared-context/README.md) | [README](antigravity/shared-context/README.md) |
| `git-workflow` | Branch protection and Conventional Commits. | [README](claude/git-workflow/README.md) | [README](antigravity/git-workflow/README.md) |
| `docs-and-quality` | Documentation standards and anti-placeholder gate. | [README](claude/docs-and-quality/README.md) | [README](antigravity/docs-and-quality/README.md) |
| `multi-agent-ops` | Loop engineering and repository research. | [README](claude/multi-agent-ops/README.md) | [README](antigravity/multi-agent-ops/README.md) |
| `agent-metrics` *(optional)* | Session recording for the `agent-meter` CLI. | [README](claude/agent-metrics/README.md) | [README](antigravity/agent-metrics/README.md) |

## Install

### Claude Code

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install senior-dev@expert-ai-developer-skills
```

`senior-dev-flutter` and `python-backend` depend on `senior-dev`, which installs automatically. See [Installing the Claude Code plugins](../docs/claude-code-installation.md) for scopes, updates and team settings.

### Google Antigravity

```bash
# One plugin
agy plugin install ./plugins/antigravity/senior-dev

# All core plugins
for p in senior-dev senior-dev-flutter python-backend senior-data-engineer sql-query-optimizer shared-context git-workflow docs-and-quality multi-agent-ops; do
  agy plugin install "./plugins/antigravity/$p"
done
```

Run these from a clone of the repository. Antigravity has no plugin dependencies, so `senior-dev-flutter` and `python-backend` bundle copies of the `senior-dev` specialists.

## Differences between hosts

| Aspect | Claude Code | Antigravity |
| :--- | :--- | :--- |
| Manifest | `.claude-plugin/plugin.json` | `plugin.json` |
| MCP config | `.mcp.json` | `mcp_config.json` |
| Tools in agents | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Skill`, `Agent`, `AskUserQuestion` | `run_command`, `view_file`, `write_to_file`, `replace_file_content`, `invoke_subagent`, `ask_question`, … |
| Shared specialists | Plugin `dependencies` | Bundled copies |
| E2E browser | Playwright MCP + evidence hook in `senior-dev` | Defined by the agent instructions |
| Stop gates | Cached: run only when code changed, block at most 3 times per turn | Per-plugin hook scripts |

Tool names never cross hosts: a test fails if Antigravity tool names appear under `claude/`.

## Adding or changing a plugin

See [CONTRIBUTING.md](../CONTRIBUTING.md).
