---
trigger: model_decision
description: Enforce SOLID, DRY, and KISS principles, code smell prevention, clean naming conventions, and refactoring strategies.
---

# Rule: Clean Code, SOLID Principles & Code Smell Prevention

**Identifier**: `clean-code-and-principles`  
**Purpose**: Enforce high code readability, maintainability, and structural integrity by applying SOLID, DRY, and KISS principles and actively eliminating technical debt/code smells.

---

## 1. Core Architectural Principles

AI agents and developers must strictly adhere to these design principles:

| Principle | Core Directive | Actionable Enforcement |
| :--- | :--- | :--- |
| **S**ingle Responsibility (SRP) | A module, class, or function must have *one, and only one, reason to change*. | Keep functions under 30 lines. Extract complex logic into helper classes/modules. |
| **O**pen/Closed (OCP) | Software entities should be *open for extension, but closed for modification*. | Use interfaces, abstract bases, and polymorphism instead of long `if-elif` / `switch` statements matching types. |
| **L**iskov Substitution (LSP) | Subtypes must be completely substitutable for their base types without altering correctness. | Derived classes must not weaken preconditions or strengthen postconditions of parent contracts. |
| **I**nterface Segregation (ISP) | Clients should not be forced to depend on methods they do not use. | Create small, specialized interfaces rather than large, generic ones. |
| **D**ependency Inversion (DIP) | Depend on abstractions, not on concrete implementations. | Inject database sessions, configuration objects, and HTTP clients instead of hardcoding their creation inside components. |
| **DRY** (Don't Repeat Yourself) | Every piece of knowledge must have a single, unambiguous representation in the system. | Abstract duplicated logic into shared utility files or packages. |
| **KISS** (Keep It Simple, Stupid) | Systems work best if they are kept simple rather than made complex. | Avoid premature optimizations, abstract patterns for trivial logic, or complex nested loops. |
| **YAGNI** (You Aren't Gonna Need It) | Do not write code based on anticipated future needs. | Focus solely on current user requirements. Avoid stubbing out empty interfaces or classes for "future features". |

---

## 2. Code Smells: Zero Tolerance Policy

Actively detect and refactor these common code smells during code reviews and modifications:

* **God Classes / Large Modules**: Class files exceeding 300 lines or handling multiple distinct tasks. *Solution: Split into separate single-purpose components.*
* **Long Methods**: Functions exceeding 30-50 lines or containing nested block depths > 3. *Solution: Use "Extract Method" refactoring.*
* **Duplicated Code**: Identical or highly similar code segments found in multiple places. *Solution: Extract into a common utility or base class.*
* **Primitive Obsession**: Using raw types (strings, integers) to represent domain concepts (URLs, emails, coordinates). *Solution: Introduce typed models or schemas (e.g., Pydantic schemas, TypeScript interfaces).*
* **Feature Envy**: A method that accesses the data of another object more than its own. *Solution: Move the method to the object whose data it accesses.*
* **Shotgun Surgery**: A change that requires modifying multiple small files across the repository. *Solution: Consolidate the shared logic or structural concerns into a single module.*

---

## 3. Code Aesthetics & Naming Conventions

* **Self-Documenting Code**: Choose descriptive, intention-revealing names for variables, functions, and classes. Avoid names like `temp`, `data`, `process`, `run`.
  * *Bad*: `def handle(d):`
  * *Good*: `def calculate_average_score(scores: list[float]) -> float:`
* **Comment Integrity**: Only write comments to explain the *Why*, not the *What*. Useless, redundant comments explaining obvious lines must be deleted.
* **Linting & Formatting Enforcement**: Automatically run the workspace linters and formatters before submitting code changes.
  * For Python: Ensure PEP 8 compliance using `ruff`, `black`, and static analysis with `mypy`.
  * For JS/TS: Ensure compliance with `eslint` and `prettier`.

---

## 4. Refactoring Strategy

When refactoring code:
1. Ensure the existing unit tests pass before making any changes.
2. Make small, surgical, incremental modifications.
3. Verify tests pass after *each* step to isolate regression issues.
4. Refactor solely for structure, never mix refactoring changes with new features in the same commit.
