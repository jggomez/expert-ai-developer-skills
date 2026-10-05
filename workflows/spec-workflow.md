# Workflow: Define What to Build (/spec)

**Command**: `/spec`  
**Key Principle**: *Spec before code*  
**Identifier**: `spec-workflow`

---

## 1. Objective
Define functional and non-functional requirements, user stories, domain boundaries, and verifiable acceptance criteria before writing code or making design assumptions.

## 2. Operational Steps
1. **Gather Context**: Review user requirements, existing code, and domain models.
2. **Align on Ambiguities**: If scope, edge cases, or requirements are unclear, ask clarifying questions or run an alignment interview (`/grill-me`).
3. **Formulate PRD / Spec**:
   - Problem statement and target user.
   - Core functional requirements and out-of-scope boundaries.
   - Acceptance criteria (Gherkin format: Given-When-Then where possible).
   - Non-Functional Requirements (NFRs): latency, availability, security, accessibility.
4. **Obtain Approval**: Present the specification to the user and confirm alignment before proceeding to planning.

## 3. Subagent Delegation & Role Boundaries
- **Role Boundary**: The Orchestrator delegates requirement gathering and PRD authoring to the requirements specialist.
- **Subagent Delegation across Runners**:
  * **Google Antigravity**:
    ```python
    invoke_subagent(
        name="product-analyst",
        prompt="Draft comprehensive PRD and acceptance criteria for: <feature-scope>"
    )
    ```
  * **Anthropic Claude Code**:
    ```python
    Agent(
        agent="product-analyst",
        prompt="Draft comprehensive PRD and acceptance criteria for: <feature-scope>"
    )
    ```
- **Primary Skills**: `design-spec-expert`, `product-analyst`.

## 4. Quality Gate Checklist
- [ ] User problem and desired outcome explicitly stated.
- [ ] Acceptance criteria defined with verifiable assertions.
- [ ] Out-of-scope items explicitly documented.
- [ ] User approval confirmed.
