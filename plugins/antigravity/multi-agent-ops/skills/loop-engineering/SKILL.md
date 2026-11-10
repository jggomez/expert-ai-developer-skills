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
3. **Concise `docs/<feature-name>/PLAN.md` (`<= 50 lines`) & 3-Tier SDLC Triage**:

| Dimension / Phase | Tier 1: Fast-Track (Low Complexity) | Tier 2: Standard (Medium Complexity) | Tier 3: Mission-Critical (Complex) |
| :--- | :--- | :--- | :--- |
| **Typical Scope** | Single-file bugfix, doc fix, typo, chore, localized refactor without public contract change | 2–4 files, new API endpoint, single UI view/widget, DB migration, non-breaking contract update | Full end-to-end feature, payment/auth flow, cross-cutting refactor, breaking public API |
| **Discovery (State 1)** | **SKIPPED**: Zero discovery artifacts authored | **SELECTIVE** (capability-gated, sequential): `spec.md` (`## Product <= 50L` / `## Design <= 30L` / `## Architecture <= 50L`), `DESIGN.md <= 110L`, `adr-*.md <= 55L` | **FULL** (capability-gated, sequential): `spec.md` (all 3 sections), `DESIGN.md <= 110L`, `adr-*.md <= 55L` |
| **Interactive Alignment Gate** | **SKIPPED**: Auto-proceeds directly to build | **MANDATORY**: `ask_question` modal approval before build | **MANDATORY**: Strict `ask_question` modal sign-off before build |
| **Build & Isolation (State 2)** | 1 `code-implementer` under Mode A (Disjoint Files) | 1..N `code-implementer` in parallel under Mode A (Disjoint Files) | 1..N `code-implementer` under Mode A or Mode B (Git Worktree Isolation if shared files touched) |
| **QA & Audit (State 3 & 4)** | Scoped test file (`exit 0`) + `compliance-verifier` (skips committee) | Full suite (`exit 0`) + `docs/<feature-name>/test-matrix.md` (`<= 80L`) + `compliance-verifier` (`APPROVED`) | **Adversarial Verification Committee** (capability-gated, verdicts returned in final message `<= 50L`, no report files): `qa-tester`, `critic`, `challenger`, `e2e-blackbox-tester`, `compliance-verifier` |
| **Token & Latency Impact** | **70–85% token & latency savings** | Balanced overhead with rigorous traceability | Maximum empirical depth & zero regression tolerance |

### Lean Execution Defaults
1. **Lightest tier that fits**: size by risk and ambiguity, not by file count. A large but well-specified change is Tier 2 with every discovery specialist `SKIP`. Scale alone never makes a task Tier 3: Tier 3 requires the user to ask for it, or a change to authentication/authorization, payments, or a destructive data migration.
2. **Scope discipline**: build exactly what was asked. Repository rules constrain *how*, never *what*; extra ideas go under "Suggestions" in the final summary.
3. **Multi-phase requests**: State 0 once (one `PLAN.md` listing every phase); per phase only build + scoped tests + one Conventional Commit + a `<= 5 line` progress note; discovery, alignment, the review committee, E2E and State 5 run once for the whole request, meaning one user message (before the first and after the last phase, or after a phase the user marks as risky).
4. **Stop on red**: never start the next phase on a failing tree.

### Every Request Is a Change
Measured on real runs: later requests reused the first request's triage, so product, design and architecture were never considered again, and every change re-ran the whole suite.
1. **One user message = one change**: the phases of one message share one triage. A later message that asks for a change is a new change `C-NN`, even on the same branch, feature and `PLAN.md`.
2. **Triage the delta again**: for each change run a short State 0 (branch and Scope Drift check, read `PLAN.md`; read `context/memory/` only if not read this session), then add one row to the `## Changes` table in `PLAN.md`: `| C-02 | <request in one line> | Tier | product | design | arch | e2e | critic/challenger |`, each cell `INVOKE`/`SKIP` plus a 3-5 word reason. Judge only what this change adds; never copy the previous row.
3. **Discovery appends**: new stories or rules -> the product analyst adds `US`/`AC` tagged `C-NN`; a new screen or visual pattern -> the UI/UX designer adds the screen delta; a new schema, contract or dependency -> the architect writes a new ADR. Run the alignment gate again only when the change is Tier 2/3 and a discovery row is `INVOKE`.
4. **Test the delta**: brief `qa-tester` with the change ID and the changed files. It extends `test-matrix.md`, runs only the affected tests, and runs the full suite at most once per change, skipping it when nothing changed since the last green full run.
5. **Keep `PLAN.md <= 50 lines`**: collapse finished change rows to one line each.

