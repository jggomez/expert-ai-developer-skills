---
trigger: always_on
description: Flutter & Dart engineering rules enforcing the 6-State Graph Engineering DAG, 3-Tier Dynamic Routing, Capability & Risk-Gated Subagent Dispatch, Conciseness Line Budgets, Target-Project AGENTS.md/DESIGN.md/MEMORY.md integration, Fail-Honest E2E reporting, and 60/120fps frame budgets.
---

# Flutter & Dart Engineering Rules & Graph Protocol

**Identifier**: `flutter-rules`

## 1. The 6-State Flutter Graph Engineering DAG

Every Flutter task follows an explicit 6-state Directed Acyclic Graph combining **3-Tier Dynamic Routing** with **Capability & Risk-Gated Dispatch**:

```
[STATE 0: BRANCH, MEMORY, TARGET AGENTS.md & CAPABILITY-GATED TRIAGE]
  ├─► Check Git Branch: Auto-create 'feat/<slug>' off base (main/dev); ask_question on Scope Drift
  ├─► Ensure `docs/<feature-name>/` & read `context/memory/MEMORY.md` silently (~500 tokens)
  ├─► Check/Bootstrap root `AGENTS.md` (<= 90 lines) linking commands, `DESIGN.md` & `MEMORY.md`
  └─► Author `PLAN.md` (<= 50 lines/feature): Classify Tier 1/2/3 + 5-row Invoke/SKIP Triage Table
          ├───► [TIER 1: FAST-TRACK] -> Skip State 1 & modal -> 1 flutter-implementer -> Scoped flutter test -> [STATE 5]
          ├───► [TIER 2: STANDARD] -> State 1 (ONLY invoked discovery; skip if all SKIP) -> ask_question modal
          │        -> State 2 Parallel Build -> State 3/4 flutter-reviewer + qa-tester (+ release if config) -> [STATE 5]
          └───► [TIER 3: MISSION-CRITICAL] -> State 1 (Capability-gated discovery) -> ask_question modal
                   -> State 2 Isolated Build -> State 3 & 4: ADVERSARIAL REVIEW COMMITTEE -> [STATE 5]
[STATE 5: SHIP & MEMORY SYNC] -> Finalize PLAN.md, sync AGENTS.md & context/memory/, Fail-Honest E2E summary
```

## 2. Inviolable Role Boundaries & Capability-Gated Governance

- **Automated Git Branch Governance & Scope Drift Protocol**: Never develop directly on protected base branches (`main`, `master`, `develop`, `dev`). At State 0, inspect `git symbolic-ref --short HEAD`: if on a base branch, auto-create `git checkout -b feat/<slug>` (or `fix/<slug>`). On an existing feature branch, detect orthogonal requests (**Scope Drift**) and prompt via `ask_question` recommending `feat/<new-slug>`.
- **Orchestrator Boundary**: `flutter-feature-orchestrator` is strictly prohibited from editing `.dart` files in `lib/` or `test/`. Direct writes are restricted to `PLAN.md`, root `AGENTS.md`, root `DESIGN.md`, `doc/adr/*.md`, `context/memory/**`, `.agents/`, and `docs/` (`docs/<feature-name>/`).
- **Target-Project `AGENTS.md` + `DESIGN.md` + `context/memory/MEMORY.md` Integration**:
  - Silently read `context/memory/MEMORY.md` at `State 0` (~500 tokens); drill down on demand.
  - At `State 0` / `State 5`, check if root `AGENTS.md` exists. If missing (or stack/commands/conventions changed), generate/update a concise root `AGENTS.md` (`<= 90 lines`) linking executable commands (`flutter analyze`, `flutter test`), root `DESIGN.md`, and `context/memory/MEMORY.md`.
