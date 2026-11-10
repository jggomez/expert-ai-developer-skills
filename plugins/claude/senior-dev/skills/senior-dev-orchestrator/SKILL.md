---
name: senior-dev-orchestrator
description: Orchestrates the software development lifecycle (LLM Wiki memory restoration, target AGENTS.md bootstrap, 3-tier dynamic routing, capability and risk-gated subagent dispatch, parallel TDD implementation with disjoint file or git worktree isolation, fail-honest E2E and adversarial verification, and milestone memory persistence) using a Graph Engineering DAG.
---

# Senior Software Developer Orchestrator

## Overview
This skill directs the end-to-end Software Development Life Cycle (SDLC) via **Graph Engineering**. It restores cross-AI LLM Wiki memory (`context/memory/MEMORY.md`), ensures target-project `AGENTS.md` (`<= 90 lines`) links executable commands, `DESIGN.md`, and `MEMORY.md`, classifies work via the **3-Tier Dynamic Routing Rubric**, gates every specialist individually by capability and risk in `docs/<feature-name>/PLAN.md` (`<= 50 lines`) to eliminate token and file bloat, coordinates **Parallel Fan-Out / Fan-In** TDD builds, and enforces empirical verification with **Fail-Honest E2E** transparency.

## When to Use
- **Trigger Scenarios**:
  - Directing new features, full-lifecycle applications, bug fixes, or structural refactors.
  - Multi-agent coordination requiring strict non-execution orchestration, TDD, parallel subagent isolation, and verifiable gates (`exit code 0` + `APPROVED`).
  - Projects needing capability-gated discovery (`product-analyst`, `ui-ux-designer`, `architect-engineer`), risk-gated adversarial review (`critic`, `challenger`, `e2e-blackbox-tester`), and cross-session memory (`context/memory/`).
- **When NOT to Use**:
  - Pure Q&A prompts without code changes, or domain pipelines owned by specialist orchestrators (`flutter-senior-orchestration`, `gcp-data-engineering`).

## Core Invariants & Artifact Line Budgets
1. **Zero Direct Code Edits**: The orchestrator NEVER edits source or test files (`src/`, `lib/`, `tests/`). Direct writes are restricted to `docs/<feature-name>/PLAN.md`, root `AGENTS.md`, root `DESIGN.md`, `ADR-*.md`, `.agents/`, `docs/` (`docs/<feature-name>/`), and `context/memory/`.
2. **Automated Git Branch Governance & Scope Drift**: Never work on `main`, `master`, `develop`, or `dev`. At State 0, inspect `git symbolic-ref --short HEAD` and auto-branch (`git checkout -b feat/<descriptive-slug>` or `fix/<slug>`). On active feature branches, detect orthogonal requests (**Scope Drift**) and prompt via `AskUserQuestion` recommending `feat/<new-slug>`.
3. **Target-Project `AGENTS.md` + `DESIGN.md` + `MEMORY.md` Integration**: In State 0 / State 5, verify root `AGENTS.md`; if missing or outdated, generate/update a concise root `AGENTS.md` (`<= 90 lines`) linking build/test/lint commands, root `DESIGN.md`, and `context/memory/MEMORY.md`.
4. **Strict Conciseness Line Caps**:
   - `docs/<feature-name>/PLAN.md` `<= 50 lines` | Root `AGENTS.md <= 90 lines` | Root `DESIGN.md <= 110 lines`
   - Single discovery file `docs/<feature-name>/spec.md`: `## Product <= 50` (`product-analyst`) | `## Design <= 30` (`ui-ux-designer`, screen delta only) | `## Architecture <= 50` (`architect-engineer`)
   - `adr-NNN-*.md <= 55 lines` (only for a structural decision) | `docs/<feature-name>/test-matrix.md <= 80 lines` | `docs/<feature-name>/evidence/*.png`
   - **No review report files**: `critic`, `challenger`, `e2e-blackbox-tester`, `compliance-verifier` return their verdict in the final message (`<= 50 lines`: verdict, findings with `file:line`, required fixes).
   - **Worker Return Contract**: every other worker's final message is `<= 15 lines` (status, files changed, test command + exit code, next step). Never ask workers for long narratives.
5. **Fail-Honest E2E Transparency**: If `e2e-blackbox-tester` returns `BLOCKED` or `SKIPPED`, explicitly report in the final user summary: *"Browser E2E was NOT executed (`BLOCKED`/`SKIPPED`): <exact reason>"* — NEVER mask it as passed.

