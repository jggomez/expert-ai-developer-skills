---
name: senior-dev-orchestrator
description: Orchestrates the software development lifecycle (requirements, architecture, TDD implementation, E2E testing, verification), scaling the process to the task instead of running every phase unconditionally. Trigger when the user wants to design, build, or refactor software using senior engineering best practices.
---

# Senior Software Developer Orchestrator

## Overview
This skill provides an end-to-end software engineering orchestration framework. It acts as the lead orchestrator across the full Software Development Life Cycle (SDLC), coordinating requirements analysis, architectural design, test-driven implementation, integration testing, and compliance auditing. Rather than enforcing heavyweight bureaucracy on every task, it dynamically scales the phases to match the scope, complexity, and risk of the change.

## When to Use
### Trigger Scenarios
- Orchestrating complex, multi-phase feature development from initial request to merge.
- Coordinating subagents across distinct SDLC specializations (Product, Architecture, Code, QA, Compliance).
- Structuring major refactorings or architectural migrations that touch multiple layers.
- Running end-to-end development loops in Claude Code or Antigravity.

### When NOT to Use
- **Trivial 1-line fixes or typos**: Implement directly using standard editing tools without running full SDLC overhead.
- **Isolated unit test additions**: Route directly to `test-driven-development` or `testing-expert`.
- **Pure documentation or diagramming**: Route directly to `documentation-expert`.
- **Single SQL query tuning**: Route to `sql-query-optimization` or `bigquery-query-optimization`.

## Process
### 1. Task Sizing Matrix
Assess the scope before running phases. Never default to the heaviest process without need:

| Task Shape | Phases to Run | Primary Artifact |
| :--- | :--- | :--- |
| **Trivial / 1-line fix** | Phase 3 (Implementation + Unit Test) | Tested code diff |
| **Small feature / local change** | Phase 1 (Brief notes) → Phase 3 (TDD) → Phase 5 (Targeted check) | Code + Unit tests |
| **New feature / cross-module** | Phase 1 (PRD) → Phase 2 (Design/ADR) → Phase 3 (TDD) → Phase 4 (E2E/RTM) → Phase 5 (Audit) | Full SDLC deliverables |
| **Architectural refactor** | Phase 2 (ADR/Spec) → Phase 3 (TDD) → Phase 4 (Regression suite) → Phase 5 (Audit) | ADR + Refactored code |

### 2. Execution Phases
1. **Phase 1: Product Understanding (`product-analyst`)**
   - Identify primary user goals, scope boundaries, constraints, and edge cases.
   - Ask targeted clarifying questions only when genuine ambiguity exists.
   - Output: Requirements summary or structured Product Requirements Document (PRD).
2. **Phase 2: Architecture & Design (`senior-architect-engineering`)**
   - Evaluate Quality Attribute Drivers (QADs) such as performance, security, and maintainability.
   - Apply KISS/YAGNI to select the simplest robust architecture.
   - Output: Architecture blueprint or Architectural Decision Record (ADR).
3. **Phase 3: Implementation via TDD (`code-implementer` & `test-driven-development`)**
   - Enforce the Red-Green-Refactor cycle: failing test first, minimal production code, refactor to clean code.
   - Output: Source code and passing unit/integration tests.
4. **Phase 4: E2E & Integration Testing (`qa-tester`)**
   - Verify multi-component integration, happy paths, and critical edge cases.
   - Map test cases to requirement IDs via a Requirement Traceability Matrix (RTM) when a PRD was generated.
   - Output: E2E test suite and execution report.
5. **Phase 5: Verification & Compliance Audit (`compliance-verifier`)**
   - Audit code against security standards (OWASP, secret scanning), static analysis, and NFRs.
   - Output: Audit Verdict (`APPROVED` or `REJECTED` with remediation steps).

## Usage
### Example Prompts
- *"Orchestrate the end-to-end development of a user profile notification service, from PRD to verified release."*
- *"We need to refactor our authentication layer to support OAuth2 and session refresh. Size the task and run the appropriate SDLC phases."*
- *"Build a new billing webhook handler using senior engineering best practices with strict TDD and a compliance audit."*

### Host Execution Instructions
- **Claude Code**: Delegate discrete phases to specialized task descriptions or subagents, inspecting outputs at each phase boundary.
- **Antigravity**: Launch subagents sequentially or in parallel using `invoke_subagent` (e.g. `product-analyst`, `code-implementer`, `qa-tester`, `compliance-verifier`) based on task sizing.

## Red Flags
- Running all 5 phases for trivial bug fixes or typo corrections.
- Skipping TDD and writing implementation code before writing tests.
- Proceeding to Phase 3 when functional requirements remain fundamentally ambiguous.
- Allowing subagents or tasks to proceed past Phase 5 without an explicit `APPROVED` audit verdict.
- Gold-plating architectural patterns (e.g., microservices, event sourcing) when a simple module suffices.

## Verification
- [ ] Task scope correctly classified in the Task Sizing Matrix.
- [ ] All scoped phases executed with documented outputs.
- [ ] 100% of automated unit and integration tests pass without failures or skipped assertions.
- [ ] Static analysis, linting, and formatting pass with zero errors.
- [ ] Final compliance verdict is `APPROVED`.