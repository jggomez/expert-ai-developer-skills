---
name: flutter-performance-profiling
description: Use when a Flutter app janks, drops frames, is slow to start, or feels heavy — diagnose with DevTools timeline, profile mode, the raster vs UI thread split, shader jank, and startup tracing, then fix the specific cause. Goes beyond the official flutter-fix-layout-issues (which resolves overflow/constraint errors) to runtime performance the analyzer cannot see.
---

# Flutter Performance Profiling

`flutter-fix-layout-issues` fixes *errors* the framework reports. This skill is
for the app that runs fine and still feels bad: jank, slow scroll, long
time-to-interactive. Measure first, fix the named cause, measure again.

## When to run

- "This screen stutters when I scroll."
- "The app takes 3 seconds to show anything."
- A perf regression report, or a pre-release perf pass.

## Never guess — measure in profile mode

```bash
flutter run --profile               # NOT debug (debug is not representative) and NOT release (no tooling)
flutter run --profile --trace-startup --verbose   # for startup analysis; writes start_up_info.json
```

Open **DevTools → Performance**. Record while reproducing the problem. Read:

- **UI thread** (Dart) frames over ~16ms (60Hz) / ~8ms (120Hz) → your
  `build`/layout/paint is too expensive.
- **Raster thread** frames over budget → GPU work: shaders, saveLayer,
  large/complex clips, opacity layers, overdraw.
- **"Shader compilation"** entries on first run of an animation → shader jank.

## Diagnose → fix by symptom

| Symptom in the timeline | Likely cause | Fix |
| :--- | :--- | :--- |
| Tall **UI thread** bars during scroll | rebuilding too much per frame | narrow rebuild scope (see `flutter-review-checklist` §1); `const`; `ListView.builder`; selectors instead of whole-tree `watch` |
| Tall UI bars, spikes on data change | expensive work in `build()` | memoise; move compute to `initState` / an isolate (`compute()`); precompute derived lists |
| Tall **raster** bars, steady | `Opacity`, `ClipRRect`/`ClipPath`, `ShaderMask`, `BackdropFilter` on a big/animated subtree | use decoration `borderRadius`, `AnimatedOpacity`, pre-clipped assets; add `RepaintBoundary` to isolate |
| Raster spikes only the **first** time an animation plays | shader compilation jank | bundle a shader warm-up (SkSL) — `flutter run --profile --cache-sksl --purge-persistent-cache`, capture, ship via `--bundle-sksl-path`; or use Impeller (default on iOS; enable on Android and re-test) |
| Long gap before first frame | heavy synchronous work in `main()` / first `build` | defer non-critical init; `runApp` early with a lightweight first frame; lazy-load |
| Jank only on low-end Android | overdraw, big images | check "Highlight repaints" / "Highlight oversized images" in DevTools; set `cacheWidth`/`cacheHeight`; reduce layers |
| Memory climbs over time | leaked controllers / subscriptions | `flutter-review-checklist` §2; DevTools → Memory → diff snapshots |

## Guardrails to keep a regression from coming back

- Keep a scripted scroll/interaction and check frame times in CI where feasible
  (`integration_test` + `flutter drive --profile`, or `flutter test integration_test --profile`).
- Add a `RepaintBoundary` + a golden for the isolated expensive component.
- Record the before/after frame numbers in the PR.

## Reference

- [Jank-hunting playbook — step by step](references/jank-hunting-playbook.md)
