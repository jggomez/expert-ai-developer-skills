# Workflow: Plan How to Build It (/plan)

**Command**: `/plan`  
**Key Principle**: *Small, atomic tasks*  
**Identifier**: `plan-workflow`

---

## 1. Objective
Restore cross-AI LLM Wiki context (`context/memory/`), evaluate the **Mandatory Discovery & Architecture Triage Gate**, architect the system solution, record Architectural Decision Records (ADRs), and decompose the feature into small, atomic, independently verifiable tasks organized into **Parallel Execution Tracks** with explicit workspace isolation (`Disjoint Files` vs. `Git Worktree`).

## 2. Operational Steps
1. **Restore LLM Wiki Memory (`State 0`)**:
   - Check if `context/memory/MEMORY.md` exists; if so, read it silently (~500 tokens) to restore cross-AI handoff state. Read `context/memory/architecture.md`, `conventions.md`, or `log/YYYY-MM-DD.md` only on demand.
2. **Evaluate the Discovery & Architecture Triage Matrix (`State 0 -> State 1`)**:
   - Before writing implementation tasks for `code-implementer`, evaluate both discovery specialists against the mandatory rubric and embed the `## Discovery & Architecture Triage` table in `PLAN.md`:

   | Specialist | Mandatory Invocation Criteria (`MUST INVOKE`) | Allowed Skip Criteria (`MAY SKIP`) |
   | :--- | :--- | :--- |
   | **`product-analyst`** | - New user-facing feature or workflow<br>- Unstated edge cases, permissions, or validation rules<br>- Open-ended or ambiguous business prompt | - Pure technical bugfix with known root cause<br>- Internal refactor with zero user-facing behavior change<br>- Complete PRD already exists on disk |
   | **`architect-engineer`** | - Creates or modifies **>= 2 files or modules**<br>- Changes database schemas, migrations, or API contracts<br>- Introduces a new design pattern or external dependency<br>- Crosses architectural layers | - Single-file localized fix where the architecture and interfaces are already established |

3. **Analyze Trade-offs & Architecture (`State 1`)**:
   - When triggered by the Triage Matrix, invoke `product-analyst` and/or `architect-engineer` (sequentially or in parallel fan-out) **before** delegating to `code-implementer`.
   - Evaluate architecture patterns (Hexagonal, Clean, Layered) and record trade-offs in an ADR under `doc/adr/` (or `docs/adr/`).
4. **Author `PLAN.md` with Parallel Track & Isolation Mode Classification**:
   - The Orchestrator authors `PLAN.md` directly, establishing the Graph Engineering DAG, the `## Discovery & Architecture Triage` table, and atomic task checklists.
   - Break implementation into small tasks (each touching 1-3 files where possible) sequenced bottom-up: Interfaces/Contracts -> Core Domain -> Data Layer -> Presentation/UI.
   - Classify parallel tracks by **Workspace Isolation Mode**:
     * **Mode A — Disjoint File Partitioning (`Disjoint Files` / `Workspace: 'inherit'`) [DEFAULT]**: Parallel `code-implementer` tracks modify strictly non-overlapping files/directories. Each track declares an explicit `Exclusive Owned Files` list. Zero `git merge` overhead upon Fan-In.
     * **Mode B — Git Worktree Isolation (`Git Worktree` / `Workspace: 'branch'` or `Workspace: 'share'`)**: Parallel `code-implementer` tracks must touch shared files (e.g., `package.json`, shared routers, DI containers) or run conflicting builds. Each track runs in an isolated git branch/worktree and merges cleanly at Fan-In.

   ```markdown
   ## Discovery & Architecture Triage
   | Specialist | Decision (`INVOKE` / `SKIP`) | Rationale |
   | :--- | :--- | :--- |
   | `product-analyst` | `INVOKE` / `SKIP` | <concrete reason per rubric> |
   | `architect-engineer` | `INVOKE` / `SKIP` | <concrete reason per rubric> |

   ## Parallel Execution Tracks
   | Track ID | Subagent | Isolation Mode (`Disjoint Files` / `Git Worktree`) | Exclusive Owned Files | Verification Command |
   | :--- | :--- | :--- | :--- | :--- |
   | Track A | `code-implementer` | `Disjoint Files` | `src/domain/*`, `tests/unit/domain/*` | `pytest tests/unit/domain/` |
   | Track B | `code-implementer` | `Disjoint Files` | `src/infra/*`, `tests/unit/infra/*` | `pytest tests/unit/infra/` |
   ```

5. **Define Verifiable Success Criteria (`State 3 & 4`)**:
   - Document exact test commands for `qa-tester` (`exit code 0` proof) and compliance checks for `compliance-verifier` (`APPROVED` verdict), executed in parallel upon implementation Fan-In.

## 3. Subagent Delegation & Inviolable Role Boundaries
- **Inviolable Role Boundaries**:
  * `PLAN.md` is strictly authored and maintained by the Lead Orchestrator (`senior-dev-orchestrator` or `flutter-feature-orchestrator`).
  * Requirements disambiguation (`product-analyst`) and architecture design/ADR generation (`architect-engineer` or `flutter-architect`) are delegated per the Discovery Triage Matrix.
  * The Orchestrator is strictly prohibited from implementing code; all code implementation is delegated to dedicated worker subagents (`code-implementer` or `flutter-implementer`).
- **Subagent Delegation across Runners**:
  * **Google Antigravity** (Single or Parallel Fan-Out):
    ```python
    invoke_subagent(
        name="architect-engineer",
        prompt="Analyze system architecture and draft ADR for: <technical-scope>"
    )
    ```
    *(For parallel discovery or implementation fan-out, pass multiple entries in `Subagents=[...]` with `Workspace: 'inherit'` for Disjoint Files or `Workspace: 'branch'` for Git Worktree; for Flutter applications, use `name="flutter-architect"`)*
  * **Anthropic Claude Code** (Single or Concurrent Fan-Out):
    ```python
    Agent(
        agent="architect-engineer",
        prompt="Analyze system architecture and draft ADR for: <technical-scope>"
    )
    ```
    *(Emit multiple `Agent(...)` calls in the same turn for parallel fan-out; for Flutter applications, use `agent="flutter-architect"`)*
- **Primary Skills**: `senior-dev-orchestrator`, `senior-architect-engineering`, `product-analyst`, `loop-engineering`, `context-restore`, `context-capture`, `design-spec-expert`, `flutter-architecture-decisions`.

## 4. Quality Gate Checklist
- [ ] `context/memory/MEMORY.md` silently checked/restored at `State 0`.
- [ ] `## Discovery & Architecture Triage` matrix evaluated and recorded in `PLAN.md`.
- [ ] Architecture aligns with SOLID and clean design principles; ADR drafted and saved in `doc/adr/` if architectural decisions were made.
- [ ] `PLAN.md` authored by Orchestrator with atomic sub-tasks and `## Parallel Execution Tracks` specifying `Disjoint Files` vs. `Git Worktree` isolation.
- [ ] Code implementation explicitly designated for delegation to worker subagents (`code-implementer` / `flutter-implementer`), followed by parallel `qa-tester` and `compliance-verifier` gates.
