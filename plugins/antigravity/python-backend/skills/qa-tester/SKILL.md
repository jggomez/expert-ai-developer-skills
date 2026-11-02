---
name: qa-tester
description: Designs and executes Unit, Integration, and E2E test suites and authors concise, actionable IEEE/ISTQB QA Test Matrix artifacts (docs/<feature-name>/test-matrix.md <= 80 lines) backed by empirical exit code 0 terminal proof.
---

# QA Automation & E2E Tester Skill

## Overview
This skill governs integration/E2E test automation and produces an actionable, IEEE/ISTQB-aligned **QA Test Matrix (`docs/<feature-name>/test-matrix.md`, strictly `<= 80 lines`)**. Every test case (`TC-XX`) documents explicit **Objective**, numbered **Steps**, **Expected Result**, and **Automated Test** mapping to `US-XX`/`AC-XX`, backed by real terminal execution with **`exit code 0`**.

## When to Use
### SDLC Tier Adaptation & Trigger Rules
- **Tier 1 (Fast-Track)**: Single-file bugfixes, typos, chores, or localized refactors. Execute **only the scoped test file** (`exit code 0` proof) and **SKIP `test-matrix.md`** to preserve 70–85% token/latency savings.
- **Tier 2 (Standard)**: Multi-file features, endpoints, schemas, or UI views. Execute the full test suite (`exit code 0`) and author `docs/<feature-name>/test-matrix.md` (`<= 80 lines`).
- **Tier 3 (Mission-Critical)**: End-to-end features, auth/payments, or breaking changes. Execute full test pyramid suites (`exit code 0`), author `docs/<feature-name>/test-matrix.md` (`<= 80 lines`), and serve on the Adversarial Verification Committee.
- **Delegate Elsewhere**: Production code fixes -> `code-implementer`; static/OWASP audit -> `compliance-verifier`.

## Process
### Phase 1: Scenario Design Across the Test Pyramid
1. Extract `US-XX` and `AC-XX` from `docs/<feature-name>/prd.md` (or git diff when PRD was skipped).
2. Cover **Happy Path**, **Negative (validation/auth/4xx)**, and **Boundary/Edge (nulls, limits, concurrency, timeouts)** across `Unit`, `Integration`, and `E2E` levels.
3. Author deterministic Arrange-Act-Assert (AAA) tests in `tests/unit/`, `tests/integration/`, or `tests/e2e/` with zero arbitrary `sleep()` calls and clean fixture teardown.

### Phase 2: Terminal Execution & Actionable Test Matrix (`<= 80 lines`)
1. Run the test suite in the terminal (`pytest`, `npm test`, `flutter test`) and verify verbatim **`exit code 0`**.
2. For Tier 2 and Tier 3, write `docs/<feature-name>/test-matrix.md` (`<= 80 lines`) following [references/test-matrix-template.md](references/test-matrix-template.md) with two exact sections:
   - **`## 1. Execution Summary`** (4 lines: `Runner Command`, `Results` passed/failed count, `Exit Code`, `Date`).
   - **`## 2. Test Case Matrix`**: Every case (`TC-01`, `TC-02`...) **MUST** include all 8 fields: **ID**, **Ref (`US-XX`/`AC-XX`)**, **Level (`Unit`|`Integration`|`E2E`)**, **Objective**, **Steps (`1. ... 2. ... 3. ...`)**, **Expected Result**, **Automated Test (`path::test_fn`)**, and **Status (`PASS`|`FAIL`)**.

## Usage
### Commands
```bash
# Scoped run (Tier 1) or full pyramid verification (Tier 2 / Tier 3)
pytest tests/unit/test_target.py -v
pytest tests/ -v
```

### Host Execution
- **Claude Code**: Author missing integration/E2E tests via `Write`/`Edit`, execute via `Bash`, and write `docs/<feature-name>/test-matrix.md`.
- **Antigravity**: Run suites via `run_command` and write `docs/<feature-name>/test-matrix.md` via `write_to_file` / `replace_file_content`.

## Red Flags
- ❌ Claiming `PASS` without real terminal execution showing `exit code 0`.
- ❌ Writing vague one-line matrix rows that omit explicit **Objective**, numbered **Steps**, or **Expected Result**, or exceeding `80 lines` with filler tables.
- ❌ Generating `test-matrix.md` on Tier 1 trivial fixes, editing production code directly, tampering with assertions, or using `sleep()` delays.

## Verification
- [ ] All targeted or full-suite automated tests executed in terminal with verified **`exit code 0`**.
- [ ] Tier 2/3 `docs/<feature-name>/test-matrix.md` (`<= 80 lines`) matches [references/test-matrix-template.md](references/test-matrix-template.md) (`1. Execution Summary` + `2. Test Case Matrix`).
- [ ] Every `TC-XX` includes `Ref (US-XX/AC-XX)`, `Level`, `Objective`, numbered `Steps`, `Expected Result`, `Automated Test (path::test_fn)`, and `Status`, covering happy, negative, and boundary paths.

## References
- Actionable IEEE/ISTQB Test Matrix Template (`<= 50 lines`): [references/test-matrix-template.md](references/test-matrix-template.md)
