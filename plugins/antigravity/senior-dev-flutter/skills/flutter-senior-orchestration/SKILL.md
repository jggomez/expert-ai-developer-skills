---
name: flutter-senior-orchestration
description: Use to run a Flutter feature or fix end to end — restoring cross-AI context (context/memory/), bootstrapping root AGENTS.md, 3-tier dynamic routing, capability and risk-gated subagent dispatch via PLAN.md, sequencing official flutter-*/dart-* skills, and dispatching parallel or sequential subagents (ui-ux-designer, flutter-architect, flutter-implementer, flutter-reviewer, flutter-release-engineer, qa-tester).
---

# Flutter Senior Orchestration

## Overview
The **Flutter Senior Orchestration** skill governs end-to-end delivery of Flutter and Dart applications across a 6-state Graph Engineering DAG: silent Cross-AI LLM Wiki memory restoration (`context/memory/MEMORY.md`), target-project `AGENTS.md` (`<= 90 lines`) integration, **3-Tier Dynamic Routing**, **Capability & Risk-Gated Dispatch** in `PLAN.md` (`<= 50 lines` per feature), parallel TDD implementation, tiered review (`Adversarial Review Committee`), **Fail-Honest E2E** transparency, and milestone memory persistence across **Claude Code** and **Google Antigravity**.

## When to Use
- **Trigger Scenarios**:
  - Orchestrating Flutter features, multi-screen flows, widget refactors, state management migrations, 60/120fps jank fixes, or multi-platform store releases.
  - Coordinating capability-gated discovery (`ui-ux-designer`, `flutter-architect`), isolated parallel `flutter-implementer` tracks, and tiered verification (`flutter-reviewer`, `flutter-release-engineer`, `qa-tester`).
- **When NOT to Use**:
  - Pure backend tasks (`python-expert`, `database-migration-expert`) or single-turn Q&A without code edits.

## Core Invariants & Artifact Line Budgets
1. **Zero Direct Dart Implementation**: The orchestrator NEVER edits `.dart` files (`lib/`, `test/`). Direct writes are restricted to `PLAN.md`, root `AGENTS.md`, root `DESIGN.md`, `doc/adr/*.md`, `docs/` (`docs/<feature-name>/`), `.agents/`, and `context/memory/`.
2. **Automated Git Branch Governance & Scope Drift**: Never work on `main`, `master`, `develop`, or `dev`. At State 0, inspect `git symbolic-ref --short HEAD` and auto-branch (`git checkout -b feat/<descriptive-slug>` or `fix/<slug>`). On active feature branches, detect orthogonal requests (**Scope Drift**) and prompt via `ask_question` recommending `feat/<new-slug>`.
3. **Target-Project `AGENTS.md` + `DESIGN.md` + `MEMORY.md` Integration**: In State 0 / State 5, verify root `AGENTS.md`; if missing or if stack/commands/conventions changed, generate/update a concise root `AGENTS.md` (`<= 90 lines`) linking executable commands (`flutter analyze`, `flutter test`), root `DESIGN.md`, and `context/memory/MEMORY.md`.
4. **Strict Conciseness Line Caps**:
   - `PLAN.md` feature block `<= 50 lines` | Root `AGENTS.md <= 90 lines` | Root `DESIGN.md <= 110 lines`
   - `docs/<feature-name>/prd.md <= 70 lines` | `docs/<feature-name>/design.md <= 35 lines` (screen delta only)
   - `adr-NNN-*.md <= 55 lines` | `docs/<feature-name>/architecture.md <= 70 lines`
   - `docs/<feature-name>/test-matrix.md <= 80 lines` | Review / adversarial / blackbox reports `<= 50 lines` each
