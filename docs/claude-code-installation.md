# Installing the Claude Code plugins

This repository is a Claude Code **plugin marketplace**: `.claude-plugin/marketplace.json` lists every
plugin under `plugins/claude/`. Install from GitHub; never copy plugin folders by hand.

## 1. Install

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install senior-dev-flutter@expert-ai-developer-skills
```

- One step (Claude Code 2.1.292+): `claude plugin install senior-dev-flutter --marketplace jggomez/expert-ai-developer-skills`.
- Inside a session use the slash form: `/plugin marketplace add …`, `/plugin install …`.
- **Dependencies install themselves.** `senior-dev-flutter` and `python-backend` declare
  `"dependencies": ["senior-dev"]`, so installing either one also installs and enables `senior-dev`
  at the same scope.
- **Try a branch before it is merged**: `claude plugin marketplace add jggomez/expert-ai-developer-skills#<branch>`.

Every plugin listed in `.claude-plugin/marketplace.json` installs the same way; each plugin README has its own line.

| Plugin | Install |
| :--- | :--- |
| `senior-dev` | `claude plugin install senior-dev@expert-ai-developer-skills` |
| `senior-dev-flutter` | `claude plugin install senior-dev-flutter@expert-ai-developer-skills` |
| `python-backend` | `claude plugin install python-backend@expert-ai-developer-skills` |
| `senior-data-engineer` | `claude plugin install senior-data-engineer@expert-ai-developer-skills` |
| `sql-query-optimizer` | `claude plugin install sql-query-optimizer@expert-ai-developer-skills` |
| `shared-context` | `claude plugin install shared-context@expert-ai-developer-skills` |
| `git-workflow` | `claude plugin install git-workflow@expert-ai-developer-skills` |
| `docs-and-quality` | `claude plugin install docs-and-quality@expert-ai-developer-skills` |
| `multi-agent-ops` | `claude plugin install multi-agent-ops@expert-ai-developer-skills` |

## 2. Updates

The plugins deliberately have **no `version`** in `plugin.json`: Claude Code then versions each plugin
by its git commit, so every push to the marketplace branch is a new version. (A fixed `version` is the
cache key and would keep everyone on the old copy forever.)

- **Automatic**: auto-update is **off** by default for third-party marketplaces. Turn it on in
  `/plugin` → Marketplaces → *Enable auto-update*, or with `"autoUpdate": true` (section 3).
- **Manual**:
  ```bash
  claude plugin marketplace update expert-ai-developer-skills
  claude plugin update senior-dev-flutter@expert-ai-developer-skills   # restart Claude Code to apply
  ```

## 3. Per project / team (`.claude/settings.json` in the project repo)

```json
{
  "extraKnownMarketplaces": {
    "expert-ai-developer-skills": {
      "source": { "source": "github", "repo": "jggomez/expert-ai-developer-skills" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "senior-dev-flutter@expert-ai-developer-skills": true
  }
}
```

The marketplace registers when each contributor accepts the folder-trust dialog. Each contributor then
installs once at project scope:

```bash
claude plugin install senior-dev-flutter@expert-ai-developer-skills --scope project
```

## 4. Where things live

| Path (under `~/.claude/plugins/`) | Content |
| :--- | :--- |
| `marketplaces/expert-ai-developer-skills/` | Clone of this repository |
| `cache/expert-ai-developer-skills/<plugin>/<version>/` | The installed copy of each plugin |
| `data/<plugin-id>/` | Persistent plugin data (`${CLAUDE_PLUGIN_DATA}`) |
| `known_marketplaces.json`, `installed_plugins.json` | Registries |

Installed plugins are copies: files outside a plugin's own folder are not available to it, which is why
every plugin carries its own `hooks/shared/` and `skills/`.

## 5. Developing the plugins

Load a working copy without installing (changes apply on restart):

```bash
claude --plugin-dir ./plugins/claude/senior-dev --plugin-dir ./plugins/claude/senior-dev-flutter
```

After editing `/skills` or `plugins/antigravity/`, regenerate the Claude copies and validate:

```bash
python3 scripts/sync_plugin_skills.py && python3 scripts/sync_agents.py
claude plugin validate .
```

## 6. Limitations

- **claude.ai/code (cloud sessions)** does not load plugins installed on your machine or enabled by a
  repository's `.claude/settings.json`. Only plugins pushed through server-managed settings (admin
  console, Team/Enterprise) reach cloud sessions.
- **Private forks**: Claude Code uses your existing git credentials (SSH agent, or `gh auth login` +
  `gh auth setup-git`). A `GITHUB_TOKEN` variable alone does not authenticate background updates.
