---
trigger: always_on
description: Multi-agent operations and loop engineering rules enforcing the 6-state Graph Engineering DAG, 3-Tier SDLC, State 0 per-subagent Invoke/SKIP capability gating, concise artifact caps, Google DESIGN.md, root AGENTS.md, and Fail-Honest E2E verification.
---

# Multi-Agent Operations & Loop Engineering Rules

**Identifier**: `multi-agent-ops-rules`

## 1. Graph Engineering State Machine & 3-Tier Adaptive SDLC

All multi-agent workflows execute a deterministic 6-state DAG dynamically scaled across three SDLC tiers:
- **State 0 (Memory Restore & SDLC Triage)**: Enforce Git Branch Governance (`feat/<slug>` from protected branches; `ask_question` on Scope Drift), create `docs/<feature-name>/`, silently read `context/memory/MEMORY.md` (`<= 80-100 lines`, ~500 tokens), bootstrap/sync target-project root `AGENTS.md` (`<= 90 lines`), and author `PLAN.md` (`<= 50 lines`) with a per-subagent `Invoke / SKIP` triage table.
- **State 1 & 1.5 (Discovery & Alignment Gate)**: Skipped in Tier 1; capability-gated in Tier 2 & Tier 3, followed by a mandatory `ask_question` approval modal before State 2 implementation.
- **State 2 -> State 5 (Build, Verification & Ship)**: Isolated parallel implementation, empirical QA + compliance verification, and State 5 `PLAN.md` + `context/memory/` update.

| Phase | Tier 1: Fast-Track | Tier 2: Standard | Tier 3: Mission-Critical |
| :--- | :--- | :--- | :--- |
| **Triggers** | Single-file bugfix, docs, chore, typo, local refactor | 2–4 modules, new endpoint, single UI view, DB migration | End-to-end feature, auth/payments, breaking API, major refactor |
| **State 1 Discovery** | **SKIPPED** (zero discovery artifacts) | **Capability-Gated** (`Invoke / SKIP` per specialist) | **Capability-Gated** (`Invoke / SKIP` per specialist) |
| **State 1.5 Alignment** | **SKIPPED** (auto-proceeds to State 2) | **MANDATORY** `ask_question` modal sign-off | **MANDATORY** `ask_question` modal sign-off |
| **State 2 Build** | 1 `code-implementer` (Mode A) | 1..N `code-implementer` (Mode A Disjoint Files) | 1..N `code-implementer` (Mode A or Mode B Worktree) |
| **State 3 & 4 Verify** | Scoped `qa-tester` + `compliance-verifier` | Full suite + `test-matrix.md` + `compliance-verifier` | Capability-gated Adversarial Committee + `compliance-verifier` |

## 2. State 0 Per-Subagent `Invoke / SKIP` Capability Gating & Line Caps

Never dispatch rigid subagent bundles blindly. Evaluate each specialist at State 0 and enforce strict Zero-Fluff line budgets:
- **`product-analyst`**: **Invoke** ONLY if business scope, user stories, or acceptance criteria are ambiguous/missing (`docs/<feature-name>/prd.md <= 70 lines`). **SKIP** when prompt scope is explicit or for bugfixes, refactors, chores, docs, and CLIs.
- **`ui-ux-designer`**: **Invoke** ONLY if UI screens/components change AND root `DESIGN.md` is missing or new visual patterns/tokens are introduced (official Google 2-layer root `DESIGN.md <= 110 lines` + optional `docs/<feature-name>/design.md <= 35 lines` delta). **SKIP** for backend, CLI, data pipelines, or minor UI tweaks covered by `DESIGN.md`.
- **`architect-engineer`**: **Invoke** ONLY for structural decisions (new DB schema, cross-service contracts, core dependencies, pattern shifts; MADR `docs/<feature-name>/adr-NNN-*.md <= 55 lines`, optional `docs/<feature-name>/architecture.md <= 70 lines`). **SKIP** when following established repo patterns.
- **`qa-tester`**: **Invoke** across all tiers — scoped test file in Tier 1; full test suite (`exit code 0`) + `docs/<feature-name>/test-matrix.md` (`<= 80 lines`) in Tier 2 & Tier 3.
- **`critic`** *(Tier 3)*: **Invoke** ONLY if diff `>= 150 LOC` or multi-module structural refactor (`docs/<feature-name>/critic-review.md <= 50 lines`). Otherwise **SKIP**.
- **`challenger`** *(Tier 3)*: **Invoke** ONLY for high-risk logic: auth, payments, concurrency, untrusted inputs, or destructive mutations (`docs/<feature-name>/adversarial-report.md <= 50 lines`). Otherwise **SKIP**.
- **`e2e-blackbox-tester`** *(Tier 3)*: **Invoke** ONLY when a runnable web UI exists (`docs/<feature-name>/blackbox-report.md <= 50 lines` + Playwright `.png` screenshots at `375/768/1280/1920px` in `docs/<feature-name>/evidence/`). Otherwise **SKIP**.
- **`compliance-verifier`**: **Invoke** across all tiers for static analysis, OWASP security audit, physical E2E `.png` evidence verification, and `APPROVED` sign-off.
- **Root Governance Caps**: Target-project `AGENTS.md <= 90 lines` (commands, conventions, links to `DESIGN.md` & `context/memory/MEMORY.md`); `PLAN.md <= 50 lines`.

## 3. Fail-Honest E2E Verification & Finite Self-Correction

- **Fail-Honest E2E Protocol**: `e2e-blackbox-tester` executes real Playwright browser checks via `run_command`. If no live web server or Chromium binary can run, it **MUST** report `BLOCKED` or `SKIPPED` — never fabricate or hallucinate `PASSED` — and the orchestrator **MUST** surface `BLOCKED`/`SKIPPED` statuses explicitly to the user.
- **Finite Self-Correction (Max 3 Retries)**: On test or compliance failure (`REJECTED`), loop back to `code-implementer` up to **3 iterations**. If unresolved after 3 attempts, pause and escalate to the user via `ask_question` with root cause and failing traces.

## 4. Delegation Boundary, Workspace Isolation & Token Conservation

- **Orchestrator Non-Execution Constraint**: Orchestrators (`senior-dev-orchestrator`, `flutter-feature-orchestrator`) are **STRICTLY PROHIBITED** from editing `src/`, `lib/`, or `tests/`. Direct writes are restricted to `PLAN.md`, `AGENTS.md`, `DESIGN.md`, `ADR-*.md`, `.agents/`, `docs/`, and `context/memory/`.
- **Pre-Dispatch Collision Analysis**:
  - **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**: Parallel workers receive non-overlapping `Exclusive Owned Files` lists with zero merge overhead.
  - **Mode B — Git Worktree Isolation (`Workspace: 'branch'` / `'share'` or `git worktree`)**: Mandatory whenever parallel tracks touch shared files (`package.json`, `pubspec.yaml`, routers, DI) or run conflicting builds.
- **Scoped Test Isolation**: Parallel implementers in State 2 run ONLY their assigned test file; full test suite execution is reserved for State 3 Fan-In by `qa-tester`.
- **Reactive Wakeup & Cross-AI Memory**: Never poll subagents or tasks in loops; read files with `grep_search` or line slices; update `context/memory/MEMORY.md` (`<= 80-100 lines`), `architecture.md`/`conventions.md`, and a 5–8 line `context/memory/log/YYYY-MM-DD.md` block only at State 5.
