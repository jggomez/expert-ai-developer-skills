---
name: senior-dev-orchestrator
description: Orchestrates the software development lifecycle (LLM Wiki memory restoration, 3-tier dynamic routing, mandatory discovery triage, parallel architecture/PRD fan-out, parallel TDD implementation with disjoint file or git worktree isolation, adversarial verification committee, and milestone memory persistence) using a Graph Engineering DAG. Trigger when the user wants to design, build, or refactor software using senior engineering best practices.
---

# Senior Software Developer Orchestrator

## Overview
This skill provides an end-to-end software engineering orchestration framework powered by **Graph Engineering**. It acts as the lead technical director across the full Software Development Life Cycle (SDLC): restoring cross-AI LLM Wiki memory (`context/memory/`) at startup, evaluating the **3-Tier Dynamic Routing Rubric** and **Mandatory Discovery Triage Gate**, executing upfront discovery (`product-analyst`, `ui-ux-designer`, and/or `architect-engineer`), orchestrating **Parallel Fan-Out / Fan-In** implementation across isolated `code-implementer` tracks, running rigorous verification (fast-track scoped QA, standard compliance, or the full **Adversarial Verification Committee**: `qa-tester`, `critic`, `challenger`, `e2e-blackbox-tester`, `compliance-verifier`), and persisting milestone knowledge back into `context/memory/`.

## When to Use
- **Trigger Scenarios**:
  - Directing new features, full-lifecycle applications, bug fixes, or major code refactoring.
  - Multi-agent coordination requiring strict separation of concerns (planning & discovery vs. implementation vs. testing & compliance).
  - Software development workflows requiring Test-Driven Development (TDD), 3-tier dynamic routing, parallel subagent fan-out, and verifiable quality gates (`exit code 0` + `APPROVED` compliance verdict).
  - Mission-critical or complex projects requiring upfront product discovery (`PRD`), UI design systems (`design.md`), formal Architecture Decision Records (`ADR-*.md`), adversarial verification, and cross-session memory continuity (`context/memory/`).
- **When NOT to Use**:
  - Simple conversational questions or explanations that do not involve workspace code modifications.
  - Domain-specific pipelines governed by dedicated specialist orchestrators (e.g., Flutter mobile/web features use `flutter-senior-orchestration`, GCP lakehouse pipelines use `gcp-data-engineering`).

## Core Invariants
1. **The Orchestrator Never Implements**: The orchestrator is strictly forbidden from writing or modifying application source code or tests directly. Direct file-writing tools are reserved exclusively for `PLAN.md`, `ADR-*.md`, `.agents/`, `docs/`, and `context/memory/`. All production and test code edits MUST be delegated to `code-implementer`.
2. **Automated Git Branch Governance**: The orchestrator must never develop directly on base or protected branches (`main`, `master`, `develop`, `dev`). At State 0, before authoring tasks or modifying files, the orchestrator inspects the active branch (`git symbolic-ref --short HEAD`). If on a base branch, it MUST automatically provision a dedicated branch using Conventional naming (`feat/<descriptive-slug>` for features, `fix/<slug>` for bug fixes) and switch to it via `git checkout -b <type>/<slug>`.
3. **Proactive Scope Drift Detection**: When already on an active feature branch, if an incoming user request represents an orthogonal or unrelated functionality, the orchestrator MUST detect this Scope Drift and proactively ask the user (via `ask_question` in Antigravity or interactive question) recommending a new isolated branch (`feat/<new-slug>`). If the user confirms, it switches branches; if the user declines, it proceeds on the current branch.
4. **Feature Directory Creation in State 0 / State 1**: The orchestrator detects incoming feature requests and derives the `<feature-name>` slug (e.g., `user-auth`, `order-checkout`). It ensures the `docs/<feature-name>/` directory is created (creating `docs/` if not present) where all discovery artifacts (`prd.md`, `design.md`, `architecture.md`, `adr-*.md`) and verification artifacts (`test-matrix.md`, `critic-review.md`, `adversarial-report.md`, `blackbox-report.md`) will be stored. If the workspace already has `docs/specifications/` or existing docs, it instructs discovery specialists to synchronize them.
5. **State 0 Memory Restore & 3-Tier Dynamic Routing**: Before delegating any code changes, the orchestrator MUST silently check and read `context/memory/MEMORY.md` (if present) and author/update `PLAN.md` containing an explicit `## 3-Tier Dynamic Routing & Discovery Triage` table and a `## Parallel Execution Tracks` table.
6. **Deterministic Upfront Discovery**: Whenever the Discovery Triage Rubric triggers `product-analyst`, `ui-ux-designer`, and/or `architect-engineer`, they MUST be invoked (sequentially or in parallel) **before** dispatching `code-implementer`.
7. **Interactive User Alignment Gate (State 1 -> State 2 Transition)**:
   - For **Tier 2 (Standard)** and **Tier 3 (Mission-Critical / Complex)** tasks, the orchestrator MUST PAUSE and query the user using `ask_question` (interactive GUI dialog modal) presenting a structured summary of Product Scope (`docs/<feature-name>/prd.md`), UI/UX Design decisions & components (`docs/<feature-name>/design.md`), and Architectural decisions & ADRs (`docs/<feature-name>/architecture.md`), asking: *"Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"*. The orchestrator waits for explicit user confirmation before delegating to `code-implementer`.
   - For **Tier 1 (Fast-Track)** tasks (pure technical bugfixes with known root causes or single-file localized refactors), the orchestrator may proceed directly to State 2 without interruption.
