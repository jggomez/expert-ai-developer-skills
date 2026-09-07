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
2. **Decompose into Atomic Tasks**:
   - Break implementation into small tasks (each touching 1-3 files maximum).
   - Sequence tasks to build bottom-up: Interfaces/Contracts -> Core Domain -> Data Layer -> Presentation/UI.
3. **Analyze Dependencies & Parallelization**:
   - Identify disjoint tasks eligible for parallel subagent execution (`Workspace='branch'` or `Workspace='share'`).
4. **Define Verifiable Success Criteria**:
   - Document exact test commands for each task.

## 3. Delegation & Tools
- **Antigravity Subagent**: Delegate to `architect-engineer` (or `flutter-architect` for Flutter apps).
- **Primary Skills**: `senior-architect-engineering`, `design-spec-expert`.

## 4. Quality Gate Checklist
- [ ] Architecture aligns with SOLID and clean design principles.
- [ ] ADR drafted and saved in `doc/adr/` if architectural decisions were made.
- [ ] Every sub-task is atomic, single-purpose, and independently testable.
- [ ] Plan artifact generated and reviewed.
