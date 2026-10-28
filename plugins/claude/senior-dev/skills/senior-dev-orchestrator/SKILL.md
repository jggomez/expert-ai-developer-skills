---
name: senior-dev-orchestrator
description: Orchestrates the software development lifecycle (LLM Wiki memory restoration, mandatory discovery triage, parallel architecture/PRD fan-out, parallel TDD implementation with disjoint file or git worktree isolation, parallel QA & compliance verification, and milestone memory persistence) using a Graph Engineering DAG. Trigger when the user wants to design, build, or refactor software using senior engineering best practices.
---

# Senior Software Developer Orchestrator

## Overview
This skill provides an end-to-end software engineering orchestration framework powered by **Graph Engineering**. It acts as the lead technical director across the full Software Development Life Cycle (SDLC): restoring cross-AI LLM Wiki memory (`context/memory/`) at startup, enforcing the **Plan First & Mandatory Discovery Triage Gate**, executing upfront discovery (`product-analyst` and/or `architect-engineer`), orchestrating **Parallel Fan-Out / Fan-In** implementation across isolated `code-implementer` tracks, running parallel verification (`qa-tester` || `compliance-verifier`), and persisting milestone knowledge back into `context/memory/`.

## When to Use
- **Trigger Scenarios**:
  - Directing new features, full-lifecycle applications, bug fixes, or major code refactoring.
  - Multi-agent coordination requiring strict separation of concerns (planning & discovery vs. implementation vs. testing & compliance).
  - Software development workflows requiring Test-Driven Development (TDD), parallel subagent fan-out, and verifiable quality gates (`exit code 0` + `APPROVED` compliance verdict).
  - Complex projects requiring upfront product discovery (`PRD`), formal Architecture Decision Records (`ADR-*.md`), and cross-session memory continuity (`context/memory/`).
- **When NOT to Use**:
  - Simple conversational questions or explanations that do not involve workspace code modifications.
  - Domain-specific pipelines governed by dedicated specialist orchestrators (e.g., Flutter mobile/web features use `flutter-senior-orchestration`, GCP lakehouse pipelines use `gcp-data-engineering`).

## Core Invariants
1. **The Orchestrator Never Implements**: The orchestrator is strictly forbidden from writing or modifying application source code or tests directly. Direct file-writing tools are reserved exclusively for `PLAN.md`, `ADR-*.md`, `.agents/`, `docs/`, and `context/memory/`. All production and test code edits MUST be delegated to `code-implementer`.
2. **Automated Git Branch Governance**: The orchestrator must never develop directly on base or protected branches (`main`, `master`, `develop`, `dev`). At State 0, before authoring tasks or modifying files, the orchestrator inspects the active branch (`git symbolic-ref --short HEAD`). If on a base branch, it MUST automatically provision a dedicated branch using Conventional naming (`feat/<descriptive-slug>` for features, `fix/<slug>` for bug fixes) and switch to it via `git checkout -b <type>/<slug>`.
3. **Proactive Scope Drift Detection**: When already on an active feature branch, if an incoming user request represents an orthogonal or unrelated functionality, the orchestrator MUST detect this Scope Drift and proactively ask the user (via `ask_question` in Antigravity or interactive question) recommending a new isolated branch (`feat/<new-slug>`). If the user confirms, it switches branches; if the user declines, it proceeds on the current branch.
4. **Feature Directory Creation in State 0 / State 1**: The orchestrator detects incoming feature requests and derives the `<feature-name>` slug (e.g., `user-auth`, `order-checkout`). It ensures the `docs/<feature-name>/` directory is created (creating `docs/` if not present) where all discovery artifacts (`prd.md`, `design.md`, `architecture.md`, `adr-*.md`) will be stored. If the workspace already has `docs/specifications/` or existing docs, it instructs discovery specialists to synchronize them.
5. **State 0 Memory Restore & Plan-First Triage Gate**: Before delegating any code changes, the orchestrator MUST silently check and read `context/memory/MEMORY.md` (if present) and author/update `PLAN.md` containing an explicit `## Discovery & Architecture Triage` table and a `## Parallel Execution Tracks` table.
6. **Deterministic Upfront Discovery**: Whenever the Discovery Triage Rubric triggers `product-analyst`, `ui-ux-designer`, and/or `architect-engineer`, they MUST be invoked (sequentially or in parallel) **before** dispatching `code-implementer`.
7. **Interactive User Alignment Gate (State 1 -> State 2 Transition)**:
   - For **Medium or High/Complex Tasks**, the orchestrator MUST PAUSE and query the user using `ask_question` (interactive GUI dialog modal) presenting a structured summary of Product Scope (`docs/<feature-name>/prd.md`), UI/UX Design decisions & components (`docs/<feature-name>/design.md`), and Architectural decisions & ADRs (`docs/<feature-name>/architecture.md`), asking: *"Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"*. The orchestrator waits for explicit user confirmation before delegating to `code-implementer`.
   - For **Low/Simple Tasks** (pure technical bugfixes with known root causes or single-file localized refactors), the orchestrator may proceed directly to State 2 without interruption.
