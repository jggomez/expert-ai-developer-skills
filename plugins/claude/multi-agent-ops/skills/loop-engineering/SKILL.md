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
### 3-Tier Adaptive SDLC State Machine
Multi-agent engineering workflows scale dynamically based on change complexity and risk profile. Rather than running a monolithic pipeline for every prompt, the orchestrator classifies incoming tasks into one of three execution tiers:

| Dimension / Phase | Tier 1: Fast-Track (Low Complexity) | Tier 2: Standard (Medium Complexity) | Tier 3: Mission-Critical (Complex) |
| :--- | :--- | :--- | :--- |
| **Typical Scope** | Single-file bugfix, doc fix, typo, chore, localized refactor without public contract change | 2–4 files, new API endpoint, single UI view/widget, database migration, non-breaking contract update | Full end-to-end feature, payment/auth flow, cross-cutting architectural refactor, public breaking API |
| **Discovery Phase (State 1)** | **SKIPPED**: Zero PRD/design/architecture docs authored | **SELECTIVE**: Targeted discovery via `product-analyst`, `ui-ux-designer`, or `architect-engineer` as needed | **FULL**: Comprehensive discovery via `product-analyst` (`prd.md`), `ui-ux-designer` (`design.md`), and `architect-engineer` (`architecture.md` / `ADR-*.md`) |
| **Interactive User Alignment Gate** | **SKIPPED**: Auto-proceeds directly to implementation | **MANDATORY**: Interactive modal (`ask_question`) presenting PRD/design/architecture summary for user approval | **MANDATORY**: Strict interactive modal (`ask_question`) requiring explicit user approval before build |
| **Build & Partitioning (State 2)** | 1 `code-implementer` under Mode A (Disjoint Files) | 1..N `code-implementer` in parallel under Mode A (Disjoint Files) | 1..N `code-implementer` in parallel under Mode A or Mode B (Git Worktree Isolation if shared files touched) |
| **QA Verification (State 3)** | Scoped test execution (only affected test file run) | Full test suite execution + standardized QA Test Matrix artifact (`docs/<feature-name>/test-matrix.md`) | Full test suite execution + standardized QA Test Matrix artifact (`docs/<feature-name>/test-matrix.md`) with pyramid coverage |
| **Verification & Committee (State 4)** | Standard `compliance-verifier` audit (bypasses adversarial committee) | Parallel `qa-tester` (exit code 0) and `compliance-verifier` (APPROVED) | **Adversarial Verification Committee**: `qa-tester`, `critic`, `challenger`, `e2e-blackbox-tester`, and `compliance-verifier` |
| **Token & Latency Impact** | **70–85% token & latency savings** | Balanced overhead with rigorous quality verification | Maximum depth, empirical verification, and zero regression tolerance |

#### Tier 1 Execution Protocol (Fast-Track)
1. **Triage**: Confirm change is strictly confined to a single file, isolated bugfix, typo, or localized chore.
2. **Direct Dispatch**: Bypass State 1 discovery and bypass State 1.5 interactive user dialog. Dispatch directly to 1 `code-implementer`.
3. **Scoped Test & Audit**: Run only the targeted test file to prevent contention and delays, followed by a standard `compliance-verifier` check. Adversarial review committee is bypassed.

#### Tier 2 Execution Protocol (Standard)
1. **Triage**: Identify multi-file change (2–4 files), single endpoint, or localized UI view.
2. **Selective Discovery**: Trigger specialists based on change domain (`product-analyst` for requirements, `ui-ux-designer` for visual, `architect-engineer` for schema/contracts). Store artifacts in `docs/<feature-name>/`.
3. **Interactive User Alignment**: Pause and query user via `ask_question` with a summary of the scope and architecture before proceeding.
4. **Parallel Build**: Run parallel `code-implementer` subagents under Mode A with disjoint owned files.
5. **QA & Audit**: `qa-tester` authors `docs/<feature-name>/test-matrix.md` and verifies exit code 0 across the full test suite; `compliance-verifier` issues formal approval.

