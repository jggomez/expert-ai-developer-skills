---
trigger: model_decision
description: Enforcement rule requiring mandatory automated testing and verification after code generation, feature additions, or modifications.
---

# Rule: Testing After Code Changes & Verification Gates

**Identifier**: `testing-after-changes`

## 1. Golden Rule of Verification

**NEVER** declare a coding task, bug fix, or feature complete without empirical proof of successful runtime test execution (`exit code 0`). Agents **MUST NOT** rely on static code inspection alone.

## 2. Trigger Scenarios & Verification Gates

| Trigger Event | Required Verification Action | Quality Gate |
| :--- | :--- | :--- |
| **New Feature** | **MUST** execute unit/integration tests covering happy paths, null bounds, and error states. | 100% test pass rate. |
| **Bug Fix** | **MUST** execute regression test proving failure before fix and clean pass after fix. | Verified fix in log output. |
| **Refactoring** | **MUST** execute test suite before AND after refactoring edits. | Zero regressions. |
| **Dependencies** | **MUST** run full test suite checking for breaking changes or deprecation warnings. | Clean build + pass. |

## 3. Mandatory 3-Step Verification Protocol

1. **Locate Test Runner**: **MUST** find test suites (`pytest`, `npm test`, `cargo test`, `go test`).
2. **Execute Targeted Tests**: **MUST** run targeted test files first. If failures occur, **MUST** inspect full log tracebacks.
3. **Validate Exit Code**: **MUST** confirm `exit code 0` and zero failing assertions before finalizing task.
