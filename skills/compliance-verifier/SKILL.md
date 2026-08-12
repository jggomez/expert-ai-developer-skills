---
name: compliance-verifier
description: Guides the final quality assurance and compliance verification of a project. Trigger when checking non-functional requirements, static code analysis, test coverage, and security compliance before release.
---

# Compliance Verifier Skill

## Overview
This skill ensures that code passes all quality gates, security audits, and non-functional requirements (NFRs) before final approval.

## Procedural Workflow

### Phase 1: Code Quality & Coverage Audit
1. Execute static analysis tools (e.g., linters, type checkers).
2. Review the test suite execution logs to confirm adequate coverage.
3. Check for obvious code smells or architectural anti-patterns.

### Phase 2: Security & Vulnerability Checks
1. Scan for OWASP top vulnerabilities (e.g., injection, broken access control).
2. Ensure no hardcoded credentials or sensitive data are committed.

### Phase 3: Non-Functional Requirements (NFRs) Validation
1. Verify that the implemented solution adheres to the Quality Attribute Drivers (QADs) such as performance boundaries and maintainability standards.

### Phase 4: Final Verdict
- Issue an **APPROVED** status if all checks pass.
- Issue a **REJECTED** status if any critical check fails, explicitly listing the actionable remediation steps.