### Safe Parallel Dispatch
1. **Parallel only when it pays**: `>= 2` independent, substantial tracks split by ownership (app, package, module); otherwise one implementer. At most 3 implementers at once.
2. **Contract first**: shared contracts (API/schema, data model, shared package) and shared files (manifests, lockfiles, routers, DI, entry points, migrations, generated code) change in ONE integration step that is committed before the fan-out.
3. **Mode A [DEFAULT] — one working tree, disjoint files**: every brief lists `Owned Files`, `Forbidden` files, the scoped test command and the return contract. Workers never run git writes, dependency installs or code generation, and run only their scoped tests. The orchestrator runs the affected suites once at fan-in and commits each track with `git add <owned files>`.
4. **Mode B — worktrees, only when tracks must edit the same files and cannot be sequenced**:
   - Claude Code (`isolation: "worktree"`): worktrees branch from the default branch unless a settings file (`.claude/settings.json`, `.claude/settings.local.json` or `~/.claude/settings.json`) sets `"worktree": {"baseRef": "head"}`; each worktree is a fresh checkout, so gitignored files are copied only when listed in `.worktreeinclude` and dependencies are installed inside the worktree.
   - Antigravity (workspace `branch`): the base commit is undocumented, so the worker first runs `git merge-base --is-ancestor <feature HEAD sha> HEAD` and stops on a non-zero exit.
   - Either host: `python3 ./skills/loop-engineering/scripts/run_parallel_agents.py tasks.json` creates the worktrees from the current HEAD.
   - Workers commit on their own branch and return its name; the orchestrator merges one branch at a time (`git merge --no-ff`), tests after each merge, and on a conflict aborts the merge and hands it to an implementer.
5. **Worker Return Contract**: workers return `<= 15 lines` (status, files changed, test command + exit code, next step); reviewers return `<= 50 lines` (verdict, `file:line` findings, required fixes).

### Discovery & Review Topologies
1. **Sequential discovery**: product -> design -> architecture, never in parallel (they share `docs/<feature-name>/spec.md`, each editing only its own section).
2. **Adversarial Review Committee (Tier 3)**: capability-gated `critic` (`>= 150 LOC` diffs), `challenger` (auth/payments/concurrency/untrusted input), fail-honest `e2e-blackbox-tester` (only with a runnable web UI).
3. **Self-Correction Protocol (Strict 3-Loop Cap)**: remediate surgically up to 3 iterations; then halt and escalate (failing output, hypotheses tried, decision needed).

## Usage
```bash
python3 ./skills/loop-engineering/scripts/run_parallel_agents.py tasks.json   # Mode B worktrees from HEAD
python3 ./skills/loop-engineering/scripts/pr_cron_reviewer.py                # audit worker branches
```
- **Claude Code**: parallel fan-out = several `Agent` calls in one message; Mode B = `isolation: "worktree"` with `worktree.baseRef` set to `"head"`.
- **Antigravity**: several subagents in one `invoke_subagent` call; workspace `inherit` for Mode A, `branch` for Mode B.

## Red Flags
- Reusing a previous change's `Invoke / SKIP` row for a new request, or running the full suite once per agent instead of at most once per change.
- ❌ Concurrent workers editing overlapping files, running git writes or codegen in a shared tree, or running the full test suite inside parallel worker loops.
- ❌ Running the full Tier 3 ceremony on every phase of a well-specified request, or adding features nobody asked for.
- ❌ Over-invoking discovery specialists or adversarial committees on Tier 1 tasks (destroying 70–85% token/latency savings).
- ❌ Leaving target projects without a concise root `AGENTS.md` (`<= 90 lines`) wired to executable commands, `DESIGN.md`, and `context/memory/MEMORY.md`.
- ❌ Exceeding the 3-loop self-correction cap or skipping `ask_question` alignment on Tier 2 / Tier 3 tasks.

## Verification
- [ ] SDLC Tier (`Tier 1` `Fast-Track`, `Tier 2` `Standard`, or `Tier 3` `Mission-Critical`) and capability-gated `Invoke / SKIP` table recorded in `docs/<feature-name>/PLAN.md` (`<= 50 lines`).
- [ ] Target-project root `AGENTS.md` (`<= 90 lines`) bootstrapped or updated per [references/project-agents-template.md](references/project-agents-template.md) when missing or outdated.
- [ ] Parallel tracks verified collision-free (contract-first step committed; Mode A disjoint files, or Mode B worktrees with a verified base commit), with the 3-loop self-correction cap enforced.

## References
- [Target-Project AGENTS.md Template (`<= 65 lines`)](references/project-agents-template.md)
- [Loop Engineering & Multi-Agent Orchestration Reference](references/loop-architecture.md)
