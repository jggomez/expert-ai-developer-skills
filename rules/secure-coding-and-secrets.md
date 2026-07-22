---
trigger: model_decision
description: Protect credentials, prevent hardcoded secrets, validate input parameters, and adhere to OWASP security standards.
---

# Rule: Secure Coding & Secrets Prevention

**Identifier**: `secure-coding-and-secrets`  
**Purpose**: Prevent security vulnerabilities, injection flaws, and accidental leaks of cryptographic keys, API tokens, passwords, or service credentials into version control history.

---

## 1. Secrets Leak Prevention

### Strict Exclusion Rule
Never commit files containing sensitive information. The following file types and naming patterns must be excluded from Git at all times:
* **Environment Files**: `.env`, `.env.local`, `.env.production`, `*.env`
* **JSON Credentials**: `google-services.json`, `GoogleService-Info.plist`, `*credentials*.json`, `*keyfile*.json`
* **Private Keys / Certificates**: `*.pem`, `*.key`, `*.p12`, `*.cer`, `*.crt`
* **Local Session State**: `.agents/`, `logs/`, `tmp/`

### Secret Scanning Audit
Prior to any `git push`, developers and agents must run check sweeps on modified code blocks. Scan for hardcoded patterns matching:
* API keys (e.g., `AIzaSy...` for Google, `sk-proj-...` for OpenAI)
* Database connection URIs (e.g., `postgresql://user:pass@host:port/db`)
* Authorization headers or bearer tokens

*If any hardcoded secret is found, it must be removed, placed in a `.env` file, and injected via environment variables.*

---

## 2. Secure Coding Practices (OWASP Top 10 Alignment)

Always adhere to these secure programming constraints:

### Input Sanitization & Validation
* Always validate incoming payload structures using typed data validation schemas (e.g., Pydantic models, JSON Schema).
* Sanitize all user-provided strings before saving to database engines or outputting to UI views to prevent Cross-Site Scripting (XSS).

### SQL Injection Prevention
* Never construct raw SQL queries using string formatting or concatenation.
* Always use parameterized queries, prepared statements, or ORM parameter binding (e.g., SQLAlchemy parameters, Knex query builder).

### Broken Access Control
* Ensure authentication is validated on every private API route.
* Apply Least Privilege: Ensure APIs verify both *authentication* (who the user is) and *authorization* (whether they have permission to access that specific resource id).

### Cryptographic Security
* Never use deprecated hashing algorithms (MD5, SHA1) for passwords. Always use modern salted hashing functions (bcrypt, Argon2, PBKDF2).
* Avoid storing plaintext configurations for encryption algorithms; rotate cryptographic keys using KMS (Key Management Services) or GCP Secret Manager.
