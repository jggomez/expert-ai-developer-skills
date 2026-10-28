---
trigger: always_on
description: Flutter & Dart engineering rules enforcing the 6-State Graph Engineering DAG, 3-Tier Dynamic Routing, Mandatory Architecture Triage Gate, Parallel Fan-Out/Fan-In isolation, Adversarial Review Committee, Cross-AI LLM Wiki memory (context/memory/), and 60/120fps frame budgets.
---

# Flutter & Dart Engineering Rules & Graph Protocol

**Identifier**: `flutter-rules`

## 1. The 6-State Flutter Graph Engineering DAG

Every Flutter task follows an explicit 6-state Directed Acyclic Graph with 3-tier dynamic routing and Parallel Fan-Out / Fan-In:

```
[STATE 0: MEMORY RESTORE & 3-TIER ROUTING GATE]
  ├─► Check Git Branch: If base (main/dev), auto-create 'feat/<slug>'; if Scope Drift, ask user
  ├─► Derive `<feature-name>` slug & ensure `docs/<feature-name>/` directory is created
  ├─► Read context/memory/MEMORY.md (~500 tokens); drill down on demand
  └─► Author/Update PLAN.md with ## 3-Tier Dynamic Routing & Architecture Triage + ## Parallel Execution Tracks
          │
          ├───► [TIER 1: FAST-TRACK (Single-widget localized UI tweak / doc)]
          │        ├── Skip discovery (ui-ux-designer / flutter-architect)
          │        ├── Skip alignment modal (Auto-proceed directly to State 2)
          │        ├── 1 flutter-implementer (Mode A: 'inherit')
          │        └── Fast scoped QA (flutter test assigned test -> exit code 0) ──► [STATE 5]
          │
          ├───► [TIER 2: STANDARD (New screen/view / multi-widget flow)]
          │        ├── State 1: Selective discovery (ui-ux-designer || flutter-architect)
          │        ├── Interactive User Alignment Gate: PAUSE & ask_question modal
          │        ├── State 2: Parallel flutter-implementer tracks (Mode A or Mode B)
          │        └── State 3 & 4: Parallel flutter-reviewer + flutter-release-engineer (docs/<feature-name>/test-matrix.md) ──► [STATE 5]
          │
          └───► [TIER 3: MISSION-CRITICAL / COMPLEX (Greenfield app / core state migration / payment / store release)]
                   ├── State 1: Full discovery in docs/<feature-name>/ (prd.md, design.md, architecture.md, adrs)
                   ├── Interactive User Alignment Gate: PAUSE & ask_question modal (mandatory user sign-off)
                   ├── State 2: Parallel flutter-implementer tracks with strict workspace isolation
                   └── State 3 & 4: ADVERSARIAL REVIEW COMMITTEE (Parallel Fan-Out):
                            ├── flutter-reviewer (60/120fps frame budget, .dispose() leaks, BuildContext gaps)
                            ├── flutter-release-engineer (build flavors, signing, pubspec verification)
                            └── qa-tester (full test suite execution + docs/<feature-name>/test-matrix.md)
                                     │ (If defects found: loop back to State 2, max 3 iterations)
                                     ▼ (Clean 60/120fps, zero leaks, passing tests & builds)
[STATE 5: SHIP & LLM WIKI MEMORY UPDATE]
  └─► Update PLAN.md + Persist milestone into context/memory/ (MEMORY.md, architecture.md, conventions.md, log/YYYY-MM-DD.md)
```

## 2. Inviolable Role Boundaries & Triage Rules

- **Automated Git Branch Governance & Scope Drift Protocol**: The orchestrator must never develop or modify code directly on base or protected branches (`main`, `master`, `develop`, `dev`). At State 0, before authoring tasks or modifying files, it checks the active branch (`git symbolic-ref --short HEAD`). If on a base branch, it automatically creates and switches to a dedicated feature branch using Conventional naming (`git checkout -b feat/<slug>` or `git checkout -b fix/<slug>`). When on an existing feature branch and the user request represents orthogonal or unrelated functionality, it detects scope drift and proactively prompts the user via `ask_question` recommending a new dedicated branch.
- **Feature Directory Creation in State 0 / State 1**: The orchestrator detects incoming feature requests and derives the `<feature-name>` slug (e.g. `user-auth`, `order-checkout`). It ensures `docs/<feature-name>/` directory is created (creating `docs/` if not present) where all discovery artifacts (`prd.md`, `design.md`, `architecture.md`, `adr-*.md`) and verification artifacts (`test-matrix.md`) will be stored. If the workspace already has `docs/specifications/` or existing docs, it instructs specialists to synchronize them.
- **Orchestrator Boundary**: `flutter-feature-orchestrator` is purely a Coordinator. It is **STRICTLY PROHIBITED** from directly editing `.dart` files in `lib/` or `test/`. It only edits `PLAN.md`, `doc/adr/*.md`, `context/memory/**`, `.agents/`, and markdown files in `docs/` (including `docs/<feature-name>/`).
- **3-Tier Dynamic Routing Rubric for Flutter**:
  - **Tier 1 (Fast-Track)**: Single-widget localized UI tweaks, minor text/styling adjustments with zero state or routing changes, documentation/comment updates. Skip discovery (`ui-ux-designer`, `flutter-architect`), skip alignment modal (auto-proceed), dispatch 1 `flutter-implementer` (`Workspace: 'inherit'`), and perform fast scoped QA (`flutter test <assigned_test>.dart` with `exit code 0`).
  - **Tier 2 (Standard)**: New screens/views, multi-widget flows, presentation components with local state, route additions, or moderate state refactoring (>= 2 widgets/notifiers). Perform selective discovery upfront (`ui-ux-designer` for mobile `design.md` tokens/touch targets and/or `flutter-architect` for ADRs/contracts) in `docs/<feature-name>/`, pause for Interactive User Alignment Gate (`ask_question`), run parallel implementation (Mode A Disjoint Files or Mode B Git Worktree), and verify via `docs/<feature-name>/test-matrix.md` (`exit code 0`) plus parallel `flutter-reviewer` and `flutter-release-engineer`.
  - **Tier 3 (Mission-Critical / Complex)**: Greenfield Flutter apps from scratch, core state management architecture migrations (e.g. Provider to Riverpod/Bloc), payment/checkout or auth flows, native platform channels/FFI, or production store release bundle engineering. Author full discovery suite in `docs/<feature-name>/` (`prd.md`, mobile `design.md`, `architecture.md`, `doc/adr/*.md`), enforce mandatory Interactive User Alignment Gate (`ask_question`), execute parallel implementation with strict collision prevention, and dispatch the full **Adversarial Review Committee**:
    - `flutter-reviewer`: 60/120fps frame budgets, `.dispose()` leak audits, `BuildContext` async gap checks, accessibility semantics.
    - `flutter-release-engineer`: Flavor separation, `--dart-define-from-file`, app signing, release build matrix for iOS/Android/Web.
    - `qa-tester`: Full test suite execution across unit, widget, and golden tests, generating `docs/<feature-name>/test-matrix.md` with 100% critical path coverage & `exit code 0`.
