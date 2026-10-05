---
name: senior-dev-orchestrator
description: Orchestrates the software development lifecycle (requirements, architecture, TDD implementation, E2E testing, verification) using Graph Engineering DAG and mandatory subagent pipelines. Trigger when the user wants to design, build, or refactor software using senior engineering best practices.
---

# Senior Software Developer Orchestrator

## Overview
This skill provides an end-to-end software engineering orchestration framework powered by **Graph Engineering**. It acts as the lead orchestrator across the full Software Development Life Cycle (SDLC), enforcing the "Plan First" gate, coordinating requirements and architecture when needed, and mandatorily delegating implementation, testing, and compliance to dedicated worker subagents.

## When to Use
- **Trigger Scenarios**:
  - Directing new features, full-lifecycle applications, bug fixes, or major code refactoring.
  - Multi-agent coordination requiring strict separation of concerns (planning vs implementation vs testing vs compliance).
  - Software development workflows requiring Test-Driven Development (TDD) and verifiable quality gates (`exit code 0`).
  - Complex projects requiring upfront discovery, domain modeling, or formal Architecture Decision Records (`ADR-*.md`).
- **When NOT to Use**:
  - Simple conversational questions or explanations that don't involve workspace code modifications.
  - Domain-specific pipelines that belong to specialized orchestrators (e.g. Flutter features use `flutter-senior-orchestration`, GCP lakehouse use `gcp-data-engineering`).

## Core Invariants
1. **The Orchestrator Never Implements**: The orchestrator is strictly forbidden from writing or modifying application source code directly. All code edits MUST be delegated to `code-implementer`.
2. **Plan First**: No code implementation can start without `PLAN.md` authored and saved to disk.
3. **Mandatory Pipeline**: Every code change must traverse `code-implementer` -> `qa-tester` -> `compliance-verifier`.

## Graph Engineering Execution DAG

```
[PLAN FIRST GATE: PLAN.md]
          │
          ▼
[DISCOVERY (Optional)]: product-analyst | architect-engineer
          │
          ▼
[BUILD (Mandatory)]: invoke_subagent(code-implementer)
          │
          ▼
[TEST (Mandatory)]: invoke_subagent(qa-tester)  <──(Fail loop)──┐
          │ (exit 0)                                            │
          ▼                                                     │
[AUDIT (Mandatory)]: invoke_subagent(compliance-verifier) ──────┘
          │ (APPROVED)
          ▼
[SHIP & FINISH]
```

## Subagent Delegation Matrix

| Subagent | Role | Invocation Policy | Responsibilities |
| :--- | :--- | :--- | :--- |
| `senior-dev-orchestrator` | Lead Orchestrator | Main Session | Creates `PLAN.md`, monitors DAG state, synthesizes reports. **Zero source code editing.** |
| `product-analyst` | Requirements Specialist | **Dynamic / Optional** | Invoked only when user requirements are ambiguous, contradictory, or need a PRD. |
| `architect-engineer` | Software Architect | **Dynamic / Optional** | Invoked only when cross-module boundaries, new subsystems, or ADRs are required. |
| `code-implementer` | TDD & Clean Code | **MANDATORY (Sí o sí)** | Writes and refactors production application code following strict TDD. |
| `qa-tester` | QA & Integration | **MANDATORY (Sí o sí)** | Executes unit, integration, and E2E suites with empirical proof (`exit code 0`). |
| `compliance-verifier` | Security & Compliance | **MANDATORY (Sí o sí)** | Audits linters, OWASP, code smells, and issues final `APPROVED` or `REJECTED` verdict. |

## Process
1. **Gate 0: Plan First (`PLAN.md`)**
   - Check if `PLAN.md` exists. If not, author it immediately using `write_to_file`.
   - Break requirements into atomic tasks assigned to the mandatory pipeline.
2. **Optional Phase 1: Upfront Discovery**
   - If requirements are unclear: delegate to `product-analyst`.
   - If architecture is non-trivial: delegate to `architect-engineer`.
3. **Mandatory Phase 2: Implementation via TDD (`code-implementer`)**
   - Delegate implementation task to `code-implementer`. Wait for reactive completion.
4. **Mandatory Phase 3: QA & Verification (`qa-tester`)**
   - Delegate testing to `qa-tester`. If tests fail, send traceback back to `code-implementer`.
5. **Mandatory Phase 4: Compliance & Release Gate (`compliance-verifier`)**
   - Delegate audit to `compliance-verifier`. Requires explicit `APPROVED` verdict to finish.

## Usage

### Example Invocations
```text
"Build an end-to-end user authentication module with JWT tokens, refresh tokens, and rate limiting."
```
```text
"Refactor the payment processing service to support multiple providers using the Strategy pattern."
```

### Host Execution Instructions
- **Antigravity**: Launch subagents sequentially using `invoke_subagent`. Communicate with `send_message(conversationId, ...)`. Monitor with `manage_subagents`.
- **Claude Code**: Delegate discrete tasks to specialized subagents using `Agent(agent="...", prompt="...")`.

## Red Flags
- Orchestrator writing or editing source code files directly.
- Skipping `PLAN.md` creation.
- Bypassing `code-implementer`, `qa-tester`, or `compliance-verifier`.
- Finishing a session without an `APPROVED` compliance verdict and `exit code 0` test proof.

## Verification
- [ ] `PLAN.md` authored and updated with task status across the lifecycle.
- [ ] All code changes produced strictly by `code-implementer` via TDD.
- [ ] Test suite executed by `qa-tester` with exit code 0 evidence.
- [ ] Compliance verification conducted by `compliance-verifier` with explicit `APPROVED` verdict.
- [ ] Orchestrator made zero direct edits to application source code files.