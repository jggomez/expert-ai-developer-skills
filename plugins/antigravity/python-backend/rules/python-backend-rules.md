---
trigger: always_on
description: Python backend engineering rules enforcing Gitflow branch safety, 6-State Plan-First DAG, 3-Tier Dynamic SDLC, Capability & Risk-Gated Subagent Dispatch, Conciseness Line Budgets, Target-Project AGENTS.md/DESIGN.md/MEMORY.md integration, Fail-Honest E2E reporting, Alembic migrations, and TDD guarantees.
---

# Python Backend Engineering Rules & Graph Protocol

**Identifier**: `python-backend-rules`

These rules enforce Cross-AI LLM Wiki memory (`context/memory/`), target-project `AGENTS.md` integration, **3-Tier Dynamic SDLC** with **Capability & Risk-Gated Dispatch**, `docs/<feature-name>/` artifact conciseness, State 1.5 Interactive User Alignment Gate, parallel vertical slice isolation, Git Branch Governance, TDD with QA Test Matrix (`docs/<feature-name>/test-matrix.md`), Fail-Honest E2E reporting, and zero-downtime Alembic migrations.

---

## 1. 6-State Graph Engineering DAG

Every Python backend feature, bugfix, or refactoring workflow transitions through the 6-state DAG:

```
[STATE 0: BRANCH, MEMORY, TARGET AGENTS.md & CAPABILITY-GATED TRIAGE]
  ├─► 1. Git Branch Governance: Auto-branch feat/<slug> off base (main/dev); ask_question on Scope Drift
  ├─► 2. Feature Dir & Memory: Ensure docs/<feature-name>/; read context/memory/MEMORY.md (~500 tok)
  ├─► 3. Target AGENTS.md: Ensure root AGENTS.md (<= 90 lines) links commands, DESIGN.md & MEMORY.md
  └─► 4. Author PLAN.md (<= 50 lines/feature): Classify Tier 1/2/3 + 5-row Invoke/SKIP Triage Table
          ├──────────────────────────────┬──────────────────────────────┐
          ▼                              ▼                              ▼
  [Tier 1: Fast-Track]           [Tier 2: Standard]            [Tier 3: Mission-Critical]
  (Skip State 1 & Modal)         (Capability-Gated State 1)    (Capability-Gated State 1)
          │                              │                              │
          │                              ▼                              ▼
          │                      [INTERACTIVE USER ALIGNMENT GATE (STATE 1.5)]
          │                      └── ask_question modal -> Explicit user sign-off
          ▼                              ▼                              ▼
[STATE 2: TDD IMPLEMENTATION — PARALLEL VERTICAL SLICES & WORKSPACE ISOLATION]
  ├── Mode A (Default): Disjoint Files (Workspace: 'inherit', non-overlapping Owned Files)
  ├── Mode B: Git Worktree Isolation (shared main.py, router wiring, settings.py, or Alembic heads)
  └── Scoped Test Isolation: Run ONLY assigned test file during loops (pytest <assigned_test>.py)
          ▼                              ▼                              ▼
[STATE 3 & 4: QA VERIFICATION & RISK-GATED ADVERSARIAL AUDIT]
  ├── Tier 1: Scoped qa-tester (exit code 0) + compliance-verifier (APPROVED)
  ├── Tier 2: Full test-matrix.md (<= 80 lines, exit code 0) + compliance-verifier (APPROVED)
  └── Tier 3: Adversarial Verification Committee: qa-tester + compliance-verifier
              + risk/UI-gated critic, challenger, e2e-blackbox-tester (<= 50 lines each)
          ▼ (Max 3 fix iterations via loop-engineering)
[STATE 5: SHIP & MEMORY SYNC] -> Finalize PLAN.md, sync AGENTS.md & context/memory/, Fail-Honest E2E summary
```

---

## 2. 3-Tier Dynamic SDLC & Capability/Risk-Gated Dispatch

| Dimension / Phase | Tier 1: Fast-Track (Low Complexity) | Tier 2: Standard (Medium Complexity) | Tier 3: Mission-Critical (Complex) |
| :--- | :--- | :--- | :--- |
| **Scope & Triggers** | Single-file bugfixes, typos, docs, localized route tweaks (`< 2` files). No schema or public contract change. | `2–4` files/modules, new API endpoint, Pydantic DTO change, or single Alembic/Django migration. | Core auth/RBAC, payments/billing, DB engine migration, breaking OpenAPI contracts, greenfield services. |
| **Discovery (State 1)** | **SKIPPED**: Zero discovery overhead. | **CAPABILITY-GATED**: Only `INVOKE` specialists run; skip State 1 files if all `SKIP`. | **CAPABILITY-GATED**: Triggered `prd.md`, `api-spec.md`, `architecture.md`, `adr-*.md`. |
| **Alignment Gate (1.5)** | **SKIPPED**: Auto-proceeds to State 2. | **MANDATORY**: `ask_question` modal presenting API spec/plan & schema summary. | **MANDATORY**: Strict `ask_question` modal requiring explicit user sign-off. |
| **Build Mode (State 2)** | 1 `code-implementer` in Mode A (`Workspace: 'inherit'`). | 1..N `code-implementer` in parallel (Mode A Disjoint Files or Mode B Worktree). | 1..N `code-implementer` in parallel with strict Collision Analysis & isolation. |
| **Verification (State 3/4)** | Scoped `pytest` (`exit code 0`) + `compliance-verifier`. | Full `test-matrix.md` (`<= 80 lines`, `exit code 0`) + `compliance-verifier` (`APPROVED`). | **Adversarial Verification Committee**: `qa-tester` + `compliance-verifier` + risk/UI-gated `critic`, `challenger`, `e2e-blackbox-tester`. |

