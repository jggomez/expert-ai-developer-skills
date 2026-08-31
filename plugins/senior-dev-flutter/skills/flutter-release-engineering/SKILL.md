---
name: flutter-release-engineering
description: Use when setting up or reviewing how a Flutter app ships — build flavors and environment config (--dart-define-from-file), app signing, the flutter build matrix per platform, version/build-number strategy, store metadata, and whether to use an over-the-air update service (Shorebird). Covers release concerns the official Flutter/Dart skills do not.
---

# Flutter Release Engineering

The official skills stop at feature code. This one covers getting that code to
users safely and repeatably: config, signing, the build matrix, versioning, and
OTA updates.

## When to run

- First real release of an app, or adding a new environment (staging).
- CI produces artifacts that aren't reproducible or leak config.
- A decision about Shorebird / code-push is on the table.

## 1. Environment config — never hard-code

- One config file per environment, injected at build time:
  `flutter build <target> --dart-define-from-file=config/prod.json`
  (`dev.json`, `staging.json`, `prod.json`). Read with
  `String.fromEnvironment` / `int.fromEnvironment` behind a typed `AppConfig`.
- `config/*.json` for **non-secret** switches (base URL, feature flags, log
  level). Real secrets (signing keys, service-account JSON, API keys that must
  not ship) go in the CI secret store and platform-native config, never in Dart
  source or `pubspec.yaml`.
- Android **product flavors** + iOS **schemes/xcconfig** for anything that must
  differ at the native layer (app id suffix, app name, icons, Firebase file).
  Pair with `--flavor`.

## 2. Signing

- **Android**: `key.properties` (git-ignored) + `keystore` in the CI secret
  store; `signingConfigs` in `build.gradle` reads it; never commit the keystore.
  Prefer Play App Signing (upload key only in CI).
- **iOS**: managed signing via Xcode/App Store Connect API key in CI (e.g.
  `match`/fastlane or `xcodebuild -allowProvisioningUpdates` with an ASC key).
  No `.p12` / profiles in the repo.
- Verify a release build is actually signed before shipping (`apksigner verify`,
  `codesign -dv`).

## 3. Build matrix

| Target | Command | Artifact |
| :--- | :--- | :--- |
| Android (store) | `flutter build appbundle --release --flavor prod --dart-define-from-file=config/prod.json` | `.aab` |
| Android (sideload/QA) | `flutter build apk --release --flavor staging ...` | `.apk` |
| iOS | `flutter build ipa --release --flavor prod --export-options-plist=...` | `.ipa` |
| Web | `flutter build web --release --dart-define-from-file=...` | `build/web` |
| Desktop | `flutter build {macos,windows,linux} --release` | platform bundle |

- Build in CI from a clean checkout with a pinned Flutter version
  (`.fvmrc` / `flutter --version` recorded). Local builds are not releases.
- Keep debug symbols: `--obfuscate --split-debug-info=build/symbols` and archive
  `build/symbols` per release for crash de-obfuscation.

## 4. Versioning

- `pubspec.yaml` `version: X.Y.Z+BUILD`. `X.Y.Z` is the user-facing semver;
  `+BUILD` is a monotonic integer, set by CI (`--build-number=$CI_RUN`), never
  hand-bumped.
- Tag the release commit `vX.Y.Z`. The changelog is generated from
  Conventional Commits since the last tag (see the `commit-expert` skill).

## 5. Store metadata

- Keep screenshots, descriptions, and release notes in-repo under
  `store/<platform>/<locale>/` and push with fastlane
  `deliver`/`supply`, so metadata is reviewable and versioned.
- Release notes per version, per locale — not "bug fixes".

## 6. OTA / code-push decision (Shorebird)

Use it when: you ship Dart-only fixes often and store review latency hurts, and
your compliance allows patching in place.
Do **not** rely on it for: native code / plugin changes, permission changes,
anything the stores require review for. Treat patches as still going through the
same CI, tests, and staged rollout — a patch is a release.

## Hand-off

Produce: the config file layout, the signing setup (where each secret lives),
the CI build matrix, the versioning scheme, and the OTA decision with its
rationale. Flag anything `flutter-reviewer` should enforce (no secrets in Dart,
`--dart-define-from-file` only).

## Reference

- [Flavors, config, and the AppConfig pattern](references/flavors-and-config.md)
