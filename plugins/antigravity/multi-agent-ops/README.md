# multi-agent-ops

> Parallel agent loops, repository research and a context guard for Google Antigravity.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Antigravity-4285F4?style=flat-square)](.)

`multi-agent-ops` helps one session coordinate several workers safely. `loop-engineering` covers 3-tier
triage, parallel builds on disjoint files (Mode A, `Workspace: "inherit"`) or git worktrees (Mode B,
`Workspace: "branch"`), and a 3-iteration self-correction cap. `repo-research` maps a codebase into a
short context file. A `PreToolUse` hook stops `view_file` calls that would flood the context window.

## Requirements

- Google Antigravity with the `agy` CLI.
- `node` on `PATH` (the hook is a Node.js script).
- Python 3 and `git` for the skill scripts (worktree provisioning, branch audit, repo analysis).

## Installation

```bash
agy plugin install ./plugins/antigravity/multi-agent-ops
```

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
| `PreToolUse` (`view_file`) | `hooks/context-guard-gate.js` | Denies reading a file over 500 KB when neither `StartLine` nor `EndLine` is given. |

### Rules

| File | Purpose |
| :--- | :--- |
| `rules/multi-agent-ops-rules.md` | Always-on rule: 6-state DAG, 3-tier SDLC, per-subagent `Invoke / SKIP` triage, artifact caps, Fail-Honest E2E. |

## How it works

1. Every `view_file` call passes through `context-guard-gate.js` (10 s timeout).
2. The hook reads the file size from `AbsolutePath`. Missing files are allowed.
3. Over 500 KB without a line range, it returns `{ "decision": "deny", "reason": ... }`.
4. All other calls return `{ "decision": "allow" }`.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `[CONTEXT GUARD BLOCKED]` on `view_file` | File is over 500 KB and no line range was given. | Locate the section with `grep_search`, then pass `StartLine` and `EndLine`. |
| `git worktree add` fails in `run_parallel_agents.py` | The branch is already checked out in another worktree. | Pick a new branch name or `git worktree remove` the old worktree. |
| Guard never fires | `node` is missing or the plugin is not installed. | Install Node.js and rerun the install command. |

## Related plugins

- [senior-dev](../senior-dev/README.md): orchestrator and specialist agents that run these loops.
- [git-workflow](../git-workflow/README.md): branch safety and Conventional Commits gates.
- [shared-context](../shared-context/README.md): cross-session memory in `context/`.

## Maintenance

`skills/` is a copy of the root `/skills` catalog. After editing a skill there, run
`python3 scripts/sync_plugin_skills.py` from the repo root.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