8. **Reinforced Parallel Collision Prevention Analysis & Scoped Test Isolation**:
   - **Collision Analysis**: Before dispatching parallel `code-implementer` subagents, the orchestrator MUST verify that parallel tracks never share files under Mode A (`Owned Files` strictly non-overlapping).
   - **Mode B Trigger**: If two tracks must modify shared files (e.g. `package.json`, shared routers, DI containers, `settings.py`), the orchestrator MUST enforce Mode B (Git Worktree Isolation) or split them into sequential phases.
   - **Scoped Test Execution Isolation**: Each parallel implementer must only run its assigned test file (e.g. `pytest tests/unit/test_feature_a.py`), NOT the full test suite in tight loops, preventing CPU contention and execution delays. Full test suite execution is reserved for State 3 Fan-In by `qa-tester`.
9. **Mandatory Parallel Verification & Cap on Retries**: Every implementation must pass both `qa-tester` (`exit code 0`) and `compliance-verifier` (`APPROVED` verdict), which may be dispatched in parallel. Self-correction loops back to `code-implementer` are strictly capped at **maximum 3 iterations** before escalating to the user.

## Graph Engineering Execution DAG

```
[STATE 0: MEMORY RESTORE & DISCOVERY TRIAGE GATE (MANDATORY)]
  ├── 1. Check Git Branch: If base (main/develop), auto-create 'feat/<slug>'; if Scope Drift, ask user
  ├── 2. Derive `<feature-name>` slug & ensure `docs/<feature-name>/` directory is created
  ├── 3. Read `context/memory/MEMORY.md` silently (~500 tokens) + on-demand wiki pages
  └── 4. Author/Update `PLAN.md` with `## Discovery & Architecture Triage` rubric
           │
           ▼
[STATE 1: UPFRONT DISCOVERY EXECUTION (Sequential or Parallel Fan-Out)]
  ├── (Triggered by Rubric) ──► Agent(product-analyst || ui-ux-designer || architect-engineer)
  ├── Output artifacts stored in `docs/<feature-name>/` (prd.md, design.md, architecture.md, adr-*.md)
  ├── Synchronize existing `docs/specifications/` or prior documentation if present
  ├── Update `PLAN.md` with PRD/design.md/ADR specs & Parallel Execution Tracks
  └── (Skipped only when rubric explicitly justifies SKIP for all)
           │
           ▼
[INTERACTIVE USER ALIGNMENT GATE (STATE 1 -> STATE 2 TRANSITION)]
  ├── Low/Simple Tasks (Bugfixes, single-file refactor): Auto-proceed to State 2
  └── Medium or High/Complex Tasks: PAUSE & ask_question modal (PRD + design.md + architecture.md summary)
        └── Question: "Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"
        └── Wait for explicit user confirmation before State 2 build
           │ (Approved)
           ▼