8. **Reinforced Parallel Collision Prevention Analysis & Scoped Test Isolation**:
   - **Collision Analysis**: Before dispatching parallel `code-implementer` subagents, the orchestrator MUST verify that parallel tracks never share files under Mode A (`Owned Files` strictly non-overlapping).
   - **Mode B Trigger**: If two tracks must modify shared files (e.g. `package.json`, shared routers, DI containers, `settings.py`), the orchestrator MUST enforce Mode B (Git Worktree Isolation) or split them into sequential phases.
   - **Scoped Test Execution Isolation**: Each parallel implementer must only run its assigned test file (e.g. `pytest tests/unit/test_feature_a.py`), NOT the full test suite in tight loops, preventing CPU contention and execution delays. Full test suite execution is reserved for State 3 Fan-In by `qa-tester`.
9. **Tiered Verification & Bounded Self-Correction**:
   - Tier 1 requires scoped test pass with `exit code 0`.
   - Tier 2 requires full test suite execution documented in `docs/<feature-name>/test-matrix.md` with `exit code 0` plus `compliance-verifier` `APPROVED` verdict.
   - Tier 3 requires parallel dispatch of the full **Adversarial Verification Committee**: `qa-tester` (test suite pass + `docs/<feature-name>/test-matrix.md`), `critic` (`docs/<feature-name>/critic-review.md`), `challenger` (`docs/<feature-name>/adversarial-report.md`), `e2e-blackbox-tester` (`docs/<feature-name>/blackbox-report.md`), and `compliance-verifier` (`APPROVED` verdict).
   - Self-correction loops back to `code-implementer` are strictly capped at **maximum 3 iterations** before escalating to the user.

## Graph Engineering Execution DAG

