---
name: loop-engineering
description: Implements 3-Tier Adaptive SDLC state machines, capability-gated discovery, target-project AGENTS.md bootstrapping, isolated parallel worker execution (Disjoint Mode A / Git Worktree Mode B), and 3-loop self-correcting review gates.
---

# Loop Engineering Skill

## Overview
This skill orchestrates multi-agent execution loops, isolated parallel worker topologies, and the **3-Tier Adaptive SDLC State Machine**. It coordinates capability-gated specialist dispatch, target-project **`AGENTS.md` (`<= 90 lines`)** bootstrapping, collision-free parallel builds (Disjoint File Mode A and Git Worktree Mode B), and deterministic **max 3-iteration** self-correction gates.

## When to Use
### Trigger Scenarios
- Triage and execution of multi-agent workflows across Tier 1 (Fast-Track), Tier 2 (Standard), and Tier 3 (Mission-Critical).
- Bootstrapping or updating a concise root `AGENTS.md` (`<= 90 lines`) in target user repositories.
- Provisioning isolated git worktrees or disjoint file partitions for concurrent worker subagents.
- Running automated PR/branch audit crons and bounded self-correcting verification loops.

### When NOT to Use
- **Pure commit message linting**: Route to `commit-expert`.
- **Standalone manual PR review without loop orchestration**: Route to `pull-request-expert`.

## Process
### State 0: Memory Restore, Target-Project `AGENTS.md` Bootstrap & 3-Tier Triage
1. **Silent Memory Restore**: Read `context/memory/MEMORY.md` if present (`~500 tokens`), loading `architecture.md`, `conventions.md`, or `log/YYYY-MM-DD.md` only on demand.
2. **Target-Project `AGENTS.md` Bootstrap (`<= 90 lines`)**: When operating in a target user repository that lacks a root `AGENTS.md`—or when its stack, build/test commands, `DESIGN.md` contract, or architectural conventions change—bootstrap or update a concise root `AGENTS.md` (`<= 90 lines`) using [references/project-agents-template.md](references/project-agents-template.md) (`1. Project Overview & Tech Stack`, `2. Executable Commands`, `3. Architecture & Coding Conventions`, `4. Design & Persistent Memory` wired to root `DESIGN.md` and `context/memory/MEMORY.md`).
3. **Concise `PLAN.md` (`<= 50 lines`) & 3-Tier SDLC Triage**:

| Dimension / Phase | Tier 1: Fast-Track (Low Complexity) | Tier 2: Standard (Medium Complexity) | Tier 3: Mission-Critical (Complex) |
| :--- | :--- | :--- | :--- |
| **Typical Scope** | Single-file bugfix, doc fix, typo, chore, localized refactor without public contract change | 2–4 files, new API endpoint, single UI view/widget, DB migration, non-breaking contract update | Full end-to-end feature, payment/auth flow, cross-cutting refactor, breaking public API |
| **Discovery (State 1)** | **SKIPPED**: Zero discovery artifacts authored | **SELECTIVE** (capability-gated): `prd.md <= 70L`, `DESIGN.md <= 110L` (+ delta `<= 35L`), `adr-*.md <= 55L` | **FULL** (capability-gated): `prd.md <= 70L`, `DESIGN.md <= 110L` (+ `design.md <= 35L`), `adr-*.md <= 55L` / `architecture.md <= 70L` |
| **Interactive Alignment Gate** | **SKIPPED**: Auto-proceeds directly to build | **MANDATORY**: `ask_question` modal approval before build | **MANDATORY**: Strict `ask_question` modal sign-off before build |
| **Build & Isolation (State 2)** | 1 `code-implementer` under Mode A (Disjoint Files) | 1..N `code-implementer` in parallel under Mode A (Disjoint Files) | 1..N `code-implementer` under Mode A or Mode B (Git Worktree Isolation if shared files touched) |
| **QA & Audit (State 3 & 4)** | Scoped test file (`exit 0`) + `compliance-verifier` (skips committee) | Full suite (`exit 0`) + `docs/<feature-name>/test-matrix.md` (`<= 80L`) + `compliance-verifier` (`APPROVED`) | **Adversarial Verification Committee** (capability-gated, reports `<= 50L`): `qa-tester`, `critic`, `challenger`, `e2e-blackbox-tester`, `compliance-verifier` |
| **Token & Latency Impact** | **70–85% token & latency savings** | Balanced overhead with rigorous traceability | Maximum empirical depth & zero regression tolerance |

