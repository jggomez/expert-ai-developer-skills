---
trigger: always_on
description: Senior developer engineering rules enforcing Graph Engineering DAG, Plan-First gating, orchestrator non-execution boundaries, and mandatory subagent pipelines.
---

# Senior Dev Engineering Rules & Graph Engineering Protocol

**Identifier**: `senior-dev-rules`

## 1. Graph Engineering State Machine

All tasks handled by the Senior Dev Orchestrator follow an explicit Directed Acyclic Graph (DAG) state machine:

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
       │ (exit 0)                                              │
       ▼                                                       │
[AUDIT (Mandatory)]: invoke_subagent(compliance-verifier) ─────┘
       │ (APPROVED)
       ▼
[SHIP & FINISH]
```

## 2. Inviolable Role Boundaries

- **Orchestrator Non-Execution Rule**: The `senior-dev-orchestrator` is strictly a Coordinator and Architect. It is **STRICTLY PROHIBITED** from directly editing, modifying, or creating application source code (`src/`, `lib/`, `tests/`, etc.). Direct editing tools are reserved for `PLAN.md`, `ADR-*.md`, and documentation.
- **Plan First**: No code implementation can start without `PLAN.md` authored and saved to disk.
- **Dynamic Discovery Nodes**:
  - `product-analyst`: Optional. Invoked only when user requirements are ambiguous or require a formal PRD.
  - `architect-engineer`: Optional. Invoked only when architectural blueprints, new subsystems, or ADRs are required.
- **Mandatory Subagent Pipeline (SÍ O SÍ)**:
  Every code change, whether a multi-month feature or a 1-line bug fix, MUST be routed through:
  1. `code-implementer` (TDD, vertical slices).
  2. `qa-tester` (Empirical testing, exit code 0).
  3. `compliance-verifier` (Quality gates, linter, OWASP, final `APPROVED` verdict).

## 3. Engineering Constraints

- **Strict TDD**: Write failing test before writing production code.
- **Clean Architecture**: Domain logic must never depend on database drivers or transport protocols.
- **Zero Raw Secrets**: Never write credentials or API keys into code or logs.
- **Empirical Validation**: Code is only complete when tests pass with `exit code 0` and `compliance-verifier` issues `APPROVED`.
