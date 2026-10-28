---
name: qa-tester
description: Guides the creation of End-to-End (E2E) test automation suites, system integration tests, and standardized QA Test Matrix artifacts. Trigger when validating business workflows, building UI/API end-to-end tests, or verifying feature compliance.
---

# QA Automation & E2E Tester Skill

## Overview
This skill provides a rigorous framework for designing, implementing, and executing End-to-End (E2E) automation suites, system integration tests, and standardized QA Test Matrix artifacts (`docs/<feature-name>/test-matrix.md`). It acts as a Senior QA Automation Architect and Integration Specialist, ensuring software delivers expected business outcomes, handles edge cases gracefully, prevents regressions, adheres to the test pyramid, and maintains strict traceability to requirements backed by empirical terminal execution evidence (`exit code 0`).

## When to Use
### Trigger Scenarios
- Validating end-to-end user journeys across frontend, backend, database, and third-party mocks.
- Constructing the standardized **QA Test Matrix Artifact** (`docs/<feature-name>/test-matrix.md`) mapping test suites to PRD acceptance criteria.
- Validating test coverage across the Test Pyramid (Unit, Integration, E2E/Component).
- Designing exhaustive test cases covering Happy Paths, Negative Scenarios, and Boundary/Edge Cases.
- Automating regression testing suites for release readiness.
- Validating complex asynchronous workflows, webhooks, or event pipelines.

### When NOT to Use
- **Unit test creation during initial coding**: Route to `test-driven-development` or `code-implementer`.
- **BDD Gherkin specification authoring**: Route to `testing-expert`.
- **Pre-commit and linting pipelines**: Route to `build-and-ci-gates`.
- **Tier 1 Fast-Track isolated bug fixes**: Run scoped tests directly without generating an exhaustive E2E matrix.

## Process
### SDLC Tier Adaptation
- **Tier 1 (Fast-Track / Low Complexity)**: Single-file bugfixes, typos, chores. Run the targeted test suite directly and provide scoped terminal proof (`exit code 0`). Standard `test-matrix.md` generation is bypassed to preserve 70–85% token and latency savings.
- **Tier 2 (Standard / Medium Complexity)**: 2–4 files, new endpoint, single UI view, schema changes. Author standardized `docs/<feature-name>/test-matrix.md`, execute full unit and integration suites with terminal proof (`exit code 0`).
- **Tier 3 (Mission-Critical / Complex)**: Full end-to-end features, payment/auth flows, architectural changes. Author comprehensive `docs/<feature-name>/test-matrix.md` covering all pyramid tiers (unit, integration, e2e/component), and participate in the **Adversarial Verification Committee** alongside `critic`, `challenger`, and `e2e-blackbox-tester`.

### Phase 1: Test Plan & Matrix Construction
1. Review the Product Requirements Document (`docs/<feature-name>/prd.md`) and Architecture Blueprint (`docs/<feature-name>/architecture.md`).
2. Extract all User Stories and Acceptance Criteria (AC).
3. Formulate test scenarios across three critical dimensions:
   - **Happy Paths (Positive)**: Primary user journeys, valid state transitions, and expected success payloads.
   - **Negative Test Cases**: Malformed inputs, missing headers, authentication/authorization failures, invalid schemas, and unexpected payloads.
   - **Boundary & Edge Cases**: Minimum/maximum data extremes, null/empty collections, race conditions, timeouts, rate limits, and network latency drops.
4. Classify test scenarios into the **Test Pyramid**:
   - **Unit**: Isolated module functions, pure domain logic, value objects, and schemas.
   - **Integration**: Database persistence, API contracts, cross-module communication, and service stubs.
   - **E2E / Component**: Complete end-to-end user journeys and system interactions.

### Phase 2: Automated Test Suite Development & Execution
1. Create dedicated integration/E2E test files in standard directory hierarchies (e.g., `tests/integration/test_*.py`, `tests/e2e/test_*.py`, or `cypress/e2e/*.spec.ts`).
2. Utilize deterministic waits, polling assertions, or event listeners (strictly forbidden from using arbitrary `sleep()` delays).
3. Follow the Arrange-Act-Assert (AAA) pattern.
4. Execute test runners via the terminal (`pytest`, `flutter test`, `npm test`) and capture verbatim stdout/stderr output. Verify empirical proof with `exit code 0`.

### Phase 3: Deliverable Reporting — Standardized QA Test Matrix
Generate the standardized markdown artifact at `docs/<feature-name>/test-matrix.md` using the exact canonical structure:

