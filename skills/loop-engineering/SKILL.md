---
name: loop-engineering
description: Implements self-correcting agent execution loops, multi-agent parallel workflows, workspace isolation (Git Worktrees), and automated cron-based Pull Request auditing. Use this skill when asked to orchestrate parallel workers or construct review loops.
---

# Loop Engineering Skill

## Overview
This skill designs and executes multi-agent workflows, isolated parallel worker topologies, and self-correcting development loops. It acts as a Loop Engineering and Multi-Agent Orchestrator, enabling manager agents to coordinate multiple worker agents operating concurrently in dedicated git worktrees, protected by automated review crons and quality verification gates.

## When to Use
### Trigger Scenarios
- Orchestrating multi-agent parallel execution across disjoint modules or features.
- Provisioning isolated git worktrees to prevent mutational file conflicts among concurrent agents.
- Setting up automated periodic review crons to audit open pull requests and branches.
- Establishing self-correcting execution loops that detect build/test failures and automatically remediate code.

### When NOT to Use
- **Single-agent sequential development tasks**: Standard execution suffices.
- **Trivial isolated fixes**: Avoid worktree provisioning overhead.
- **Pure git commit message validation**: Route to `commit-expert`.
- **Stand-alone manual code reviews**: Route to `pull-request-expert`.

## Process
### Phase 1: Task Decomposition & Worktree Provisioning
1. Identify independent, disjoint tasks with zero shared mutational state.
2. Run the worktree provisioning script to create one isolated git worktree and branch per task:
   ```bash
   python3 ./skills/loop-engineering/scripts/run_parallel_agents.py --tasks "task1:path1" "task2:path2"
   ```
   The script creates the worktree directories and outputs ready-to-use prompts for each subagent.

### Phase 2: Parallel Subagent Dispatching
1. Launch concurrent subagents via host-native subagent tools (`invoke_subagent` on Antigravity, Task on Claude Code).
2. Assign each subagent to its dedicated worktree directory and branch.
3. Subagents execute implementation and local testing autonomously within their isolated directories.

### Phase 3: Continuous Review Crons & Quality Gates
1. Run automated PR/branch auditors to scan feature and bugfix branches:
   ```bash
   python3 ./skills/loop-engineering/scripts/pr_cron_reviewer.py
   ```
2. The auditor runs static analyzers, test runners, and secret scanners against git diffs, appending actionable comments to the review log.

### Phase 4: Self-Correction Loop
1. If quality gates fail, the manager or worker agent checks out the branch, reads the error traceback, applies targeted fixes, and pushes updates.
2. Re-trigger the review cron until 100% of quality checks pass.

## Usage
### Commands & Automation Scripts
```bash
# Provision isolated worktrees and generate subagent prompts
python3 ./skills/loop-engineering/scripts/run_parallel_agents.py

# Execute automated PR and branch diff quality review cron
python3 ./skills/loop-engineering/scripts/pr_cron_reviewer.py
```

### Example Prompts
- *"Provision isolated worktrees for these 3 independent API routes and dispatch parallel subagents."*
- *"Run the PR review cron to inspect all active feature branches for quality gate compliance."*
- *"Orchestrate a self-correcting development loop for this refactoring until all tests pass."*

### Host Execution Instructions
- **Claude Code**: Run `run_parallel_agents.py` to create worktrees, then dispatch subagents into each worktree path.
- **Antigravity**: Launch subagents with `Workspace='branch'` or `Workspace='share'` and monitor execution reactively.

## Red Flags
- Spawning parallel subagents in the same directory without worktree isolation (causing race conditions and file collisions).
- Bypassing the self-correction loop when quality gates fail.
- Allowing subagents to commit directly to production branches without PR review.
- Running parallel subagents on heavily coupled tasks with shared mutable state.

## Verification
- [ ] Worktrees provisioned cleanly with isolated branches:
  ```bash
  python3 ./skills/loop-engineering/scripts/run_parallel_agents.py
  ```
- [ ] Subagents execute and commit changes to their respective branches without collision.
- [ ] PR cron reviewer passes with zero gate failures:
  ```bash
  python3 ./skills/loop-engineering/scripts/pr_cron_reviewer.py
  ```
- [ ] Self-correction loop successfully resolves any test or lint failures before merge.

## References
- [Loop Engineering & Multi-Agent Orchestration Reference](references/loop-architecture.md)

