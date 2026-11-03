---
trigger: model_decision
description: Apply when planning or coordinating a multi-step coding task, splitting work across subagents, or deciding how much process (plan, review, QA) a change needs.
---

# Rule: Engineering Execution Workflow

**Identifier**: `loop-engineering-workflow`

Scale the process to the risk of the change, never to its size. The full state machine lives in the `loop-engineering` skill and the orchestrator agents; this rule only holds the invariants.

## 1. Lean by Default
- **MUST** pick the lightest tier that fits: Tier 1 (Fast-Track) for fixes, chores and localized refactors; Tier 2 (Standard) for a new endpoint, screen or schema change; Tier 3 (Mission-Critical) only for auth, payments, data migrations or breaking public APIs. Scale alone **NEVER** makes a task Tier 3.
- **MUST** build exactly what was asked. Project rules constrain *how*, never *what*; list extra ideas as suggestions instead of implementing them.
- **Multi-phase requests**: plan and confirm once, then run each phase at its own tier. Stop and report when a phase goes red instead of starting the next one.

## 2. Plan, Delegate, Prove
- **MUST** write a short `PLAN.md` before multi-file changes; small surgical edits need none.
- Orchestrators coordinate and write only plans and docs; implementers write code.
- "Done" means a test command with `exit code 0`. **NEVER** weaken assertions to reach green. Run `qa-tester` / `compliance-verifier` when the tier calls for them, not on every change.

## 3. Parallel Work Without Collisions
- Run tasks in parallel only when they are truly independent and the gain is real; at most 3 implementers at once.
- **Contract first**: agree on shared types, API shapes and file ownership before fanning out.
- **Default (shared tree)**: every worker owns a disjoint list of files and **NEVER** runs git writes, dependency installs or code generation; the orchestrator does those once after fan-in.
- **When files must overlap**: give each worker its own git worktree branched from the current feature branch, have each commit there, and merge the branches one at a time with tests after each merge.
