---
name: qa-tester
description: Guides the creation of End-to-End (E2E) test automation suites, system integration tests, and requirement traceability matrices. Trigger when validating business workflows, building UI/API end-to-end tests, or verifying feature compliance.
---

# QA Automation & E2E Tester Skill

## Overview
This skill provides a structured workflow for designing, implementing, and running End-to-End (E2E) and integration tests. It validates that the application satisfies business goals, handles boundary conditions gracefully, and avoids regressions.

## Procedural Workflow

### Phase 1: Test Plan & Matrix Construction
1. Review the Product Requirements Document (PRD) and Architecture Blueprint.
2. Formulate test scenarios for:
   - **Happy Paths**: Core expected user journeys.
   - **Alternative Paths**: Edge cases and input boundary failures.
   - **Integration Touchpoints**: API endpoints, database interactions, and state mutations.
3. Map every test case to a Functional Requirement ID (e.g., `FR-01`).

### Phase 2: E2E Test Suite Development
1. Create dedicated E2E test files (e.g., `tests/e2e/auth.spec.ts` or `tests/integration/api.test.py`) using `write_to_file`.
2. Execute the test suite inside the execution environment via `run_command`:
   ```bash
   npm run test:e2e
   # or: pytest tests/e2e/
   ```
3. Inspect stderr/stdout outputs to confirm all test scenarios pass.

### Phase 3: Deliverable Reporting
Generate a structured report containing the **Requirement Traceability Matrix** and test output summaries.

---

## Output Template: Requirement Traceability Matrix & E2E Report

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