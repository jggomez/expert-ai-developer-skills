# Jank-hunting playbook

Work top to bottom. Stop when the timeline is under budget.

## 0. Reproduce in profile mode

- `flutter run --profile` on a **real device** representative of your worst
  supported hardware (a mid/low Android, not the simulator).
- Reproduce the exact interaction. Note whether it's *scroll*, *transition*,
  *first play of an animation*, or *startup*.

## 1. Record and classify the frames

DevTools → Performance → Record. For each janky frame, is the tall bar on the
**UI thread** (Dart: build/layout/paint) or the **Raster thread** (GPU)?

- UI-thread bound → §2
- Raster-thread bound → §3
- Only the first frame of an animation is bad → §4 (shaders)
- Long time before *any* frame → §5 (startup)

## 2. UI-thread bound

1. Turn on **"Track widget builds"**. Find the widget rebuilding most.
2. Is it rebuilding more than it must?
   - Missing `const` on static subtrees.
   - `setState` / `notifyListeners` / whole-object `watch` high in the tree.
   - `FutureBuilder`/`StreamBuilder` fed a future/stream created in `build()`.
   - `MediaQuery.of` / `Theme.of` read at the top of a large `build()`.
   Fix with the narrowest-scope technique (leaf widget, selector,
   `ValueListenableBuilder`, `MediaQuery.sizeOf`).
3. Is a single `build`/layout genuinely expensive (big list sort, JSON parse,
   image decode, regex)? Move it off the frame: memoise, `initState`,
   `compute()` / a long-lived isolate, or precompute when data arrives.
4. Long lists: `ListView.builder` / slivers, not `ListView(children:)`; avoid
   `shrinkWrap: true`; give items stable `ValueKey`s.

## 3. Raster-thread bound

1. DevTools → **"Highlight repaints"**: rainbow borders that flash on
   non-changing content mean unnecessary repaint → wrap the changing part and
   add `RepaintBoundary`.
2. DevTools → **"Highlight oversized images"**: set `cacheWidth`/`cacheHeight`
   to the displayed size; use `cached_network_image`.
3. Expensive layers: `Opacity` → `AnimatedOpacity` or opacity in a shader/asset;
   `ClipRRect`/`ClipPath` on animated subtree → `BoxDecoration(borderRadius:)`
   or pre-clip the asset; `BackdropFilter` → smallest possible area, static if
   possible.
4. Overdraw: flatten stacked opaque containers; avoid full-screen gradients
   behind opaque content.

## 4. Shader compilation jank (first-run stutter)

1. Confirm: timeline shows `_CompileShader` / "Shader compilation" on the first
   play only.
2. Try **Impeller** first — default on iOS; enable on Android
   (`--enable-impeller` / manifest flag) and re-test; it removes runtime shader
   compilation for most cases.
3. If still on Skia: warm up SkSL —
   `flutter run --profile --cache-sksl --purge-persistent-cache`, exercise every
   animation/transition, then `flutter build <target> --bundle-sksl-path
   flutter_01.sksl.json`.

## 5. Startup

1. `flutter run --profile --trace-startup` → inspect `start_up_info.json`
   (`timeToFirstFrameMicros`, `timeToFrameworkInitMicros`).
2. Move heavy work out of `main()` and the first `build`: plugin init, DB open,
   remote config, analytics. Show a cheap first frame, then hydrate.
3. Defer `precacheImage` / font loading past the first frame.
4. Consider deferred components / lazy route registration for large apps.

## 6. Lock it in

- Record before/after frame times (ms) or `timeToFirstFrameMicros` in the PR.
- Add `RepaintBoundary` + a golden around the fixed component.
- Where practical, a `flutter drive --profile` scenario in CI that asserts
  `frameBuildTime`/`frameRasterizerTime` percentiles.