```
[STATE 0: MEMORY RESTORE & 3-TIER DYNAMIC ROUTING GATE (MANDATORY)]
  ├── 1. Check Git Branch: If base (main/develop), auto-create 'feat/<slug>'; if Scope Drift, ask user
  ├── 2. Derive `<feature-name>` slug & ensure `docs/<feature-name>/` directory is created
  ├── 3. Read `context/memory/MEMORY.md` silently (~500 tokens) + on-demand wiki pages
  └── 4. Author/Update `PLAN.md` evaluating 3-Tier Routing & Discovery Triage
           │
           ├───► [TIER 1: FAST-TRACK (Single-file bugfix / internal refactor)]
           │        ├── Skip discovery (product-analyst / ui-ux-designer / architect-engineer)
           │        ├── Skip alignment modal (Auto-proceed)
           │        ├── 1 code-implementer (Mode A: 'inherit')
           │        └── Fast scoped QA (qa-tester on assigned test file -> exit 0) ──► [STATE 5]
           │
           ├───► [TIER 2: STANDARD (Multi-file feature / API contract / schema change)]
           │        ├── State 1: Selective discovery (product-analyst || ui-ux-designer || architect-engineer)
           │        ├── Interactive User Alignment Gate: PAUSE & ask_question modal
           │        ├── State 2: Parallel code-implementer tracks (Mode A or Mode B)
           │        └── State 3 & 4: Parallel QA (docs/<feature-name>/test-matrix.md) + compliance-verifier ──► [STATE 5]
           │
           └───► [TIER 3: MISSION-CRITICAL / COMPLEX (Core architecture / auth / payments / greenfield)]
                    ├── State 1: Full discovery in docs/<feature-name>/ (prd.md, design.md, architecture.md, adrs)
                    ├── Interactive User Alignment Gate: PAUSE & ask_question modal (mandatory sign-off)
                    ├── State 2: Parallel code-implementer tracks with strict workspace isolation
                    └── State 3 & 4: ADVERSARIAL VERIFICATION COMMITTEE (Parallel Fan-Out):
                             ├── qa-tester (exit code 0 proof + docs/<feature-name>/test-matrix.md)
                             ├── critic (docs/<feature-name>/critic-review.md)
                             ├── challenger (docs/<feature-name>/adversarial-report.md)
                             ├── e2e-blackbox-tester (docs/<feature-name>/blackbox-report.md)
                             └── compliance-verifier (APPROVED verdict)
                                      │ (If defects found: loop back to State 2, max 3 iterations)
                                      ▼ (All 5 pass & approve)
[STATE 5: SHIP & LLM WIKI MEMORY UPDATE (MANDATORY)]
  ├── 1. Mark all tasks completed in `PLAN.md`
  ├── 2. Persist milestone to `context/memory/` (`MEMORY.md`, `architecture.md`/`conventions.md`, `log/YYYY-MM-DD.md`)
  └── 3. Deliver final verification & release report
```

## 3-Tier Dynamic Routing Rubric

At State 0, every task is classified into one of three execution tiers in `PLAN.md`:

| Tier | Characteristics & Trigger Criteria | Discovery & Alignment Gate | Implementation & Verification Protocol |
| :--- | :--- | :--- | :--- |
| **Tier 1: Fast-Track** | - Single-file localized bugfix with known root cause<br>- Pure internal refactor with zero behavior change<br>- Minor doc/config tweak (< 2 files affected)<br>- Architecture, interfaces, and dependencies already established | - **Discovery**: SKIP all discovery specialists (`product-analyst`, `ui-ux-designer`, `architect-engineer`).<br>- **Alignment Gate**: SKIP interactive modal (auto-proceed). | - **Implementation**: 1 `code-implementer` (`Workspace: 'inherit'`).<br>- **Verification**: Fast scoped QA (`qa-tester` runs assigned test file -> `exit code 0`). |
| **Tier 2: Standard** | - Multi-file feature or refactoring (>= 2 files/modules)<br>- Changes to database schemas, migrations, or API contracts<br>- Addition of new UI screens/views or frontend components<br>- Crosses architectural layers (Domain / Application / Infrastructure / Presentation) | - **Discovery**: Selective upfront discovery (`product-analyst`, `ui-ux-designer`, and/or `architect-engineer` per triage criteria). Store in `docs/<feature-name>/`.<br>- **Alignment Gate**: PAUSE & `ask_question` modal for user approval. | - **Implementation**: 1..N parallel `code-implementer` subagents (Mode A Disjoint Files or Mode B Git Worktree).<br>- **Verification**: Full test suite execution documented in `docs/<feature-name>/test-matrix.md` (`exit code 0`) + `compliance-verifier` (`APPROVED` verdict). |
| **Tier 3: Mission-Critical / Complex** | - Greenfield application or major subsystem from scratch<br>- Core architectural overhaul or breaking API migration<br>- Security, authentication, authorization, cryptography, or session boundaries<br>- Financial, billing, payment processing, or compliance-regulated workflows<br>- High-concurrency, distributed consensus, or mission-critical data integrity pipelines | - **Discovery**: Full discovery suite in `docs/<feature-name>/` (`prd.md`, `design.md`, `architecture.md`, `adr-*.md`).<br>- **Alignment Gate**: Mandatory PAUSE & `ask_question` modal requiring explicit user sign-off. | - **Implementation**: Parallel `code-implementer` tracks with strict Collision Analysis and workspace isolation.<br>- **Verification**: Parallel dispatch of the full **Adversarial Verification Committee**:<br>  1. `qa-tester` (`docs/<feature-name>/test-matrix.md` + `exit code 0`)<br>  2. `critic` (`docs/<feature-name>/critic-review.md`)<br>  3. `challenger` (`docs/<feature-name>/adversarial-report.md`)<br>  4. `e2e-blackbox-tester` (`docs/<feature-name>/blackbox-report.md`)<br>  5. `compliance-verifier` (`APPROVED` verdict). |

