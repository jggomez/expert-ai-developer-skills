---
name: senior-dev-orchestrator
description: Orchestrates the software development lifecycle (LLM Wiki memory restoration, target AGENTS.md bootstrap, 3-tier dynamic routing, capability and risk-gated subagent dispatch, parallel TDD implementation with disjoint file or git worktree isolation, fail-honest E2E and adversarial verification, and milestone memory persistence) using a Graph Engineering DAG.
---

# Senior Software Developer Orchestrator

## Overview
This skill directs the end-to-end Software Development Life Cycle (SDLC) via **Graph Engineering**. It restores cross-AI LLM Wiki memory (`context/memory/MEMORY.md`), ensures target-project `AGENTS.md` (`<= 90 lines`) links executable commands, `DESIGN.md`, and `MEMORY.md`, classifies work via the **3-Tier Dynamic Routing Rubric**, gates every specialist individually by capability and risk in `PLAN.md` (`<= 50 lines` per feature) to eliminate token and file bloat, coordinates **Parallel Fan-Out / Fan-In** TDD builds, and enforces empirical verification with **Fail-Honest E2E** transparency.

## When to Use
- **Trigger Scenarios**:
  - Directing new features, full-lifecycle applications, bug fixes, or structural refactors.
  - Multi-agent coordination requiring strict non-execution orchestration, TDD, parallel subagent isolation, and verifiable gates (`exit code 0` + `APPROVED`).
  - Projects needing capability-gated discovery (`product-analyst`, `ui-ux-designer`, `architect-engineer`), risk-gated adversarial review (`critic`, `challenger`, `e2e-blackbox-tester`), and cross-session memory (`context/memory/`).
- **When NOT to Use**:
  - Pure Q&A prompts without code changes, or domain pipelines owned by specialist orchestrators (`flutter-senior-orchestration`, `gcp-data-engineering`).

## Core Invariants & Artifact Line Budgets
1. **Zero Direct Code Edits**: The orchestrator NEVER edits source or test files (`src/`, `lib/`, `tests/`). Direct writes are restricted to `PLAN.md`, root `AGENTS.md`, root `DESIGN.md`, `ADR-*.md`, `.agents/`, `docs/` (`docs/<feature-name>/`), and `context/memory/`.
2. **Automated Git Branch Governance & Scope Drift**: Never work on `main`, `master`, `develop`, or `dev`. At State 0, inspect `git symbolic-ref --short HEAD` and auto-branch (`git checkout -b feat/<descriptive-slug>` or `fix/<slug>`). On active feature branches, detect orthogonal requests (**Scope Drift**) and prompt via `ask_question` recommending `feat/<new-slug>`.
3. **Target-Project `AGENTS.md` + `DESIGN.md` + `MEMORY.md` Integration**: In State 0 / State 5, verify root `AGENTS.md`; if missing or outdated, generate/update a concise root `AGENTS.md` (`<= 90 lines`) linking build/test/lint commands, root `DESIGN.md`, and `context/memory/MEMORY.md`.
4. **Strict Conciseness Line Caps**:
   - `PLAN.md` feature block `<= 50 lines` | Root `AGENTS.md <= 90 lines` | Root `DESIGN.md <= 110 lines`
   - `docs/<feature-name>/prd.md <= 70 lines` | `docs/<feature-name>/design.md <= 35 lines` (screen delta only)
   - `adr-NNN-*.md <= 55 lines` | `docs/<feature-name>/architecture.md <= 70 lines`
   - `docs/<feature-name>/test-matrix.md <= 80 lines` | `critic-review.md`, `adversarial-report.md`, `blackbox-report.md <= 50 lines` each
5. **Fail-Honest E2E Transparency**: If `e2e-blackbox-tester` returns `BLOCKED` or `SKIPPED`, explicitly report in the final user summary: *"Browser E2E was NOT executed (`BLOCKED`/`SKIPPED`): <exact reason>"* — NEVER mask it as passed.

## 3-Tier Dynamic Routing & Capability/Risk-Gated Dispatch