### 5-Row `Discovery & Architecture Triage` (`Invoke / SKIP`) Rubric
Every `PLAN.md` (`<= 50 lines` per feature) MUST include a compact 5-row table justifying every invoked and skipped subagent in 1 line:
1. **`product-analyst`**: **INVOKE ONLY IF** business scope, user stories, or acceptance criteria are missing/ambiguous (`docs/<feature-name>/prd.md <= 70 lines`). **SKIP** when stories/criteria are already clear, or for bugfixes, refactors, docs, chores, and technical CLIs.
2. **`ui-ux-designer`**: **INVOKE ONLY IF** full-stack UI templates/components (Jinja2/HTMX/admin views) are created/modified AND root `DESIGN.md` is missing or new visual patterns are needed (root `DESIGN.md <= 110 lines`; `docs/<feature-name>/design.md <= 35 lines`). **ALWAYS SKIP** on pure backend APIs, CLIs, workers, and SQL pipelines.
3. **`architect-engineer` (`design-spec-expert` / `database-migration-expert`)**: **INVOKE ONLY IF** a genuine structural decision is needed (new SQLAlchemy/Django schema or Alembic migration, cross-service/breaking OpenAPI contract, new core dependency, pattern shift; `adr-NNN-*.md <= 55 lines`, `docs/<feature-name>/architecture.md` & `api-spec.md <= 70 lines`). **SKIP** when following established repository architecture.
4. **`critic` & `challenger` (Risk-Gated in Tier 3)**: Invoke `critic` **ONLY IF** diff is `>= 150 LOC` or a multi-module structural refactor (`critic-review.md <= 50 lines`). Invoke `challenger` **ONLY IF** touching high-risk domains (auth, payments, concurrency/locks, untrusted external input parsing, destructive DB mutations; `adversarial-report.md <= 50 lines`).
5. **`e2e-blackbox-tester`**: **INVOKE ONLY IF** a runnable web UI (`localhost`/staging URL) exists AND UI/user flows were touched (`blackbox-report.md <= 50 lines`). **ALWAYS SKIP** on pure Python backends/APIs, CLIs, libraries, or data pipelines without web UI.
- **Zero-Bloat Fast-Forward**: If ALL Discovery specialists evaluate to `SKIP` (even on a Tier 2 well-specified backend endpoint), skip State 1 discovery file bloat and go straight to alignment/build.

### Strict Artifact Line Budgets & Target `AGENTS.md` Integration
- **Target `AGENTS.md` (`<= 90 lines`)**: Checked at State 0 / State 5; generated or updated if missing or if stack/commands/conventions changed, linking executable commands (`pytest`, `ruff check .`, `mypy .`, `alembic`), root `DESIGN.md` (if UI exists), and `context/memory/MEMORY.md`.
- **Line Caps**: `PLAN.md <= 50 lines/feature` | `AGENTS.md <= 90` | `prd.md` & `api-spec.md <= 70` | `DESIGN.md <= 110` (`design.md <= 35`) | `adr-NNN-*.md <= 55` | `architecture.md <= 70` | `docs/<feature-name>/test-matrix.md <= 80` | `critic-review.md`, `adversarial-report.md`, `blackbox-report.md <= 50` each.
- **Fail-Honest E2E Transparency**: If `e2e-blackbox-tester` returns `BLOCKED` or `SKIPPED`, the orchestrator MUST explicitly tell the user: *"Browser E2E was NOT executed (`BLOCKED`/`SKIPPED`): <exact reason>"* — NEVER mask it as passed.

---

## 3. Parallel Vertical Slices, Git Branch Governance & Quality Gates

- **Collision Prevention & Scoped Tests**: Verify disjoint `Owned Files` in **Mode A (`Disjoint Files`)** (`Workspace: 'inherit'`). Enforce **Mode B (`Git Worktree Isolation`)** whenever parallel tracks touch shared files (`main.py`, router wiring, DI, `settings.py`) or generate Alembic migration heads. Parallel implementers run ONLY their assigned test file (`pytest tests/unit/test_orders.py`) during loops; full suite runs at State 3.
- **Git Branch Governance & Proactive Scope Drift**: Never write Python code or commit directly to `main`, `master`, `develop`, or `dev`. At State 0, inspect `git symbolic-ref --short HEAD`: auto-branch `git checkout -b feat/<descriptive-slug>` (or `fix/<slug>`) off base branches; prompt via `ask_question` on **Scope Drift** (`feat/<new-slug>`).
- **TDD, Static Analysis & Security**: Every feature/fix requires Red-Green-Refactor unit/integration tests (`exit code 0`), `ruff check .`, `mypy .`, and `bandit -r .` (`APPROVED` by `compliance-verifier`).
- **Zero-Downtime Database Migrations**: Never modify ORM models without an Alembic/Django migration verified via `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` on an isolated DB, using Expand-Contract phases for breaking changes.
- **Deployment Guardrails & Memory (`context/memory/`)**: Never deploy or run production migrations without explicit user permission; never commit plaintext secrets. Silently read `context/memory/MEMORY.md` at `State 0` and update `context/memory/` (`MEMORY.md <= 80-100 lines`, topic pages, `5-8 line` log block in `log/YYYY-MM-DD.md`) **only at `State 5`**.
