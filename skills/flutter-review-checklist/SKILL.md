---
name: flutter-review-checklist
description: Use when reviewing a Flutter/Dart pull request or auditing existing Flutter code for quality — rebuild scope, const correctness, key usage, dispose/leak safety, BuildContext across async gaps, list and image performance, RepaintBoundary, accessibility semantics, and golden coverage. Complements dart-run-static-analysis (which runs the linter) and flutter-fix-layout-issues (which fixes overflow errors) with the senior judgment those do not encode.
---

# Flutter Review Checklist

`dart analyze` catches lint violations. `flutter-fix-layout-issues` fixes render
overflows. This skill is the review pass in between: the framework-specific
mistakes that compile, pass the linter, and still ship jank, leaks, or broken
accessibility.

## When to run

- Reviewing any PR that touches `lib/**` widgets, state, or platform code.
- Auditing a screen that "feels slow" or a codebase before a release.

## How to run

1. **Baseline with the tools first** — don't hand-review what a machine finds:
   ```bash
   dart analyze
   dart format --output=none --set-exit-if-changed .
   flutter test --coverage
   python3 ./skills/flutter-review-checklist/scripts/flutter_project_audit.py
   ```
   Use the official `dart-run-static-analysis` skill to clear analyzer findings
   before the human pass.
2. **Walk the checklist**: [references/flutter-review-checklist.md](references/flutter-review-checklist.md).
   Only raise an item when you can point at the line and name the concrete
   failure (a rebuild that will happen, a controller that will leak) — not "this
   could be cleaner".
3. **Check against the ADRs** (`doc/adr/`): does the PR follow the recorded state
   management and module-boundary decisions? A deviation needs its own ADR, not
   a review nit.
4. **Verdict**: block only on correctness, leaks, accessibility regressions, or
   an ADR violation. Everything else is a non-blocking suggestion.

## The high-value checks (full list in the reference)

- **Rebuild scope** — `setState` / `notifyListeners` rebuilding a whole page
  instead of a leaf; missing `const`; `MediaQuery.of(context)` /
  `Theme.of(context)` read high in the tree causing wide rebuilds.
- **Lifecycle** — every `AnimationController`, `TextEditingController`,
  `StreamSubscription`, `FocusNode`, `ScrollController` has a matching
  `dispose()`.
- **`BuildContext` after `await`** — using `context` after an async gap without a
  `mounted` check.
- **Lists** — `ListView(children: [...])` for long/unbounded lists instead of
  `ListView.builder`; missing `RepaintBoundary` around expensive repeating
  items; no `cacheExtent` tuning where it matters.
- **Images** — network images without `cacheWidth`/`cacheHeight` or a caching
  package; decoding full-res images into small boxes.
- **Keys** — reorderable/inserted list items without stable `Key`s; `GlobalKey`
  used where a `ValueKey` would do.
- **Accessibility** — icon-only buttons without `Semantics`/`tooltip`; text that
  ignores `MediaQuery.textScaler`; tap targets under 48dp.
- **Testing** — new widget with branching UI and no widget test; visual change
  with no golden; business logic added with no unit test (see
  `flutter-test-strategy`).

## Hand-off

Return an explicit list: blocking issues (file:line + the concrete failure),
non-blocking suggestions, and any ADR deviation. Pass release-affecting findings
to `flutter-release-engineer`.