### 3-Tier SDLC Rubric
| Tier | Scope & Triggers | Discovery & Alignment Gate | Build & Verification Protocol |
| :--- | :--- | :--- | :--- |
| **Tier 1: Fast-Track** | Single-file localized bugfix, internal refactor without contract change, doc/chore (`< 2` files). | **SKIP** State 1 discovery and `ask_question` modal (auto-proceed). | 1 `code-implementer` (`Workspace: 'inherit'`). Scoped `qa-tester` (`exit code 0`) + `compliance-verifier`. |
| **Tier 2: Standard** | `2–4` files/modules, new API endpoint, DB migration, or single UI view/component. | **Capability-Gated** State 1 (skip State 1 files if all `SKIP`). **Mandatory** `ask_question` alignment modal. | Parallel `code-implementer` (Mode A/B). Full `qa-tester` (`test-matrix.md <= 80`) + `compliance-verifier` (`APPROVED`) (+ `e2e-blackbox-tester` ONLY if web UI). |
| **Tier 3: Mission-Critical** | Greenfield app, auth/security, payments/billing, breaking contracts, core architecture shift. | **Capability-Gated** State 1 in `docs/<feature-name>/`. **Mandatory** `ask_question` sign-off. | Isolated parallel `code-implementer`. **Adversarial Verification Committee**: `qa-tester` + `compliance-verifier` + risk/UI-gated `critic`, `challenger`, `e2e-blackbox-tester`. |

### 5-Row `Discovery & Architecture Triage` (`Invoke / SKIP`) Rubric
Every `PLAN.md` (`<= 50 lines`) MUST include a compact 5-row table justifying each specialist in 1 line:

| Subagent | `INVOKE ONLY IF` | `SKIP WHEN` |
| :--- | :--- | :--- |
| **`product-analyst`** | Business scope, user stories, or acceptance criteria are missing/ambiguous (`prd.md <= 70 lines`). | User prompt already specifies clear stories/criteria, or bugfixes, refactors, docs, chores, technical CLIs. |
| **`ui-ux-designer`** | UI screens/widgets/components are created/modified AND root `DESIGN.md` is missing or new visual patterns are needed (`DESIGN.md <= 110`, `design.md <= 35`). | Pure backend/API/CLI/SQL tasks, or minor UI changes already covered by root `DESIGN.md`. |
| **`architect-engineer`** | Genuine structural decision needed: new DB schema/migration, cross-service API contract, new core dependency, pattern shift (`adr <= 55`, `architecture.md <= 70`). | Changes follow established repository architecture (even across `>= 2` files). |
| **`critic` & `challenger`** | Tier 3 risk gates: `critic` ONLY IF diff `>= 150 LOC` or multi-module structural refactor; `challenger` ONLY IF touching auth, payments, concurrency/locks, untrusted input parsing, or destructive mutations (`<= 50 lines`). | Small/localized diffs without structural risk (`critic`), or standard CRUD/UI without high-risk security/concurrency surfaces (`challenger`). |
| **`e2e-blackbox-tester`** | Runnable web UI (`localhost`/staging URL) exists AND UI/user flows were touched (`blackbox-report.md <= 50 lines`). | **ALWAYS SKIP** on pure backends/APIs, CLIs, libraries, SQL/data pipelines, or mobile-only targets without web. |

> **Zero-Bloat Fast-Forward**: When ALL Discovery rows evaluate to `SKIP` (e.g., a well-specified Tier 2 backend task following existing patterns), skip State 1 discovery files completely and proceed directly to the `ask_question` alignment modal and State 2 build.

## Process

### 1. State 0: Branch Governance, Memory, Target `AGENTS.md` & Triage Gate
- **Git Branch Governance**: Check `git symbolic-ref --short HEAD`; auto-branch `feat/<descriptive-kebab-slug>` or `fix/<slug>` from base branches; prompt via `ask_question` on **Scope Drift**.
- **Feature Directory & Memory**: Ensure `docs/<feature-name>/` exists (syncing `docs/specifications/` if present). Silently read `context/memory/MEMORY.md` (~500 tokens); read topic pages only on demand.
- **Target `AGENTS.md` Check**: Create or update root `AGENTS.md` (`<= 90 lines`) if missing or if stack/commands/conventions changed, linking commands, `DESIGN.md`, and `context/memory/MEMORY.md`.
- **Author `PLAN.md` (`<= 50 lines`)**: Classify Tier 1/2/3, fill the 5-row `Invoke / SKIP` triage table, and define `Parallel Execution Tracks`.

