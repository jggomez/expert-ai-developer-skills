---
name: refactoring-code-expert
description: Executes structural improvements on existing code to increase maintainability, readability, and extensibility without altering external behavior. Use this skill to address technical debt, fix "Code Smells", apply design patterns, or improve adherence to SOLID principles.
---

# Refactoring Code Expert Skill

## Overview
This skill guides safe, disciplined, and incremental structural improvements to existing codebases without modifying external behavior. It acts as a Senior Software Architect and Refactoring Specialist, treating refactoring not as a risky "big-bang rewrite", but as a controlled sequence of micro-transformations protected by a robust automated test safety net.

## When to Use
### Trigger Scenarios
- Eliminating code smells (God classes, long methods, duplicated logic, high cyclomatic complexity).
- Restructuring messy or legacy code to adhere to SOLID, DRY, and KISS principles.
- Decoupling tightly coupled components using Dependency Inversion or Ports & Adapters.
- Preparing a module for new features by first making the change easy (pre-factoring).

### When NOT to Use
- **Adding new functional capabilities or modifying contracts**: Route to `code-implementer` or `test-driven-development`.
- **Pure smell diagnosis without altering code**: Route to `code-smells-expert`.
- **Database schema modifications**: Route to `database-migration-expert`.
- **Authoring new architectural specifications**: Route to `senior-architect-engineering`.

## Process
### Phase 1: Test Safety Net & Characterization
1. **The Golden Rule**: Refactoring changes internal structure, NEVER external behavior. If observable behavior changes, the refactoring is broken.
2. Verify existing test coverage before editing any code:
   ```bash
   python3 ./skills/refactoring-code-expert/scripts/run_tests.py
   ```
3. If tests are absent or inadequate, write minimal "Characterization Tests" to pin down existing behavior before modifying the implementation.

### Phase 2: Micro-Refactoring Sequence Plan
Formulate a sequence of atomic, low-risk micro-refactorings:
- *Extract Method / Function*: Isolate cohesive blocks of logic into well-named functions.
- *Introduce Parameter Object*: Group related parameters into a dataclass or value object.
- *Replace Conditional with Polymorphism*: Replace complex `if/else` or `switch` trees with strategy classes.
- *Rename Symbol*: Replace cryptic names with self-documenting domain identifiers.

### Phase 3: Incremental Execution Loop
Execute the changes one step at a time:
1. Apply a single micro-refactoring.
2. Run the test suite: `python3 ./skills/refactoring-code-expert/scripts/run_tests.py`.
3. If green, proceed to the next step. If red, undo immediately and diagnose before proceeding.
4. Leave the codebase cleaner than you found it (Boy Scout Rule).

## Usage
### Commands & Automation Scripts
```bash
# Detect and execute test suite before and after refactorings
python3 ./skills/refactoring-code-expert/scripts/run_tests.py
```

### Example Prompts
- *"Refactor this 250-line order processing function to extract validation and payment logic, keeping all tests passing."*
- *"Refactor this legacy user manager class to decouple it from direct database queries via repository interfaces."*
- *"Apply the strategy pattern to clean up this large nested switch statement in our shipping rate calculator."*

### Host Execution Instructions
- **Claude Code**: Run `run_tests.py` via the bash tool between micro-refactorings to guarantee continuous green state.
- **Antigravity**: Apply changes incrementally, verifying test suite execution at each step before completing the turn.

## Red Flags
- Changing external API behavior or function return signatures while claiming to refactor.
- Refactoring without a green, passing test suite.
- Attempting a large-scale rewrite all at once rather than baby steps.
- Introducing complex design patterns where a simple function extraction would suffice.
- Commenting out tests or assertions to make a refactored module pass.

## Verification
- [ ] 100% of unit and integration tests pass before starting and after completion.
- [ ] Automated test runner exits cleanly with zero failures:
  ```bash
  python3 ./skills/refactoring-code-expert/scripts/run_tests.py
  ```
- [ ] Public interfaces, schemas, and observable behaviors remain strictly identical.
- [ ] Target code smells and cyclomatic complexity are demonstrably reduced.

## References
For detailed catalogs of code transformations and step-by-step mechanics:
- [Refactoring Techniques Reference](references/refactoring-techniques.md)