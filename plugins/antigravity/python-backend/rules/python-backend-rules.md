---
trigger: always_on
description: Python backend engineering rules enforcing Gitflow branch safety, 6-State Plan-First DAG, 3-Tier Dynamic SDLC, docs/<feature-name>/ feature directory convention, State 1.5 Interactive User Alignment Gate, QA Test Matrix (docs/<feature-name>/test-matrix.md), Alembic migrations, Cross-AI LLM Wiki memory (context/memory/), TDD guarantees, and deployment restrictions.
---

# Python Backend Engineering Rules & Graph Protocol

**Identifier**: `python-backend-rules`

These rules enforce development guidelines, Cross-AI LLM Wiki memory (`context/memory/`), upfront architecture/migration triage, 3-Tier Dynamic SDLC, `docs/<feature-name>/` feature artifact centralization, State 1.5 Interactive User Alignment Gate, parallel vertical slice execution with collision prevention, Git Branch Governance, test-driven guarantees with standardized QA Test Matrix (`docs/<feature-name>/test-matrix.md`), Alembic zero-downtime migrations, and deployment restrictions for all Python backend projects.

---

## 1. 6-State Graph Engineering DAG

Every Python backend feature, bugfix, or refactoring workflow transitions through the 6-state DAG:

```
[STATE 0: MEMORY RESTORE, BRANCH GOVERNANCE & 3-TIER ROUTING GATE]
  ├─► 1. Active Branch Inspection: Auto-branch from base branches (main/dev); detect Scope Drift via ask_question
  ├─► 2. Feature Directory Creation: Derive <feature-name> slug & ensure docs/<feature-name>/ is created
  ├─► 3. Silent LLM Wiki Restore: Read context/memory/MEMORY.md (~500 tokens); drill down on demand
  └─► 4. Author/Update PLAN.md evaluating 3-Tier Dynamic Routing & Discovery Triage
          │
          ├──────────────────────────────┬──────────────────────────────┐
          ▼                              ▼                              ▼
  [Tier 1: Fast-Track]           [Tier 2: Standard]            [Tier 3: Mission-Critical]
  (Skip State 1 Discovery)       (Selective Discovery)         (Full Discovery: API Spec+Arch+ADRs)
  (Skip Alignment Modal)                  │                              │
          │                               ▼                              ▼
          │                      [INTERACTIVE USER ALIGNMENT GATE (STATE 1.5)]
          │                      ├── Modal via ask_question presenting API Spec/Schema/Arch
          │                      └── Mandatory explicit user sign-off before build
          │                               │                              │
          ▼                               ▼                              ▼
[STATE 2: TDD IMPLEMENTATION — PARALLEL VERTICAL SLICES & WORKSPACE ISOLATION]
  ├── Mode A (Default): Disjoint Files (Workspace: 'inherit' with strict non-overlapping Owned Files)
  ├── Mode B: Git Worktree Isolation (Workspace: 'branch' / 'share' for shared main.py, router wiring, or Alembic migrations)
  └── Scoped Test Isolation: Implementers run ONLY assigned test file during loops (pytest <assigned_test>.py)
          │                               │                              │
          ▼                               ▼                              ▼
[STATE 3 & 4: QA VERIFICATION & STATIC/SECURITY AUDIT (PARALLEL FAN-OUT)]
  ├── Tier 1: Scoped test verification (qa-tester -> exit code 0)
  ├── Tier 2: Full test suite in docs/<feature-name>/test-matrix.md (exit code 0) + compliance-verifier (APPROVED)
  └── Tier 3: Adversarial Verification Committee (Parallel Fan-Out):
        ├── qa-tester: Comprehensive docs/<feature-name>/test-matrix.md (exit code 0 empirical proof)
        ├── critic: Code quality, SOLID review, N+1 query sweep (docs/<feature-name>/critic-review.md)
        ├── challenger: Boundary stress, invalid payloads, race conditions (docs/<feature-name>/adversarial-report.md)
        └── compliance-verifier: Ruff, Mypy, Bandit security audit (APPROVED verdict)
          │ (If Fail / Rejected: loop back to State 2 code-implementer — Max 3 iterations via loop-engineering)
          ▼
[STATE 5: SHIP & LLM WIKI MEMORY UPDATE]
  ├─► Mark all tasks completed in PLAN.md
  └─► Persist milestone to context/memory/ (MEMORY.md, architecture.md, conventions.md, log/YYYY-MM-DD.md)
```

---

## 2. 3-Tier Dynamic SDLC Specification & Discovery Triage

Execution workflows scale dynamically according to task scope, surface area, and architectural risk:

