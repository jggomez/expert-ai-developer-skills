---
trigger: model_decision
description: 7-stage Loop Engineering cycle (PLAN->TASK->BUILD->TEST->VERIFICATION->DOCUMENTATION->COMMIT) with parallel subagent delegation, skill orchestration, and manager auditing, scaled to the size of the task.
---

# Rule: Loop Engineering Execution Workflow

**Identifier**: `loop-engineering-workflow`

## 1. Scaled 7-Stage Cycle

The 7-stage cycle below applies in full to new features and system-level changes. **MUST** scale it down for smaller work:

`1. PLAN -> 2. TASK -> 3. BUILD -> 4. TEST -> 5. VERIFICATION -> 6. DOCUMENTATION -> 7. COMMIT`

* Trivial fix / isolated bug: skip PLAN and TASK, go straight to BUILD -> TEST -> COMMIT.
* Small, well-scoped change: skip TASK (no parallelization needed); keep the rest.
* **NEVER** default to running all 7 stages "to be safe" — that is itself over-engineering.

## 2. Stage Specifications & Skill Orchestration

| Stage | Objective | Directives & Mandatory Skills |
| :--- | :--- | :--- |
| **1. PLAN** | Architectural Alignment | **MUST NOT** write code without an approved plan, when this stage applies. Use `senior-architect-engineering`, `design-spec-expert`. |
| **2. TASK** | Breakdown & Parallelization | For work that splits into disjoint files, **MUST** perform dependency analysis and spawn subagents in isolated workspaces (e.g. separate git worktrees) for each. |
| **3. BUILD** | Implementation | **MUST** write clean, typed code in English adhering to SOLID. Use `python-expert` or the relevant language-expert skill. |
| **4. TEST** | TDD Validation | **MUST** follow Red-Green-Refactor. **NEVER** ignore failing test output. Use `test-driven-development`, `testing-expert`. |
| **5. VERIFICATION**| Manager Audit | **MUST** audit subagent deliverables and pass static analysis + security gates. Use `build-and-ci-gates`, `security-audit`. |
| **6. DOCS** | System Documentation | **MUST** update docstrings, READMEs, and Mermaid diagrams. Use `documentation-expert`, `repo-research`. |
| **7. COMMIT** | Semantic Commit | **MUST** format conventional commit and verify git status. Use `commit-expert`, `/commit-push` workflow. |

## 3. Manager Quality Gates

* **NEVER** declare victory in Stage 5 without empirical runtime execution evidence (`exit code 0`).
* **NEVER** allow subagents to mutate overlapping files concurrently without isolation.
* **MUST** execute full regression tests after integrating subagent outputs.
