# Deciding the test layer — worked examples

The rule: **test at the lowest layer that can catch the failure.** Below, the
failure mode drives the choice.

## Example 1 — "Discount is applied wrong for orders over $100"

- Failure lives in a pricing rule → **unit test** on the pricing function /
  domain service with a table of inputs. No widget needed.
- Do *not* write a widget test that types into a cart and reads the total — it
  would pass or fail for many unrelated reasons and be 100x slower.

## Example 2 — "Profile screen shows a spinner forever when the API 500s"

- Failure is a missing error branch in the widget's state handling → **widget
  test**: pump the widget with a repository fake that throws, assert the error
  UI renders and the retry button calls the retry path.
- The domain layer is fine; no unit test change. No integration test — the fake
  is enough.

## Example 3 — "Button looks off in dark mode / at 2x text scale"

- Failure is visual → **golden test** for that component in
  {light, dark} × {1.0x, 2.0x text scale}. Use `flutter-add-widget-preview` to
  drive the previews.
- Keep goldens to *stable, reused* components (buttons, cards, list tiles), not
  whole screens — full-screen goldens break on every copy tweak.

## Example 4 — "Users can't complete checkout on a real device"

- Failure spans navigation, platform channels, real async → **integration
  test** in `integration_test/`: launch the app, sign in with a test account,
  add an item, pay with the sandbox, assert the confirmation screen.
- One test for the happy path plus one for the most common failure (declined
  card). Not fifteen permutations — those are unit/widget tests.

## Example 5 — "`Order.fromJson` crashes on a null `shippedAt`"

- **Unit test** with the exact malformed payload. This is the canonical
  bug-fix test: it fails before the `fromJson` fix, passes after.

## Example 6 — "Adding a `LoginNotifier` (Riverpod)"

- State transitions (`idle → loading → success | failure`) → **unit test** the
  notifier with a fake `AuthRepository` (`dart-generate-test-mocks`).
- The login *form widget* (validation messages, disabled button while loading)
  → **widget test**.
- The end-to-end "open app → log in → land on home" → one **integration test**.
- Three layers, each catching what the others can't.

## Smell: the test that's at the wrong layer

- A widget test that asserts a computed value (should be unit).
- A unit test that constructs a `WidgetTester` (should be widget).
- An integration test asserting a single widget's padding (should be
  widget/golden).
- A golden of an entire scrolling screen (too brittle — golden the components).
