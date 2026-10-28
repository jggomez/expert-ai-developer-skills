---
trigger: always_on
description: Flutter & Dart engineering rules enforcing the 6-State Graph Engineering DAG, Mandatory Architecture Triage Gate, Parallel Fan-Out/Fan-In isolation, Cross-AI LLM Wiki memory (context/memory/), and 60/120fps frame budgets.
---

# Flutter & Dart Engineering Rules & Graph Protocol

**Identifier**: `flutter-rules`

## 1. The 6-State Flutter Graph Engineering DAG

Every Flutter task follows an explicit 6-state Directed Acyclic Graph with Parallel Fan-Out / Fan-In:

```
[STATE 0: MEMORY RESTORE & ARCHITECTURE TRIAGE GATE]
  ├─► Check Git Branch: If base (main/dev), auto-create 'feat/<slug>'; if Scope Drift, ask user
  ├─► Derive `<feature-name>` slug & ensure `docs/<feature-name>/` directory is created
  ├─► Read context/memory/MEMORY.md (~500 tokens); drill down on demand
  └─► Author/Update PLAN.md with ## Discovery & Architecture Triage + ## Parallel Execution Tracks
          │
          ▼
[STATE 1: UPFRONT ARCHITECTURE EXECUTION (Sequential or Parallel Fan-Out)]
  ├─► Evaluate ui-ux-designer / design.md mobile triage (screens/widgets, theme, tokens, 48x48dp touch targets)
  ├─► invoke_subagent(flutter-architect) — MANDATORY when >=2 screens/widgets/notifiers,
  │   state management (Riverpod/Bloc/Signals), GoRouter routes, or native plugins change
  ├─► Store discovery outputs in `docs/<feature-name>/` (prd.md, design.md, architecture.md, adr-*.md)
  └─► Synchronize existing `docs/specifications/` or legacy documentation if present
          │
          ▼
[INTERACTIVE USER ALIGNMENT GATE (STATE 1 -> STATE 2 TRANSITION)]
  ├── Low/Simple Tasks (Bugfixes, single-widget UI tweak): Auto-proceed to State 2
  └── Medium or High/Complex Tasks: PAUSE & `ask_question` (PRD + design.md + architecture.md summary)
        └── Wait for explicit user confirmation before State 2 build
        │ (Approved)
        ▼
[STATE 2: IMPLEMENTATION — PARALLEL FAN-OUT & WORKSPACE ISOLATION]
  ├── Collision Analysis: Verify zero file overlaps in Mode A; trigger Mode B if shared files touched
  ├── Mode A (Default): Disjoint File Partitioning (Workspace: 'inherit', non-overlapping Owned Files)
  ├── Mode B: Git Worktree Isolation (Workspace: 'share'/'branch' or git worktree for pubspec/router/build_runner)
  ├── Scoped Test Isolation: Implementers run ONLY assigned test file (e.g. flutter test test/features/a_test.dart)
  └── invoke_subagent(flutter-implementer) x 1..N in parallel ──► Fan-In barrier
          │
          ▼
[STATE 3 & 4: REVIEW & RELEASE VERIFICATION — PARALLEL FAN-OUT]
  ├─► invoke_subagent(flutter-reviewer)         (full suite test run, 60/120fps jank, .dispose() leaks, async gaps)
  └─► invoke_subagent(flutter-release-engineer) (flavors, signing, pubspec verification)
          │
          ├─── (Findings / Regressions? Loop back to State 2 flutter-implementer — Max 3 iterations)
          │ (Clean 60/120fps, Zero Leaks, & Passing Tests)
          ▼
[STATE 5: SHIP & LLM WIKI MEMORY UPDATE]
  └─► Update PLAN.md + Persist milestone into context/memory/ (MEMORY.md, architecture.md, conventions.md, log/YYYY-MM-DD.md)
```

## 2. Inviolable Role Boundaries & Triage Rules