```markdown
# QA Test Matrix: <feature-name>

## 1. Feature & Specification Metadata
- **Feature Slug**: `<feature-name>`
- **PRD Reference**: `docs/<feature-name>/prd.md`
- **Architecture Reference**: `docs/<feature-name>/architecture.md`
- **SDLC Tier**: Tier 2 (Standard) | Tier 3 (Mission-Critical)
- **Target Environments / Suites**: Unit, Integration, E2E

## 2. Requirement Traceability Matrix (RTM) & Acceptance Criteria Mapping
| Requirement / AC ID | User Story / Acceptance Criteria | Test File & Case Name | Pyramid Level | Scenario Type | Status |
|---|---|---|---|---|---|
| **AC-01** | User authenticates with valid credentials | `tests/integration/test_auth.py::test_login_success` | Integration | Happy Path | PASS |
| **AC-02** | Invalid credentials return 401 Unauthorized | `tests/integration/test_auth.py::test_login_invalid_password` | Integration | Negative | PASS |
| **AC-03** | Empty email/password rejected with 422 Unprocessable | `tests/unit/test_auth_schema.py::test_missing_fields` | Unit | Negative | PASS |
| **AC-04** | Rapid consecutive logins trigger rate limiting | `tests/e2e/test_rate_limits.py::test_rate_limit_lockout` | E2E | Boundary / Edge | PASS |

## 3. Test Pyramid Classification
| Pyramid Tier | Scope & Focus | Framework / Runner | Total Tests | Passed | Pass Rate |
|---|---|---|---|---|---|
| **Unit** | Isolated functions, domain entities, value objects | `pytest tests/unit/` | 14 | 14 | 100% |
| **Integration** | Service boundaries, DB persistence, API contracts | `pytest tests/integration/` | 8 | 8 | 100% |
| **E2E / Component** | End-to-end user journeys, UI flows, service mocks | Playwright / Cypress / `pytest tests/e2e/` | 4 | 4 | 100% |

## 4. Scenario Categories & Coverage Analysis
### 4.1. Happy Path (Positive) Test Cases
- [x] Primary workflow success under standard operating conditions.
- [x] Expected state transitions, database records, and response payloads.

### 4.2. Negative Test Cases
- [x] Malformed or missing headers/payloads.
- [x] Unauthorized access, expired tokens, or invalid permissions.
- [x] Unhandled exception recovery and standardized error response models.

### 4.3. Boundary & Edge Cases
- [x] Input extremes (0, -1, max string length, empty collections, nulls).
- [x] Race conditions, concurrency conflicts, and idempotent retries.
- [x] Network timeouts, latency spikes, and external service dependency degradation.

## 5. Empirical Execution Proof Log
```text
$ pytest tests/ -v
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.0.2
collected 26 items

tests/unit/test_auth_schema.py::test_missing_fields PASSED               [  4%]
tests/integration/test_auth.py::test_login_success PASSED                [ 50%]
tests/integration/test_auth.py::test_login_invalid_password PASSED       [ 75%]
tests/e2e/test_rate_limits.py::test_rate_limit_lockout PASSED           [100%]

============================== 26 passed in 1.45s ==============================
Exit Code: 0
```
```

## Usage
### Commands & Test Invocations
```bash
# Node / Playwright / Cypress
npm run test:e2e

# Python / Pytest integration and E2E suites
pytest tests/integration/ -v
pytest tests/e2e/ -v

# Full suite verification with exit code capture
pytest tests/ -v
```

### Example Prompts
- *"Construct the QA test matrix in docs/order-checkout/test-matrix.md covering happy paths, negative cases, and edge cases across the test pyramid."*
- *"Create an E2E test suite for the shopping cart and checkout flow, mapping each test case to the PRD acceptance criteria."*
- *"Execute the full integration test suite, capturing terminal proof with exit code 0 to satisfy the QA verification gate."*

### Host Execution Instructions
- **Claude Code**: Author test files using `Write` / `Edit` and run tests via `Bash`, generating `docs/<feature-name>/test-matrix.md`.
- **Antigravity**: Launch as the QA testing subagent (`qa-tester`) using `run_command` to execute tests and `write_to_file` to author `docs/<feature-name>/test-matrix.md`.

## Red Flags
- Reporting tests as passed without real terminal execution evidence and `exit code 0`.
- Missing any of the required sections in `docs/<feature-name>/test-matrix.md` (metadata, RTM, pyramid classification, scenario categories, proof log).
- Omitting negative test cases or boundary/edge conditions from the test matrix.
- Generating bloated test matrices for Tier 1 trivial fixes instead of executing targeted scoped tests.
- Using hardcoded delays or `sleep()` instead of deterministic condition-based waiters.
- Testing implementation details or internal state rather than externally observable behavior.
- Incomplete teardown leaving leftover database records, open ports, or mock state leaks.

## Verification
- [ ] Standardized QA Test Matrix artifact created at `docs/<feature-name>/test-matrix.md` for Tier 2 and Tier 3 tasks.
- [ ] All PRD acceptance criteria mapped to specific test cases in the Requirement Traceability Matrix.
- [ ] Happy path, negative, and boundary/edge test cases explicitly documented and verified.
- [ ] Test Pyramid coverage (unit, integration, e2e/component) classified with pass rates.
- [ ] Empirical terminal execution proof log included showing verbatim runner output with `exit code 0`.
- [ ] All tests execute hermetically with zero flakiness and clean teardown.