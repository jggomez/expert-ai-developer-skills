# OWASP Top 10 (2021) Security Audit Checklist

Use this checklist during security audits to systematically verify compliance with all 10 OWASP Top 10 vulnerability classes.

---

## A01:2021 - Broken Access Control
- [ ] **BOLA / IDOR (Insecure Direct Object Reference)**:
  - *Symptom*: Enpoints like `GET /api/orders/{id}` load resources without validating ownership.
  - *Audit*: Verify that the authenticated user ID matches the resource owner ID in the database before returning data.
- [ ] **Missing Function-Level Access Control**:
  - *Symptom*: Administrative endpoints (e.g. `POST /api/admin/config`) do not explicitly enforce role-based access controls (RBAC) or attribute-based controls (ABAC).
  - *Audit*: Trace routes to ensure custom middleware/decorators (e.g. `@admin_required`, `@has_permission`) protect all privileged endpoints.
- [ ] **Metadata Manipulation**:
  - *Symptom*: Replaying requests with manipulated body fields (e.g. changing `is_admin: false` to `is_admin: true` during registration).
  - *Audit*: Inspect model serializers to ensure read-only fields are protected from mass-assignment/auto-binding.
- [ ] **Permissive CORS Policies**:
  - *Symptom*: `Access-Control-Allow-Origin: *` returned on authenticated APIs.
  - *Audit*: Check CORS headers configuration in server setup.

---

## A02:2021 - Cryptographic Failures
- [ ] **Hardcoded Secrets**:
  - *Symptom*: API keys, private keys, database passwords, or JWT secrets declared directly in code files.
  - *Audit*: Scan codebase with `secret_scanner.py` and inspect `.gitignore`.
- [ ] **Insecure Data Transit**:
  - *Symptom*: Internal or external communications using HTTP, FTP, or SMTP instead of HTTPS, SFTP, or SMTPS.
  - *Audit*: Check connection URLs and verify SSL/TLS settings for API clients and databases.
- [ ] **Weak Hash & Cryptographic Algorithms**:
  - *Symptom*: Using MD5 or SHA1 for password hashing, or DES/Blowfish for encryption.
  - *Audit*: Ensure passwords are saved using Argon2, bcrypt, or PBKDF2. Ensure AES-GCM or AES-CBC is used for encryption.
- [ ] **Missing Sensitive Data Encryption at Rest**:
  - *Symptom*: PII (emails, SSNs, credit card numbers) stored as plaintext in database columns.
  - *Audit*: Check schemas and ORM mapping. Recommend database-level or application-level encryption.

---

## A03:2021 - Injection
- [ ] **SQL/NoSQL Injection**:
  - *Symptom*: Concatenating variables directly into raw queries (e.g., `execute(f"SELECT * FROM users WHERE name = '{input}'")`).
  - *Audit*: Check all database calls. Ensure parameterized queries, placeholders (`%s`, `?`), or ORM methods are used.
- [ ] **Command Injection**:
  - *Symptom*: Spawning shell commands using unvalidated user input (`os.system`, `subprocess.run(..., shell=True)`).
  - *Audit*: Check all subprocess calls. Ensure list-format arguments are passed and `shell=True` is disabled.
- [ ] **XSS (Cross-Site Scripting)**:
  - *Symptom*: Rendering user input directly to the browser DOM without escaping (e.g., `innerHTML = user_input`).
  - *Audit*: In client-side logic, inspect raw rendering methods. In templating engines, verify auto-escaping settings.
- [ ] **LDAP, XPath, or Log Injection**:
  - *Symptom*: User input containing newline characters injected into logs or directory queries.
  - *Audit*: Ensure logs sanitize user input by stripping control characters.

---

## A04:2021 - Insecure Design
- [ ] **Lack of Threat Modeling**:
  - *Symptom*: App contains no logical separation of trust zones (e.g. front-end, back-end, internal database).
  - *Audit*: Verify if secure design principles are followed.
- [ ] **Insecure Business Logic**:
  - *Symptom*: Users can perform logic violations (e.g., withdrawing negative amounts of money to add balance, checking out with a negative quantity cart).
  - *Audit*: Inspect state machine changes and validation flows for numeric inputs.
