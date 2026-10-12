---
name: loop-engineering
description: Implements self-correcting agent execution loops, multi-agent parallel workflows, workspace isolation (Git Worktrees), and automated cron-based Pull Request auditing. Use this skill when asked to orchestrate parallel workers or construct review loops.
---

# Loop Engineering Skill

## Overview
This skill designs and executes multi-agent workflows, isolated parallel worker topologies, and self-correcting development loops. It acts as a Loop Engineering and Multi-Agent Orchestrator, enabling manager agents to coordinate multiple worker agents operating concurrently in dedicated git worktrees, protected by automated review crons, deterministic iteration caps, and quality verification gates.

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
### Multi-Agent Topologies Taxonomy
Multi-agent systems require rigorous topologies to avoid race conditions, context contamination, and execution chaos:
1. **Manager-Worker Topology**:
   - An orchestrator coordinates high-level objectives, decomposes tasks into independent deliverables, and delegates execution to specialized worker subagents.
   - Workers execute autonomously in isolated git worktrees or branches with zero shared mutable state, returning structured reports to the manager.
2. **Sequential Pipeline (DAG)**:
   - Deterministic state machine governing sequential transitions: `Plan -> Build -> Test -> Audit -> Ship`.
   - Each phase enforces strict entry and exit criteria; failure loops back directly to the responsible upstream phase rather than restarting blindly.
3. **Review Committee**:
   - Parallel specialist evaluations where multiple independent agents concurrently evaluate code diffs for distinct domains (e.g. Security, Architecture, Performance, QA).
   - Findings are aggregated and synthesized into an actionable checklist before merge approval.

### Phase 1: Task Decomposition & Worktree Provisioning
1. Identify independent, disjoint tasks with zero shared mutational state.
2. Run the worktree provisioning script to create one isolated git worktree and branch per task:
   ```bash
   python3 ./skills/loop-engineering/scripts/run_parallel_agents.py --tasks "task1:path1" "task2:path2"
   ```
   The script creates the worktree directories and outputs ready-to-use prompts for each subagent.

### Phase 2: Parallel Subagent Dispatching
1. Launch concurrent subagents via host-native subagent tools (`invoke_subagent` on Antigravity, `Agent` on Claude Code).
2. Assign each subagent to its dedicated worktree directory and branch.
3. Subagents execute implementation and local testing autonomously within their isolated directories.

### Phase 3: Continuous Review Crons & Quality Gates
1. Run automated PR/branch auditors to scan feature and bugfix branches:
   ```bash
   python3 ./skills/loop-engineering/scripts/pr_cron_reviewer.py
   ```
2. The auditor runs static analyzers, test runners, and secret scanners against git diffs, appending actionable comments to the review log.

### Phase 4: Self-Correction Protocol (Strict 3-Loop Cap)
1. **Defect Detection**: If quality gates fail, the subagent analyzes the exact traceback, compiler diagnostic, or linter error.
2. **Targeted Remediation**: The subagent applies surgical fixes to the failing code and re-runs the verification command.
3. **Strict 3-Loop Cap**:
   - Auto-remediation is strictly bounded to a **maximum of 3 self-correction cycles**.
   - Under no circumstances may an agent enter a runaway loop beyond 3 attempts.
4. **Escalation Mechanism**:
   - If a defect persists after 3 cycles, the agent must immediately **halt execution**.
   - Compile a comprehensive diagnostic report detailing:
     * Exact failing assertion or error traceback.
     * The 3 remediation hypotheses attempted and why each failed.
     * Specific questions or guidance requested from the user.
   - Escalate to the user and await manual intervention.

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
- *"Orchestrate a self-correcting development loop for this refactoring until all tests pass, adhering to the 3-loop cap."*

### Host Execution Instructions
- **Claude Code**: Run `run_parallel_agents.py` to create worktrees, then dispatch subagents into each worktree path via `Agent(agent="...", prompt="...")`.
- **Antigravity**: Launch subagents with `invoke_subagent(name="...", prompt="...")` using `Workspace='branch'` or `Workspace='share'` and monitor execution reactively.

## Red Flags
- Spawning parallel subagents in the same directory without worktree isolation (causing race conditions and file collisions).
- Exceeding the 3-loop cap and entering runaway, cost-inefficient retry loops.
- Bypassing the self-correction protocol when quality gates fail.
- Allowing subagents to commit directly to production branches without PR review.
- Running parallel subagents on heavily coupled tasks with shared mutable state.

## Verification
- [ ] Multi-agent topology (Manager-Worker, DAG, or Review Committee) explicitly chosen and documented.
- [ ] Worktrees provisioned cleanly with isolated branches:
  ```bash
  python3 ./skills/loop-engineering/scripts/run_parallel_agents.py
  ```
- [ ] Subagents execute and commit changes to their respective branches without collision.
- [ ] PR cron reviewer passes with zero gate failures:
  ```bash
  python3 ./skills/loop-engineering/scripts/pr_cron_reviewer.py
  ```
- [ ] Self-correction protocol strictly adheres to the 3-loop cap, escalating persistent defects to the user after 3 cycles.

## References
- [Loop Engineering & Multi-Agent Orchestration Reference](references/loop-architecture.md)
