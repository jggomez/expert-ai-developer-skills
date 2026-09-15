---
name: security-audit
description: Conducts comprehensive security reviews on source code, infrastructure as code (IaC), and architectural designs. It identifies vulnerabilities such as injection flaws, broken access control, and exposure of sensitive data. Use this skill when asked to perform a security audit, a pentest review, check for OWASP Top 10 violations, or ensure compliance with security best practices.
---

# Security Audit Skill

## Overview
This skill conducts systematic security reviews across source code, infrastructure declarations, and architectural boundaries. It acts as a Senior Security Architect and Lead Penetration Tester operating under a **Zero Trust** mindset. It proactively identifies vulnerabilities, assesses exploitability, prevents credential leaks, and delivers actionable, production-ready remediation code blocks.

## When to Use
### Trigger Scenarios
- Auditing codebases, branches, or PR diffs for OWASP Top 10 vulnerabilities (Injection, Broken Access Control, SSRF, etc.).
- Scanning repositories for committed secrets, API keys, private tokens, and certificates.
- Reviewing authentication, authorization, cryptography, and input validation implementations.
- Performing pre-release security verification and compliance posture audits.

### When NOT to Use
- **Code style, whitespace, and formatting linting**: Route to `build-and-ci-gates`.
- **Performance latency profiling**: Route to `performance-scalability`.
- **Architectural pattern design**: Route to `senior-architect-engineering`.
- **General unit testing**: Route to `test-driven-development`.

## Process
### Phase 1: Automated Secret & Pattern Scanning
Execute the automated scanner to detect leaked API tokens, private keys, and high-risk API invocations:
```bash
python3 ./skills/security-audit/scripts/secret_scanner.py [optional_path_to_scan]
```
The scanner checks for AWS/GCP tokens, private keys, hardcoded passwords, and risky calls (`eval`, `exec`, unescaped raw queries).

### Phase 2: OWASP Top 10 Codebase Audit
Review critical components against the security checklist:
- **A01: Broken Access Control**: Verify object-level permissions (IDOR protection) on every protected route.
- **A02: Cryptographic Failures**: Ensure secure algorithms (AES-GCM, Argon2/bcrypt), strong TLS, and zero hardcoded keys.
- **A03: Injection**: Verify parameterized queries (SQL, NoSQL, ORM) and safe subprocess execution (avoiding `shell=True`).
- **A05: Security Misconfiguration**: Check default credentials, permissive CORS headers, and overly verbose stack trace exposures.
- **A07: Identification and Authentication Failures**: Check session expiration, brute force protections, and secure cookie attributes (`HttpOnly`, `Secure`, `SameSite`).

### Phase 3: Vulnerability Reporting & Remediation
For every security vulnerability found, produce a formal finding report:
```markdown
### [SEV] Vulnerability Title
- **Severity**: CRITICAL | HIGH | MEDIUM | LOW
- **CWE / OWASP**: (e.g. CWE-89 / OWASP A03:2021-Injection)
- **Location**: `path/to/file.py:42`
- **Exploit Scenario**: Concrete example of how an attacker could leverage the flaw.
- **Remediation**: Corrected, secure drop-in code block.
```

## Usage
### Commands & Automation Scripts
```bash
# Scan whole workspace or a specific target directory for leaked secrets
python3 ./skills/security-audit/scripts/secret_scanner.py .
python3 ./skills/security-audit/scripts/secret_scanner.py src/
```

### Example Prompts
- *"Run a security audit on our user authentication controller for OWASP Top 10 issues."*
- *"Scan this repository for hardcoded secrets, private tokens, or credential leaks."*
- *"Audit this payment webhook handler for replay attacks, signature verification, and injection vulnerabilities."*

### Host Execution Instructions
- **Claude Code**: Run `secret_scanner.py` via bash, then audit diffs manually against the OWASP checklist.
- **Antigravity**: Launch security audits before merging code changes or declaring a feature release-ready.

## Red Flags
- Hardcoded passwords, API keys, JWT secrets, or private keys committed to the repository.
- String concatenation or f-strings used to assemble SQL queries or shell commands.
- Catching exceptions silently without logging security-relevant failures (auditing blind spots).
- Running subprocesses with `shell=True` using untrusted inputs.
- Storing passwords with reversible encryption or weak hashing (MD5, SHA1, plain SHA256 without salt).

## Verification
- [ ] Secret scanner executes cleanly with zero leaked credentials detected:
  ```bash
  python3 ./skills/security-audit/scripts/secret_scanner.py .
  ```
- [ ] Zero unparameterized SQL queries or shell injection hazards exist.
- [ ] Authentication and authorization checks verified on all external endpoints.
- [ ] All reported vulnerabilities contain concrete exploit scenarios and verified remediation code.

## References
For detailed vulnerability patterns and verification checklists:
- [Security Audit & OWASP Checklist](references/owasp-checklist.md)