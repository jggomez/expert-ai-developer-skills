---
name: testing-expert
description: Guidelines, best practices, and templates for automated and manual software testing across languages. Covers Arrange-Act-Assert (AAA), mocking boundaries, and writing human-readable specifications using Gherkin BDD syntax.
---

# Testing Expert Skill

## Overview
This skill guides the design, structuring, and validation of automated test suites and Behavior-Driven Development (BDD) specifications. It acts as a Lead QA Engineer and Test Automation Specialist, ensuring that tests are hermetic, isolated, self-documenting, structured using the Arrange-Act-Assert (AAA) pattern, and specified using valid Gherkin syntax.

## When to Use
### Trigger Scenarios
- Designing test suites across the testing pyramid (Unit, Component, Integration, System).
- Authoring human-readable BDD specifications using Gherkin (`.feature` files).
- Standardizing test structures using the Arrange-Act-Assert (AAA) convention.
- Auditing and validating Gherkin scenario syntax and parameterization tables.

### When NOT to Use
- **Day-to-day TDD implementation cycle**: Route to `test-driven-development` or `code-implementer`.
- **E2E user journey test execution and RTM reporting**: Route to `qa-tester`.
- **CI/CD pipeline test runner setup**: Route to `build-and-ci-gates`.
- **Static code smell scanning**: Route to `code-smells-expert`.

## Process
### Phase 1: BDD Specification Design in Gherkin
Draft human-readable feature specifications using standard Gherkin keywords:
- **`Feature`**: High-level business capability being validated.
- **`Background`**: Shared setup prerequisites across scenarios in the feature.
- **`Scenario` / `Scenario Outline`**: Discrete behavioral specification.
  - **`Given`**: Initial state or prerequisite setup.
  - **`When`**: Specific action or event triggered by the user/system.
  - **`Then`**: Observable outcome and expected assertion.
  - **`Examples`**: Parameterization table mapping boundary values.

### Phase 2: Hermetic AAA Test Layout
Structure both unit and integration tests strictly according to the AAA pattern:
1. **Arrange**: Set up inputs, mocks, test fixtures, and expected parameters.
2. **Act**: Execute the single unit of behavior under test.
3. **Assert**: Verify the expected outcome with specific, unambiguous assertions.
*Hermeticity Rule: Every test must be completely isolated, with zero state carried over between test executions.*

### Phase 3: Automated Gherkin Syntax Validation
Execute the Gherkin validator script to detect structural defects (missing Examples tables, bad Background ordering, duplicate names, or step-less scenarios):
```bash
python3 ./skills/testing-expert/scripts/validate_gherkin.py
```

## Usage
### Commands & Automation Scripts
```bash
# Validate all Gherkin .feature files in the repository
python3 ./skills/testing-expert/scripts/validate_gherkin.py
```

### Example Prompts
- *"Write Gherkin BDD scenarios for the password reset workflow, covering happy paths and lockout boundaries."*
- *"Structure this integration test suite using strict Arrange-Act-Assert partitions and hermetic mocks."*
- *"Validate all .feature files in our tests directory for syntax errors."*

### Host Execution Instructions
- **Claude Code**: Run `validate_gherkin.py` via bash to audit `.feature` files.
- **Antigravity**: Verify BDD specifications before generating test step definitions.

## Red Flags
- Order-dependent tests that fail when run in isolation or random order.
- `Scenario Outline` blocks missing the required `Examples:` data table.
- Testing multiple unrelated behaviors inside a single test case.
- Calling external live third-party network APIs in unit or integration test suites.

## Verification
- [ ] Automated Gherkin validator passes cleanly with zero syntax violations:
  ```bash
  python3 ./skills/testing-expert/scripts/validate_gherkin.py
  ```
- [ ] All tests follow Arrange-Act-Assert (AAA) separation.
- [ ] External network and database dependencies mocked in unit test suites.
- [ ] Scenarios test externally visible behavior rather than internal private state.

## References
- [Software Testing Best Practices Reference](references/testing-best-practices.md)
- [Behavior-Driven Development (BDD) & Gherkin Syntax](references/gherkin-syntax.md)