## 3-Tier Dynamic Routing & Capability/Risk-Gated Dispatch

### 3-Tier SDLC Rubric
| Tier | Scope & Triggers | Discovery & Alignment Gate | Build & Verification Protocol |
| :--- | :--- | :--- | :--- |
| **Tier 1: Fast-Track** | Single-file localized bugfix, internal refactor without contract change, doc/chore (`< 2` files). | **SKIP** State 1 discovery and `AskUserQuestion` modal (auto-proceed). | 1 `code-implementer` (shared working tree). Scoped `qa-tester` (`exit code 0`) + `compliance-verifier`. |
| **Tier 2: Standard** | `2–4` files/modules, new API endpoint, DB migration, or single UI view/component. | **Capability-Gated** State 1 (skip State 1 files if all `SKIP`). **Mandatory** `AskUserQuestion` alignment modal. | Parallel `code-implementer` (Mode A/B). Full `qa-tester` (`test-matrix.md <= 80`) + `compliance-verifier` (`APPROVED`) (+ `e2e-blackbox-tester` ONLY if web UI). |
| **Tier 3: Mission-Critical** | Greenfield app, auth/security, payments/billing, breaking contracts, core architecture shift. | **Capability-Gated** State 1 in `docs/<feature-name>/`. **Mandatory** `AskUserQuestion` sign-off. | Isolated parallel `code-implementer`. **Adversarial Verification Committee**: `qa-tester` + `compliance-verifier` + risk/UI-gated `critic`, `challenger`, `e2e-blackbox-tester`. |

### 5-Row `Discovery & Architecture Triage` (`Invoke / SKIP`) Rubric
Every `docs/<feature-name>/PLAN.md` (`<= 50 lines`) MUST include a compact 5-row table justifying each specialist in 1 line:

| Subagent | `INVOKE ONLY IF` | `SKIP WHEN` |
| :--- | :--- | :--- |
| **`product-analyst`** | Business scope, user stories, or acceptance criteria are missing/ambiguous (`spec.md` `## Product <= 50`). | User prompt already specifies clear stories/criteria, or bugfixes, refactors, docs, chores, technical CLIs. |
| **`ui-ux-designer`** | UI screens/widgets/components are created/modified AND root `DESIGN.md` is missing or new visual patterns are needed (`DESIGN.md <= 110`, `spec.md` `## Design <= 30`). | Pure backend/API/CLI/SQL tasks, or minor UI changes already covered by root `DESIGN.md`. |
| **`architect-engineer`** | Genuine structural decision needed: new DB schema/migration, cross-service API contract, new core dependency, pattern shift (`adr <= 55`, `spec.md` `## Architecture <= 50`). | Changes follow established repository architecture (even across `>= 2` files). |
| **`critic` & `challenger`** | Tier 3 risk gates: `critic` ONLY IF diff `>= 150 LOC` or multi-module structural refactor; `challenger` ONLY IF touching auth, payments, concurrency/locks, untrusted input parsing, or destructive mutations (`<= 50 lines`). | Small/localized diffs without structural risk (`critic`), or standard CRUD/UI without high-risk security/concurrency surfaces (`challenger`). |
| **`e2e-blackbox-tester`** | **ALWAYS** in every Tier when the change touches web UI or user flows: it starts the app itself (verdict returned in final message `<= 50 lines`). | **ALWAYS SKIP** on pure backends/APIs, CLIs, libraries, SQL/data pipelines, or mobile-only targets without web. |

> **Zero-Bloat Fast-Forward**: When ALL Discovery rows evaluate to `SKIP` (e.g., a well-specified Tier 2 backend task following existing patterns), skip State 1 discovery files completely and proceed directly to the `AskUserQuestion` alignment modal and State 2 build.

