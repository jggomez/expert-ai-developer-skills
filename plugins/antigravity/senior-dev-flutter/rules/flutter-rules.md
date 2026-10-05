---
trigger: always_on
description: Flutter & Dart engineering rules enforcing Graph Engineering DAG, 60/120fps frame budgets, state management discipline, and mandatory subagent orchestration.
---

# Flutter & Dart Engineering Rules & Graph Protocol

**Identifier**: `flutter-rules`

## 1. The Flutter Graph Engineering DAG

Every Flutter task follows an explicit Directed Acyclic Graph:

```
[PLAN FIRST GATE: PLAN.md]
          │
          ▼
[ARCHITECTURE (Optional)]: flutter-architect
          │
          ▼
[BUILD (Mandatory)]: invoke_subagent(flutter-implementer)
          │
          ▼
[REVIEW & AUDIT (Mandatory)]: invoke_subagent(flutter-reviewer)  <──(Fix loop)──┐
          │ (Clean 60fps & Passing Tests)                                       │
          ▼                                                                     │
[RELEASE & SHIP (Mandatory)]: invoke_subagent(flutter-release-engineer) ───────┘
          │ (Ready to merge)
          ▼
[DELIVERY REPORT]
```

## 2. Inviolable Role Boundaries

- **Orchestrator Boundary**: `flutter-feature-orchestrator` is purely a Coordinator. It is **STRICTLY PROHIBITED** from directly editing `.dart` files in `lib/` or `test/`. It only edits `PLAN.md`, `doc/adr/*.md`, and markdown files.
- **Plan First**: A `PLAN.md` must be saved to disk before any Dart code is written.
- **Mandatory Pipeline**: Every UI or logic modification must traverse `flutter-implementer` -> `flutter-reviewer` -> `flutter-release-engineer`.

## 3. Flutter Framework Constraints

- **Frame Budget**: 60fps (16ms) / 120fps (8ms). Prevent expensive computations inside `build()`.
- **State Management**: One primary solution per app (Riverpod/Bloc/Signals). Use `setState` only for local ephemeral widget state.
- **Memory Leaks**: All `AnimationController`, `TextEditingController`, and `StreamSubscription` instances must call `.dispose()`.
- **Async Gaps**: Always check `if (!mounted) return;` before using `BuildContext` across `await`.
- **Config & Secrets**: Use `--dart-define-from-file` with `config/<env>.json`. Never commit secrets.