- **3-Tier Dynamic Routing & Capability/Risk-Gated Dispatch (Anti-Over-Invocation)**:
  - Keep **Tier 1 (Fast-Track)** (`< 2` files localized tweak/fix), **Tier 2 (Standard)** (`2–4` files, new screen/flow/route), and **Tier 3 (Mission-Critical)** (greenfield app, core state migration, payments/auth, FFI/native plugins, store release), **BUT gate every subagent individually in State 0** via a 5-row `Invoke / SKIP` table in `PLAN.md` (`<= 50 lines`):
    1. **`product-analyst`**: **INVOKE ONLY IF** business scope, user stories, or acceptance criteria are missing/ambiguous (`docs/<feature-name>/prd.md <= 70 lines`). **SKIP** when clear stories/criteria exist, or for bugfixes, refactors, docs, and chores.
    2. **`ui-ux-designer`**: **INVOKE ONLY IF** Flutter screens/widgets/components are created/modified AND root `DESIGN.md` is missing or new mobile visual patterns/48x48dp touch tokens are needed (root `DESIGN.md <= 110 lines`; `docs/<feature-name>/design.md <= 35 lines` for screen deltas). **SKIP** on non-visual data/logic fixes or minor UI tweaks already covered by `DESIGN.md`.
    3. **`flutter-architect`**: **INVOKE ONLY IF** a genuine structural decision is needed (state management architecture/contract shift, `GoRouter`/deep-link topology change, new native plugin/FFI/platform channel; `adr-NNN-*.md <= 55 lines`, `docs/<feature-name>/architecture.md <= 70 lines`). **SKIP** when following established repository architecture.
    4. **`flutter-release-engineer` & Risk Gates (`critic` / `challenger`)**: Invoke `flutter-release-engineer` **ONLY IF** `pubspec.yaml`, flavors, `--dart-define-from-file`, signing, native configs, or store bundles change (and in Tier 3 `Adversarial Review Committee`); in Tier 3, invoke `critic` ONLY IF diff `>= 150 LOC` / structural refactor and `challenger` ONLY IF touching auth, payments, concurrency/isolates, untrusted input parsing, or destructive mutations (`<= 50 lines`).
    5. **`e2e-blackbox-tester`**: **INVOKE ONLY IF** a runnable Flutter Web UI (`localhost`/staging URL) exists AND UI/user flows were touched (`blackbox-report.md <= 50 lines`). **ALWAYS SKIP** on mobile-only targets without web (`iOS`/`Android`-only) or pure data/logic tasks.
  - **Zero-Bloat Fast-Forward**: If ALL Discovery specialists evaluate to `SKIP`, skip State 1 discovery file bloat and go straight to alignment/build.
- **Interactive User Alignment Gate (State 1 -> State 2)**: Skip for Tier 1. Mandatory `ask_question` modal for Tier 2 & Tier 3 summarizing scope, mobile UI design, and architecture before delegating to `flutter-implementer`.
- **Collision Analysis & Scoped Test Isolation (`State 2`)**:
  - **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**: Strictly non-overlapping `Owned Files` across parallel `flutter-implementer` tracks.
  - **Mode B — Git Worktree Isolation (`Workspace: 'share'` / `'branch'` or `git worktree`)**: Mandatory when parallel tracks modify shared files (`main.dart`, global router, `pubspec.yaml`, DI, `build_runner`).
  - **Scoped Test Isolation**: Parallel implementers run ONLY their assigned test file during TDD loops; full suite execution is reserved for State 3.
- **Strict Artifact Line Budgets & Fail-Honest E2E (`State 3 & 4`)**:
  - Enforce hard line caps: `PLAN.md <= 50 lines/feature`, `AGENTS.md <= 90`, `prd.md <= 70`, `DESIGN.md <= 110`, `design.md <= 35`, `adr-NNN-*.md <= 55`, `architecture.md <= 70`, `docs/<feature-name>/test-matrix.md <= 80`, review/adversarial/blackbox reports `<= 50`.
  - **Fail-Honest E2E**: If `e2e-blackbox-tester` returns `BLOCKED` or `SKIPPED`, explicitly report: *"Browser E2E was NOT executed (`BLOCKED`/`SKIPPED`): <exact reason>"* — NEVER mask it as passed.
  - Self-correction retries back to `flutter-implementer` are capped at **max 3 iterations**.
- **State 5 — LLM Wiki Memory (`context/memory/`)**: Update `context/memory/MEMORY.md` (`<= 80-100 lines`), topic pages if changed, and `context/memory/log/YYYY-MM-DD.md` (`5-8 lines`) only at `State 5`.

## 3. Flutter Framework Constraints

- **Frame Budget**: 60fps (16ms) / 120fps (8ms). Prevent expensive computations inside `build()`.
- **State & Lifecycle**: One primary state solution per app (Riverpod/Bloc/Signals); dispose all controllers/subscriptions (`.dispose()`); guard `BuildContext` across `await` (`if (!mounted) return;`).
- **Config & Secrets**: Use `--dart-define-from-file` with `config/<env>.json`; never commit raw secrets.
