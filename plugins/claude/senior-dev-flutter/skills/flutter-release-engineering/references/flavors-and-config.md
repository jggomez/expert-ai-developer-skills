# Flavors, config, and the AppConfig pattern

## Layout

```
config/
├── dev.json          # non-secret switches per environment
├── staging.json
└── prod.json
lib/
└── src/config/
    └── app_config.dart   # typed access, read once
```

`config/prod.json`:
```json
{
  "APP_ENV": "prod",
  "API_BASE_URL": "https://api.example.com",
  "SENTRY_DSN": "https://public@sentry.example.com/42",
  "LOG_LEVEL": "warning",
  "FEATURE_NEW_CHECKOUT": true
}
```
> Only values that are safe to ship in the binary. A `SENTRY_DSN` public key is
> fine; a signing key or a private service-account is not — those live in CI
> secrets and native config.

## Typed access

```dart
class AppConfig {
  const AppConfig._();

  static const env = String.fromEnvironment('APP_ENV', defaultValue: 'dev');
  static const apiBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const logLevel = String.fromEnvironment('LOG_LEVEL', defaultValue: 'info');
  static const featureNewCheckout =
      bool.fromEnvironment('FEATURE_NEW_CHECKOUT');

  static bool get isProd => env == 'prod';
}
```

`*.fromEnvironment` is `const` — the values are baked in at compile time, so a
build is pinned to one environment. There is no runtime env switching.

## Build

```bash
flutter run   --dart-define-from-file=config/dev.json
flutter build appbundle --release --flavor prod \
  --dart-define-from-file=config/prod.json \
  --obfuscate --split-debug-info=build/symbols
```

## Native flavors (when JSON config is not enough)

Use Android product flavors + iOS schemes when these must differ:

- application id / bundle id suffix (`.dev`, `.staging`) so all three install
  side by side
- app display name and launcher icon
- `google-services.json` / `GoogleService-Info.plist` per environment
- native feature toggles, deep-link schemes

`android/app/build.gradle`:
```gradle
flavorDimensions += "env"
productFlavors {
    dev     { dimension "env"; applicationIdSuffix ".dev";     resValue "string", "app_name", "App Dev" }
    staging { dimension "env"; applicationIdSuffix ".staging"; resValue "string", "app_name", "App Stg" }
    prod    { dimension "env";                                  resValue "string", "app_name", "App" }
}
```

Then `flutter build ... --flavor prod` and put the per-flavor Firebase files in
`android/app/src/<flavor>/`.

## Rules

1. Zero secrets in Dart source, `pubspec.yaml`, or `config/*.json` that ships.
2. One build = one environment. No runtime environment picker in production.
3. CI sets `--build-number`; humans set `version:` (the semver part) only.
4. Archive `build/symbols` for every release build.
5. `config/*.json` is committed (it's not secret); the keystore, `key.properties`,
   `*.p12`, and provisioning profiles are git-ignored and live in CI secrets.
