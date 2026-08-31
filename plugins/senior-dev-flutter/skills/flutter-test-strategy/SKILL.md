---
name: flutter-test-strategy
description: Use when deciding what to test in a Flutter/Dart codebase and at which layer — unit vs widget vs golden vs integration — and when setting coverage gates. Complements the official how-to skills (flutter-add-widget-test, flutter-add-integration-test, flutter-add-widget-preview, dart-add-unit-test, dart-generate-test-mocks, dart-collect-coverage), which write the tests once you know which kind to write.
---

# Flutter Test Strategy

The official skills tell you *how* to write each kind of test. This skill
decides *what* gets a test, at *which* layer, and *what bar* the suite must
clear. It routes to the official skills; it does not restate them.

## When to run

- Standing up testing for a new app or feature area.
- A PR review asks "does this need a test, and what kind?".
- Setting or revising CI coverage thresholds.

## The layering rule

Test at the **lowest layer that can catch the failure**. Push logic down so it
can be unit-tested; reserve widget/integration tests for what only they can
verify.

| Layer | Verifies | Official skill to invoke | Cost |
| :--- | :--- | :--- | :--- |
| **Unit** (`package:test`) | domain logic, mappers, `fromJson`/`toJson`, state transitions of a `Notifier`/`Bloc`/`Cubit` with a fake repository | `dart-add-unit-test`, `dart-generate-test-mocks` | cheap — the bulk of the suite |
| **Widget** (`WidgetTester`) | a widget renders the right thing for a given state, branch logic (loading/error/empty/data), user interaction updates state | `flutter-add-widget-test` | medium |
| **Golden** | pixel-level appearance of a stable component across themes / text scales | `flutter-add-widget-preview` (previews) + golden files | medium; brittle if overused |
| **Integration** (`integration_test/`) | a real multi-screen flow on a device/emulator: launch → sign in → do the thing → assert | `flutter-add-integration-test` | expensive — a handful, for critical journeys only |

## What must have a test (block a PR without one)

- New or changed **domain logic** → unit test.
- New **branching UI** (a widget that renders differently for
  loading/error/empty/data) → widget test covering each branch.
- New **critical user journey** or a change to one (auth, payment, onboarding)
  → integration test touched.
- A **bug fix** → a test that fails before the fix and passes after.

## What does *not* need a dedicated test

- Pure layout with no logic and no history of breaking (a `Padding` around a
  `Text`).
- Generated code (`*.g.dart`, `*.freezed.dart`).
- Third-party widgets you only configure.

Do not chase a coverage number by testing getters.

## Coverage gates

- Collect with `dart-collect-coverage` (`flutter test --coverage` → LCOV).
- Gate **per-package line coverage**, not a repo-wide average that hides gaps.
- Start at the current number rounded down; ratchet up, never down.
- Exclude generated files from the denominator (`genhtml`/`lcov --remove` on
  `*.g.dart`, `*.freezed.dart`, `*.gr.dart`, `*.config.dart`).
- CI fails the build below the gate — a warning nobody reads is not a gate.

## Hand-off

Produce a per-feature test plan: which layers, which official skill writes each,
and the coverage gate. Pass it to `flutter-implementer` (TDD) and record the
gate for `flutter-reviewer`.

## Reference

- [Deciding the layer — worked examples](references/test-pyramid-flutter.md)
