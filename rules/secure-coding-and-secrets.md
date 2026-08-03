---
trigger: model_decision
description: Protect credentials, prevent hardcoded secrets, validate input parameters, and adhere to OWASP security standards.
---

# Rule: Secure Coding & Secrets Prevention

**Identifier**: `secure-coding-and-secrets`

## 1. Secrets Leak Prevention Directives

* **NEVER** commit credential files to Git. Exclusion **MUST** be enforced for:
  - Environment Files: `.env`, `.env.local`, `*.env`
  - JSON Keys & Certs: `google-services.json`, `GoogleService-Info.plist`, `*.pem`, `*.key`, `*.p12`
  - Local Session State: `.agents/`, `logs/`, `tmp/`
* **MUST** scan modified code before staging for API keys (`AIza...`, `sk-...`), DB URIs, or bearer tokens.
* **MUST** extract secrets into environment variables accessed via `.env`.

## 2. OWASP Secure Coding Constraints

* **SQL Injection**: **NEVER** concatenate strings in SQL statements. **MUST** use parameterized ORM queries.
* **Input Validation**: **MUST** validate incoming payloads via schemas (Pydantic/JSON Schema). **MUST** sanitize inputs against XSS.
* **Access Control**: **MUST** verify authentication AND resource authorization on all non-public endpoints.
* **Cryptography**: **NEVER** use MD5 or SHA1 for passwords. **MUST** use Argon2, bcrypt, or PBKDF2.