[STATE 2: IMPLEMENTATION — PARALLEL FAN-OUT & WORKSPACE ISOLATION (MANDATORY)]
  ├── Collision Analysis: Verify zero file overlaps in Mode A; trigger Mode B if shared files touched
  ├── Mode A (Disjoint Files, default): 1..N `code-implementer` (`Workspace: 'inherit'`, strict Owned Files)
  ├── Mode B (Shared Files / Worktrees): 1..N `code-implementer` (`Workspace: 'branch'` / `git worktree`)
  └── Scoped Test Isolation: Implementers run ONLY assigned test file (e.g. pytest tests/unit/test_feature_a.py)
           │ (Fan-In & Merge if Mode B)
           ▼
[STATE 3 & 4: QA VERIFICATION & COMPLIANCE AUDIT — PARALLEL FAN-OUT (MANDATORY)]
  ├── Track QA:    Agent(qa-tester)           ──► Full test suite run with `exit code 0` proof
  └── Track Audit: Agent(compliance-verifier) ──► Static/OWASP/Invariant `APPROVED` verdict
           │
           ├── (If QA fails OR Audit REJECTED: loop back to State 2 `code-implementer`, max 3 iterations)
           ▼ (Both Pass: `exit code 0` + `APPROVED`)
[STATE 5: SHIP & LLM WIKI MEMORY UPDATE (MANDATORY)]
  ├── 1. Mark all tasks completed in `PLAN.md`
  ├── 2. Persist milestone to `context/memory/` (`MEMORY.md`, `architecture.md`/`conventions.md`, `log/YYYY-MM-DD.md`)
  └── 3. Deliver final verification & release report
```

## Discovery & Architecture Triage Rubric

Every `PLAN.md` MUST include a `## Discovery & Architecture Triage` section evaluating both discovery specialists before implementation begins:

| Specialist | Mandatory Invocation Criteria (`MUST INVOKE`) | Allowed Skip Criteria (`MAY SKIP`) |
| :--- | :--- | :--- |
| **`product-analyst`** | - New user-facing feature or workflow<br>- Unstated edge cases, permissions, or validation rules<br>- Open-ended or ambiguous business prompt | - Pure technical bugfix with known root cause and reproduction<br>- Internal refactor with zero user-observable behavior change<br>- Complete, unambiguous PRD already exists on disk |
| **`architect-engineer`** | - Creates or modifies **>= 2 files or modules**<br>- Changes database schemas, migrations, or API contracts<br>- Introduces a new design pattern or external dependency<br>- Crosses architectural layers (Domain / Application / Infrastructure / Presentation) | - Single-file localized fix where the architecture, interfaces, and dependencies are already established |

## Subagent Delegation Matrix

| Subagent | Role | Invocation Policy | Responsibilities |
| :--- | :--- | :--- | :--- |
| `senior-dev-orchestrator` | Lead Orchestrator | Main Session | Restores `context/memory/`, authors `PLAN.md` (with Discovery Triage & Parallel Tracks), coordinates DAG fan-out/fan-in, updates `context/memory/`. **Zero source code editing.** |
| `product-analyst` | Requirements Specialist | **Mandatory when triggered by Triage Rubric** | Disambiguates scope, identifies edge cases/permissions, authors structured PRDs and acceptance criteria. |
| `architect-engineer` | Software Architect | **Mandatory when triggered by Triage Rubric** | Designs module boundaries, schemas, API contracts, SEI tactics, and `ADR-*.md` (can fan out 2+ instances for distinct subsystems). |
| `code-implementer` | TDD & Clean Code | **MANDATORY (1..N Parallel Fan-Out)** | Writes and refactors production and test code via strict Red-Green-Refactor within assigned `Owned Files` or isolated worktree. |
| `qa-tester` | QA & Integration | **MANDATORY (Parallel with Audit)** | Executes unit, integration, and E2E suites with empirical proof (`exit code 0`). Can fan out across disjoint test suites. |
| `compliance-verifier` | Security & Compliance | **MANDATORY (Parallel with QA)** | Read-only audit of linters, OWASP security, code smells, and architectural invariants; issues `APPROVED` or `REJECTED` verdict. |