| Dimension / Phase | Tier 1: Fast-Track (Low Complexity) | Tier 2: Standard (Medium Complexity) | Tier 3: Mission-Critical (Complex) |
| :--- | :--- | :--- | :--- |
| **Scope & Triggers** | Single-file bugfixes, typos, docs, localized route tweaks (< 2 files). No schema or public contract change. | 2–4 files/modules, new API endpoint, Pydantic model change, or single Alembic/Django migration. | Core auth/permissions, payment/billing flows, database engine migration, breaking OpenAPI contracts, greenfield services. |
| **Discovery (State 1)** | **SKIPPED**: Zero discovery overhead. | **SELECTIVE**: Targeted discovery in `docs/<feature-name>/`: `api-spec.md` and/or `architecture.md`. | **FULL**: Comprehensive discovery in `docs/<feature-name>/`: `api-spec.md`, `architecture.md`, and `adr-*.md`. |
| **Alignment Gate (State 1.5)** | **SKIPPED**: Auto-proceeds directly to State 2 build. | **MANDATORY**: Interactive modal (`ask_question`) presenting API spec and schema summary for approval. | **MANDATORY**: Strict interactive modal (`ask_question`) requiring explicit user sign-off. |
| **Build Mode (State 2)** | 1 `code-implementer` in Mode A (`Workspace: 'inherit'`). | 1..N `code-implementer` in parallel under Mode A (Disjoint Files) or Mode B. | 1..N `code-implementer` in parallel under Mode A or Mode B (Git Worktree Isolation). |
| **QA Verification (State 3)** | Scoped test execution (`pytest <assigned_test>.py` -> exit 0). | Full test suite execution + `docs/<feature-name>/test-matrix.md` with `exit code 0`. | Full test suite execution + standardized QA Test Matrix (`docs/<feature-name>/test-matrix.md`) across test pyramid. |
| **Verification & Committee (State 4)** | Scoped `qa-tester` proof. Bypasses adversarial committee. | Parallel `qa-tester` (`exit code 0`) and `compliance-verifier` (`APPROVED`). | **Adversarial Verification Committee**: `qa-tester`, `critic`, `challenger`, `compliance-verifier`. |
| **Token & Latency Impact** | **70–85% token & latency savings**. | Balanced overhead with rigorous quality verification. | Maximum depth, empirical verification, and zero regression tolerance. |

### Feature Directory Convention (`docs/<feature-name>/`)
All discovery and verification deliverables must be centralized in `docs/<feature-name>/`:
- `docs/<feature-name>/api-spec.md`: OpenAPI specifications, route contracts, Pydantic request/response models.
- `docs/<feature-name>/architecture.md`: Component topology, ERD diagrams, migration strategies.
- `docs/<feature-name>/adr-*.md`: Architectural Decision Records for major design choices.
- `docs/<feature-name>/test-matrix.md`: Standardized QA test matrix with pass/fail counts and exit code 0 evidence.
- `docs/<feature-name>/critic-review.md`: Code smells, SOLID analysis, and maintainability critique.
- `docs/<feature-name>/adversarial-report.md`: Edge-case stress testing, boundary probes, and negative test findings.

### State 1.5: Interactive User Alignment Gate
On Tier 2 and Tier 3 tasks, the orchestrator MUST PAUSE and present a structured summary via `ask_question`:
- Proposed API Endpoints & Request/Response Contracts (`docs/<feature-name>/api-spec.md`)
- Database Schema changes & Alembic migration plan (`docs/<feature-name>/architecture.md`)
- Architecture decisions & ADRs (`docs/<feature-name>/architecture.md`)
- Prompt Question: *"Do you approve the API specification, database migration strategy, and architectural decisions before proceeding to code implementation?"*
- Explicit confirmation must be obtained before delegating to `code-implementer`.

---

## 3. Parallel Vertical Slices & Collision Prevention

- **Collision Prevention Analysis**:
  - Before launching parallel implementers, verify that parallel tracks operate on strictly disjoint files under Mode A.
  - If tracks must modify shared files (e.g., shared `main.py`, router registration, DI containers, `settings.py`) or generate Alembic migrations, enforce **Mode B (Git Worktree Isolation)**.
- **Mode A (`Disjoint Files`) [DEFAULT]**:
  - Parallel implementation tracks operate on non-overlapping files (e.g., `app/routers/orders.py` + `app/services/orders.py` + `tests/unit/test_orders.py` vs. `app/routers/payments.py` + `app/services/payments.py` + `tests/unit/test_payments.py`) with `Workspace: 'inherit'` and zero merge overhead.
- **Mode B (`Git Worktree Isolation`)**:
  - Mandatory whenever parallel tracks generate Alembic/Django migration revisions (preventing revision head collisions) or touch shared configuration files. Merged cleanly before final QA Fan-In.
- **Scoped Test Execution Isolation**:
  - During implementation loops, parallel implementers must run ONLY their assigned test file (`pytest tests/unit/test_orders.py`), NEVER the full test suite in tight loops. Full test suite execution is reserved for State 3 Fan-In by `qa-tester`.

