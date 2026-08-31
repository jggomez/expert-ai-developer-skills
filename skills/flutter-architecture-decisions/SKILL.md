---
name: flutter-architecture-decisions
description: Use when choosing state management for a Flutter app (Riverpod vs Bloc vs signals vs setState), drawing package/module boundaries, deciding what belongs in the UI/logic/data layers, or recording a Flutter architecture decision (ADR). Complements the official flutter-apply-architecture-best-practices skill, which teaches the layered pattern — this one helps you pick and record the choices it leaves open.
---

# Flutter Architecture Decisions

The official **`flutter-apply-architecture-best-practices`** skill (from
`flutter/agent-plugins`) teaches the recommended layered structure — UI,
logic/domain, data — and how to wire it. This skill covers the decisions that
skill leaves to you: *which* state solution, *where* the boundaries go, and how
to write it down so it is not re-litigated next sprint.

## When to run

- Starting a new app or a new feature area with non-trivial state.
- A PR review raises "should this be a package?" or "why Bloc here and Riverpod there?".
- Before adopting a new dependency that shapes the architecture (a router, a DI
  container, a persistence layer).

Do **not** run for a one-widget fix or a change that stays inside an existing,
already-decided module — apply the existing ADR and move on.

## How to use

1. **Apply the layered pattern first.** Invoke `flutter-apply-architecture-best-practices`
   for the UI / logic / data split. This skill assumes that split exists.
2. **Pick state management** with the matrix in
   [references/state-management-decision-matrix.md](references/state-management-decision-matrix.md).
   Choose one primary solution per app; a second is allowed only with a written
   reason. Don't mix three.
3. **Draw module boundaries** with the checklist below. A boundary earns its
   keep only when it has a stable contract and an independent reason to change.
4. **Record it** as an ADR using [references/adr-template.md](references/adr-template.md).
   One short file per decision under `doc/adr/` (or the repo's existing location).

## Module boundary checklist

Split code into a separate package / feature module only when **two or more** hold:

- It has consumers that are not this app (another app, a package, a plugin).
- It changes for a reason unrelated to the rest of the app (different domain,
  different release cadence).
- It has a narrow, testable public API you can name in one sentence.
- Its build/test can run without the full app.

Otherwise keep it a folder. A `lib/src/feature/<name>/` folder with `ui/`,
`domain/`, `data/` is enough for most features. `melos` / a multi-package repo is
a response to real scale, not a starting point.

## Anti-patterns this skill exists to prevent

- Choosing an architecture "to be safe" that the app's actual state complexity
  never justifies (global store for three screens).
- Three state solutions in one codebase because each feature picked its own.
- A `core` / `common` / `shared` package that becomes a dumping ground with no
  contract.
- Deciding in a PR comment thread and never writing it down.

## Hand-off

Feed the chosen state solution, the module map, and the ADR path to
`flutter-implementer` and note them for `flutter-reviewer` so review checks
against the decision, not against taste.
