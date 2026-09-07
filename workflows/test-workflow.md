# Workflow: Prove It Works (/test)

**Command**: `/test`  
**Key Principle**: *Tests are proof*  
**Identifier**: `test-workflow`

---

## 1. Objective
Validate functional correctness, regression safety, and edge-case resilience through automated test suites, producing objective empirical evidence of success (`exit code 0`).

## 2. Operational Steps
1. **Identify Test Scopes**:
   - Locate existing test runner (`pytest`, `flutter test`, `npm test`, `cargo test`).
2. **Execute Full Suite**:
   - Run unit, integration, and E2E suites.
   - If tests fail, read exact stack traces and error messages. Never guess or suppress failures.
3. **Evaluate Test Adequacy**:
   - Check happy path coverage.
   - Check error handling, bad input payloads, boundary conditions, and timeouts.
   - For UI/Flutter: verify widget tests and golden tests.
4. **Produce Verification Evidence**:
   - Document the exact command and terminal output proving all tests pass.

## 3. Delegation & Tools
- **Antigravity Subagent**: Delegate to `qa-tester` (or `flutter-implementer`).
- **Primary Skills**: `test-driven-development`, `testing-expert`, `flutter-test-strategy`.

## 4. Quality Gate Checklist
- [ ] 100% of relevant test cases passing cleanly.
- [ ] Edge cases, error paths, and boundary conditions covered.
- [ ] Zero skipped assertions or mock bypasses.
- [ ] Empirical execution evidence verified.
