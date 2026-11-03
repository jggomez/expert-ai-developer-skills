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
  `/plugin` → Marketplaces → *Enable auto-update*, or with `"autoUpdate": true` (section 5).
- **Manual**:
  ```bash
  claude plugin marketplace update expert-ai-developer-skills
  claude plugin update senior-dev-flutter@expert-ai-developer-skills   # restart Claude Code to apply
  ```

## 3. Install scopes

The plugin does not choose its scope; you do, with `--scope` at install time (default: `user`).
The scope only decides **which settings file** gets the `enabledPlugins` entry:

| Scope | `enabledPlugins` written to | Active in |
| :--- | :--- | :--- |
| `user` (default) | `~/.claude/settings.json` | Every project on your machine |
| `project` | `<project>/.claude/settings.json` (commit it) | That project, for everyone who clones it |
| `local` | `<project>/.claude/settings.local.json` (not committed) | That project, only for you |

The plugin files never go into the project: every scope uses the shared copy in
`~/.claude/plugins/cache/` (section 6). A project whose settings do not enable the plugin does not load it.

To keep a plugin out of every other project, install it with `--scope project` and declare the
marketplace in the project too, then remove the user-level marketplace:

```bash
cd <your-project>
claude plugin marketplace add jggomez/expert-ai-developer-skills --scope project
claude plugin install senior-dev-flutter@expert-ai-developer-skills --scope project
claude plugin marketplace remove expert-ai-developer-skills --scope user
```

## 4. Choose the main agent

By default a session starts with the general Claude agent, which delegates to plugin subagents when a
task matches their description. To talk to an orchestrator directly, start it as the main agent:

```bash
claude --agent senior-dev-flutter:flutter-feature-orchestrator
```

Or make it the default for one project in `<project>/.claude/settings.json`:

```json
{ "agent": "senior-dev-flutter:flutter-feature-orchestrator" }
```

Run `/agents` inside a session to list the agents available in that project.

## 5. Per project / team (`.claude/settings.json` in the project repo)

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

### Parallel workers in their own worktree

By default the orchestrators run parallel implementers in the same checkout, each on its own files
(Mode A). They give each worker its own git worktree (Mode B) only when two tracks must touch the same
files. Claude Code creates those worktrees from the repository's default branch (`"fresh"`), not from
your feature branch, so a worker would start without your in-progress commits. To let the orchestrator
use Mode B, add this to the project's `.claude/settings.json` (team), `.claude/settings.local.json`
(only you) or `~/.claude/settings.json` (every project):

```json
{
  "worktree": {
    "baseRef": "head"
  }
}
```

Without it, the orchestrator asks you to add the setting or runs those tracks one after another.

Each worktree is a fresh checkout under `.claude/worktrees/`:

- **Gitignored files are not copied** unless listed in a `.worktreeinclude` file at the project root
  (`.gitignore` syntax). Example for a Flutter project:

  ```text
  .env
  android/key.properties
  ```

- **Dependencies are not installed**: the worker runs `flutter pub get` (and `build_runner` if used),
  `uv sync` or `npm ci` inside its own worktree before testing.
- Add `.claude/worktrees/` to `.gitignore` so worktrees do not show up as untracked files.
- Each worker commits on its own branch and never pushes; the orchestrator merges the branches one at
  a time and runs the tests after each merge. Worktrees without changes are removed automatically;
  run `git worktree list` and `git worktree remove <path>` for the rest.

Project-scoped plugins installed in the main checkout also load in its worktrees. Reference:
[Run parallel sessions with worktrees](https://code.claude.com/docs/en/worktrees).

## 6. Where things live

| Path (under `~/.claude/plugins/`) | Content |
| :--- | :--- |
| `marketplaces/expert-ai-developer-skills/` | Clone of this repository |
| `cache/expert-ai-developer-skills/<plugin>/<version>/` | The installed copy of each plugin |
| `data/<plugin-id>/` | Persistent plugin data (`${CLAUDE_PLUGIN_DATA}`) |
| `known_marketplaces.json`, `installed_plugins.json` | Registries |

Installed plugins are copies: files outside a plugin's own folder are not available to it, which is why
every plugin carries its own `hooks/shared/` and `skills/`.

## 7. Developing the plugins

Load a working copy without installing (changes apply on restart):

```bash
claude --plugin-dir ./plugins/claude/senior-dev --plugin-dir ./plugins/claude/senior-dev-flutter
```

After editing `/skills` or `plugins/antigravity/`, regenerate the Claude copies and validate:

```bash
python3 scripts/sync_plugin_skills.py && python3 scripts/sync_agents.py
claude plugin validate .
```

## 8. Limitations

- **claude.ai/code (cloud sessions)** does not load plugins installed on your machine or enabled by a
  repository's `.claude/settings.json`. Only plugins pushed through server-managed settings (admin
  console, Team/Enterprise) reach cloud sessions.
- **Private forks**: Claude Code uses your existing git credentials (SSH agent, or `gh auth login` +
  `gh auth setup-git`). A `GITHUB_TOKEN` variable alone does not authenticate background updates.