### Multi-Agent Topologies & Isolation Modes
1. **Manager-Worker**: Orchestrator decomposes tasks and dispatches isolated workers (`Mode A` strictly non-overlapping `Owned Files`, or `Mode B` Git Worktrees when shared routers/configs are touched). Each parallel worker runs **only its scoped test file** during State 2 loops.
2. **Sequential DAG**: Deterministic `Plan -> Discover -> Align -> Build -> Verify -> Ship` state machine.
3. **Adversarial Review Committee**: Capability-gated Tier 3 specialists (`critic` for `>= 150 LOC` diffs, `challenger` for auth/payments/concurrency/untrusted input, fail-honest `e2e-blackbox-tester` only when a runnable web UI exists).

### Worktree Provisioning, PR Crons & 3-Loop Self-Correction Cap
1. **Worktree Provisioning (Mode B)**:
   ```bash
   python3 ./skills/loop-engineering/scripts/run_parallel_agents.py --tasks "task1:path1" "task2:path2"
   ```
2. **Automated Branch Review Cron**:
   ```bash
   python3 ./skills/loop-engineering/scripts/pr_cron_reviewer.py
   ```
3. **Self-Correction Protocol (Strict 3-Loop Cap)**: On test or compliance failure, remediate surgically up to a **maximum of 3 iterations**. If still failing after 3 attempts, halt immediately and escalate a concise diagnostic report (failing traceback, 3 hypotheses tried, user decision needed).

## Usage
```bash
python3 ./skills/loop-engineering/scripts/run_parallel_agents.py
python3 ./skills/loop-engineering/scripts/pr_cron_reviewer.py
```
- **Claude Code**: Provision worktrees when Mode B applies and dispatch workers via `Agent(...)`.
- **Antigravity**: Dispatch workers via `Agent(...)` (`Workspace='inherit'` for Mode A, `Workspace='branch'`/`'share'` for Mode B).

## Red Flags
- ❌ Concurrent workers editing overlapping files without Mode B Git Worktree isolation, or running the full test suite inside parallel worker loops.
- ❌ Over-invoking discovery specialists or adversarial committees on Tier 1 tasks (destroying 70–85% token/latency savings).
- ❌ Leaving target projects without a concise root `AGENTS.md` (`<= 90 lines`) wired to executable commands, `DESIGN.md`, and `context/memory/MEMORY.md`.
- ❌ Exceeding the 3-loop self-correction cap or skipping `ask_question` alignment on Tier 2 / Tier 3 tasks.

## Verification
- [ ] SDLC Tier (`Tier 1` `Fast-Track`, `Tier 2` `Standard`, or `Tier 3` `Mission-Critical`) and capability-gated `Invoke / SKIP` table recorded in `PLAN.md` (`<= 50 lines`).
- [ ] Target-project root `AGENTS.md` (`<= 90 lines`) bootstrapped or updated per [references/project-agents-template.md](references/project-agents-template.md) when missing or outdated.
- [ ] Parallel tracks verified collision-free (Mode A disjoint files or Mode B worktrees via `run_parallel_agents.py`), with 3-loop self-correction cap enforced.

## References
- [Target-Project AGENTS.md Template (`<= 65 lines`)](references/project-agents-template.md)
- [Loop Engineering & Multi-Agent Orchestration Reference](references/loop-architecture.md)
