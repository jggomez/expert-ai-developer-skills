# Workflow: Simplify the Code (/code-simplify)

**Command**: `/code-simplify`  
**Key Principle**: *Clarity over cleverness*  
**Identifier**: `code-simplify-workflow`

---

## 1. Objective
Refactor complex, convoluted, or over-engineered code to minimize cognitive overhead, eliminate dead code, and reduce technical debt while strictly preserving external behavior.

## 2. Operational Steps
1. **Establish Test Baseline**:
   - Ensure automated unit and integration tests are green before touching code. Never refactor without test coverage!
2. **Scan for Over-Engineering & Code Smells**:
   - God classes, long methods (>30 lines), deep nesting (>3 levels).
   - Speculative generalizations, unused interfaces, dead code, redundant wrappers.
   - Duplicated logic (violating DRY).
3. **Execute Surgical Simplification**:
   - Extract small, single-purpose functions.
   - Replace complex nested conditions with guard clauses and early returns.
   - Flatten unnecessary abstraction layers.
4. **Continuous Regression Testing**:
   - Run tests after every single transformation to ensure zero behavior changes.

## 3. Subagent Delegation & Role Boundaries
- **Role Boundary**: The Lead Orchestrator directs simplification objectives; actual code modifications are delegated to `code-implementer` (or `flutter-implementer`).
- **Subagent Delegation across Runners**:
  * **Google Antigravity**:
    ```python
    invoke_subagent(
        name="code-implementer",
        prompt="Surgically refactor and simplify code to remove smells while keeping all tests passing for: <file-or-module>"
    )
    ```
    *(For Flutter applications, use `name="flutter-implementer"`)*
  * **Anthropic Claude Code**:
    ```python
    Agent(
        agent="code-implementer",
        prompt="Surgically refactor and simplify code to remove smells while keeping all tests passing for: <file-or-module>"
    )
    ```
    *(For Flutter applications, use `agent="flutter-implementer"`)*
- **Primary Skills**: `refactoring-code-expert`, `code-smells-expert`, `guidelines-karpathy`.

## 4. Quality Gate Checklist
- [ ] Automated tests pass with 100% success before and after refactoring.
- [ ] External API contracts and runtime behavior strictly preserved.
- [ ] Cognitive complexity and line counts visibly reduced.
- [ ] Dead code, unused abstractions, and redundant comments removed.