## Discovery & Architecture Triage Rubric

Every `PLAN.md` MUST include a `## Discovery & Architecture Triage` section evaluating discovery specialists before implementation begins:

| Specialist | Mandatory Invocation Criteria (`MUST INVOKE`) | Allowed Skip Criteria (`MAY SKIP`) |
| :--- | :--- | :--- |
| **`product-analyst`** | - New user-facing feature or workflow<br>- Unstated edge cases, permissions, or validation rules<br>- Open-ended or ambiguous business prompt | - Pure technical bugfix with known root cause and reproduction<br>- Internal refactor with zero user-observable behavior change<br>- Complete, unambiguous PRD already exists on disk |
| **`ui-ux-designer`** | - Greenfield application with UI, or new frontend screens/views/widgets<br>- Modifications to styling, theming, layout, responsiveness, or accessibility<br>- Workspace lacks a standard `design.md` | - Pure backend services, APIs, data pipelines, CLI tools, infrastructure<br>- Non-visual bugfixes or internal utility refactoring |
| **`architect-engineer`** | - Creates or modifies **>= 2 files or modules**<br>- Changes database schemas, migrations, or API contracts<br>- Introduces a new design pattern or external dependency<br>- Crosses architectural layers (Domain / Application / Infrastructure / Presentation) | - Single-file localized fix where the architecture, interfaces, and dependencies are already established |

## Subagent Delegation Matrix

| Subagent | Role | Invocation Policy | Responsibilities & Standard Artifacts |
| :--- | :--- | :--- | :--- |
| `senior-dev-orchestrator` | Lead Orchestrator | Main Session | Restores `context/memory/`, authors `PLAN.md` (with 3-Tier Routing, Discovery Triage & Parallel Tracks), coordinates DAG fan-out/fan-in, updates `context/memory/`. **Zero source code editing.** |
| `product-analyst` | Requirements Specialist | **Mandatory for Tier 2/3 when triggered** | Disambiguates scope, identifies edge cases/permissions, authors structured PRDs and acceptance criteria in `docs/<feature-name>/prd.md`. |
| `ui-ux-designer` | Design Systems Specialist | **Mandatory for UI features in Tier 2/3** | Establishes design tokens, component hierarchies, responsive layouts, and accessibility guidelines in `docs/<feature-name>/design.md`. |
| `architect-engineer` | Software Architect | **Mandatory for multi-file/cross-layer in Tier 2/3** | Designs module boundaries, schemas, API contracts, SEI tactics, and `ADR-*.md` in `docs/<feature-name>/architecture.md`. |
| `code-implementer` | TDD & Clean Code | **MANDATORY (1..N Parallel Fan-Out)** | Writes and refactors production and test code via strict Red-Green-Refactor within assigned `Owned Files` (Mode A) or isolated worktree (Mode B). |
| `qa-tester` | QA & Test Matrix | **MANDATORY across all tiers** | Executes scoped tests (Tier 1) or full suites with test matrix in `docs/<feature-name>/test-matrix.md` (`exit code 0` empirical proof). |
| `critic` | Architecture & Code Critic | **Mandatory for Tier 3 (Adversarial Committee)** | Independent code & architecture quality critique, identifying maintainability smells, anti-patterns, and structural risks in `docs/<feature-name>/critic-review.md`. |
| `challenger` | Adversarial Red-Team | **Mandatory for Tier 3 (Adversarial Committee)** | Injects hostile inputs, attacks state invariants, probes race conditions, and stress-tests boundary failures in `docs/<feature-name>/adversarial-report.md`. |
| `e2e-blackbox-tester` | Blackbox Scenario Tester | **Mandatory for Tier 3 (Adversarial Committee)** | Validates end-to-end user workflows and API contracts as a sealed black box without implementation bias in `docs/<feature-name>/blackbox-report.md`. |
| `compliance-verifier` | Security & Compliance | **MANDATORY for Tier 2 & Tier 3** | Read-only audit of linters, OWASP security, code smells, and architectural invariants; issues `APPROVED` or `REJECTED` verdict. |

