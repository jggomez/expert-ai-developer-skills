---
trigger: always_on
description: Senior developer engineering rules enforcing Graph Engineering DAG, 3-Tier Adaptive SDLC, Capability & Risk-Gated Subagent Dispatch, Conciseness Line Budgets, Target-Project AGENTS.md/DESIGN.md/MEMORY.md integration, Fail-Honest E2E reporting, and orchestrator non-execution boundaries.
---

# Senior Dev Engineering Rules & Graph Engineering Protocol

**Identifier**: `senior-dev-rules`

## 1. Graph Engineering State Machine (Execution DAG)

All tasks handled by `senior-dev-orchestrator` follow a 6-state Directed Acyclic Graph (DAG) combining **3-Tier Adaptive SDLC** with **Capability & Risk-Gated Dispatch**:

```
[STATE 0: BRANCH, MEMORY, TARGET AGENTS.md & CAPABILITY-GATED TRIAGE (MANDATORY)]
  ├── Check Git Branch: Auto-create 'feat/<slug>' off base (main/develop); ask_question on Scope Drift
  ├── Ensure `docs/<feature-name>/` & read `context/memory/MEMORY.md` silently (~500 tokens)
  ├── Check/Bootstrap root `AGENTS.md` (<= 90 lines) linking commands, `DESIGN.md` & `MEMORY.md`
  └── Author `PLAN.md` (<= 50 lines/feature): Classify Tier 1/2/3 + 5-row Invoke/SKIP Triage Table
        ├───► [TIER 1: FAST-TRACK] -> Skip State 1 & modal -> 1 code-implementer -> Scoped QA + compliance -> [STATE 5]
        ├───► [TIER 2: STANDARD] -> State 1 (ONLY invoked specialists; skip if all SKIP) -> ask_question modal
        │        -> State 2 Parallel Build -> State 3/4 QA (test-matrix.md <= 80) + compliance (+ web E2E if UI) -> [STATE 5]
        └───► [TIER 3: MISSION-CRITICAL] -> State 1 (Capability-gated discovery) -> ask_question modal
                 -> State 2 Isolated Build -> State 3/4 Risk-Gated Adversarial Verification Committee -> [STATE 5]
[STATE 5: SHIP & MEMORY SYNC] -> Finalize PLAN.md, sync AGENTS.md & context/memory/, Fail-Honest E2E summary
```

## 2. Inviolable Role Boundaries & Capability-Gated Governance

- **Git Branch Governance & Proactive Scope Drift**: Never develop directly on protected base branches (`main`, `master`, `develop`, `dev`). At State 0, inspect `git symbolic-ref --short HEAD`: if on a base branch, automatically provision `git checkout -b feat/<slug>` (or `fix/<slug>`) and notify the user. When already on a feature branch and an orthogonal request arrives (**Scope Drift**), prompt via `ask_question` recommending `feat/<new-slug>`.
- **Orchestrator Non-Execution Rule**: `senior-dev-orchestrator` is strictly prohibited from editing application source code or tests (`src/`, `lib/`, `tests/`, etc.). Direct writing tools are reserved exclusively for `PLAN.md`, root `AGENTS.md`, root `DESIGN.md`, `ADR-*.md`, `.agents/`, `docs/` (`docs/<feature-name>/`), and `context/memory/`.
- **Target-Project `AGENTS.md` + `DESIGN.md` + `context/memory/MEMORY.md` Integration**:
  - At State 0, silently read `context/memory/MEMORY.md` (~500 tokens), opening `architecture.md`, `conventions.md`, or `log/YYYY-MM-DD.md` only on demand.
  - At State 0 / State 5, check if the target project has a root `AGENTS.md`. If missing (or if stack/commands/conventions changed), generate/update a concise root `AGENTS.md` (`<= 90 lines`) linking executable build/test/lint commands, root `DESIGN.md`, and `context/memory/MEMORY.md`.