5. **Fail-Honest E2E Transparency**: If `e2e-blackbox-tester` returns `BLOCKED` or `SKIPPED` (e.g., mobile-only target without web, server couldn't start, Chromium unavailable), explicitly tell the user in the final summary: *"Browser E2E was NOT executed (`BLOCKED`/`SKIPPED`): <exact reason>"* — NEVER mask it as passed.

## 3-Tier Dynamic Routing & Capability/Risk-Gated Dispatch

### 3-Tier SDLC Rubric for Flutter
| Tier | Scope & Triggers | Discovery & Alignment Gate | Build & Verification Protocol |
| :--- | :--- | :--- | :--- |
| **Tier 1: Fast-Track** | Single-widget localized UI/logic fix or doc/chore (`< 2` files); state/routing/plugins unchanged. | **SKIP** State 1 discovery and `ask_question` modal (auto-proceed). | 1 `flutter-implementer` (`Workspace: 'inherit'`). Scoped `flutter test` (`exit code 0`) + quick `flutter-reviewer` check. |
| **Tier 2: Standard** | `2–4` files, new screen/view, multi-widget flow, local state, or route addition. | **Capability-Gated** State 1 (skip State 1 files if all `SKIP`). **Mandatory** `ask_question` modal. | Parallel `flutter-implementer` (Mode A/B). `flutter-reviewer` + `qa-tester` (`test-matrix.md <= 80`) + gated `flutter-release-engineer`. |
| **Tier 3: Mission-Critical** | Greenfield app, core state migration (Riverpod/Bloc), auth/payments, FFI/native plugins, store release. | **Capability-Gated** State 1 in `docs/<feature-name>/`. **Mandatory** `ask_question` sign-off. | Isolated parallel `flutter-implementer`. **Adversarial Review Committee**: `flutter-reviewer` + `flutter-release-engineer` + `qa-tester` (+ risk/web-gated specialists). |

### 5-Row `Discovery & Architecture Triage` (`Invoke / SKIP`) Rubric
Every `PLAN.md` (`<= 50 lines`) MUST include a compact 5-row table justifying each specialist in 1 line:

| Subagent | `INVOKE ONLY IF` | `SKIP WHEN` |
| :--- | :--- | :--- |
| **`product-analyst`** | Business scope, user stories, or acceptance criteria are missing/ambiguous (`prd.md <= 70 lines`). | User prompt already specifies clear stories/criteria, or bugfixes, refactors, docs, chores. |
| **`ui-ux-designer`** | Flutter screens/widgets/components are created/modified AND root `DESIGN.md` is missing or new mobile visual patterns/48x48dp touch tokens are needed (`DESIGN.md <= 110`, `design.md <= 35`). | Non-visual data/repository/state tasks, or minor UI changes already covered by root `DESIGN.md`. |
| **`flutter-architect`** | Genuine structural decision needed: state management pattern/contract shift, `GoRouter`/deep-link topology change, new native plugin/FFI/platform channel (`adr <= 55`, `architecture.md <= 70`). | Changes follow established repository architecture (even across `>= 2` files). |
| **`flutter-release-engineer` & Risk Gates** | `flutter-release-engineer` ONLY IF `pubspec.yaml`, flavors, `--dart-define-from-file`, signing, native configs, or store bundles change (and Tier 3); Tier 3 `critic` ONLY IF diff `>= 150 LOC` / structural refactor; `challenger` ONLY IF auth, payments, concurrency/isolates, untrusted input, or destructive mutations (`<= 50 lines`). | Pure Dart widget/domain changes without pubspec/signing impact or high-risk security/concurrency surfaces. |
| **`e2e-blackbox-tester`** | Runnable Flutter Web UI (`localhost`/staging URL) exists AND UI/user flows were touched (`blackbox-report.md <= 50 lines`). | **ALWAYS SKIP** on mobile-only targets without web (`iOS`/`Android`-only) or pure data/logic layers. |

> **Zero-Bloat Fast-Forward**: When ALL Discovery rows evaluate to `SKIP`, skip State 1 discovery file bloat completely and proceed directly to the `ask_question` alignment modal and State 2 build.

## Process

### 1. State 0: Branch Governance, Memory, Target `AGENTS.md` & Triage Gate
1. **Git Branch Governance**: Inspect `git symbolic-ref --short HEAD`; auto-branch `feat/<descriptive-slug>` or `fix/<slug>` off base branches; prompt via `ask_question` on **Scope Drift**.
2. **Feature Directory & Memory**: Ensure `docs/<feature-name>/` exists (syncing `docs/specifications/` if present). Silently read `context/memory/MEMORY.md` (~500 tokens); drill down on demand.
3. **Target `AGENTS.md` Check**: Create or update root `AGENTS.md` (`<= 90 lines`) if missing or if stack/commands/conventions changed, linking commands, root `DESIGN.md`, and `context/memory/MEMORY.md`.
4. **Author `PLAN.md` (`<= 50 lines`)**: Classify Tier 1/2/3, complete the 5-row `Invoke / SKIP` triage table, and define `Parallel Execution Tracks`.

### 2. State 1 & 1.5: Capability-Gated Discovery & Interactive User Alignment Gate
- **State 1**: Skip for Tier 1 or when all Discovery specialists are `SKIP`. Otherwise dispatch ONLY `INVOKE` specialists (`product-analyst`, `ui-ux-designer`, `flutter-architect`) within strict line budgets.
- **State 1.5 (`Interactive User Alignment Gate`)**: Auto-proceed on Tier 1. On Tier 2 & Tier 3, PAUSE and call `ask_question` summarizing scope, mobile UI design (`DESIGN.md` / `design.md`), and Flutter architecture (`architecture.md` / ADRs), asking: *"Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"* Wait for explicit approval.

### 3. State 2: Parallel Build, Collision Analysis & Scoped Test Isolation
- **Collision Analysis**: Verify non-overlapping `Owned Files` in **Mode A — Disjoint File Partitioning** (`Workspace: 'inherit'`). Enforce **Mode B — Git Worktree Isolation** (`Workspace: 'share'` / `'branch'` or `git worktree`) whenever tracks touch shared files (`main.dart`, router, `pubspec.yaml`, DI, `build_runner`).
- **Scoped Test Isolation**: Parallel `flutter-implementer` instances run ONLY their assigned test file during TDD loops; full suite execution waits for State 3.

### 4. State 3 & 4: Review, Release & Adversarial Review Committee
- **Tier 1**: Scoped `flutter test` (`exit code 0`) + `flutter-reviewer` check.
- **Tier 2**: Parallel `flutter-reviewer` (60/120fps, `.dispose()` leaks, `BuildContext` async gaps, semantics) + `qa-tester` (`docs/<feature-name>/test-matrix.md <= 80 lines` + `exit code 0`) + gated `flutter-release-engineer`.
- **Tier 3 (`Adversarial Review Committee`)**: Parallel `flutter-reviewer`, `flutter-release-engineer`, and `qa-tester` (`test-matrix.md <= 80` + `exit code 0`), plus risk/web-gated `critic`, `challenger`, and `e2e-blackbox-tester` (`<= 50 lines` each).
- **Bounded Retries & Fail-Honest E2E**: Max 3 fix loops to `flutter-implementer`. Always disclose `BLOCKED`/`SKIPPED` browser E2E honestly in the final summary.

### 5. State 5: Ship, `AGENTS.md` Sync & LLM Wiki Memory Update
- Mark tasks complete in `PLAN.md`, sync root `AGENTS.md` (`<= 90 lines`) if changed, and update `context/memory/` (`MEMORY.md <= 80-100 lines`, topic pages if changed, `5-8 line` log entry in `context/memory/log/YYYY-MM-DD.md`). Never write checkpoints on intermediate turns.

## Usage
- **Claude Code**: Invoke via `/skill flutter-senior-orchestration` or `flutter-feature-orchestrator`, dispatching parallel `Agent` calls.
- **Google Antigravity**: Dispatch subagents via `invoke_subagent`, gate alignment via `ask_question`, and verify with `flutter analyze` and `flutter test`.

## Red Flags
- Editing `.dart` source or test files directly in the orchestrator.
- Over-invoking specialists whose capability/risk gate evaluates to `SKIP` (e.g., running `e2e-blackbox-tester` on mobile-only targets without web, or `flutter-architect` when following existing patterns).
- Masking `BLOCKED` or `SKIPPED` browser E2E as passed instead of explicitly reporting *"Browser E2E was NOT executed (`BLOCKED`/`SKIPPED`): <exact reason>"*.
- Exceeding artifact line budgets, skipping `ask_question` on Tier 2/3, omitting Mode B worktree isolation on shared files (`pubspec.yaml`, router, `build_runner`), omitting `.dispose()` or `mounted` checks, or committing raw secrets.

## Verification
- [ ] `State 0`: Branch checked (`feat/<slug>` auto-created; Scope Drift checked); `docs/<feature-name>/` created; `context/memory/MEMORY.md` read; root `AGENTS.md` (`<= 90 lines`) checked; `PLAN.md` (`<= 50 lines`) has 5-row `Invoke / SKIP` triage.
- [ ] `State 1 & 1.5`: Only capability-triggered specialists ran within line caps; Tier 2/3 `ask_question` approval received.
- [ ] `State 2`: Collision analysis enforced Mode A or Mode B; parallel `flutter-implementer` tracks ran scoped tests only.
- [ ] `State 3 & 4`: Tiered verification passed (`flutter-reviewer` 60/120fps & zero leaks, `flutter-release-engineer`, `qa-tester` `test-matrix.md <= 80` & `exit code 0` in `Adversarial Review Committee`); `BLOCKED`/`SKIPPED` E2E disclosed honestly.
- [ ] `State 5`: `PLAN.md`, root `AGENTS.md` (if changed), and `context/memory/` updated once at completion.