## Process

### 1. State 0: Memory Restore & 3-Tier Dynamic Routing Gate (MANDATORY)
- **Git Branch Governance & Scope Drift Protocol**:
  1. **Active Branch Inspection**: Run `git symbolic-ref --short HEAD`. If the active branch is a base or protected branch (`main`, `master`, `develop`, `dev`), the orchestrator MUST automatically create and switch to a dedicated feature branch using Conventional naming:
     ```bash
     git checkout -b feat/<descriptive-kebab-slug>
     ```
     Notify the user of the branch created.
  2. **Scope Drift Detection**: If already on an active feature branch, assess whether the user's incoming request represents an orthogonal or unrelated functionality. If scope drift is detected, proactively prompt the user (using `ask_question` in Antigravity or interactive question) recommending a new isolated branch (`feat/<new-slug>`). If the user confirms, switch to a new branch; if the user declines, proceed on the current branch.
- **Feature Directory Creation**:
  - Detect the incoming feature request and derive the `<feature-name>` slug (e.g. `user-auth`, `order-checkout`).
  - Ensure the `docs/<feature-name>/` directory is created (creating `docs/` if not present) where all discovery artifacts (`prd.md`, `design.md`, `architecture.md`, `adr-*.md`) and verification artifacts (`test-matrix.md`, `critic-review.md`, `adversarial-report.md`, `blackbox-report.md`) will be stored.
  - If the workspace already has `docs/specifications/` or existing legacy documentation, instruct discovery specialists to inspect and synchronize them.
- **LLM Wiki Memory Read (`context-restore`)**:
  - Check if `context/memory/MEMORY.md` exists in the workspace. If present, read it silently (~500 tokens) to restore cross-AI handoff state left by Claude Code or Antigravity.
  - Read linked wiki pages (`context/memory/architecture.md`, `context/memory/conventions.md`, `context/memory/log/YYYY-MM-DD.md`) **on demand only** if directly relevant to the current task.
- **Plan First & 3-Tier Dynamic Routing Evaluation (`PLAN.md`)**:
  - Author or update `PLAN.md` immediately using `write_to_file`.
  - Classify the task into **Tier 1 (Fast-Track)**, **Tier 2 (Standard)**, or **Tier 3 (Mission-Critical / Complex)** based on the 3-Tier Dynamic Routing Rubric.
  - For Tier 2 and Tier 3, evaluate the **Discovery Triage Rubric** for `product-analyst`, `ui-ux-designer`, and `architect-engineer`, recording the decision (`INVOKE` vs. `SKIP` + concrete justification) in `PLAN.md`.

### 2. State 1: Upfront Discovery Execution (Sequential or Parallel Fan-Out)
- **Tier 1**: Skip State 1 completely.
- **Tier 2 & Tier 3**: When the Triage Gate triggers `product-analyst`, `ui-ux-designer`, and/or `architect-engineer`, invoke them **before** delegating to `code-implementer`.
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
- **Tier 1**: Auto-proceed directly to State 2 without interruption.
- **Tier 2 & Tier 3**:
  - The Orchestrator MUST PAUSE and query the user using `ask_question` (interactive GUI dialog modal).
  - Present a structured summary of:
    * Product Scope (`docs/<feature-name>/prd.md`)
    * UI/UX Design decisions & components (`docs/<feature-name>/design.md`)
    * Architectural decisions & ADRs (`docs/<feature-name>/architecture.md`)
  - Prompt Question: *"Do you approve the product scope, UI design, and architectural decisions before proceeding to code implementation?"*
  - The Orchestrator MUST wait for explicit user confirmation before proceeding to State 2 or delegating to `code-implementer`.

### 3. State 2: Implementation — Parallel Fan-Out & Workspace Isolation (MANDATORY)
- **Reinforced Parallel Collision Prevention Analysis**:
  - **Collision Analysis**: Before dispatching parallel `code-implementer` subagents, the orchestrator MUST verify that parallel tracks never share files under Mode A (`Owned Files` strictly non-overlapping).
  - **Mode B Trigger**: If two tracks must modify shared files (e.g., `package.json`, shared routers, DI containers, `settings.py`), the orchestrator MUST enforce Mode B (Git Worktree Isolation) or split them into sequential phases.
  - **Scoped Test Execution Isolation**: Each parallel implementer must only run its assigned test file (e.g. `pytest tests/unit/test_feature_a.py`), NOT the full test suite in tight loops, to avoid CPU contention, redundant testing, and major execution delays. Full test suite execution is strictly reserved for State 3 Fan-In by `qa-tester`.
