---
trigger: glob
globs: "**/*.dart, **/pubspec.yaml, **/analysis_options.yaml"
description: Flutter and Dart constraints applied while editing Dart code or pubspec - frame budget, lifecycle safety, config and secrets, branch safety and test proof.
---

# Flutter Rules

- **Git Branch Governance**: never edit `.dart` or `pubspec.yaml` on `main`, `master`, `develop` or `dev`; create `feat/<slug>` first. **Scope Drift**: ask before mixing an unrelated request into the current branch.
- **Frame budget**: 16 ms (60 fps) / 8 ms (120 fps). No heavy work, I/O or object churn inside `build()`; prefer `const` widgets and keyed lists.
- **One state solution per app** (Riverpod, Bloc or Signals, whichever the app already uses); never introduce a second one.
- **Lifecycle**: dispose every controller, stream subscription and animation (`dispose()`); after any `await`, guard `BuildContext` use with `if (!context.mounted) return;`.
- **Shared files** (`pubspec.yaml`, `pubspec.lock`, `main.dart`, the global router, DI, generated `*.g.dart` / `*.freezed.dart`): change them in one step; never edit generated files by hand, regenerate with `dart run build_runner build`.
- **Config and secrets**: use `--dart-define-from-file=config/<env>.json`; never commit keys, keystores or signing passwords.
- **Proof**: `dart analyze` clean and `flutter test <affected tests>` exit code `0` before claiming done; report `BLOCKED` with the exact error when a device, emulator or SDK is missing.
- **Design**: follow root `DESIGN.md` tokens when it exists (48x48 dp touch targets, semantic labels).
