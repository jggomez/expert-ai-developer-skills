---
name: flutter-upgrade-migration
description: Use when upgrading the Flutter/Dart SDK, bumping dependencies across major versions, or clearing deprecation warnings across a codebase. Covers project-scale framework migration — the ordered upgrade sweep, deprecation triage, and dependency major-bump strategy — that the official dart fix / dart-resolve-package-conflicts skills do not, while deferring pub-conflict resolution to them.
---

# Flutter Upgrade & Migration

`dart fix` applies mechanical fixes. `dart-resolve-package-conflicts` untangles
`pub get`. This skill is the plan around them: upgrading the SDK and major
dependencies across a whole app without a stalled multi-week branch.

## When to run

- Moving to a new Flutter stable (e.g. 3.24 → 3.29 → next).
- A dependency you rely on releases a breaking major.
- Deprecation warnings have accumulated and `dart analyze` is noisy.

## Principles

1. **One axis at a time.** SDK bump, then deprecations, then dependency majors —
   separate commits, ideally separate PRs. Never bundle.
2. **Pin before you start.** Record the current Flutter version (`.fvmrc` /
   `flutter --version`) and commit a green `pubspec.lock`. That's your rollback.
3. **Tests are the safety net.** If coverage is thin, the upgrade is riskier —
   consider adding tests to the hot paths first (`flutter-test-strategy`).
4. **Small, reviewable steps.** A 400-file "migrate everything" diff gets
   rubber-stamped. Slice by package/feature.

## The ordered sweep

### Step 1 — SDK upgrade

```bash
git switch -c chore/flutter-<version>
flutter --version                 # record the OLD version in the PR
flutter upgrade                    # or fvm use <version>
flutter pub get
dart analyze                       # capture the new warnings/errors
flutter test                       # capture new failures
```

- Read the release notes for that Flutter version and the embedded Dart
  version. Note **breaking changes** and **deprecations** that apply.
- Fix only what the SDK bump broke. Keep this commit to compile + tests green.

### Step 2 — mechanical deprecation fixes

```bash
dart fix --dry-run                 # review
dart fix --apply
dart format .
dart analyze                       # should be quieter now
```

- `dart fix` handles the codemods the SDK ships (e.g. renamed APIs,
  `withOpacity` → `withValues`, `MediaQuery.of` → `MediaQuery.sizeOf`).
- What `dart fix` can't do, do by hand, grouped by deprecation, one commit each:
  `grep -rn "<deprecated symbol>" lib test`.

### Step 3 — dependency majors

- List them: `flutter pub outdated`. Sort by blast radius (a router or state lib
  is a project; a lint pack is a line).
- One dependency per branch. Read its CHANGELOG/migration guide. Update usages
  behind your own abstraction where one exists (repository, wrapper).
- Bump `flutter_lints` / `very_good_analysis` last and clear the new lints as
  their own PR.
- Use `dart-resolve-package-conflicts` for any `pub get` version-solve failure —
  don't hand-edit constraints blindly.

### Step 4 — verify

- `dart analyze` clean (or a documented, ticketed allowlist).
- `flutter test` + `integration_test` green.
- Build every target in the release matrix (`flutter-release-engineering`) —
  breakage often shows only at build time (Gradle/AGP, Xcode, Impeller).
- Manual smoke of the critical journeys.
- Update `.fvmrc` / CI Flutter version and the "record the OLD version" note
  becomes the PR's before/after.

## Deprecation triage

| Warning volume | Action |
| :--- | :--- |
| A handful | fix in the SDK-upgrade PR |
| Dozens, all one API | `dart fix` if covered, else one dedicated PR |
| Hundreds across many APIs | a tracked migration: one PR per API family, a checklist issue, do not block the SDK upgrade on it |

## Hand-off

Deliver: the before/after Flutter+Dart versions, the list of breaking changes
handled, remaining deprecations with a ticket, dependency majors done vs.
deferred, and confirmation the release build matrix passes.
