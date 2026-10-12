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
2. **State 0 Memory Restore & Plan-First Triage Gate**: Before delegating any code changes, the orchestrator MUST silently check and read `context/memory/MEMORY.md` (if present) and author/update `PLAN.md` containing an explicit `## Discovery & Architecture Triage` table and a `## Parallel Execution Tracks` table.
3. **Deterministic Upfront Discovery**: Whenever the Discovery Triage Rubric triggers `product-analyst` and/or `architect-engineer`, they MUST be invoked (sequentially or in parallel) **before** dispatching `code-implementer`.
4. **Parallel Fan-Out & Workspace Isolation**: Parallel `code-implementer` subagents MUST operate either on strictly non-overlapping `Owned Files` partitions (**Mode A: Disjoint File Partitioning**) or inside isolated git branches/worktrees (**Mode B: Git Worktree Isolation**).
5. **Mandatory Parallel Verification & Cap on Retries**: Every implementation must pass both `qa-tester` (`exit code 0`) and `compliance-verifier` (`APPROVED` verdict), which may be dispatched in parallel. Self-correction loops back to `code-implementer` are strictly capped at **maximum 3 iterations** before escalating to the user.

## Graph Engineering Execution DAG

```
[STATE 0: MEMORY RESTORE & DISCOVERY TRIAGE GATE (MANDATORY)]
  ├── 1. Read `context/memory/MEMORY.md` silently (~500 tokens) + on-demand wiki pages
  └── 2. Author/Update `PLAN.md` with `## Discovery & Architecture Triage` rubric
           │
           ▼
[STATE 1: UPFRONT DISCOVERY EXECUTION (Sequential or Parallel Fan-Out)]
  ├── (Triggered by Rubric) ──► invoke_subagent(product-analyst || architect-engineer)
  ├── Update `PLAN.md` with PRD/ADR specs & Parallel Execution Tracks
  └── (Skipped only when rubric explicitly justifies SKIP for both)
           │
           ▼
[STATE 2: IMPLEMENTATION — PARALLEL FAN-OUT & WORKSPACE ISOLATION (MANDATORY)]
  ├── Mode A (Disjoint Files, default): 1..N `code-implementer` (`Workspace: 'inherit'`, strict Owned Files)
  └── Mode B (Shared Files / Worktrees): 1..N `code-implementer` (`Workspace: 'branch'` / `git worktree`)
           │ (Fan-In & Merge if Mode B)
           ▼
[STATE 3 & 4: QA VERIFICATION & COMPLIANCE AUDIT — PARALLEL FAN-OUT (MANDATORY)]
  ├── Track QA:    invoke_subagent(qa-tester)           ──► Requires `exit code 0` proof
  └── Track Audit: invoke_subagent(compliance-verifier) ──► Requires `APPROVED` verdict
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
- **LLM Wiki Memory Read (`context-restore`)**:
  - Check if `context/memory/MEMORY.md` exists in the workspace. If present, read it silently (~500 tokens) to restore cross-AI handoff state left by Claude Code or Antigravity.
  - Read linked wiki pages (`context/memory/architecture.md`, `context/memory/conventions.md`, `context/memory/log/YYYY-MM-DD.md`) **on demand only** if directly relevant to the current task.
- **Mandatory Discovery & Architecture Triage (`PLAN.md`)**:
  - Author or update `PLAN.md` immediately using `write_to_file`.
  - Evaluate the **Discovery Triage Rubric** for `product-analyst` and `architect-engineer` and record the decision (`INVOKE` vs. `SKIP` + concrete justification) in a `## Discovery & Architecture Triage` table inside `PLAN.md`.

### 2. State 1: Upfront Discovery Execution (Sequential or Parallel Fan-Out)
- When the Triage Gate triggers `product-analyst` and/or `architect-engineer`, invoke them **before** delegating to `code-implementer`.
- **Parallel Discovery Fan-Out**:
  - Invoke `product-analyst` and `architect-engineer` **in parallel** (or spawn 2+ `architect-engineer` instances in parallel for distinct subsystems/domains) when their scopes are independent.
  - Invoke them **sequentially** (`product-analyst` -> `architect-engineer`) when architectural boundaries depend on product scope disambiguation.
