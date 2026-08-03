---
trigger: model_decision
description: Enforcement rule requiring Test-Driven Development (TDD) best practices, Red-Green-Refactor cycles, unit/integration testing strategies, mock boundaries, and agent verification standards for Google Antigravity.
---

# Rule: Test-Driven Development (TDD) Best Practices

**Identifier**: `tdd-best-practices`

## 1. Core Mandates

1. **Test First**: **NEVER** write production code without a failing test (RED state) reproducing the bug or defining the feature.
2. **Empirical Evidence**: **NEVER** declare a task completed without verified clean test execution output (`exit code 0`).
3. **Zero Test Tampering**: **NEVER** delete assertions, lower thresholds, swallow exceptions, or return hardcoded dummy data to force a pass.
4. **Surgical Iterations**: **MUST** execute relevant unit tests after every single code edit.

## 2. 3-Phase TDD Lifecycle (`RED -> GREEN -> REFACTOR`)

| Phase | Objective | Mandatory Directives |
| :--- | :--- | :--- |
| **1. RED** | Write Failing Test | **MUST** run test and confirm it fails for expected reason. Inspect log traceback. |
| **2. GREEN** | Minimal Code to Pass | Write minimal code. If execution fails, **MUST** read full un-truncated logs before touching code. |
| **3. REFACTOR**| Clean Without Regression | **MUST** re-run tests after *each* structural edit to ensure behavior remains 100% green. |

## 3. Test Design & Mocking Rules

* **AAA Pattern**: Tests **MUST** follow `Arrange -> Act -> Assert` layout explicitly.
* **Descriptive Naming**: **MUST** use pattern: `test_<unit>_<scenario>_<expected_outcome>()`.
* **Mock Boundaries**: **MUST** mock external APIs, DBs, and network I/O. **NEVER** mock the unit under test.
* **Speed & Determinism**: Unit tests **MUST** execute deterministically without real network calls or long delays.