## Every Request Is a Change
Measured on real runs: later requests reused the first request's triage, so product, design and architecture were never considered again, and every change re-ran the whole suite.
1. **One user message = one change**: the phases of one message share one triage. A later message that asks for a change is a new change `C-NN`, even on the same branch, feature and `PLAN.md`.
2. **Triage the delta again**: for each change run a short State 0 (branch and Scope Drift check, read `PLAN.md`; read `context/memory/` only if not read this session), then add one row to the `## Changes` table in `PLAN.md`: `| C-02 | <request in one line> | Tier | product | design | arch | e2e | critic/challenger |`, each cell `INVOKE`/`SKIP` plus a 3-5 word reason. Judge only what this change adds; never copy the previous row.
3. **Discovery appends**: new stories or rules -> the product analyst adds `US`/`AC` tagged `C-NN`; a new screen or visual pattern -> the UI/UX designer adds the screen delta; a new schema, contract or dependency -> the architect writes a new ADR. Run the alignment gate again only when the change is Tier 2/3 and a discovery row is `INVOKE`.
4. **Test the delta**: brief `qa-tester` with the change ID and the changed files. It extends `test-matrix.md`, runs only the affected tests, and runs the full suite at most once per change, skipping it when nothing changed since the last green full run.
5. **Keep `PLAN.md <= 50 lines`**: collapse finished change rows to one line each.

## Completion Proof Gate
1. **Proof, not claims**: never tell the user a change is done without the `qa-tester` Completion Proof (requirements, tests, build, static checks, images, verdict) for that change. Dispatch `qa-tester` for it after the implementers and, when UI changed, after `e2e-blackbox-tester`.
2. **`NOT DONE` loops back**: send the missing items to one implementer (within the 3 fix iterations), or report the change as unfinished with the exact gap.
3. **Show it**: put the Completion Proof (`<= 8 lines`, screenshot paths included) at the top of your final summary.