- Update `PLAN.md` with the resulting PRD specifications, ADRs, and a `## Parallel Execution Tracks` table specifying each implementation track's `Isolation Mode` (`Disjoint Files` vs. `Git Worktree`) and `Owned Files`.

### 3. State 2: Implementation — Parallel Fan-Out & Workspace Isolation (MANDATORY)
- Dispatch **1 to N `code-implementer` subagents** (sequentially for a single track, or in parallel for independent tracks):
  - **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**:
    - Used when parallel implementation tracks modify strictly non-overlapping files/directories.
    - Each `code-implementer` receives an explicit `Exclusive Owned Files` list in its prompt and is strictly forbidden from editing files outside its partition.
    - Produces zero `git merge` overhead upon Fan-In.
  - **Mode B — Git Worktree Isolation (`Workspace: 'share'` / `Workspace: 'branch'` in Antigravity, or `git worktree` via `loop-engineering` in Claude Code)**:
    - Used when parallel `code-implementer` instances must modify shared files (e.g., `package.json`, shared routers, DI containers) or execute conflicting build processes.
    - Upon Fan-In, branches/worktrees are merged cleanly before running final QA and Compliance verification.

### 4. State 3 & 4: QA Verification & Compliance Audit — Parallel Fan-Out (MANDATORY)
- Dispatch `qa-tester` (`exit code 0` empirical test proof) and `compliance-verifier` (read-only static analysis, OWASP security, and architectural invariant audit yielding `APPROVED` verdict) **in parallel** (as well as multiple `qa-tester` instances across disjoint test suites when applicable).
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
  - Launch single or parallel subagents using `invoke_subagent` (pass multiple entries in `Subagents: [...]` for parallel fan-out, setting `Workspace: 'inherit'` for Mode A Disjoint Files or `Workspace: 'branch'` / `Workspace: 'share'` for Mode B Worktree Isolation).
  - Communicate follow-ups with `send_message` and monitor with `manage_subagents`.
- **Claude Code**:
  - Dispatch single or concurrent subagents by emitting multiple `Agent(agent="...", prompt="...")` tool calls in a single assistant turn (using `loop-engineering` worktree isolation when shared files are modified).

## Red Flags
- Orchestrator writing or editing application source code or test files directly.
- Skipping `State 0` (`context/memory/MEMORY.md` check and `PLAN.md` creation with the `## Discovery & Architecture Triage` rubric).
- Skipping `architect-engineer` when >= 2 files/modules are modified, or skipping `product-analyst` on ambiguous/new user-facing features.
- Spawning parallel `code-implementer` subagents on overlapping files without Git Worktree isolation (`Mode B`).
- Exceeding 3 self-correction loops without escalating to the user, or finishing without both `exit code 0` (`qa-tester`) and `APPROVED` (`compliance-verifier`).
- Writing `context/memory/` checkpoints on every intermediate turn instead of once at `State 5` milestone completion.

## Verification
- [ ] `State 0` completed: `context/memory/MEMORY.md` restored (if present) and `PLAN.md` authored with `## Discovery & Architecture Triage` table.
- [ ] `State 1` completed: `product-analyst` and/or `architect-engineer` invoked upfront (sequentially or in parallel) whenever mandated by the Triage Rubric.
- [ ] `State 2` completed: All code changes produced strictly by 1..N `code-implementer` subagents via TDD under explicit `Disjoint Files` (`Mode A`) or `Git Worktree` (`Mode B`) isolation.
- [ ] `State 3 & 4` completed: Parallel verification executed by `qa-tester` (`exit code 0` proof) and `compliance-verifier` (explicit `APPROVED` verdict).
- [ ] `State 5` completed: `PLAN.md` finalized and milestone persisted to `context/memory/` (`MEMORY.md`, topic pages, and `log/YYYY-MM-DD.md`).
- [ ] Orchestrator made zero direct edits to application source code files.