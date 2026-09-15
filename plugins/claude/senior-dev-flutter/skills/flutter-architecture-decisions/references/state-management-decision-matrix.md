# State management decision matrix (Flutter)

Pick **one** primary solution for the app. The goal is a boring, consistent
default — not the "best" library.

## Quick routing

| Situation | Default choice |
| :--- | :--- |
| Local, ephemeral widget state (a toggle, a form field, an animation controller) | `setState` / `StatefulWidget` — always, regardless of the app-wide choice |
| Small app, few cross-screen dependencies, team new to Flutter | `provider` + `ChangeNotifier`, or `flutter_riverpod` with `Notifier` |
| Medium/large app, many async data sources, want compile-safe DI and easy testing | `flutter_riverpod` (`Notifier` / `AsyncNotifier`) |
| Team already fluent in the pattern, wants strict event→state modelling and traceability | `flutter_bloc` (`Cubit` for simple, `Bloc` for event-sourced) |
| Fine-grained reactivity, minimal boilerplate, mostly synchronous derived state | `signals` |
| Server-driven / offline-first data caching is the hard part | pair the choice above with a data layer (`drift`, `isar`, `dio` + repository); state mgmt only holds view state |

## Comparison

| Axis | `setState` | `provider` | `riverpod` | `bloc` | `signals` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Boilerplate | none | low | low–med | med–high | low |
| Compile-time safety of DI | n/a | weak (runtime `context`) | strong | strong | medium |
| Async handling | manual | manual | `AsyncValue` built in | via states | manual |
| Testability without widgets | n/a | ok | excellent | excellent | good |
| Traceability / time-travel | none | none | dev-tools | strong | dev-tools |
| Learning curve | trivial | low | medium | high | low–medium |
| Good for very large teams | no | risky | yes | yes | emerging |

## Rules

1. **`setState` is not "the wrong answer".** Local state stays local no matter
   what the app uses globally.
2. **One primary solution.** A second is allowed only with an ADR explaining the
   boundary (e.g. "legacy module X stays on Bloc until rewritten").
3. **State holds view state, not business rules.** Business logic lives in the
   domain layer and is plain Dart, testable without Flutter.
4. **Don't put I/O in a Notifier/Bloc.** Inject a repository; the state object
   calls it.
5. **Re-evaluate only on a real trigger** — a perf problem, a testing pain, a
   team change — not because a newer library trended.

## Migration cost signal

Switching the primary solution touches every feature. Budget it as a project,
write the ADR that supersedes the old one, and do it feature-by-feature behind
the repository interface — never a big-bang branch.
