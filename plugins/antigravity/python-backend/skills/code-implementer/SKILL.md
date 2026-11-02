---
name: code-implementer
description: Guides the implementation of code using Test-Driven Development (TDD) and clean code principles. Trigger when implementing new features, fixing bugs, or refactoring existing code.
---

# Code Implementer Skill

## Overview
This skill guides the implementation of production-grade code adhering to Test-Driven Development (TDD), SOLID, DRY, and KISS principles. It acts as a Senior Code Implementer that translates architectural designs, interfaces, and product requirements into clean, well-tested, and maintainable software.

## When to Use
### Trigger Scenarios
- Writing new production code, API endpoints, algorithms, or services.
- Fixing identified bugs, security vulnerabilities, or regression defects.
- Executing code refactorings while preserving external behavior and contracts.
- Implementing features following architectural blueprints or design specifications.

### When NOT to Use
- **High-level system design & ADR authoring**: Route to `senior-architect-engineering` or `design-spec-expert`.
- **Requirements definition & PRD generation**: Route to `product-analyst`.
- **E2E & user-journey test suites**: Route to `qa-tester`.
- **Final release compliance & security sign-off**: Route to `compliance-verifier`.

## Process
### Phase 1: Context & Contract Ingestion
1. Read the Architecture Blueprint, PRD, or surrounding codebase contracts before writing code. For an isolated fix, inspect the target module and its existing unit tests.
2. Confirm system boundaries, schema types, and error handling policies.

### Phase 2: Test-Driven Development (TDD) Cycle
Enforce the strict Red-Green-Refactor loop:
1. **Red**: Write a failing unit or component test asserting the target behavior, matching AAA (Arrange-Act-Assert) pattern. Run the test to confirm failure for the expected reason.
2. **Green**: Write the minimal amount of production code needed to satisfy the test assertions. Avoid speculative generalizations or gold-plating.
3. **Refactor**: Clean up the implementation: eliminate duplication, improve variable naming, extract helper functions, and optimize performance while keeping all tests 100% green.

### Phase 3: Validation & Quality Gate
1. Execute the local unit test suite to verify 100% pass rate.
2. Run language formatters and linters (e.g., `black`, `ruff`, `eslint`, `dart format`).
3. Ensure no compiler or static analysis warnings remain.

## Usage
### Example Prompts
- *"Implement the user registration endpoint using strict TDD — write the failing unit test first, then the handler."*
- *"Fix the null pointer bug in the cart calculation service and add a regression test covering the edge case."*
- *"Refactor this payment adapter module to decouple Stripe API calls behind an interface, keeping tests green."*

### Host Execution Instructions
- **Claude Code**: Provide implementation tasks directly, specifying TDD Red-Green-Refactor expectations.
- **Antigravity**: Launch as the implementation subagent (`invoke_subagent`) following the design phase.

## Red Flags
- Writing production code before writing the failing test.
- Writing superficial assertions (e.g. `assert True` or checking only `status_code == 200` without validating payload).
- Swallowing exceptions with bare `except:` or silent fallbacks.
- Over-engineering abstractions for hypothetical future features (YAGNI violation).
- Leaving commented-out code or unused debug statements.

## Verification
- [ ] Failing test written and confirmed failing before implementation.
- [ ] 100% of unit and module tests pass with zero failures.
- [ ] No regression introduced to adjacent test suites.
- [ ] Code formatted and linted cleanly with zero warnings.
- [ ] Implementation satisfies all acceptance criteria without scope creep.