- **3-Tier Dynamic SDLC & Capability/Risk-Gated Dispatch (Anti-Over-Invocation)**:
  - Keep **Tier 1 (Fast-Track)** (`< 2` files localized bugfix/refactor/chore), **Tier 2 (Standard)** (`2–4` files, endpoint, migration, UI screen), and **Tier 3 (Mission-Critical)** (greenfield, auth, payments, core architecture), **BUT evaluate every subagent individually in State 0** via a 5-row `Invoke / SKIP` table in `PLAN.md` (`<= 50 lines`):
    1. **`product-analyst`**: **INVOKE ONLY IF** business scope, user stories, or acceptance criteria are missing/ambiguous (`docs/<feature-name>/prd.md <= 70 lines`). **SKIP** when prompt already defines clear stories/criteria, or for bugfixes, refactors, docs, chores, and technical CLIs.
    2. **`ui-ux-designer`**: **INVOKE ONLY IF** UI screens/widgets/components are created/modified AND root `DESIGN.md` is missing or new visual patterns are needed (root `DESIGN.md <= 110 lines`; `docs/<feature-name>/design.md <= 35 lines` for screen deltas). **SKIP** on backend/API/CLI/SQL tasks or minor UI changes already covered by `DESIGN.md`.
    3. **`architect-engineer`**: **INVOKE ONLY IF** a genuine structural decision is needed (new DB schema/migration, cross-service API contract, new core dependency, architectural pattern shift; `adr-NNN-*.md <= 55 lines`, `docs/<feature-name>/architecture.md <= 70 lines`). **SKIP** when following established repository architecture.
    4. **`critic` & `challenger` (Risk-Gated in Tier 3)**: Invoke `critic` **ONLY IF** diff is `>= 150 LOC` or a multi-module structural refactor (`critic-review.md <= 50 lines`). Invoke `challenger` **ONLY IF** touching high-risk domains (auth, payments, concurrency/locks, untrusted external input parsing, destructive mutations; `adversarial-report.md <= 50 lines`).
    5. **`e2e-blackbox-tester`**: **INVOKE ONLY IF** a runnable web UI (`localhost`/staging URL) exists AND UI/user flows were touched (`blackbox-report.md <= 50 lines`). **ALWAYS SKIP** on pure backends/APIs, CLIs, libraries, SQL/data pipelines, or mobile-only targets without web.
  - **Zero-Bloat Fast-Forward**: If ALL Discovery specialists evaluate to `SKIP` (even on a Tier 2 well-specified technical task), skip State 1 discovery file bloat and proceed straight to alignment/build.
- **Interactive User Alignment Gate (State 1 -> State 2)**: Skip for Tier 1. Mandatory `ask_question` modal for Tier 2 & Tier 3 presenting scope, UI design, and architectural decisions before delegating to `code-implementer`.
- **Collision Analysis & Scoped Test Isolation (`State 2`)**:
  - **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**: Strictly non-overlapping `Owned Files` across parallel `code-implementer` tracks; zero merge overhead.
  - **Mode B — Git Worktree Isolation (`Workspace: 'share'` / `'branch'` or `git worktree`)**: Mandatory when parallel tracks modify shared files (`package.json`, routers, DI containers, `settings.py`).
  - **Scoped Test Isolation**: Parallel implementers run ONLY their assigned test file during TDD loops; full suite execution is reserved for State 3 `qa-tester`.
- **Strict Artifact Line Budgets & Fail-Honest E2E Transparency (`State 3 & 4`)**:
  - Enforce hard line caps: `PLAN.md <= 50 lines/feature`, `AGENTS.md <= 90`, `prd.md <= 70`, `DESIGN.md <= 110`, `design.md <= 35`, `adr-NNN-*.md <= 55`, `architecture.md <= 70`, `docs/<feature-name>/test-matrix.md <= 80`, and adversarial/blackbox reports `<= 50 lines`.
  - **Fail-Honest E2E**: If `e2e-blackbox-tester` returns `BLOCKED` (e.g., server couldn't start, Chromium unavailable) or `SKIPPED`, the orchestrator MUST explicitly tell the user: *"Browser E2E was NOT executed (`BLOCKED`/`SKIPPED`): <exact reason>"* — NEVER mask it as passed.
  - Self-correction retries back to `code-implementer` are capped at **max 3 iterations**.
- **State 5 — LLM Wiki Memory Persistence (`context/memory/`)**: Update `context/memory/MEMORY.md` in-place (`<= 80-100 lines`), update `architecture.md`/`conventions.md` if changed, and append a `5-8 line` block to `context/memory/log/YYYY-MM-DD.md` once per completed milestone.

## 3. Engineering Constraints

- **Strict TDD**: Red-Green-Refactor cycle; empirical proof via `exit code 0` + `compliance-verifier` `APPROVED`.
- **Clean Architecture & Zero Secrets**: Keep domain logic framework-independent; never write raw secrets into code or logs.