- Dispatch **`code-implementer` subagents** (single instance for Tier 1, 1 to N parallel tracks for Tier 2/3):
  - **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**:
    - Used when parallel implementation tracks modify strictly non-overlapping files/directories.
    - Each `code-implementer` receives an explicit `Exclusive Owned Files` list in its prompt and is strictly forbidden from editing files outside its partition.
    - Produces zero `git merge` overhead upon Fan-In.
  - **Mode B — Git Worktree Isolation (`Workspace: 'share'` / `Workspace: 'branch'` in Antigravity, or `git worktree` via `loop-engineering` in Claude Code)**:
    - Used when parallel `code-implementer` instances must modify shared files (e.g., `package.json`, shared routers, DI containers) or execute conflicting build processes.
    - Upon Fan-In, branches/worktrees are merged cleanly before running verification.

### 4. State 3 & 4: QA Verification & Adversarial Verification Committee — Parallel Fan-Out
Verification rigor is determined by the task tier:
- **Tier 1 (Fast-Track)**:
  - Dispatch `qa-tester` to execute the scoped test suite for the modified component (`exit code 0` empirical proof).
- **Tier 2 (Standard)**:
  - Dispatch `qa-tester` and `compliance-verifier` in parallel.
  - `qa-tester` executes the full test suite and documents the coverage and pass results in `docs/<feature-name>/test-matrix.md` with `exit code 0` empirical proof.
  - `compliance-verifier` executes read-only static analysis, OWASP security checks, and architectural invariant checks, issuing an `APPROVED` or `REJECTED` verdict.
- **Tier 3 (Mission-Critical / Complex — Adversarial Verification Committee)**:
  - Dispatch the full **Adversarial Verification Committee** in parallel:
    1. `qa-tester`: Full test suite run, regression testing, and generation of `docs/<feature-name>/test-matrix.md` proving 100% critical path coverage with `exit code 0`.
    2. `critic`: Independent architectural and clean code audit; probes for code smells, maintainability traps, hidden technical debt, and missing abstractions, producing `docs/<feature-name>/critic-review.md`.
    3. `challenger`: Adversarial red-team probe; attacks edge-case assumptions, simulates race conditions, boundary overflows, and invariant violations, producing `docs/<feature-name>/adversarial-report.md`.
    4. `e2e-blackbox-tester`: End-to-end blackbox workflow verification; validates user-facing journeys and API contracts as an external caller without internal structural assumptions, producing `docs/<feature-name>/blackbox-report.md`.
    5. `compliance-verifier`: Read-only audit of linters, security (OWASP Top 10), and architectural invariants, issuing `APPROVED` or `REJECTED` verdict.
- **Bounded Self-Correction Loop**:
  - If any verification member fails or reports a defect (`qa-tester` non-zero exit code, `critic`/`challenger`/`e2e-blackbox-tester` defect findings, or `compliance-verifier` `REJECTED`), route the exact failure tracebacks/findings back to `code-implementer` and re-verify.
  - Strictly cap self-correction at **maximum 3 iterations** before escalating to the user with root-cause diagnostics.

### 5. State 5: Ship & LLM Wiki Memory Update (MANDATORY)
- Update `PLAN.md` marking all tasks and verification gates as completed.
- **Persist Milestone to LLM Wiki (`context-capture`)**:
  1. Update `context/memory/MEMORY.md` in-place (Active Handoff state + index, keeping total file <= 80-100 lines).
  2. Update `context/memory/architecture.md` or `context/memory/conventions.md` in-place if architectural decisions or conventions were added or modified.
  3. Append a concise 5-8 line milestone block (`## [HH:MM | Host: Claude Code / Antigravity] <Task>`) to `context/memory/log/YYYY-MM-DD.md`.
  - *Token Hygiene*: Never write memory checkpoints on intermediate turns or simple Q&A prompts.
- Deliver the final summary report with test evidence, committee reports, and compliance sign-off.

## Usage

