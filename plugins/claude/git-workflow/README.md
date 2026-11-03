# git-workflow

> Branch safety, Conventional Commits and clean-merge gates for Claude Code.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-orange?style=flat-square)](../../../docs/claude-code-installation.md)

`git-workflow` keeps git history clean while an agent works. A `PreToolUse` hook rejects git writes on
`main` or `develop` and commit messages that break Conventional Commits. A `Stop` hook keeps the turn
open while a merge, rebase, cherry-pick or revert is unfinished. Two skills cover commit messages and
pull requests.

## Requirements

- Claude Code with plugin support.
- `node` on `PATH` (hooks are Node.js scripts).
- `git`. Python 3 to run the skill validator scripts.

## Installation

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install git-workflow@expert-ai-developer-skills
```

Updates, project scope and local development: [docs/claude-code-installation.md](../../../docs/claude-code-installation.md).

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
| `PreToolUse` (`Bash`) | `hooks/gitflow-branch-gate.js` | Denies `git add`, `git commit`, `git push` and `git merge` when the current branch is `main` or `develop`. Denies `git commit -m` messages that do not match `<type>(<scope>): <description>`. |
| `Stop` | `hooks/git-clean-stop-gate.js` | Blocks the stop when a merge, rebase, cherry-pick or revert is in progress, files are unmerged, or `git diff --check` finds conflict markers. |

## How it works

1. Every `Bash` call passes through `gitflow-branch-gate.js` (15 s timeout).
2. The gate reads the branch with `git symbolic-ref --short HEAD`. Detached HEAD or a non-git folder is allowed.
3. Allowed commit types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
4. On `Stop`, `git-clean-stop-gate.js` exits 2 with the problems on stderr, so Claude keeps working.
5. The stop gate blocks at most 3 times per turn. After that it lets the turn end with a notice.
6. Gate state is kept in the repository's git directory (`claude-stop-gates-*.json`).

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `[GITFLOW SAFETY VIOLATION]` on `git add` or `git commit` | Current branch is `main` or `develop`. | `git checkout -b feat/<slug>` and retry. |
| `[CONVENTIONAL COMMIT VIOLATION]` | The `-m` message has no valid type prefix. | Use `<type>(<scope>): <description>`, e.g. `fix(cart): prevent duplicate checkout`. |
| Claude keeps working after it tried to stop | Unfinished merge/rebase or conflict markers. | Finish or abort the operation (`git merge --abort`, `git rebase --abort`) and resolve markers. |
| Notice "still failing after 3 fix attempts" | Stop gate hit its per-turn limit. | Review the reported files, fix them, then start a new turn. |
| No hook fires | `node` is missing or the plugin is disabled. | Install Node.js and check `/plugin`. |

## Related plugins

- [senior-dev](../senior-dev/README.md): orchestrated SDLC that commits on feature branches.
- [docs-and-quality](../docs-and-quality/README.md): anti-lazy code gate and documentation standards.
- [multi-agent-ops](../multi-agent-ops/README.md): git worktree isolation for parallel work.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
