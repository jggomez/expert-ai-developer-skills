---
trigger: always_on
description: Multi-agent operations and loop engineering rules enforcing the Graph Engineering DAG, 3-Tier Dynamic Routing Rubric, Review Committee topologies, finite self-correction loops, Parallel Fan-Out/Fan-In workspace isolation, and token conservation.
---

# Multi-Agent Operations & Loop Engineering Rules

**Identifier**: `multi-agent-ops-rules`

## 1. Graph Engineering State Machine & 3-Tier Dynamic Routing Rubric

All multi-agent execution flows follow an explicit 6-state Directed Acyclic Graph (DAG) state machine with dynamic 3-tier routing:

```
[STATE 0: MEMORY RESTORE & 3-TIER SDLC TRIAGE GATE (MANDATORY)]
  ├── Check Git Branch: If base (main/develop), auto-create 'feat/<slug>'; if Scope Drift, ask user
  ├── Derive `<feature-name>` slug & ensure `docs/<feature-name>/` directory is created
  ├── Read `context/memory/MEMORY.md` silently (~500 tokens) + on-demand wiki pages
  └── Classify Task Tier in `PLAN.md` (Tier 1: Fast-Track | Tier 2: Standard | Tier 3: Mission-Critical)
           │
           ├──────────────────────────────┬──────────────────────────────┐
           ▼                              ▼                              ▼
  [Tier 1: Fast-Track]           [Tier 2: Standard]            [Tier 3: Mission-Critical]
  (Skip State 1 Discovery)       (Selective Discovery)         (Full Discovery: PRD+Design+ADR)
  (Skip Interactive Modal)                │                              │
           │                              ▼                              ▼
           │                     [INTERACTIVE ALIGNMENT GATE (STATE 1.5)]
           │                     ├── Modal via `ask_question` presenting PRD/Design/Arch
           │                     └── Mandatory explicit user sign-off before build
           │                              │                              │
           ▼                              ▼                              ▼
[STATE 2: IMPLEMENTATION — PARALLEL FAN-OUT & WORKSPACE ISOLATION (MANDATORY)]
  ├── Tier 1: 1 `code-implementer` in Mode A (Disjoint Files)
  ├── Tier 2: 1..N `code-implementer` in parallel under Mode A (Disjoint Files)
  ├── Tier 3: 1..N `code-implementer` in parallel under Mode A or Mode B (Git Worktree Isolation)
  └── Scoped Test Isolation: Implementers run ONLY assigned test file during loops
           │                              │                              │
           ▼                              ▼                              ▼
[STATE 3 & 4: QA VERIFICATION & COMPLIANCE AUDIT (MANDATORY)]
  ├── Tier 1: Scoped test verification (`qa-tester`) + `compliance-verifier` (Skip Adversarial)
  ├── Tier 2: Full test suite + `docs/<feature-name>/test-matrix.md` (`qa-tester`) + `compliance-verifier`
  └── Tier 3: Adversarial Verification Committee:
        ├── `qa-tester`: Standardized `test-matrix.md` across test pyramid + terminal exit 0 proof
        ├── `critic`: Code smell detection, SOLID review, maintainability audit
        ├── `challenger`: Boundary probe, failure mode injection, concurrency/edge stress
        ├── `e2e-blackbox-tester`: Blackbox user journey and failure resilience verification
        └── `compliance-verifier`: Static analysis, OWASP security audit, APPROVED verdict
           │ (If Fail/REJECTED: loop back to State 2 `code-implementer`, max 3 iterations)
           ▼
[STATE 5: SHIP & LLM WIKI MEMORY UPDATE (MANDATORY)]
  ├── Finalize `PLAN.md`
  └── Update `context/memory/` (`MEMORY.md`, `architecture.md`/`conventions.md`, `log/YYYY-MM-DD.md`)
```

### 1.1. Dynamic 3-Tier Adaptive SDLC Specification

| Dimension / Phase | Tier 1: Fast-Track (Low Complexity) | Tier 2: Standard (Medium Complexity) | Tier 3: Mission-Critical (Complex) |
| :--- | :--- | :--- | :--- |
| **Scope & Triggers** | Single-file bugfixes, docs, chores, typos, localized refactoring without public contract changes | 2–4 files/modules, new API endpoints, single UI view/widget, database schema changes | Full end-to-end features, payment/auth flows, architectural refactoring, breaking public APIs, major releases |
| **Discovery (State 1)** | **SKIPPED**: Zero discovery overhead; no PRD, design.md, or architecture.md authored | **SELECTIVE**: Targeted discovery via `product-analyst`, `ui-ux-designer`, or `architect-engineer` | **FULL**: Comprehensive discovery via `product-analyst` (`prd.md`), `ui-ux-designer` (`design.md`), and `architect-engineer` (`architecture.md` / ADRs) |
| **Interactive Alignment (State 1.5)** | **SKIPPED**: Auto-proceeds to implementation | **MANDATORY**: Interactive modal (`ask_question`) presenting PRD/design/architecture summary for user approval | **MANDATORY**: Strict interactive modal (`ask_question`) requiring explicit user sign-off |
| **Build Mode (State 2)** | 1 `code-implementer` in Mode A (Disjoint Files) | 1..N `code-implementer` in parallel under Mode A (Disjoint Files) | 1..N `code-implementer` in parallel under Mode A or Mode B (Git Worktree Isolation) |
| **QA Verification (State 3)** | Scoped test execution (only affected test file run) | Full test suite execution + standardized QA Test Matrix (`docs/<feature-name>/test-matrix.md`) | Full test suite execution + standardized QA Test Matrix (`docs/<feature-name>/test-matrix.md`) across test pyramid |
| **Verification & Committee (State 4)** | Scoped `qa-tester` test proof + `compliance-verifier` audit (bypasses adversarial committee) | Parallel `qa-tester` (`exit code 0`) and `compliance-verifier` (`APPROVED`) | **Adversarial Verification Committee**: `qa-tester`, `critic`, `challenger`, `e2e-blackbox-tester`, `compliance-verifier` |
| **Token & Latency Impact** | **70–85% token & latency savings** | Balanced overhead with rigorous quality verification | Maximum depth, empirical verification, and zero regression tolerance |