### Example Invocations
```text
"Build an end-to-end user authentication module with JWT tokens, refresh tokens, and rate limiting."
```
```text
"Refactor the payment processing service and notification worker in parallel to support multi-tenant webhooks."
```
```text
"Fix the null pointer bug in the calculation utility when order total is zero."
```

### Host Execution Instructions
- **Antigravity**:
  - Launch single or parallel subagents using `invoke_subagent` (pass multiple entries in `Subagents: [...]` for parallel fan-out, setting `Workspace: 'inherit'` for Mode A Disjoint Files or `Workspace: 'branch'` / `Workspace: 'share'` for Mode B Worktree Isolation).
  - Valid subagent TypeNames: `product-analyst`, `ui-ux-designer`, `architect-engineer`, `code-implementer`, `qa-tester`, `critic`, `challenger`, `e2e-blackbox-tester`, `compliance-verifier`.
  - Communicate follow-ups with `send_message` and monitor with `manage_subagents`.
  - Use `ask_question` for interactive GUI dialog confirmations at State 1 -> State 2 alignment gate and scope drift detection.
- **Claude Code**:
  - Dispatch single or concurrent subagents by emitting multiple `Agent(agent="...", prompt="...")` tool calls in a single assistant turn (using `loop-engineering` worktree isolation when shared files are modified).

## Red Flags
- Orchestrator writing or editing application source code or test files directly.
- Skipping `State 0` (`context/memory/MEMORY.md` check, `<feature-name>` directory creation in `docs/<feature-name>/`, and `PLAN.md` creation with 3-Tier Routing & Discovery Triage).
- Misclassifying a multi-file or cross-layer feature as Tier 1 to bypass discovery and user alignment.
- Skipping `architect-engineer` when >= 2 files/modules are modified, or skipping `product-analyst` on ambiguous/new user-facing features in Tier 2/3.
- Proceeding to State 2 on Tier 2/3 tasks without pausing for the Interactive User Alignment Gate via `ask_question`.
- Spawning parallel `code-implementer` subagents on overlapping files without Git Worktree isolation (`Mode B`).
- Parallel implementers running full repository test suites in tight loops instead of scoped test files.
- Omitting the Adversarial Verification Committee (`critic`, `challenger`, `e2e-blackbox-tester`) on Tier 3 mission-critical features.
- Exceeding 3 self-correction loops without escalating to the user, or finishing without both `exit code 0` (`qa-tester`) and `APPROVED` (`compliance-verifier`).
- Writing `context/memory/` checkpoints on every intermediate turn instead of once at `State 5` milestone completion.

## Verification
- [ ] `State 0` completed: Active branch checked/auto-created; `<feature-name>` derived and `docs/<feature-name>/` created; `context/memory/MEMORY.md` restored (if present); `PLAN.md` authored with `## 3-Tier Dynamic Routing & Discovery Triage` table.
- [ ] `State 1` completed: For Tier 2/3, `product-analyst`, `ui-ux-designer`, and/or `architect-engineer` invoked upfront per Triage Rubric; discovery artifacts placed in `docs/<feature-name>/` (`prd.md`, `design.md`, `architecture.md`).
- [ ] Interactive User Alignment Gate completed: For Tier 2/3 tasks, paused and obtained user approval via `ask_question` before proceeding to code implementation.
- [ ] `State 2` completed: Collision analysis verified disjoint `Owned Files` (Mode A) or triggered Git Worktree isolation (Mode B); parallel implementers executed scoped tests; all code changes produced strictly by 1..N `code-implementer` subagents via TDD.
- [ ] `State 3 & 4` completed:
  - Tier 1: Scoped tests pass with `exit code 0`.
  - Tier 2: `qa-tester` (`docs/<feature-name>/test-matrix.md` with `exit code 0`) and `compliance-verifier` (`APPROVED` verdict).
  - Tier 3: Full Adversarial Verification Committee passed (`qa-tester` with `test-matrix.md`, `critic` with `critic-review.md`, `challenger` with `adversarial-report.md`, `e2e-blackbox-tester` with `blackbox-report.md`, and `compliance-verifier` with `APPROVED` verdict).
- [ ] `State 5` completed: `PLAN.md` finalized and milestone persisted to `context/memory/` (`MEMORY.md`, topic pages, and `log/YYYY-MM-DD.md`).
- [ ] Orchestrator made zero direct edits to application source code files.
