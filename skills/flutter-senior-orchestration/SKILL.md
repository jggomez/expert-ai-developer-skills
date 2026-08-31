---
name: flutter-senior-orchestration
description: Use to run a Flutter feature or fix end to end — sizing the task, sequencing the official flutter-*/dart-* how-to skills in the right order, and routing phases to the architect, implementer, reviewer, and release-engineer subagents. This is the phase map the flutter-feature-orchestrator agent follows; it decides and delegates, it does not restate the official procedures.
---

# Flutter Senior Orchestration

The phase breakdown for taking a Flutter change from request to merged, using
the official Dart/Flutter skills for every "how", and this repo's `senior-dev-flutter`
subagents for the "which", "in what order", and "is it good enough".

## Prerequisite

The official skill packs are installed:
`npx skills add flutter/agent-plugins --skill '*' --agent universal --yes`
and `npx skills add dart-lang/skills --skill '*' --agent universal --yes`,
plus the Dart & Flutter MCP server (`dart mcp-server`).

## Size the task first

| Task shape | Phases to run |
| :--- | :--- |
| One-widget fix, no logic, no new dep | Implement + targeted test. Skip architecture, skip release. |
| Small feature inside an existing, ADR-covered module | Light plan → Implement (TDD) → Review. |
| New feature area, new state, new deps, or crosses module boundaries | Full: Architecture → Implement → Test → Review → (Release if it ships this cycle). |
| SDK / dependency upgrade | `flutter-upgrade-migration` drives; Review + build-matrix verify. |
| "It's slow / it janks" | `flutter-performance-profiling` drives; Review guards the fix. |

When the right size is unclear, ask the user — do not default to the full
pipeline "to be safe".

## Phases

### 1. Architecture — only when a real decision exists
Route to **`flutter-architect`**. It applies the official
`flutter-apply-architecture-best-practices` for the layered split, then uses
`flutter-architecture-decisions` to choose state management, draw module
boundaries, and record an ADR. Output: the ADR path + a module map.
Skip entirely for a change inside an already-decided module.

### 2. Test plan
Route to **`flutter-implementer`** carrying `flutter-test-strategy`: which layer
each new behavior is tested at, which official skill writes it
(`dart-add-unit-test`, `flutter-add-widget-test`, `flutter-add-integration-test`,
`flutter-add-widget-preview`, `dart-generate-test-mocks`), and the coverage gate.

### 3. Implement (TDD)
**`flutter-implementer`**: red → green → refactor. For every mechanic — layout,
routing, serialization, localization, HTTP, writing a given test kind — it
invokes the matching official `flutter-*` / `dart-*` skill rather than
improvising. It runs `dart analyze` (via `dart-run-static-analysis`) and
`dart format` before handing off.

### 4. Review
**`flutter-reviewer`**: runs the tool baseline, walks
`flutter-review-checklist`, and checks the diff against the ADRs. Verdict:
block only on correctness, leaks, accessibility regressions, or an ADR
violation.

### 5. Release (only if this change ships now)
**`flutter-release-engineer`**: config via `--dart-define-from-file`, signing,
the `flutter build` matrix, version/build-number, store notes, and the OTA
decision — per `flutter-release-engineering`.

## Orchestrator rules

- Delegate; don't reimplement. Each subagent carries its own skills.
- Run only the phases the task size calls for.
- Keep the user-facing summary proportional to the change.
- Every "how" question goes to an official skill, never a hand-written procedure.