## 2. Review Committee Topologies & Delegation Architecture

- **Manager-Worker Topology**:
  - The Orchestrator (`senior-dev-orchestrator`, `flutter-feature-orchestrator`) acts purely as Technical Director and Coordinator.
  - **Strict Non-Execution Constraint**: Orchestrators are **STRICTLY PROHIBITED** from directly editing, creating, or modifying application code or tests (`src/`, `lib/`, `tests/`).
  - Direct file modification tools are reserved exclusively for planning, governance, and memory (`PLAN.md`, `ADR-*.md`, `.agents/`, `docs/`, `context/memory/`).
  - All analysis, design, implementation, and test verification **MUST** be delegated to specialized worker subagents.
- **Parallel Fan-Out / Fan-In Topology**:
  - Used during State 2 Build to divide decoupled features into non-overlapping work tracks.
  - Pre-dispatch Collision Analysis: Orchestrator verifies that parallel tracks have strictly disjoint `Owned Files` partitions under Mode A.
  - Tracks merge cleanly at Fan-In before initiating verification.
- **Adversarial Verification Committee Topology (Tier 3)**:
  - Dispatched concurrently upon implementation Fan-In for mission-critical tasks:
    1. `qa-tester`: Standardized `docs/<feature-name>/test-matrix.md` across test pyramid with terminal proof (`exit code 0`).
    2. `critic`: Code smell detection, SOLID invariant review, and maintainability audit in `docs/<feature-name>/critic-review.md`.
    3. `challenger`: Adversarial edge-case probe, boundary conditions, concurrency races, and negative test verification in `docs/<feature-name>/adversarial-report.md`.
    4. `e2e-blackbox-tester`: End-to-end blackbox user journey and failure resilience testing in `docs/<feature-name>/blackbox-report.md`.
    5. `compliance-verifier`: Static analysis, OWASP security audit, and architectural invariant audit yielding `APPROVED`.

## 3. Finite Self-Correction Protocol

- **Max 3 Retries**: When automated test suites, linter checks, or compliance audits fail, the agent is permitted a maximum of **3 self-correction iterations**.
- **User Escalation**: If defects cannot be resolved within 3 iterations, the agent **MUST** pause and escalate to the user using `ask_question`, detailing the root cause, failing test traces, and attempted fixes.
- **Infinite Loop Ban**: Never enter unbounded retry loops attempting blind permutations of failing code.

## 4. Workspace & Test Isolation Protocol

- **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**:
  - When concurrent subagents operate on strictly non-overlapping `Owned Files` sets, dispatch them in parallel with `Workspace: 'inherit'`.
  - Each subagent prompt MUST list its `Exclusive Owned Files` and forbid edits outside that partition, achieving zero `git merge` or worktree overhead upon Fan-In.
- **Mode B — Git Worktree Isolation (`Workspace: 'branch'` / `'share'` or `git worktree`)**:
  - Used when concurrent subagents must touch shared files (`package.json`, `pubspec.yaml`, shared routers, DI containers) or run conflicting build processes.
  - Each parallel worker executes in an isolated git branch/worktree and merges cleanly at Fan-In before final QA.
- **Scoped Test Execution Isolation**:
  - Each parallel implementer during State 2 must run ONLY its assigned test file (e.g. `pytest tests/unit/test_feature_a.py`), NOT the full test suite in tight loops, preventing CPU contention and execution delays.
  - Full test suite execution is reserved for State 3 Fan-In by `qa-tester`.

## 5. Token Conservation & Reactive Execution Invariants

- **Reactive Wakeup**: Do NOT poll in a loop for task or subagent status. Trust the system's reactive message delivery and notifications.
- **Token-Optimized Research**: Never dump multi-thousand-line files into the conversation context when locating a function or symbol. Use `grep_search` or slice notation (`StartLine` and `EndLine`) with `view_file`.
- **Cross-AI LLM Wiki Continuity (`context/memory/`)**:
  - At **State 0**, silently read `context/memory/MEMORY.md` (~500 tokens) and open linked wiki pages (`architecture.md`, `conventions.md`, `log/YYYY-MM-DD.md`) only on demand.
  - At **State 5 (Ship & Finish)**, update `context/memory/MEMORY.md` in-place (`<= 80-100 lines`), update `architecture.md` / `conventions.md` in-place when applicable, and append a 5-8 line milestone entry to `context/memory/log/YYYY-MM-DD.md`. Never write checkpoints on intermediate turns or simple Q&A prompts.
