# Flutter review checklist (full)

Raise an item only with a file:line and a concrete failure. `[block]` = must fix
before merge; `[warn]` = non-blocking suggestion.

## 1. Rebuild scope & widget cost

- `[warn]` Widget subtree that never changes is not `const`. Add `const`; it
  skips rebuild and element re-creation.
- `[block]` `setState()` in a large `State` rebuilds an expensive subtree when
  only a leaf changed. Split the leaf into its own widget, or use a
  `ValueListenableBuilder` / selector.
- `[warn]` `Theme.of(context)` / `MediaQuery.of(context)` / `.watch` read near
  the top of a big `build()` — every dependency change rebuilds the whole
  method. Read it in the smallest widget that needs it, or use
  `MediaQuery.sizeOf` / `.textScalerOf` (dependency-scoped accessors).
- `[warn]` `Builder` / `LayoutBuilder` wrapping more than what needs the new
  context/constraints.
- `[block]` Work in `build()` that is not pure: network calls, `DateTime.now()`
  driving layout, list sorting, `Random()`. Move to `initState` /
  a state object / a memoised value.

## 2. Lifecycle & leaks

- `[block]` `AnimationController`, `TextEditingController`, `ScrollController`,
  `FocusNode`, `PageController`, `TabController` created in `initState` without
  a `dispose()`.
- `[block]` `StreamSubscription` / `Timer` / `Ticker` not cancelled in
  `dispose()`.
- `[block]` Listener added (`addListener`, `stream.listen`) with no matching
  removal.
- `[warn]` `didChangeDependencies` re-subscribing without first cancelling the
  previous subscription.
- `[block]` A `GlobalKey` stored in a field and reused across rebuilds of
  different widgets.

## 3. Async & context

- `[block]` `BuildContext` used after `await` with no `if (!mounted) return;`
  (or `context.mounted` check) between the await and the use.
- `[block]` `Navigator` / `ScaffoldMessenger` / `Theme.of` called on a context
  captured before an async gap.
- `[warn]` `Future` created in `build()` and passed to `FutureBuilder` — it
  re-runs on every rebuild. Hoist the future into state.
- `[warn]` Unawaited future with side effects and no error handling
  (`unawaited(...)` at least, ideally `.catchError` / try-catch).

## 4. Lists & scrolling

- `[block]` `ListView(children: [...])` / `Column` inside `SingleChildScrollView`
  for a list that can grow unbounded. Use `ListView.builder` /
  `SliverList.builder`.
- `[warn]` Expensive, visually-stable repeating item without `RepaintBoundary`.
- `[warn]` `shrinkWrap: true` on a large list (forces full layout).
- `[warn]` Nested scrollables without `physics` / `NeverScrollableScrollPhysics`
  where nesting is intentional.
- `[warn]` Reorderable or dynamically-inserted items without a stable `ValueKey`
  → wrong element reuse, lost scroll position, broken animations.

## 5. Images & assets

- `[warn]` `Image.network` without `cacheWidth`/`cacheHeight` (or a caching
  package like `cached_network_image`) when the display box is small.
- `[warn]` Large asset decoded at full resolution into a thumbnail.
- `[warn]` `Opacity` / `ClipRRect` / `ShaderMask` on a frequently-rebuilt
  subtree (each forces an offscreen layer). Prefer `AnimatedOpacity`,
  `borderRadius` on the decoration, or a pre-clipped asset.

## 6. Accessibility

- `[block]` Icon-only `IconButton` / `GestureDetector` with no `tooltip` /
  `Semantics(label: ...)`.
- `[warn]` Hard-coded font sizes / heights that break when
  `MediaQuery.textScalerOf(context)` is large.
- `[warn]` Tap target smaller than 48x48 logical px.
- `[warn]` Color-only status indication (no icon/text) — fails color-blind and
  contrast checks.
- `[warn]` `ExcludeSemantics` / `Semantics` misused so the screen reader reads
  duplicates or nothing.

## 7. State & architecture conformance

- `[block]` I/O (`http`, `dio`, `drift`, file access) inside a widget,
  `Notifier`, `Bloc`, or `ChangeNotifier` instead of a repository.
- `[block]` New code violates a recorded ADR (state solution, module boundary)
  with no superseding ADR.
- `[warn]` Business rule implemented in a widget instead of a plain-Dart domain
  object.
- `[warn]` `BuildContext` passed into a non-widget layer.

## 8. Testing (delegate depth to `flutter-test-strategy`)

- `[block]` New branching UI with no widget test.
- `[block]` New domain logic with no unit test.
- `[warn]` Visual change with no golden test / preview update.
- `[warn]` Integration-level flow (login, checkout) changed with no integration
  test touched.

## 9. Platform & plugins

- `[warn]` `Platform.isX` branching in widget code instead of an abstraction.
- `[warn]` New plugin dependency without checking it supports the app's target
  platforms and `flutter` constraint.
- `[block]` Secrets / API keys committed in Dart source or `pubspec.yaml`
  instead of `--dart-define-from-file` / platform config (see
  `flutter-release-engineering`).