---

## 4. Development & Branch Safety (Git Branch Governance)

- **Git Branch Governance & Auto-Branching**: Never write Python code or commit directly to protected base branches (`main`, `master`, `develop`, `dev`). At State 0, before authoring tasks or modifying Python files, inspect the active branch via `git symbolic-ref --short HEAD`. If on a base branch, automatically provision and switch to a dedicated feature branch using Conventional naming (`git checkout -b feat/<descriptive-slug>` or `fix/<slug>`) and notify the user before any file modifications.
- **Proactive Scope Drift Detection**: When already on an existing feature branch and the user requests orthogonal or unrelated functionality, detect the domain pivot and proactively prompt the user via `ask_question` recommending a dedicated branch (`feat/<new-slug>`). If the user confirms, switch branches; if declined, proceed on the current branch.
- **Feature Isolation**: All work must be conducted on isolated branches prefixed with `feat/` or `fix/` (e.g. `feat/add-oauth-flow`).
- **Production Branch**: The `main` branch represents the Production (prd) environment. Merging to `main` must only occur via PRs after full validation and code reviews.

---

## 5. Testing & Quality Guarantees (TDD & QA Test Matrix)

- **AI-Generated Code Guarantee**: For every piece of business logic or feature code generated by the AI, corresponding Unit and/or Integration tests **must** be created following strict Test-Driven Development (Red-Green-Refactor).
- **QA Test Matrix Artifact (`docs/<feature-name>/test-matrix.md`)**:
  - On Tier 2 and Tier 3 tasks, `qa-tester` must generate `docs/<feature-name>/test-matrix.md` documenting test coverage across the test pyramid (Unit, Integration, API Contract, E2E).
  - Must include empirical execution evidence demonstrating `exit code 0`.
- **Static Analysis & Security Scanning**:
  - Run `ruff check .` to verify formatting and linting standards with zero errors.
  - Run `mypy .` to enforce static type hints across services, repositories, and schemas.
  - Run `bandit -r .` to detect SQL injection, insecure deserialization, or credential leaks.

---

## 6. Database Migration Protocol (Zero-Downtime & Head Safety)

- **Mandatory Migration Files**: Never modify SQLAlchemy/Django ORM models without generating and verifying an Alembic or Django migration script.
- **Isolated Upgrade & Downgrade Testing**: Test both migration upgrade and downgrade scripts against an isolated database before declaring the task completed:
  ```bash
  alembic upgrade head
  alembic downgrade -1
  alembic upgrade head
  ```
- **Zero-Downtime Expand-Contract Pattern**:
  - Phase 1 (Expand): Add nullable columns, new tables, or dual-writing triggers without breaking existing queries.
  - Phase 2 (Contract): Backfill historical data, switch read queries to new structures, and drop old columns/tables in a separate release.
- **Migration Head Collision Prevention**: Use Mode B Git Worktree isolation when parallel tracks touch the database layer to avoid divergent Alembic heads (`alembic heads` must always return exactly one head).

---

## 7. Deployment Restrictions & Security Guardrails

- **Explicit User Approval**: Never deploy code, docker containers, or cloud resources (e.g. Cloud Run, Kubernetes, Firebase) or execute production migrations without explicit, manual permission and review from the user.
- **Pre-deployment Verification**: Before proposing a deploy, verify that the current build is completely clean (all formatters pass, lint has 0 errors, security scan is clean, and all tests pass with `exit code 0`).
- **Secret Management**: Never commit plain-text secrets, API keys, database credentials, or tokens. Use environment variables managed via `.env` or secret managers.

---

## 8. Python Backend Architecture Best Practices

- **Eager Loading & N+1 Prevention**: Prevent N+1 queries. Always prefetch/eager load relationships (`select_related`, `joinedload`, `selectinload`) when querying models with relationships.
- **Dependency Inversion**: Decouple logic across layers. Move complex business logic into Domain Services or Repositories instead of overloading API route controllers:
  ```
  API Router (FastAPI / Django View)
          │ (DTOs / Pydantic Schemas)
          ▼
  Domain Service (Business Logic)
          │ (Entities / Repositories)
          ▼
  Repository / ORM (SQLAlchemy / Django ORM)
  ```
- **Observability**: Implement structured JSON logging with correlation IDs on all routes. Never leak raw stack traces to responses.
- **Cross-AI LLM Wiki Memory (`context/memory/`)**:
  - Silently read `context/memory/MEMORY.md` at `State 0` (~500 tokens).
  - Update `context/memory/` (`MEMORY.md`, `architecture.md`, `conventions.md`, and `log/YYYY-MM-DD.md`) **only at `State 5`** (or on explicit user handoff). Never write checkpoints on intermediate turns.
