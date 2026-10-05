---
trigger: always_on
description: 9-stage engineering execution cycle governed by Graph Engineering DAG, Plan-First gating, orchestrator non-execution boundaries, and mandatory subagents.
---

# Rule: Engineering Execution Workflow & Graph Engineering Protocol

**Identifier**: `loop-engineering-workflow`

## 1. Graph Engineering State Machine (Execution DAG)

Every software task executed under this workflow must transition through an explicit state machine:

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

## 2. Inviolable Role Boundaries

1. **Orchestrator Role Boundary**:
   - The Orchestrator is purely a Coordinator and Technical Director.
   - **STRICTLY PROHIBITED**: The Orchestrator is NEVER permitted to write or edit application source code (`src/`, `lib/`, `tests/`, etc.) directly.
   - Writing tools are EXCLUSIVELY reserved for planning and architectural records (`PLAN.md`, `ADR-*.md`, docs).
2. **Plan First**:
   - Before executing any code implementation, an up-to-date `PLAN.md` must be authored and saved to disk.
3. **Dynamic Discovery Nodes**:
   - `product-analyst`: Optional. Invoked only when user requirements are ambiguous or require a formal PRD.
   - `architect-engineer`: Optional. Invoked only when architectural blueprints, new subsystems, or ADRs are required.
4. **Mandatory Execution Pipeline (Sí o sí)**:
   - Implementation MUST be delegated to `code-implementer` via `invoke_subagent`.
   - Testing MUST be delegated to `qa-tester` via `invoke_subagent`.
   - Compliance & quality audit MUST be delegated to `compliance-verifier` via `invoke_subagent`.

## 3. Mandatory Execution Gates

- **Tests are Proof**: Never declare victory without empirical execution evidence (`exit code 0`).
- **Isolation Protocol**: Never allow parallel subagents to concurrently edit overlapping files without isolated workspaces.
- **Verification Guarantee**: `compliance-verifier` must issue an explicit `APPROVED` verdict before completing the task.
