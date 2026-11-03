# multi-agent-ops

> Parallel agent loops, repository research and a context guard for Claude Code.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-orange?style=flat-square)](../../../docs/claude-code-installation.md)

`multi-agent-ops` helps one session coordinate several workers safely. `loop-engineering` covers 3-tier
triage, parallel builds on disjoint files (Mode A) or git worktrees (Mode B), and a 3-iteration
self-correction cap. `repo-research` maps a codebase into a short context file. A `PreToolUse` hook
stops `Read` calls that would flood the context window.

## Requirements

- Claude Code with plugin support.
- `node` on `PATH` (the hook is a Node.js script).
- Python 3 and `git` for the skill scripts (worktree provisioning, branch audit, repo analysis).

## Installation

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install multi-agent-ops@expert-ai-developer-skills
```

Updates, project scope and local development: [docs/claude-code-installation.md](../../../docs/claude-code-installation.md).

## Quick start

```text
Analyze this repository and generate a project context document.
I have 3 independent features: provision one git worktree per feature and give me a prompt for each worker.
Audit the open feature branches for quality gate failures.
```

## What's included

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`loop-engineering`** | 3-tier SDLC triage, root `AGENTS.md` bootstrap, Mode A / Mode B parallel workers, 3-loop self-correction. Scripts: `run_parallel_agents.py` (one `../worktree-<task>` per task, optional `tasks.json`), `pr_cron_reviewer.py` (feature branch audit). |
| **`repo-research`** | Maps structure, stack, commands and invariants into `.agents/rules/project-context.md` (`<= 80` lines) and syncs root `AGENTS.md` and `context/memory/MEMORY.md`. Script: `repo_analyzer.py`. |

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `PreToolUse` (`Read`) | `hooks/context-guard-gate.js` | Denies reads of binary files, of lockfiles and minified bundles over 200 KB without `offset`/`limit`, and of any file over 500 KB without `offset`/`limit`. |

## How it works

1. Every `Read` call passes through `context-guard-gate.js` (15 s timeout).
2. Images and PDFs (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.pdf`) are always allowed.
3. Binary extensions are always denied: `.ico`, `.zip`, `.tar`, `.gz`, `.exe`, `.bin`, `.dylib`, `.so`, `.dll`, `.a`, `.pyc`, `.class`, `.jar`.
4. Lockfiles (`package-lock.json`, `yarn.lock`, `poetry.lock`, ...), `*.min.js`, `*.min.css` and `*.map` over 200 KB need `offset` or `limit`.
5. Any other file over 500 KB needs `offset` or `limit`.
6. Missing files and directories pass through to `Read` unchanged.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `[CONTEXT GUARD VIOLATION]` "appears to be a binary file" | Extension is on the binary list. | Inspect it with a shell tool (`unzip -l`, `file`) instead of `Read`. |
| `[CONTEXT GUARD VIOLATION]` "exceeds the 500KB safe context threshold" | Large file read without pagination. | Pass `offset` and `limit`, or search with `Grep` first. |
| `[CONTEXT GUARD VIOLATION]` on a lockfile | Lockfile or bundle over 200 KB. | Use `Grep` for the package or key you need. |
| `git worktree add` fails in `run_parallel_agents.py` | The branch is already checked out in another worktree. | Pick a new branch name or `git worktree remove` the old worktree. |

## Related plugins

- [senior-dev](../senior-dev/README.md): orchestrator and specialist agents that run these loops.
- [git-workflow](../git-workflow/README.md): branch safety and Conventional Commits gates.
- [shared-context](../shared-context/README.md): cross-session memory in `context/`.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