### 2. State 1 & 1.5: Capability-Gated Discovery & Interactive User Alignment Gate
- **State 1**: Skip for Tier 1 or when all Discovery specialists are `SKIP`. Otherwise dispatch ONLY `INVOKE` specialists (`product-analyst`, `ui-ux-designer`, `architect-engineer`) sequentially or in parallel within strict line budgets.
- **State 1.5 (`Interactive User Alignment Gate`)**: Auto-proceed on Tier 1. On Tier 2 & Tier 3, PAUSE and call `ask_question` presenting scope, UI design, and architectural summary (*"Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"*). Wait for user sign-off.

### 3. State 2: Parallel Build, Collision Analysis & Scoped Test Isolation
- **Collision Analysis**: Verify non-overlapping `Owned Files` in **Mode A — Disjoint File Partitioning** (`Workspace: 'inherit'`). Enforce **Mode B — Git Worktree Isolation** (`Workspace: 'share'` / `'branch'` or `git worktree`) whenever tracks share files (`package.json`, routers, DI, `settings.py`).
- **Scoped Test Isolation**: Parallel `code-implementer` instances run ONLY their assigned test file during TDD loops; full suite execution waits for State 3.

### 4. State 3 & 4: Tiered & Risk-Gated Verification
- **Tier 1**: Scoped `qa-tester` (`exit code 0`) + `compliance-verifier` (`APPROVED`).
- **Tier 2**: Parallel `qa-tester` (`docs/<feature-name>/test-matrix.md <= 80 lines` + `exit code 0`) + `compliance-verifier` (`APPROVED`) (+ `e2e-blackbox-tester` ONLY if web UI flows changed).
- **Tier 3 (`Adversarial Verification Committee`)**: Parallel `qa-tester` (`test-matrix.md <= 80`) + `compliance-verifier` (`APPROVED`) + risk/UI-gated `critic`, `challenger`, and `e2e-blackbox-tester` (`<= 50 lines` each).
- **Bounded Retries & Fail-Honest E2E**: Max 3 fix loops to `code-implementer`. Always surface `BLOCKED`/`SKIPPED` browser E2E honestly in the final report.

### 5. State 5: Ship, `AGENTS.md` Sync & LLM Wiki Memory Update
- Mark tasks complete in `PLAN.md`, sync root `AGENTS.md` (`<= 90 lines`) if needed, and update `context/memory/` (`MEMORY.md <= 80-100 lines`, topic pages if changed, `5-8 line` log entry in `context/memory/log/YYYY-MM-DD.md`). Never write checkpoints on intermediate turns.

## Usage
- **Antigravity**: Dispatch subagents via `Agent` (`Subagents=[...]` for parallel fan-out), follow up via `Agent` / `Agent`, and gate alignment/scope drift via `ask_question`.
- **Claude Code**: Emit single or parallel `Agent(agent="...", prompt="...")` calls (using `loop-engineering` worktrees for Mode B).

## Red Flags
- Orchestrator editing application source or test files directly.
- Over-invoking specialists whose capability/risk gate evaluates to `SKIP` (e.g., running `e2e-blackbox-tester` on pure backend/CLI tasks, or generating `prd.md`/`architecture.md` when already unambiguous/established).
- Masking `BLOCKED` or `SKIPPED` browser E2E as passed instead of explicitly reporting *"Browser E2E was NOT executed (`BLOCKED`/`SKIPPED`): <exact reason>"*.
- Exceeding artifact line budgets or skipping `State 0`, `ask_question` alignment on Tier 2/3, Mode B worktree isolation on shared files, or scoped test isolation.

## Verification
- [ ] `State 0`: Git branch verified (`feat/<slug>` auto-branched; Scope Drift checked); `docs/<feature-name>/` ensured; `context/memory/MEMORY.md` read; root `AGENTS.md` (`<= 90 lines`) checked; `PLAN.md` (`<= 50 lines`) has 5-row `Invoke / SKIP` triage.
- [ ] `State 1 & 1.5`: Only capability-triggered discovery specialists ran (within line budgets); Tier 2/3 `ask_question` approval received.
- [ ] `State 2`: Collision analysis enforced Mode A or Mode B; parallel `code-implementer` subagents ran scoped tests only.
- [ ] `State 3 & 4`: `qa-tester` (`exit code 0`) and `compliance-verifier` (`APPROVED`) passed; risk-gated committee reports (`<= 50 lines`) verified; `BLOCKED`/`SKIPPED` E2E disclosed honestly.
- [ ] `State 5`: `PLAN.md`, root `AGENTS.md` (if changed), and `context/memory/` updated once at completion.
