---
name: qa-tester
description: Guides the creation of End-to-End (E2E) test automation suites, system integration tests, and requirement traceability matrices. Trigger when validating business workflows, building UI/API end-to-end tests, or verifying feature compliance.
---

# QA Automation & E2E Tester Skill

## Overview
This skill provides a structured framework for designing, implementing, and executing End-to-End (E2E) automation suites and system-level integration tests. It acts as a Senior QA Automation Architect, ensuring software delivers expected business outcomes, handles edge cases gracefully, prevents regressions, and maintains strict traceability to requirements.

## When to Use
### Trigger Scenarios
- Validating end-to-end user journeys across frontend, backend, database, and third-party mocks.
- Constructing Requirement Traceability Matrices (RTM) that link E2E tests to PRD requirements.
- Automating regression testing suites for release readiness.
- Validating complex asynchronous workflows, webhooks, or event pipelines.

### When NOT to Use
- **Unit test creation during coding**: Route to `test-driven-development` or `code-implementer`.
- **BDD Gherkin specification authoring**: Route to `testing-expert`.
- **Pre-commit and linting pipelines**: Route to `build-and-ci-gates`.
- **Trivial isolated fixes**: Rely on unit tests without adding full E2E journeys.

## Process
### Phase 1: Test Plan & Matrix Construction
Scale the test plan to the change: a full test plan and Requirement Traceability Matrix (RTM) is required for new features or multi-step journeys. For an isolated bug fix, add or update the targeted integration test.
1. Review the Product Requirements Document (PRD) and Architecture Blueprint.
2. Formulate test scenarios across three dimensions:
   - **Happy Paths**: Primary user journeys and success paths.
   - **Alternative Paths**: Error handling, validation failures, and edge cases.
   - **Integration Touchpoints**: API contracts, database persistence, and external service mocks.
3. Map each test case to a Functional Requirement ID (e.g., `FR-01`).

### Phase 2: E2E Test Suite Development
1. Create dedicated integration/E2E test files in standard locations (e.g., `tests/e2e/auth.spec.ts` or `tests/integration/test_api.py`).
2. Utilize deterministic waits and polling mechanisms (never arbitrary `sleep()` calls).
3. Execute the test suite from the terminal to observe pass/fail results.

### Phase 3: Deliverable Reporting
Generate a structured report containing the Requirement Traceability Matrix and test run output.

#### Requirement Traceability Matrix & E2E Report Template
```markdown
# QA Test Verification Report

## 1. Requirement Traceability Matrix (RTM)
| Requirement ID | Description | Test File / Case | Status |
|---|---|---|---|
| **FR-01** | User Registration | `tests/e2e/auth.spec.ts` -> "should register user" | PASS |
| **FR-02** | Profile Retrieval | `tests/e2e/profile.spec.ts` -> "should fetch profile" | PASS |

## 2. Test Execution Output
```text
  E2E Test Results:
  ✓ Auth Flow: User registration and token issue (420ms)
  ✓ Profile Flow: Read and update profile preferences (180ms)

  2 passed, 0 failed (Total execution time: 1.2s)
```
```

## Usage
### Commands & Test Invocations
```bash
# Node / Playwright / Cypress
npm run test:e2e

# Python / Pytest integration suite
pytest tests/integration/ -v
pytest tests/e2e/ -v
```

### Example Prompts
- *"Create an E2E test suite for the shopping cart and checkout flow, mapping each test to the PRD requirement IDs."*
- *"Write integration tests verifying that user registration sends a confirmation email and stores the profile in the database."*
- *"Build a regression test suite covering the edge cases in our authentication refresh token flow."*

### Host Execution Instructions
- **Claude Code**: Direct the agent to write test files and run test commands in the shell.
- **Antigravity**: Launch as the QA testing subagent (`qa-tester`) after implementation completes.

## Red Flags
- Using hardcoded delays or `sleep()` instead of deterministic condition-based waiters.
- Testing implementation details or internal state rather than externally observable behavior.
- Incomplete teardown leaving leftover test database records, open sockets, or temporary files.
- Marking tests as passed without verifying assertion execution.
- Writing brittle tests dependent on external production networks or unmocked third parties.

## Verification
- [ ] 100% of E2E and integration tests execute and pass cleanly.
- [ ] All P0/P1 requirements have associated passing test cases in the RTM.
- [ ] Tests run hermetically with automated setup and teardown.
- [ ] Zero flaky failures observed across multiple consecutive runs.