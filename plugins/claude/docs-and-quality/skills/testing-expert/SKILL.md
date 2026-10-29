---
name: testing-expert
description: Design and validate automated tests, concise IEEE/ISTQB TC-XX test cases, hermetic Arrange-Act-Assert (AAA) suites, Gherkin BDD scenarios, and Fail-Honest execution reporting across languages.
---

# Testing Expert Skill

## Overview
This skill guides the design, structuring, and validation of hermetic automated tests, Gherkin BDD specifications, and concise IEEE/ISTQB test cases (`TC-XX`). Acting as a Lead QA Architect, it enforces Arrange-Act-Assert (AAA) isolation, boundary mocking, concise `docs/<feature-name>/test-matrix.md` (`<= 80 lines`) traceability, and strict **Fail-Honest** execution reporting.

## When to Use
### Trigger Scenarios
- Designing unit, integration, component, and E2E test cases (`TC-XX`) with explicit `Objective`, `Steps`, and `Expected Result`.
- Authoring and validating Gherkin BDD `.feature` files (`Given` / `When` / `Then` / `Examples`).
- Structuring hermetic Arrange-Act-Assert (AAA) test suites with isolated boundary mocks.
- Auditing test outcomes to enforce Fail-Honest `BLOCKED` / `SKIPPED` reporting when environments are unavailable.

### When NOT to Use
- **Inner-loop TDD production code authoring**: Route to `test-driven-development` or `code-implementer`.
- **Full State 3 QA execution & matrix sign-off**: Route to `qa-tester`.
- **Live Playwright browser journey & viewport screenshot capture**: Route to `blackbox-tester` (`e2e-blackbox-tester`).

## Process
### Phase 1: Concise IEEE/ISTQB `TC-XX` & Gherkin BDD Design
1. Define each test case (`TC-01`, `TC-02`, ...) concisely for `docs/<feature-name>/test-matrix.md` (`<= 80 lines`):
   - **Objective**: Single behavior, invariant, or boundary under verification.
   - **Steps**: Deterministic precondition + action (`Given`/`When` or concise numbered steps).
   - **Expected Result**: Observable output, state transition, or error contract (`Then`).
   - **Automated Test & Status**: Linked test path/symbol and empirical status (`PASSED`, `FAILED`, `BLOCKED`, `SKIPPED`).
2. When authoring `.feature` specs, use clean `Feature`, `Background`, `Scenario`, and `Scenario Outline` + `Examples` tables.

### Phase 2: Hermetic Arrange-Act-Assert (AAA) & Fail-Honest Execution
1. Partition every test into **Arrange** (fixtures + boundary mocks), **Act** (single invocation), and **Assert** (exact behavioral check) with zero shared mutable state across tests.
2. **Fail-Honest Rule**: If a test runner, database service, live web server, or Chromium/Playwright binary cannot run in the current environment, report `BLOCKED` or `SKIPPED` with the exact missing prerequisite — **never** stub assertions, relax thresholds, or fabricate `PASSED`.

### Phase 3: Automated Gherkin Validation
Validate all `.feature` files for missing `Examples:`, step-less scenarios, or ordering errors:
```bash
python3 ./skills/testing-expert/scripts/validate_gherkin.py
```

## Usage
### Commands & Automation Scripts
```bash
# Validate Gherkin .feature syntax across the workspace
python3 ./skills/testing-expert/scripts/validate_gherkin.py
```

### Host Execution Instructions
- **Claude Code**: Run `validate_gherkin.py` via Bash and execute targeted test runners with empirical exit-code checks.
- **Antigravity**: Validate `.feature` syntax via `Bash` and record honest `PASSED`/`FAILED`/`BLOCKED`/`SKIPPED` statuses.

## Red Flags
- Claiming `PASSED` when the runner, server, or browser was unavailable instead of reporting `BLOCKED` or `SKIPPED`.
- Bloated test matrices (`> 80 lines`) or vague `TC-XX` entries missing `Objective`, `Steps`, or `Expected Result`.
- Order-dependent tests, live external network calls in unit tests, or `Scenario Outline` blocks missing `Examples:`.

## Verification
- [ ] Every `TC-XX` specifies `Objective`, `Steps`, `Expected Result`, `Automated Test`, and honest `Status`.
- [ ] Gherkin validator exits with code `0`:
  ```bash
  python3 ./skills/testing-expert/scripts/validate_gherkin.py
  ```
- [ ] Unit and integration tests follow strict AAA isolation with external I/O mocked at boundaries.
- [ ] Unavailable runners/browsers are transparently marked `BLOCKED` or `SKIPPED` (zero faked `PASSED`).

## References
- [Software Testing Best Practices Reference](references/testing-best-practices.md)
- [Behavior-Driven Development (BDD) & Gherkin Syntax](references/gherkin-syntax.md)
