# Workflow: Plan How to Build It (/plan)

**Command**: `/plan`  
**Key Principle**: *Small, atomic tasks*  
**Identifier**: `plan-workflow`

---

## 1. Objective
Architect the system solution, select technologies/patterns, record Architectural Decision Records (ADRs), and decompose the feature into small, atomic, independently verifiable tasks.

## 2. Operational Steps
1. **Analyze Trade-offs & Architecture**:
   - Evaluate architecture patterns (Hexagonal, Clean, Layered).
   - Record architectural trade-offs in an ADR under `doc/adr/`.
2. **Author `PLAN.md`**:
   - The Orchestrator authors `PLAN.md` directly, establishing the Graph Engineering DAG and atomic checklist.
   - Break implementation into small tasks (each touching 1-3 files maximum).
   - Sequence tasks to build bottom-up: Interfaces/Contracts -> Core Domain -> Data Layer -> Presentation/UI.
3. **Analyze Dependencies & Parallelization**:
   - Identify disjoint tasks eligible for parallel subagent execution.
4. **Define Verifiable Success Criteria**:
   - Document exact test commands for each task.

## 3. Subagent Delegation & Inviolable Role Boundaries
- **Inviolable Role Boundaries**:
  * `PLAN.md` is strictly authored and maintained by the Lead Orchestrator (`senior-dev-orchestrator` or `flutter-feature-orchestrator`).
  * Architecture design and ADR generation are delegated to `architect-engineer` (or `flutter-architect`).
  * The Orchestrator is strictly prohibited from implementing code; all code implementation is delegated to dedicated worker subagents.
- **Subagent Delegation across Runners**:
  * **Google Antigravity**:
    ```python
    invoke_subagent(
        name="architect-engineer",
        prompt="Analyze system architecture and draft ADR for: <technical-scope>"
    )
    ```
    *(For Flutter applications, use `name="flutter-architect"`)*
  * **Anthropic Claude Code**:
    ```python
    Agent(
        agent="architect-engineer",
        prompt="Analyze system architecture and draft ADR for: <technical-scope>"
    )
    ```
    *(For Flutter applications, use `agent="flutter-architect"`)*
- **Primary Skills**: `senior-architect-engineering`, `design-spec-expert`, `flutter-architecture-decisions`.

## 4. Quality Gate Checklist
- [ ] Architecture aligns with SOLID and clean design principles.
- [ ] ADR drafted and saved in `doc/adr/` if architectural decisions were made.
- [ ] `PLAN.md` authored by Orchestrator with atomic, single-purpose, independently testable sub-tasks.
- [ ] Code implementation explicitly designated for delegation to worker subagents.
