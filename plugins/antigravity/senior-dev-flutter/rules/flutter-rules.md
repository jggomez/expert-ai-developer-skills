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
  ├─► Read context/memory/MEMORY.md (~500 tokens); drill down on demand
  └─► Author/Update PLAN.md with ## Discovery & Architecture Triage + ## Parallel Execution Tracks
          │
          ▼
[STATE 1: UPFRONT ARCHITECTURE EXECUTION (Sequential or Parallel Fan-Out)]
  └─► invoke_subagent(flutter-architect) — MANDATORY when >=2 screens/widgets/notifiers,
      state management (Riverpod/Bloc/Signals), GoRouter routes, or native plugins change
          │
          ▼
[STATE 2: IMPLEMENTATION — PARALLEL FAN-OUT & WORKSPACE ISOLATION]
  ├─► Mode A (Default): Disjoint File Partitioning (Workspace: 'inherit', non-overlapping Owned Files)
  └─► Mode B: Git Worktree Isolation (Workspace: 'share'/'branch' or git worktree for pubspec/router/build_runner)
  └─► invoke_subagent(flutter-implementer) x 1..N in parallel ──► Fan-In barrier
          │
          ▼
[STATE 3 & 4: REVIEW & RELEASE VERIFICATION — PARALLEL FAN-OUT]
  ├─► invoke_subagent(flutter-reviewer)         (60/120fps jank, .dispose() leaks, BuildContext async gaps, semantics)
  └─► invoke_subagent(flutter-release-engineer) (flavors, signing, pubspec verification)
          │
          ├─── (Findings / Regressions? Loop back to State 2 flutter-implementer — Max 3 iterations)
          │ (Clean 60/120fps, Zero Leaks, & Passing Tests)
          ▼
[STATE 5: SHIP & LLM WIKI MEMORY UPDATE]
  └─► Update PLAN.md + Persist milestone into context/memory/ (MEMORY.md, architecture.md, conventions.md, log/YYYY-MM-DD.md)
```

## 2. Inviolable Role Boundaries & Triage Rules

- **Orchestrator Boundary**: `flutter-feature-orchestrator` is purely a Coordinator. It is **STRICTLY PROHIBITED** from directly editing `.dart` files in `lib/` or `test/`. It only edits `PLAN.md`, `doc/adr/*.md`, `context/memory/**`, `.agents/`, and markdown files in `docs/`.
- **Plan First & Mandatory Architecture Triage**: A `PLAN.md` with a `## Discovery & Architecture Triage` table must be saved to disk before any Dart code is written. `flutter-architect` **MUST** be invoked whenever `>= 2` screens/widgets/notifiers are created/modified, state management contracts change, `GoRouter` routes change, or platform channels/native plugins are added (*only skip* for single-widget localized UI tweaks where state management is unchanged).
- **Parallel Fan-Out Isolation**: When dispatching parallel `flutter-implementer` tracks, enforce disjoint `Owned Files` under Mode A (`Workspace: 'inherit'`) or use Git Worktree isolation (Mode B) when touching shared `pubspec.yaml`, global router, or `build_runner` codegen.
- **Token-Conserving LLM Wiki Memory (`context/memory/`)**: Silently read `context/memory/MEMORY.md` at `State 0` and update `context/memory/` (`MEMORY.md`, `architecture.md`, `conventions.md`, `log/YYYY-MM-DD.md`) **only at `State 5`** (or on explicit user handoff). Never write checkpoints on intermediate turns.

## 3. Flutter Framework Constraints

- **Frame Budget**: 60fps (16ms) / 120fps (8ms). Prevent expensive computations inside `build()`.
- **State Management**: One primary solution per app (Riverpod/Bloc/Signals). Use `setState` only for local ephemeral widget state.
- **Memory Leaks**: All `AnimationController`, `TextEditingController`, `ScrollController`, `FocusNode`, and `StreamSubscription` instances must call `.dispose()`.
- **Async Gaps**: Always check `if (!mounted) return;` before using `BuildContext` across `await`.
- **Config & Secrets**: Use `--dart-define-from-file` with `config/<env>.json`. Never commit secrets.