#### Tier 3 Execution Protocol (Mission-Critical)
1. **Triage**: Classify large features, auth/financial transactions, architectural refactoring, or breaking changes.
2. **Full Discovery**: Invoke `product-analyst` (`prd.md`), `ui-ux-designer` (`design.md`), and `architect-engineer` (`architecture.md` / ADRs) sequentially or in parallel fan-out.
3. **Mandatory Interactive User Alignment**: Pause and require explicit user approval via `ask_question` before implementation begins.
4. **Isolated Build**: Enforce Mode A (disjoint files) or Mode B (Git Worktree isolation) to prevent file collisions during heavy multi-agent parallel construction.
5. **Adversarial Verification Committee**: Fan out verification across five specialized evaluators:
   - `qa-tester`: Produces `docs/<feature-name>/test-matrix.md` covering the test pyramid with terminal exit code 0 proof.
   - `critic`: Performs critical code review, code smell detection, and clean architecture audits.
   - `challenger`: Probes boundary limits, edge-case failure modes, concurrency races, and negative scenarios.
   - `e2e-blackbox-tester`: Validates end-to-end user journeys and blackbox behavioral workflows.
   - `compliance-verifier`: Conducts static analysis, OWASP security audit, and architectural invariant checks, issuing final `APPROVED` verdict.

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
   - In Tier 3 workflows, operates as the **Adversarial Verification Committee** (`qa-tester`, `critic`, `challenger`, `e2e-blackbox-tester`, `compliance-verifier`).
   - Findings are aggregated and synthesized into an actionable checklist before merge approval.

### Phase 1: Task Decomposition & Worktree Provisioning
1. Identify independent, disjoint tasks with zero shared mutational state.
2. Run the worktree provisioning script to create one isolated git worktree and branch per task:
   ```bash
   python3 ./skills/loop-engineering/scripts/run_parallel_agents.py --tasks "task1:path1" "task2:path2"
   ```
   The script creates the worktree directories and outputs ready-to-use prompts for each subagent.

### Phase 2: Parallel Subagent Dispatching
1. Launch concurrent subagents via host-native subagent tools (`Agent` on Antigravity, `Agent` on Claude Code).
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
- **Antigravity**: Launch subagents with `Agent(agent="...", prompt="...")` using `Workspace='branch'` or `Workspace='share'` and monitor execution reactively.

## Red Flags
- Spawning parallel subagents in the same directory without worktree isolation (causing race conditions and file collisions).
- Forcing full Discovery, interactive modals, or an Adversarial Verification Committee on Tier 1 low-complexity tasks (wasting 70–85% tokens and introducing massive latency).
- Skipping the interactive alignment gate (`ask_question`) or Adversarial Verification Committee on Tier 3 mission-critical tasks.
- Exceeding the 3-loop cap and entering runaway, cost-inefficient retry loops.
- Bypassing the self-correction protocol when quality gates fail.
- Allowing subagents to commit directly to production branches without PR review.
- Running parallel subagents on heavily coupled tasks with shared mutable state without Git Worktree isolation.

## Verification
- [ ] SDLC Tier (Tier 1 Fast-Track, Tier 2 Standard, or Tier 3 Mission-Critical) explicitly evaluated, documented, and justified in `PLAN.md`.
- [ ] Tier 1 tasks bypass discovery, interactive alignment dialog, and adversarial review, delivering 70–85% token and latency savings.
- [ ] Tier 2 tasks execute selective discovery, interactive user alignment gate, Mode A parallel partitioning, and produce `docs/<feature-name>/test-matrix.md`.
- [ ] Tier 3 tasks complete full discovery, require explicit user alignment approval, enforce Mode A/B workspace isolation, and achieve full Adversarial Verification Committee sign-off.
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
