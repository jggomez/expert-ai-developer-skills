---
name: code-implementer
description: Guides the implementation of code using Test-Driven Development (TDD) and clean code principles. Trigger when implementing new features, fixing bugs, or refactoring existing code.
---

# Code Implementer Skill

## Overview
This skill provides instructions for the `code-implementer` subagent to write clean, maintainable, and well-tested production code following strict TDD practices.

## Procedural Workflow

### Phase 1: Context & Requirements
1. Read the Architecture Blueprint and Product Requirements before writing code.
2. Confirm that system boundaries, module contracts, and project rules are understood.

### Phase 2: Test-Driven Development (TDD)
Execute the Red-Green-Refactor cycle:
- **Red**: Write a failing unit test that verifies the expected behavior based on the requirements.
- **Green**: Write the minimal amount of production code needed to pass the failing test. Do not over-engineer.
- **Refactor**: Improve the code structure, readability, and performance. Eliminate any code smells while keeping all tests passing.

### Phase 3: Validation
1. Execute the test suite locally to ensure 100% pass rate.
2. Ensure linters and formatters pass cleanly.