- [ ] **No Rate Limiting / Brute-Force Vulnerability**:
  - *Symptom*: Authentication or database-heavy endpoints can be queried indefinitely without limits.
  - *Audit*: Check middleware for IP/user-based rate limits (e.g., Redis-based limiter, Nginx config).

---

## A05:2021 - Security Misconfiguration
- [ ] **Verbose Error Handling & Stack Traces**:
  - *Symptom*: Application displays full tracebacks or DB connection details to users when an exception occurs.
  - *Audit*: Verify that global exception handlers return clean, generic messages to client and log detail internally.
- [ ] **Insecure Default Settings**:
  - *Symptom*: Active debug modes in production (e.g. `DEBUG = True` in Django/Flask), default passwords, or public directory indexes.
  - *Audit*: Check settings files and startup configurations.
- [ ] **Permissive Ports & Services**:
  - *Symptom*: Databases or caching services binding to `0.0.0.0` instead of `127.0.0.1` or internal private subnets.
  - *Audit*: Check docker-compose configurations or network rules.

---

## A06:2021 - Vulnerable and Outdated Components
- [ ] **Outdated Dependencies**:
  - *Symptom*: Project dependencies have unpatched vulnerabilities (CVEs).
  - *Audit*: Run dependency auditing tools:
    - *Node*: `npm audit` / `yarn audit`
    - *Python*: `pip-audit` / `safety check`
    - *Go*: `govulncheck ./...`
- [ ] **Unmaintained Libraries**:
  - *Symptom*: Using custom or obscure libraries that have not received updates in years.
  - *Audit*: Review package manifests (`package.json`, `requirements.txt`, etc.).

---

## A07:2021 - Identification and Authentication Failures
- [ ] **Weak Password Policies**:
  - *Symptom*: Allowing short or simple passwords, or lack of verification against common breached passwords.
  - *Audit*: Verify validation logic during user creation/registration.
- [ ] **Session Fixation & Hijacking**:
  - *Symptom*: Session tokens not refreshed upon login, or cookies lack secure attributes (`HttpOnly`, `Secure`, `SameSite=Strict`).
  - *Audit*: Check cookie configuration settings and session middleware.
- [ ] **Credential Stuffing Vulnerability**:
  - *Symptom*: Login page does not implement locks or delays after sequential failures.
  - *Audit*: Verify account lockout mechanics or CAPTCHA integration.

---

## A08:2021 - Software and Data Integrity Failures
- [ ] **Insecure Deserialization**:
  - *Symptom*: Deserializing untrusted data (e.g. Python's `pickle.loads()`, Node's `serialize-to-js`, Java objects) from client cookies or API requests.
  - *Audit*: Search codebase for `pickle`, `yaml.load` (without `SafeLoader`), or unsafe JSON parsing.
- [ ] **Missing CI/CD Integrity & Dependency Pinning**:
  - *Symptom*: Installing dependencies using wildcard versions (e.g. `package: "*"` or `package >= 1.0`), leaving builds open to supply chain attacks.
  - *Audit*: Verify lock files (`package-lock.json`, `poetry.lock`, `Cargo.lock`, `go.sum`) are committed and enforced in builds.

---

## A09:2021 - Security Logging and Monitoring Failures
- [ ] **Insufficient Logging**:
  - *Symptom*: Authentication failures, authorization failures, and server errors are not logged, or log format lacks context (e.g. timestamps, source IP, user ID).
  - *Audit*: Audit error handling blocks to check if `logger.error` or `logger.warn` is used correctly.
- [ ] **Lack of Alerting**:
  - *Symptom*: Repeated high-risk failures (e.g. 50+ failed logins for the same account) do not trigger notification flags.
  - *Audit*: Review system event monitoring setup.

---

## A10:2021 - Server-Side Request Forgery (SSRF)
- [ ] **Unvalidated URL Requests**:
  - *Symptom*: The server takes a user-supplied URL and makes an HTTP request to it (e.g., PDF generation from URL, webhooks, fetching profile pictures).
  - *Audit*: Verify if the server restricts requests to a whitelist of allowed domains, or checks that resolved IPs are not in private subnets (e.g. `127.0.0.1`, `10.0.0.0/8`, `169.254.169.254` AWS metadata).
