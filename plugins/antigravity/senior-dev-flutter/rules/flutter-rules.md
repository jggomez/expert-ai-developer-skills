---
trigger: model_decision
description: Flutter & Dart engineering rules enforcing the 9-stage cycle, 60/120fps frame budgets, state management discipline, and subagent orchestration.
---

# Flutter & Dart Engineering Rules

**Identifier**: `flutter-rules`

## 1. The Flutter 9-Stage Command Lifecycle

Follow this command cycle for Flutter application development:

| What you're doing | Command | Key Principle | Assigned Agent / Skill |
| :--- | :--- | :--- | :--- |
| **Define what to build** | `/spec` | Spec before code | `flutter-feature-orchestrator` |
| **Plan how to build it** | `/plan` | Small, atomic tasks | `flutter-architect` (`doc/adr/`) |
| **Build incrementally** | `/build` | One slice at a time | `flutter-implementer` |
| **Prove it works** | `/test` | Tests are proof | `flutter-implementer` (`flutter-test-strategy`) |
| **Set the quality bar** | `/constraints` | Decide it once, enforce it everywhere | `flutter-reviewer` |
| **Review before merge** | `/review` | Improve code health | `flutter-reviewer` (`flutter-review-checklist`) |
| **Audit performance** | `/perf` | Measure before you optimize | `flutter-implementer` (`flutter-performance-profiling`) |
| **Simplify the code** | `/code-simplify` | Clarity over cleverness | `flutter-implementer` |
| **Ship to production** | `/ship` | Faster is safer | `flutter-release-engineer` |

## 2. Dynamic Entry Points & Sizing

The orchestrator (`flutter-feature-orchestrator`) routes based on task complexity:
- **Widget / Single UI Bug**: Route to `/test` -> `/build` -> `/review` -> `/ship`.
- **New Feature Area**: Full sequence starting at `/spec`.
- **Frame Jank / Slow Startup**: Start at `/perf` (profile mode) -> `/build` -> `/perf` -> `/review`.
- **SDK / Package Upgrade**: Start at `/ship` (migration axis: SDK -> deprecations -> dependencies).

## 3. Flutter Framework Constraints

- **Frame Budget**: 60fps (16ms) / 120fps (8ms). Prevent expensive computations inside `build()`.
- **State Management**: One primary solution per app (Riverpod/Bloc/Signals). Use `setState` only for local ephemeral widget state.
- **Memory Leaks**: All `AnimationController`, `TextEditingController`, and `StreamSubscription` instances must call `.dispose()`.
- **Async Gaps**: Always check `if (!mounted) return;` before using `BuildContext` across `await`.
- **Config & Secrets**: Use `--dart-define-from-file` with `config/<env>.json`. Never commit secrets.