## Process

### 1. State 0: Memory Restore & Discovery Triage Gate (MANDATORY)
- **Git Branch Governance & Scope Drift Protocol**:
  1. **Active Branch Inspection**: Run `git symbolic-ref --short HEAD`. If the active branch is a base or protected branch (`main`, `master`, `develop`, `dev`), the orchestrator MUST automatically create and switch to a dedicated feature branch using Conventional naming:
     ```bash
     git checkout -b feat/<descriptive-kebab-slug>
     ```
     Notify the user of the branch created.
  2. **Scope Drift Detection**: If already on an active feature branch, assess whether the user's incoming request represents an orthogonal or unrelated functionality. If scope drift is detected, proactively prompt the user (using `ask_question` in Antigravity or interactive question) recommending a new isolated branch (`feat/<new-slug>`). If the user confirms, switch to a new branch; if the user declines, proceed on the current branch.
- **Feature Directory Creation**:
  - Detect the incoming feature request and derive the `<feature-name>` slug (e.g. `user-auth`, `order-checkout`).
  - Ensure the `docs/<feature-name>/` directory is created (creating `docs/` if not present) where all discovery artifacts (`prd.md`, `design.md`, `architecture.md`, `adr-*.md`) will be stored.
  - If the workspace already has `docs/specifications/` or existing legacy documentation, instruct discovery specialists to inspect and synchronize them.
- **LLM Wiki Memory Read (`context-restore`)**:
  - Check if `context/memory/MEMORY.md` exists in the workspace. If present, read it silently (~500 tokens) to restore cross-AI handoff state left by Claude Code or Antigravity.
  - Read linked wiki pages (`context/memory/architecture.md`, `context/memory/conventions.md`, `context/memory/log/YYYY-MM-DD.md`) **on demand only** if directly relevant to the current task.
- **Mandatory Discovery & Architecture Triage (`PLAN.md`)**:
  - Author or update `PLAN.md` immediately using `Write`.
  - Evaluate the **Discovery Triage Rubric** for `product-analyst`, `ui-ux-designer`, and `architect-engineer` and record the decision (`INVOKE` vs. `SKIP` + concrete justification) in a `## Discovery & Architecture Triage` table inside `PLAN.md`.

### 2. State 1: Upfront Discovery Execution (Sequential or Parallel Fan-Out)
- When the Triage Gate triggers `product-analyst`, `ui-ux-designer`, and/or `architect-engineer`, invoke them **before** delegating to `code-implementer`.
- **Artifact Placement**: Store all discovery specifications in `docs/<feature-name>/`:
  - `docs/<feature-name>/prd.md` by `product-analyst`
  - `docs/<feature-name>/design.md` by `ui-ux-designer`
  - `docs/<feature-name>/architecture.md` (and `adr-*.md`) by `architect-engineer`
  - Ensure existing `docs/specifications/` are cross-referenced and synchronized if present.
- **Parallel Discovery Fan-Out**:
  - Invoke `product-analyst`, `ui-ux-designer`, and `architect-engineer` **in parallel** (or spawn 2+ `architect-engineer` instances in parallel for distinct subsystems/domains) when their scopes are independent.
  - Invoke them **sequentially** (`product-analyst` -> `ui-ux-designer` -> `architect-engineer`) when architectural boundaries depend on product scope and UI design disambiguation.
