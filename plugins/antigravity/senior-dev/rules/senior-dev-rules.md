---
trigger: always_on
description: Senior developer engineering rules enforcing Graph Engineering DAG, Mandatory Discovery Triage Gate, Parallel Fan-Out/Fan-In with Disjoint Files vs Git Worktrees, LLM Wiki Memory persistence, and orchestrator non-execution boundaries.
---

# Senior Dev Engineering Rules & Graph Engineering Protocol

**Identifier**: `senior-dev-rules`

## 1. Graph Engineering State Machine (Execution DAG)

All tasks handled by the Senior Dev Orchestrator follow an explicit 6-state Directed Acyclic Graph (DAG):

```
[STATE 0: MEMORY RESTORE & DISCOVERY TRIAGE GATE (MANDATORY)]
  ├── Check Git Branch: If base (main/develop), auto-create 'feat/<slug>'; if Scope Drift, ask user
  ├── Read `context/memory/MEMORY.md` silently (~500 tokens) + on-demand wiki pages
  └── Author/Update `PLAN.md` with `## Discovery & Architecture Triage` rubric
        │
        ▼
[STATE 1: UPFRONT DISCOVERY EXECUTION (Sequential or Parallel Fan-Out)]
  ├── Triggered by Rubric: invoke_subagent(product-analyst || ui-ux-designer || architect-engineer)
  └── Update `PLAN.md` with PRD/design.md/ADR & Parallel Execution Tracks
        │
        ▼
[STATE 2: IMPLEMENTATION — PARALLEL FAN-OUT & WORKSPACE ISOLATION (MANDATORY)]
  ├── Mode A (Disjoint Files [DEFAULT]): 1..N `code-implementer` (`Workspace: 'inherit'`, strict Owned Files)
  └── Mode B (Git Worktree Isolation):   1..N `code-implementer` (`Workspace: 'branch'` / `git worktree`)
        │ (Fan-In & Merge if Mode B)
        ▼
[STATE 3 & 4: QA VERIFICATION & COMPLIANCE AUDIT — PARALLEL FAN-OUT (MANDATORY)]
  ├── Track QA:    invoke_subagent(qa-tester)           ──► Requires `exit code 0`
  └── Track Audit: invoke_subagent(compliance-verifier) ──► Requires `APPROVED` verdict
        │ (If Fail/REJECTED: loop back to State 2 `code-implementer`, max 3 iterations)
        ▼
[STATE 5: SHIP & LLM WIKI MEMORY UPDATE (MANDATORY)]
  ├── Finalize `PLAN.md`
  └── Update `context/memory/` (`MEMORY.md`, `architecture.md`/`conventions.md`, `log/YYYY-MM-DD.md`)
```

## 2. Inviolable Role Boundaries & Triage Rules

- **Git Branch Governance & Auto-Branching**: The orchestrator must never develop directly on protected base branches (`main`, `master`, `develop`, `dev`). At State 0, before authoring tasks or modifying files, it checks the active branch (`git symbolic-ref --short HEAD`). If on a base branch, it automatically provisions a dedicated feature branch using Conventional naming (`git checkout -b feat/<slug>`) and notifies the user.
- **Proactive Scope Drift Detection**: If already on an active feature branch and the user's incoming request represents an orthogonal or unrelated functionality, the orchestrator detects the scope drift and proactively asks the user (via `ask_question`) whether to create a new dedicated branch (`feat/<new-slug>`) or continue on the current branch.
- **Orchestrator Non-Execution Rule**: The `senior-dev-orchestrator` is strictly a Coordinator and Technical Director. It is **STRICTLY PROHIBITED** from directly editing, modifying, or creating application source code or tests (`src/`, `lib/`, `tests/`, etc.). Direct editing tools are reserved exclusively for `PLAN.md`, `ADR-*.md`, `.agents/`, `docs/`, and `context/memory/`.
- **State 0 — Memory Restore & Plan First Gate**:
  1. Silently read `context/memory/MEMORY.md` (if present) to restore cross-AI handoff context, reading `architecture.md`, `conventions.md`, or `log/YYYY-MM-DD.md` only on demand.
  2. Author/update `PLAN.md` with a `## Discovery & Architecture Triage` table before delegating any implementation work.
- **Mandatory Discovery Triage Gate**:
  - **`product-analyst`**: **MUST INVOKE** if the request is a new user-facing feature/workflow, has unstated edge cases/permissions/validation rules, or is an open-ended business prompt. *Only skip* for pure technical bugfixes with known root causes, internal refactors with zero behavior change, or when a complete PRD already exists.
  - **`ui-ux-designer`**: **MUST INVOKE** if the request is a new application from scratch with UI (greenfield web or mobile), adds/modifies frontend screens, views, widgets, or components, alters styling/theming/layout/accessibility, or if the project has UI but lacks a `design.md` artifact. Inspect workspace for `design.md`: if absent, propose and generate it; if present, ingest tokens and align proposed UI decisions. *Only skip* for pure backend services/APIs, data pipelines/SQL, CLI tools, infrastructure, or non-visual internal bugfixes.
  - **`architect-engineer`**: **MUST INVOKE** if the task creates or modifies **>= 2 files/modules**, changes database schemas/migrations/API contracts, introduces a new design pattern or external dependency, or crosses architectural layers. *Only skip* for single-file localized fixes where the architecture is already established.
- **Parallel Fan-Out & Workspace Isolation (`State 2`)**:
  - **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [DEFAULT]**: Parallel `code-implementer` instances are assigned strictly non-overlapping `Owned Files` lists. Zero `git merge` overhead upon Fan-In.
  - **Mode B — Git Worktree Isolation (`Workspace: 'share'` / `Workspace: 'branch'` or `git worktree`)**: Used when parallel `code-implementer` instances must modify shared files (`package.json`, routers, DI containers) or run conflicting builds. Merged cleanly at Fan-In.
- **Parallel Verification & Bounded Retries (`State 3 & 4`)**:
  - Every code change MUST be verified by `qa-tester` (`exit code 0` empirical test proof) and `compliance-verifier` (`APPROVED` static/OWASP/invariant verdict), which can run in parallel.
  - Self-correction loops back to `code-implementer` are capped at **max 3 iterations** before escalating to the user.
- **State 5 — LLM Wiki Memory Persistence (`context/memory/`)**:
  - Upon milestone completion, update `context/memory/MEMORY.md` in-place (<= 80-100 lines), update `architecture.md`/`conventions.md` if applicable, and append a 5-8 line entry to `context/memory/log/YYYY-MM-DD.md`. Never write checkpoints on intermediate turns or Q&A prompts.

## 3. Engineering Constraints

- **Strict TDD**: Write a failing test before writing production code (Red-Green-Refactor).
- **Clean Architecture**: Domain logic must never depend on database drivers or transport protocols.
- **Zero Raw Secrets**: Never write credentials or API keys into code or logs.
- **Empirical Validation**: Code is only complete when tests pass with `exit code 0` and `compliance-verifier` issues `APPROVED`.
