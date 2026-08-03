---
trigger: model_decision
description: Mandatory SOLID, DRY, KISS, and YAGNI architectural rules and negative anti-hallucination constraints.
---

# Rule: Clean Code, SOLID Principles & Code Smells

**Identifier**: `clean-code-and-principles`

## 1. Core Architectural Directives

| Principle | Directive | Actionable Constraint |
| :--- | :--- | :--- |
| **SRP** | Single Responsibility | Functions **MUST** stay under 30 lines with a single reason to change. |
| **OCP** | Open / Closed | Extend via polymorphism/interfaces. **MUST NOT** use long `if-elif/switch` type-checks. |
| **LSP** | Liskov Substitution | Subtypes **MUST** fulfill parent contracts without weakening preconditions. |
| **ISP** | Interface Segregation | **MUST** build small, targeted interfaces instead of generic bloated ones. |
| **DIP** | Dependency Inversion | **MUST** inject abstractions (DB sessions, HTTP clients), never instantiate inline. |
| **DRY** | Don't Repeat Yourself | **MUST** extract repeated logic into single, shared utility modules. |
| **KISS** | Keep It Simple | **ALWAYS** choose the simplest working design. Avoid premature complexity. |
| **YAGNI**| You Aren't Gonna Need It | **MUST NOT** write speculative code, stubs, or unused interfaces for future needs. |

## 2. Anti-Hallucination & Quality Constraints

* **NEVER** swallow exceptions or mask errors using silent `try/except: pass` or empty catch blocks.
* **NEVER** return dummy fallback data (e.g. `{}` or `0`) on API/DB failures; raise explicit errors.
* **NEVER** edit or delete existing test assertions just to make a failing implementation pass.
* **MUST NOT** create God Classes (>300 lines) or methods with nesting depth > 3.
* **MUST** run workspace linters/formatters (`ruff`, `black`, `eslint`, `prettier`) before finalizing code.
* **MUST** use self-documenting code with intent-revealing names in English.