- **Automated Git Branch Governance & Scope Drift Protocol**: The orchestrator must never develop or modify code directly on base or protected branches (`main`, `master`, `develop`, `dev`). At State 0, before authoring tasks or modifying files, it checks the active branch (`git symbolic-ref --short HEAD`). If on a base branch, it automatically creates and switches to a dedicated feature branch using Conventional naming (`git checkout -b feat/<slug>` or `git checkout -b fix/<slug>`). When on an existing feature branch and the user request represents orthogonal or unrelated functionality, it detects scope drift and proactively prompts the user via `ask_question` recommending a new dedicated branch.
- **Feature Directory Creation in State 0 / State 1**: The orchestrator detects incoming feature requests and derives the `<feature-name>` slug (e.g. `user-auth`, `order-checkout`). It ensures `docs/<feature-name>/` directory is created (creating `docs/` if not present) where all discovery artifacts (`prd.md`, `design.md`, `architecture.md`, `adr-*.md`) will be stored. If the workspace already has `docs/specifications/` or existing docs, it instructs specialists to synchronize them.
- **Orchestrator Boundary**: `flutter-feature-orchestrator` is purely a Coordinator. It is **STRICTLY PROHIBITED** from directly editing `.dart` files in `lib/` or `test/`. It only edits `PLAN.md`, `doc/adr/*.md`, `context/memory/**`, `.agents/`, and markdown files in `docs/` (including `docs/<feature-name>/`).
- **Plan First & Mandatory Discovery & Architecture Triage**: A `PLAN.md` with a `## Discovery & Architecture Triage` table must be saved to disk before any Dart code is written. `ui-ux-designer` must be evaluated and `design.md` verified/authored for screen/widget changes. `flutter-architect` **MUST** be invoked whenever `>= 2` screens/widgets/notifiers are created/modified, state management contracts change, `GoRouter` routes change, or platform channels/native plugins are added (*only skip* for single-widget localized UI tweaks where state management is unchanged).
- **Interactive User Alignment Gate (State 1 -> State 2 Transition)**:
  - When Discovery completes, evaluate task complexity:
    - **Medium or High/Complex Tasks**: The Orchestrator MUST PAUSE and query the user using `ask_question` (interactive GUI dialog modal) presenting a structured summary of Product Scope (`docs/<feature-name>/prd.md` if present), UI/UX Design decisions & components (`docs/<feature-name>/design.md`), and Architectural decisions & ADRs (`docs/<feature-name>/architecture.md` / `doc/adr/`), asking: *"Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"*. Wait for explicit user confirmation before delegating to `flutter-implementer`.
    - **Low/Simple Tasks**: Pure technical bugfixes with known root causes or single-widget localized UI tweaks proceed directly to State 2 without interruption.
- **Reinforced Parallel Collision Prevention Analysis & Scoped Test Isolation (`State 2`)**:
  - **Collision Analysis**: Orchestrator must analyze and verify that parallel tracks never share files under Mode A (`Owned Files` strictly non-overlapping).
  - **Mode B Trigger**: If two tracks must modify shared files (e.g. `main.dart`, shared router, `pubspec.yaml`, DI containers, `build_runner`), orchestrator must enforce Mode B (Git Worktree Isolation) or split them into sequential phases.
  - **Scoped Test Execution Isolation**: Each parallel implementer must only run its assigned test file (e.g. `flutter test test/features/...`), NOT the full test suite in tight loops, to avoid CPU contention, redundant testing, and major execution delays. Full test suite is reserved for State 3 Fan-In by `flutter-reviewer`.
  - **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**: Parallel `flutter-implementer` instances are assigned strictly non-overlapping `Owned Files` lists. Zero `git merge` overhead upon Fan-In.
  - **Mode B — Git Worktree Isolation (`Workspace: 'share'` / `'branch'` or `git worktree`)**: Used when parallel `flutter-implementer` instances must modify shared files (`pubspec.yaml`, global router, DI setup) or run conflicting `build_runner` codegen.
- **Parallel Verification & Bounded Retries (`State 3 & 4`)**:
  - Every code change MUST be verified by `flutter-reviewer` (full suite test pass, 60/120fps frame budgets, zero leaks) and `flutter-release-engineer` (flavors, signing, pubspec verification), which can run in parallel.
  - Self-correction loops back to `flutter-implementer` are capped at **max 3 iterations** before escalating to the user.
- **Token-Conserving LLM Wiki Memory (`context/memory/`)**: Silently read `context/memory/MEMORY.md` at `State 0` and update `context/memory/` (`MEMORY.md`, `architecture.md`, `conventions.md`, `log/YYYY-MM-DD.md`) **only at `State 5`** (or on explicit user handoff). Never write checkpoints on intermediate turns.

## 3. Flutter Framework Constraints

- **Frame Budget**: 60fps (16ms) / 120fps (8ms). Prevent expensive computations inside `build()`.
- **State Management**: One primary solution per app (Riverpod/Bloc/Signals). Use `setState` only for local ephemeral widget state.
- **Memory Leaks**: All `AnimationController`, `TextEditingController`, `ScrollController`, `FocusNode`, and `StreamSubscription` instances must call `.dispose()`.
- **Async Gaps**: Always check `if (!mounted) return;` before using `BuildContext` across `await`.
- **Config & Secrets**: Use `--dart-define-from-file` with `config/<env>.json`. Never commit secrets.
