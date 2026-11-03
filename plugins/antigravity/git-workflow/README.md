# git-workflow

> Branch safety, Conventional Commits and clean-merge gates for Google Antigravity.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Antigravity-4285F4?style=flat-square)](.)

`git-workflow` keeps git history clean while an agent works. A `PreToolUse` hook denies git writes on
`main`, `master`, `develop` or `dev` and commit messages that break Conventional Commits. A `Stop` hook keeps
the task open while merge conflicts are unresolved. An always-on rule and two skills cover branching,
commit messages and pull requests.

## Requirements

- Google Antigravity with the `agy` CLI.
- `node` on `PATH` (hooks are Node.js scripts).
- `git`. Python 3 to run the skill validator scripts.

## Installation

```bash
agy plugin install ./plugins/antigravity/git-workflow
```

## Quick start

```text
Write a Conventional Commits message for these staged changes.
Prepare this branch for a pull request: check the diff size and fill in the PR template.
Audit the last few commits on this branch for Conventional Commits compliance.
```

## What's included

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`commit-expert`** | Conventional Commits guidelines, local git hook setup and `validate_commit_msg.py`. |
| **`pull-request-expert`** | Concise, Fail-Honest PR descriptions, PR template and `validate_pr_content.py` (branch name, commit format, debug leaks). |

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `PreToolUse` (`run_command`) | `hooks/gitflow-branch-gate.js` | Denies `git add`, `git commit`, `git push` and `git merge` when the current branch is `main`, `master`, `develop` or `dev`. Denies `git commit -m` messages that do not match `<type>(<scope>): <subject>`. |
| `Stop` | `hooks/git-clean-stop-gate.js` | On a model stop, returns `continue` when `git status --porcelain` shows unresolved conflicts (`UU`, `AA`, `DD`, ...). |

### Rules

| File | Purpose |
| :--- | :--- |
| `rules/gitflow-rules.md` | Short always-on rule (~300 tokens): protected branches, auto-branching, scope drift checks, Conventional Commits, atomic staging, concise PRs. |

## How it works

1. Every `run_command` call passes through `gitflow-branch-gate.js` (15 s timeout).
2. The gate reads the branch with `git symbolic-ref --short HEAD`. A non-git folder is allowed.
3. Allowed commit types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
4. The hooks answer with JSON `{ "decision": "allow" | "deny" }` on stdout.
5. The `Stop` hook (30 s timeout) runs only when `terminationReason` is `model_stop` and the workspace has a `.git` entry.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| "Gitflow Safety Blocked" on `git add` or `git commit` | Current branch is `main`, `master`, `develop` or `dev`. | `git checkout -b feat/<slug>` and retry. |
| `[CONVENTIONAL COMMITS VIOLATION]` | The `-m` message has no valid type prefix. | Use `<type>(<scope>): <subject>`, e.g. `feat(auth): implement token refresh flow`. |
| Task continues after the agent tried to stop | Unresolved merge conflicts in the working tree. | Resolve the conflicted files and stage them. |
| No hook fires | `node` is missing or the plugin is not installed. | Install Node.js and rerun the install command. |

## Related plugins

- [senior-dev](../senior-dev/README.md): orchestrated SDLC that commits on feature branches.
- [docs-and-quality](../docs-and-quality/README.md): anti-lazy code gate and documentation standards.
- [multi-agent-ops](../multi-agent-ops/README.md): git worktree isolation for parallel work.

## Maintenance

`skills/` is a copy of the root `/skills` catalog. After editing a skill there, run
`python3 scripts/sync_plugin_skills.py` from the repo root.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