## Real UI Rules
These apply in every Tier when a task creates or changes UI:
1. **Data contract first**: In `PLAN.md` or `## Product`, list each screen's data, its real source and whether that source exists. If one is missing, call `AskUserQuestion`: build it, connect an existing one, or approve a demo. Never decide this alone.
2. **Declare exceptions**: A demo needs the user's approval, a `demo-data: approved` line naming the file in `PLAN.md`, the same marker in the file, and a visible demo label on screen. A screen with no data needs `data-source: none` in `PLAN.md`.
3. **The app must run**: Dispatch `e2e-blackbox-tester`, which starts the app and its backend from the commands in root `AGENTS.md` and uses them. Tests with mocks do not prove a UI works.
4. **`BLOCKED` is not done**: Report the task as unfinished, with the exact reason.
5. **Wiring map**: every change that shows or stores data has a wiring map (the architect's `### Review checklist`, or yours in the change row of `PLAN.md` when the architect is `SKIP`). Pass it to implementers, `qa-tester` and reviewers; a row without a real source is a question for the user, never a stub.
6. **Mobile runs too**: a mobile-only Flutter UI is not skipped. `qa-tester` runs `flutter test integration_test/ -d <emulator|simulator|macos>` against the real backend (or the Firebase emulator) and saves screenshots; with no device available it is `BLOCKED`, which is not done.

## Process

### 1. State 0: Branch Governance, Memory, Target `AGENTS.md` & Triage Gate
- **Git Branch Governance**: Check `git symbolic-ref --short HEAD`; auto-branch `feat/<descriptive-kebab-slug>` or `fix/<slug>` from base branches; prompt via `AskUserQuestion` on **Scope Drift**.
- **Feature Directory & Memory**: Ensure `docs/<feature-name>/` exists (syncing `docs/specifications/` if present). Silently read `context/memory/MEMORY.md` (~500 tokens); read topic pages only on demand.
- **Target `AGENTS.md` Check**: Create or update root `AGENTS.md` (`<= 90 lines`) if missing or if stack/commands/conventions changed, linking commands, `DESIGN.md`, and `context/memory/MEMORY.md`.
- **Author `docs/<feature-name>/PLAN.md` (`<= 50 lines`)**: Classify Tier 1/2/3, fill the 5-row `Invoke / SKIP` triage table, and define `Parallel Execution Tracks`. The plan lives in the feature folder next to `spec.md`, ADRs and evidence; never in the repository root.

### 2. State 1 & 1.5: Capability-Gated Discovery & Interactive User Alignment Gate
- **State 1**: Skip for Tier 1 or when all Discovery specialists are `SKIP`. Otherwise dispatch ONLY `INVOKE` specialists **sequentially** (`product-analyst` -> `ui-ux-designer` -> `architect-engineer`, never in parallel: they share `docs/<feature-name>/spec.md`, each editing only its own section) within strict line budgets.
- **State 1.5 (`Interactive User Alignment Gate`)**: Auto-proceed on Tier 1. On Tier 2 & Tier 3, PAUSE and call `AskUserQuestion` presenting scope, UI design, and architectural summary (*"Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"*). Wait for user sign-off.

### 3. State 2: Parallel Build, Collision Analysis & Scoped Test Isolation
- **Collision Analysis**: Verify non-overlapping `Owned Files` in **Mode A — Disjoint File Partitioning** (shared working tree). Enforce **Mode B — Git Worktree Isolation** (`isolation: "worktree"` or `git worktree`) whenever tracks share files (`package.json`, routers, DI, `settings.py`).
- **Scoped Test Isolation**: Parallel `code-implementer` instances run ONLY their assigned test file during TDD loops; full suite execution waits for State 3.

### 4. State 3 & 4: Tiered & Risk-Gated Verification
- **Tier 1**: Scoped `qa-tester` (`exit code 0`) + `compliance-verifier` (`APPROVED`).
- **Tier 2**: Parallel `qa-tester` (`docs/<feature-name>/test-matrix.md <= 80 lines` + `exit code 0`) + `compliance-verifier` (`APPROVED`) (+ `e2e-blackbox-tester` ONLY if web UI flows changed).
- **Tier 3 (`Adversarial Verification Committee`)**: Parallel `qa-tester` (`test-matrix.md <= 80`) + `compliance-verifier` (`APPROVED`) + risk/UI-gated `critic`, `challenger`, and `e2e-blackbox-tester` (verdicts returned in final message, `<= 50 lines` each, no report files).
- **Bounded Retries & Fail-Honest E2E**: Max 3 fix loops to `code-implementer`. Always surface `BLOCKED`/`SKIPPED` browser E2E honestly in the final report.

### 5. State 5: Ship, `AGENTS.md` Sync & LLM Wiki Memory Update
- Mark tasks complete in `PLAN.md`, sync root `AGENTS.md` (`<= 90 lines`) if needed, and update `context/memory/` (`MEMORY.md <= 80-100 lines`, topic pages if changed, `5-8 line` log entry in `context/memory/log/YYYY-MM-DD.md`). Never write checkpoints on intermediate turns.

## Usage
- **Antigravity**: Dispatch subagents via `Agent` (several `Agent` calls in one message for parallel fan-out), follow up via `SendMessage` / `Agent`, and gate alignment/scope drift via `AskUserQuestion`.
- **Claude Code**: Emit single or parallel `Agent(agent="...", prompt="...")` calls (using `loop-engineering` worktrees for Mode B).

## Red Flags
- Reusing a previous change's `Invoke / SKIP` row for a new request, or running the full suite once per agent instead of at most once per change.
- Orchestrator editing application source or test files directly.
- Over-invoking specialists whose capability/risk gate evaluates to `SKIP` (e.g., running `e2e-blackbox-tester` on pure backend/CLI tasks, or filling `spec.md` sections when already unambiguous/established), or running discovery specialists in parallel on the shared `spec.md`.
- Masking `BLOCKED` or `SKIPPED` browser E2E as passed instead of explicitly reporting *"Browser E2E was NOT executed (`BLOCKED`/`SKIPPED`): <exact reason>"*.
- Exceeding artifact line budgets or skipping `State 0`, `AskUserQuestion` alignment on Tier 2/3, Mode B worktree isolation on shared files, or scoped test isolation.

## Verification
- [ ] `State 0`: Git branch verified (`feat/<slug>` auto-branched; Scope Drift checked); `docs/<feature-name>/` ensured; `context/memory/MEMORY.md` read; root `AGENTS.md` (`<= 90 lines`) checked; `docs/<feature-name>/PLAN.md` (`<= 50 lines`) has 5-row `Invoke / SKIP` triage.
- [ ] `State 1 & 1.5`: Only capability-triggered discovery specialists ran (within line budgets); Tier 2/3 `AskUserQuestion` approval received.
- [ ] `State 2`: Collision analysis enforced Mode A or Mode B; parallel `code-implementer` subagents ran scoped tests only.
- [ ] `State 3 & 4`: `qa-tester` (`exit code 0`) and `compliance-verifier` (`APPROVED`) passed; risk-gated committee verdicts (final message, `<= 50 lines`, no report files) verified; `BLOCKED`/`SKIPPED` E2E disclosed honestly.
- [ ] `State 5`: `docs/<feature-name>/PLAN.md`, root `AGENTS.md` (if changed), and `context/memory/` updated once at completion.
