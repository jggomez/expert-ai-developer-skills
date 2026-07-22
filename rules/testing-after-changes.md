---
trigger: model_decision
description: Enforcement rule requiring mandatory automated testing and verification after code generation, feature additions, or modifications.
---

# Rule: Testing After Code Changes and Feature Creation

**Identifier**: `testing-after-changes`  
**Purpose**: Enforce a mandatory, automated verification quality gate immediately following any code modifications, refactorings, bug fixes, or feature additions.

---

## 1. Core Mandate

**No code change is complete until it has been verified by successfully passing an automated test suite.** 

AI agents and developers must proactively search for, execute, or write automated tests to validate their changes before declaring a task finished. Trusting model output or manual verification alone is strictly prohibited.

---

## 2. Trigger Events & Required Actions

| Scenario | Required Verification Action | Quality Gate |
| :--- | :--- | :--- |
| **New Feature / Capability** | Write new unit/integration tests covering happy paths, edge cases, and error boundaries. | 100% test pass + coverage threshold met. |
| **Bug Fix** | Write a regression test that fails *before* the fix is applied, and passes *after* the fix. | Regression test explicitly validates the fix. |
| **Code Refactoring** | Execute existing tests *before* and *after* the refactor to ensure behavior remains identical. | Zero regressions in execution. |
| **Dependency Updates** | Execute the full test suite to check for breaking changes or deprecation warnings. | Test suite passes without warnings/errors. |

---

## 3. The 3-Step Verification Protocol

When working on any change, follow this sequence:

### Step 1: Locate Existing Tests
* Search the repository for relevant test directories (e.g., `tests/`, `spec/`, `__tests__/`).
* Identify the test runner being used (e.g., `pytest`, `npm test`, `jest`, `cargo test`, `go test`).
* Locate the specific test file that targets the module being modified.

### Step 2: Execute Tests Prior to Commit
* Run the specific test suite related to your changes.
* **Do NOT** run the entire suite if it takes longer than 60 seconds unless verifying a release candidate; prioritize targeted tests first, then run the full suite.
* Ensure output is captured and analysed. If any tests fail, debug and resolve them immediately.

### Step 3: Enforce Coverage & Regression Protections
* For all new code, ensure test coverage is updated (aim for >80% coverage on new files).
* Ensure edge cases (null values, boundary limits, empty inputs, network errors) are handled and explicitly covered in assertions.
* Do not bypass linting or formatting steps; they are considered part of static testing.

---

## 4. Specific Stack Configurations

Customize these standard run commands based on the project language:

```bash
# Python (pytest)
pytest tests/ -v --cov=src

# Node.js (Jest)
npm test -- --watchAll=false

# Node.js (Vitest)
npx vitest run

# Go
go test ./... -v -cover

# Rust
cargo test
```

---

## 5. Verification Checklist for the Agent

Before calling a task complete, confirm:
- [ ] Have I identified the relevant test suite for the modified files?
- [ ] Did I run the test suite and did 100% of the tests pass?
- [ ] If I added a new feature, did I write corresponding unit or integration tests?
- [ ] If I fixed a bug, did I write a test that specifically covers that regression?
- [ ] Did I verify that no temporary or mock testing code is being committed?
