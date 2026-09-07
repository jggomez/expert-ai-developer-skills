# Workflow: Build Incrementally (/build)

**Command**: `/build`  
**Key Principle**: *One slice at a time*  
**Identifier**: `build-workflow`

---

## 1. Objective
Construct production-ready code fulfilling the planned tasks incrementally, adhering strictly to Test-Driven Development (TDD) and clean code standards.

## 2. Operational Steps
1. **Intake Task & Contracts**:
   - Read relevant requirements, ADRs, and surrounding code before modifying files.
2. **Execute Strict TDD (Red-Green-Refactor)**:
   - **RED**: Write a minimal, deterministic unit test asserting the expected behavior. Run test and verify it fails.
   - **GREEN**: Write only the minimal production code necessary to make the test pass. Avoid speculative abstractions.
   - **REFACTOR**: Clean up design, eliminate code smells, enforce DRY and SOLID, and ensure all tests stay green.
3. **Build Vertical Slices**:
   - Deliver one complete slice at a time (e.g. Model -> Endpoint -> Test) before moving to the next.
4. **Static Analysis & Formatting**:
   - Format code (`ruff format`, `dart format`, `prettier`) and verify type-checking (`mypy`, `tsc`, `dart analyze`).

## 3. Delegation & Tools
- **Antigravity Subagent**: Delegate to `code-implementer` (or `flutter-implementer`).
- **Primary Skills**: `python-expert`, `fastapi-expert`, official Flutter/Dart skills, `code-smells-expert`.

## 4. Quality Gate Checklist
- [ ] Production code accompanied by automated unit tests.
- [ ] Zero unhandled compiler/linter warnings or type errors.
- [ ] All code, comments, and identifiers written in clear English.