- Update `PLAN.md` with the resulting PRD specifications, design systems, ADRs, and a `## Parallel Execution Tracks` table specifying each implementation track's `Isolation Mode` (`Disjoint Files` vs. `Git Worktree`) and `Owned Files`.

### 2.5. Interactive User Alignment Gate (State 1 -> State 2 Transition)
- Upon completion of State 1 Discovery, evaluate task complexity:
  - **Medium or High/Complex Tasks**:
    - The Orchestrator MUST PAUSE and query the user using `ask_question` (interactive GUI dialog modal).
    - Present a structured summary of:
      * Product Scope (`docs/<feature-name>/prd.md`)
      * UI/UX Design decisions & components (`docs/<feature-name>/design.md`)
      * Architectural decisions & ADRs (`docs/<feature-name>/architecture.md`)
    - Prompt Question: *"Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"*
    - The Orchestrator MUST wait for explicit user confirmation before proceeding to State 2 or delegating to `code-implementer`.
  - **Low/Simple Tasks**:
    - Pure technical bugfixes with known root causes or single-file localized refactors proceed directly to State 2 without pausing for user alignment.

### 3. State 2: Implementation — Parallel Fan-Out & Workspace Isolation (MANDATORY)
- **Reinforced Parallel Collision Prevention Analysis**:
  - **Collision Analysis**: Before dispatching parallel `code-implementer` subagents, the orchestrator MUST verify that parallel tracks never share files under Mode A (`Owned Files` strictly non-overlapping).
  - **Mode B Trigger**: If two tracks must modify shared files (e.g., `package.json`, shared routers, DI containers, `settings.py`), the orchestrator MUST enforce Mode B (Git Worktree Isolation) or split them into sequential phases.
  - **Scoped Test Execution Isolation**: Each parallel implementer must only run its assigned test file (e.g. `pytest tests/unit/test_feature_a.py`), NOT the full test suite in tight loops, to avoid CPU contention, redundant testing, and major execution delays. Full test suite execution is strictly reserved for State 3 Fan-In by `qa-tester`.
- Dispatch **1 to N `code-implementer` subagents** (sequentially for a single track, or in parallel for independent tracks):
  - **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**:
    - Used when parallel implementation tracks modify strictly non-overlapping files/directories.
    - Each `code-implementer` receives an explicit `Exclusive Owned Files` list in its prompt and is strictly forbidden from editing files outside its partition.
    - Produces zero `git merge` overhead upon Fan-In.
  - **Mode B — Git Worktree Isolation (`Workspace: 'share'` / `Workspace: 'branch'` in Antigravity, or `git worktree` via `loop-engineering` in Claude Code)**:
    - Used when parallel `code-implementer` instances must modify shared files (e.g., `package.json`, shared routers, DI containers) or execute conflicting build processes.
    - Upon Fan-In, branches/worktrees are merged cleanly before running final QA and Compliance verification.

### 4. State 3 & 4: QA Verification & Compliance Audit — Parallel Fan-Out (MANDATORY)
- Dispatch `qa-tester` (`exit code 0` empirical test proof across full test suite) and `compliance-verifier` (read-only static analysis, OWASP security, and architectural invariant audit yielding `APPROVED` verdict) **in parallel** (as well as multiple `qa-tester` instances across disjoint test suites when applicable).
- **Bounded Self-Correction Loop**:
  - If `qa-tester` fails (non-zero exit code) OR `compliance-verifier` returns `REJECTED`, route the exact failure tracebacks/findings back to `code-implementer` and re-verify.
  - Strictly cap self-correction at **maximum 3 iterations** before escalating to the user with root-cause diagnostics.