- **Mandatory Flutter Discovery & Architecture Triage (Tier 2 & Tier 3)**: A `PLAN.md` with a `## Discovery & Architecture Triage` table must be saved to disk before any Dart code is written. `ui-ux-designer` must be evaluated and `design.md` verified/authored for screen/widget changes. `flutter-architect` **MUST** be invoked whenever `>= 2` screens/widgets/notifiers are created/modified, state management contracts change, `GoRouter` routes change, or platform channels/native plugins are added (*only skip* for single-widget localized UI tweaks where state management is unchanged).
- **Interactive User Alignment Gate (State 1 -> State 2 Transition)**:
  - When Discovery completes, evaluate task complexity:
    - **Tier 2 / Tier 3 Tasks**: The Orchestrator MUST PAUSE and query the user using `ask_question` (interactive GUI dialog modal) presenting a structured summary of Product Scope (`docs/<feature-name>/prd.md` if present), UI/UX Design decisions & components (`docs/<feature-name>/design.md`), and Architectural decisions & ADRs (`docs/<feature-name>/architecture.md` / `doc/adr/`), asking: *"Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"*. Wait for explicit user confirmation before delegating to `flutter-implementer`.
    - **Tier 1 Tasks**: Pure technical bugfixes with known root causes or single-widget localized UI tweaks proceed directly to State 2 without interruption.
- **Reinforced Parallel Collision Prevention Analysis & Scoped Test Isolation (`State 2`)**:
  - **Collision Analysis**: Orchestrator must analyze and verify that parallel tracks never share files under Mode A (`Owned Files` strictly non-overlapping).
  - **Mode B Trigger**: If two tracks must modify shared files (e.g. `main.dart`, shared router, `pubspec.yaml`, DI containers, `build_runner`), orchestrator must enforce Mode B (Git Worktree Isolation) or split them into sequential phases.
  - **Scoped Test Execution Isolation**: Each parallel implementer must only run its assigned test file (e.g. `flutter test test/features/...`), NOT the full test suite in tight loops, to avoid CPU contention, redundant testing, and major execution delays. Full test suite is reserved for State 3 Fan-In by `flutter-reviewer` / QA.
  - **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**: Parallel `flutter-implementer` instances are assigned strictly non-overlapping `Owned Files` lists. Zero `git merge` overhead upon Fan-In.
  - **Mode B — Git Worktree Isolation (`Workspace: 'share'` / `'branch'` or `git worktree`)**: Used when parallel `flutter-implementer` instances must modify shared files (`pubspec.yaml`, global router, DI setup) or run conflicting `build_runner` codegen.
- **Parallel Verification & Bounded Retries (`State 3 & 4`)**:
  - Verification must satisfy tier requirements (Tier 1 scoped tests exit 0; Tier 2 `flutter-reviewer` + `flutter-release-engineer` with `docs/<feature-name>/test-matrix.md`; Tier 3 Adversarial Review Committee).
  - Self-correction loops back to `flutter-implementer` are capped at **max 3 iterations** before escalating to the user.
- **Token-Conserving LLM Wiki Memory (`context/memory/`)**: Silently read `context/memory/MEMORY.md` at `State 0` and update `context/memory/` (`MEMORY.md`, `architecture.md`, `conventions.md`, `log/YYYY-MM-DD.md`) **only at `State 5`** (or on explicit user handoff). Never write checkpoints on intermediate turns.

## 3. Flutter Framework Constraints

- **Frame Budget**: 60fps (16ms) / 120fps (8ms). Prevent expensive computations inside `build()`.
- **State Management**: One primary solution per app (Riverpod/Bloc/Signals). Use `setState` only for local ephemeral widget state.
- **Memory Leaks**: All `AnimationController`, `TextEditingController`, `ScrollController`, `FocusNode`, and `StreamSubscription` instances must call `.dispose()`.
- **Async Gaps**: Always check `if (!mounted) return;` before using `BuildContext` across `await`.
- **Config & Secrets**: Use `--dart-define-from-file` with `config/<env>.json`. Never commit secrets.
