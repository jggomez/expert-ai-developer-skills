---
trigger: model_decision
description: Mandatory 7-stage Loop Engineering cycle (PLAN->TASK->BUILD->TEST->VERIFICATION->DOCUMENTATION->COMMIT) with parallel subagent delegation, skill orchestration, quality gates, and manager auditing.
---

# Rule: Loop Engineering Execution Workflow

**Identifier**: `loop-engineering-workflow`

## 1. Mandatory 7-Stage Cycle

All non-trivial coding tasks **MUST** execute strictly through the 7-stage Loop Engineering cycle:

`1. PLAN -> 2. TASK -> 3. BUILD -> 4. TEST -> 5. VERIFICATION -> 6. DOCUMENTATION -> 7. COMMIT`

## 2. Stage Specifications & Skill Orchestration

| Stage | Objective | Directives & Mandatory Skills |
| :--- | :--- | :--- |
| **1. PLAN** | Architectural Alignment | **MUST NOT** write code without an approved plan. Use `senior-architect-engineering`, `design-spec-expert`. |
| **2. TASK** | Breakdown & Parallelization | **MUST** perform dependency analysis. Spawn subagents (`invoke_subagent` with `Workspace='share'`) for disjoint files. |
| **3. BUILD** | Implementation | **MUST** write clean, typed code in English adhering to SOLID. Use `python-expert`, `fastapi-expert`, `modern-web-guidance`. |
| **4. TEST** | TDD Validation | **MUST** follow Red-Green-Refactor. **NEVER** ignore failing test output. Use `test-driven-development`, `testing-expert`. |
| **5. VERIFICATION**| Manager Audit | **MUST** audit subagent deliverables and pass static analysis + security gates. Use `build-and-ci-gates`, `security-audit`. |
| **6. DOCS** | System Documentation | **MUST** update docstrings, READMEs, and Mermaid diagrams. Use `documentation-expert`, `repo-research`. |
| **7. COMMIT** | Semantic Commit | **MUST** format conventional commit and verify git status. Use `commit-expert`, `/commit-push` workflow. |

## 3. Manager Quality Gates

* **NEVER** declare victory in Stage 5 without empirical runtime execution evidence (`exit code 0`).
* **NEVER** allow subagents to mutate overlapping files concurrently without isolation.
* **MUST** execute full regression tests after integrating subagent outputs.