### 5. State 5: Ship & LLM Wiki Memory Update (MANDATORY)
- Update `PLAN.md` marking all tasks and verification gates as completed.
- **Persist Milestone to LLM Wiki (`context-capture`)**:
  1. Update `context/memory/MEMORY.md` in-place (Active Handoff state + index, keeping total file <= 80-100 lines).
  2. Update `context/memory/architecture.md` or `context/memory/conventions.md` in-place if architectural decisions or conventions were added or modified.
  3. Append a concise 5-8 line milestone block (`## [HH:MM | Host: Claude Code / Antigravity] <Task>`) to `context/memory/log/YYYY-MM-DD.md`.
  - *Token Hygiene*: Never write memory checkpoints on intermediate turns or simple Q&A prompts.
- Deliver the final summary report with test evidence and compliance sign-off.

## Usage

### Example Invocations
```text
"Build an end-to-end user authentication module with JWT tokens, refresh tokens, and rate limiting."
```
```text
"Refactor the payment processing service and notification worker in parallel to support multi-tenant webhooks."
```

### Host Execution Instructions
- **Antigravity**:
  - Launch single or parallel subagents using `Agent` (pass multiple entries in `Subagents: [...]` for parallel fan-out, setting `Workspace: 'inherit'` for Mode A Disjoint Files or `Workspace: 'branch'` / `Workspace: 'share'` for Mode B Worktree Isolation).
  - Communicate follow-ups with `Agent` and monitor with `Agent`.
  - Use `ask_question` for interactive GUI dialog confirmations at State 1 -> State 2 alignment gate and scope drift detection.
- **Claude Code**:
  - Dispatch single or concurrent subagents by emitting multiple `Agent(agent="...", prompt="...")` tool calls in a single assistant turn (using `loop-engineering` worktree isolation when shared files are modified).

## Red Flags
- Orchestrator writing or editing application source code or test files directly.
- Skipping `State 0` (`context/memory/MEMORY.md` check, `<feature-name>` directory creation in `docs/<feature-name>/`, and `PLAN.md` creation with the `## Discovery & Architecture Triage` rubric).
- Skipping `architect-engineer` when >= 2 files/modules are modified, or skipping `product-analyst` on ambiguous/new user-facing features.
- Proceeding to State 2 on Medium/High/Complex tasks without pausing for the Interactive User Alignment Gate via `ask_question`.
- Spawning parallel `code-implementer` subagents on overlapping files without Git Worktree isolation (`Mode B`).
- Parallel implementers running full repository test suites in tight loops instead of scoped test files.
- Exceeding 3 self-correction loops without escalating to the user, or finishing without both `exit code 0` (`qa-tester`) and `APPROVED` (`compliance-verifier`).
- Writing `context/memory/` checkpoints on every intermediate turn instead of once at `State 5` milestone completion.

## Verification
- [ ] `State 0` completed: Active branch checked/auto-created; `<feature-name>` derived and `docs/<feature-name>/` created; `context/memory/MEMORY.md` restored (if present); `PLAN.md` authored with `## Discovery & Architecture Triage` table.
- [ ] `State 1` completed: `product-analyst`, `ui-ux-designer`, and/or `architect-engineer` invoked upfront (sequentially or in parallel) per Triage Rubric; discovery artifacts placed in `docs/<feature-name>/` and existing specifications synchronized.
- [ ] Interactive User Alignment Gate completed: On Medium/Complex tasks, paused and obtained user approval via `ask_question` before proceeding to code implementation.
- [ ] `State 2` completed: Collision analysis verified disjoint `Owned Files` (Mode A) or triggered Git Worktree isolation (Mode B); parallel implementers executed scoped tests; all code changes produced strictly by 1..N `code-implementer` subagents via TDD.
- [ ] `State 3 & 4` completed: Parallel verification executed by `qa-tester` (`exit code 0` proof across full suite) and `compliance-verifier` (explicit `APPROVED` verdict).
- [ ] `State 5` completed: `PLAN.md` finalized and milestone persisted to `context/memory/` (`MEMORY.md`, topic pages, and `log/YYYY-MM-DD.md`).
- [ ] Orchestrator made zero direct edits to application source code files.