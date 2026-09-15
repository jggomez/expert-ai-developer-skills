---
name: compliance-verifier
description: Guides the final quality assurance and compliance verification of a project. Trigger when checking non-functional requirements, static code analysis, test coverage, and security compliance before release.
---

# Compliance Verifier Skill

## Overview
This skill ensures that software deliverables pass all quality gates, static analysis checks, security audits, and non-functional requirements (NFRs) before final merge or release. It acts as the Principal Release & Compliance Auditor, evaluating readiness objectively and issuing formal verdicts (`APPROVED` or `REJECTED` with explicit remediation steps).

## When to Use
### Trigger Scenarios
- Final quality gate check before merging a Pull Request or cutting a release.
- Verifying compliance against security benchmarks (OWASP Top 10, secret scanning, credential leaks).
- Auditing Non-Functional Requirements (latency budgets, concurrency, memory limits, maintainability).
- Evaluating test coverage and static analysis results across a codebase.

### When NOT to Use
- **Active implementation and coding**: Route to `code-implementer` or `test-driven-development`.
- **Authoring E2E test scenarios**: Route to `qa-tester`.
- **Drafting Architectural Decision Records**: Route to `senior-architect-engineering`.
- **Trivial standalone typo fixes**: Quick manual verification is sufficient.

## Process
### Phase 1: Code Quality & Static Analysis Audit
1. Execute repository linters, type-checkers, and style formatters (e.g., `ruff`, `mypy`, `eslint`, `dart analyze`).
2. Verify that 100% of tests pass without skipped or failing assertions.
3. Review test coverage reports to ensure critical business logic is covered.

### Phase 2: Security & Secret Leak Audit
1. Scan the repository and diff for exposed credentials, tokens, or private keys.
2. Inspect data access and query patterns for injection flaws (SQL, command injection) or broken authorization checks.
3. Verify dependency vulnerability advisories if new dependencies were introduced.

### Phase 3: Non-Functional Requirements (NFR) Validation
1. Verify adherence to defined Quality Attribute Drivers (QADs) such as latency limits, concurrency models, and resource constraints.
2. Check for memory leaks, unclosed streams, unhandled async task rejections, or runaway loops.

### Phase 4: Formal Audit Verdict
Issue an official audit report:
- **`APPROVED`**: Issued only when all quality gates, security scans, and tests pass completely.
- **`REJECTED`**: Issued if any critical vulnerability, test failure, or NFR violation is detected, accompanied by numbered, actionable remediation instructions.

## Usage
### Verification Commands
```bash
# Example static analysis and security checks
ruff check .
mypy .
pytest --cov=. --cov-fail-under=80
```

### Example Prompts
- *"Run a full compliance audit on this PR branch: check test coverage, static analysis, secret scans, and NFRs."*
- *"Verify if our new authentication endpoint complies with OWASP guidelines and project security standards."*
- *"Audit the repository before release and provide a formal APPROVED/REJECTED verdict with findings."*

### Host Execution Instructions
- **Claude Code**: Direct the agent to execute test and linting commands, review outputs, and formulate the compliance report.
- **Antigravity**: Launch as the final compliance subagent (`compliance-verifier`) before closing a development loop or merging.

## Red Flags
- Issuing an `APPROVED` verdict without executing test suites or linters.
- Treating hardcoded secrets or disabled lint rules as acceptable "temporary" debt.
- Ignoring test coverage drops or unhandled edge cases.
- Issuing a `REJECTED` verdict without providing clear, actionable remediation steps.

## Verification
- [ ] 100% of automated tests pass cleanly with zero failures.
- [ ] Linters and type checkers report zero errors or unhandled warnings.
- [ ] Secret scanner detects zero leaked API keys, tokens, or credentials.
- [ ] NFRs and performance criteria verified against project specifications.
- [ ] Formal audit report produced with an unambiguous `APPROVED` or `REJECTED` verdict.

