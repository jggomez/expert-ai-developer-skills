---
trigger: model_decision
description: Load when dispatching several subagents, splitting work into parallel tracks, using git worktrees, or running a multi-phase plan - collision-free parallelism and bounded loops.
---

# Multi-Agent Operations Rules

Follow the `loop-engineering` skill (Lean Execution Defaults and Safe Parallel Dispatch). Invariants:
- **Lean by default**: scale alone never makes a task Tier 3; a well-specified multi-phase request runs discovery, review and E2E once, with one commit per phase. Never add features nobody asked for.
- **Parallel only when it pays**: `>= 2` independent tracks with disjoint files, at most 3 implementers at once; otherwise one implementer.
- **Contract first**: shared files (manifests, lockfiles, routers, DI, entry points, migrations, generated code) change in one committed step before the fan-out.
- **Shared working tree (workspace `inherit`)**: every worker gets `Owned Files` and `Forbidden` lists, never runs git writes, dependency installs or code generation, and runs only its scoped tests. The orchestrator commits at fan-in.
- **Worktrees (workspace `branch`) only when tracks must edit the same files**: the worker first runs `git merge-base --is-ancestor <feature HEAD sha> HEAD` and stops on a non-zero exit; it commits on its branch, and the orchestrator merges branches one at a time with tests after each.
- **Bounded loops**: at most 3 fix iterations, then stop and escalate with the failing output. Never poll subagents in a loop.
- **Fail-honest**: surface `BLOCKED` / `SKIPPED` checks to the user verbatim.
- Governance files stay small: root `AGENTS.md <= 90` lines, root `DESIGN.md <= 110`, `PLAN.md <= 50` per feature, artifacts in `docs/<feature-name>/`.
