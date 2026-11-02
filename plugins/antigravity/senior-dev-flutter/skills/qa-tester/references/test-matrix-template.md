# QA Test Matrix: <feature-name>

## 1. Execution Summary
- **Runner Command**: `pytest tests/ -v`
- **Results**: `18 passed, 0 failed` across Unit, Integration, and E2E tiers
- **Exit Code**: `0` (verified via terminal execution)
- **Date**: `YYYY-MM-DD`

## 2. Test Case Matrix

| ID | Ref (`US-XX`/`AC-XX`) | Level (`Unit`\|`Integration`\|`E2E`) | Objective | Steps | Expected Result | Automated Test (`path::test_fn`) | Status (`PASS`\|`FAIL`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | `US-01` / `AC-01` | `Integration` | Verify primary happy-path authentication flow | 1. Seed active user in test DB. 2. POST `/api/login` with valid credentials. 3. Inspect HTTP status and JWT claims. | Returns `200 OK` with signed access token and session record persisted. | `tests/integration/test_auth.py::test_login_valid_credentials` | `PASS` |
| **TC-02** | `US-01` / `AC-02` | `Unit` | Reject malformed or missing login fields | 1. Construct payload with empty `email` or missing `password`. 2. Validate against `LoginRequest` schema. 3. Assert validation error fields. | Raises validation error (`422`) listing exact missing/invalid fields before DB call. | `tests/unit/test_auth_schema.py::test_login_rejects_empty_fields` | `PASS` |
| **TC-03** | `US-02` / `AC-03` | `Integration` | Enforce role-based authorization on protected route | 1. Authenticate non-admin user token. 2. DELETE `/api/users/42` with bearer token. 3. Check response and DB row. | Returns `403 Forbidden`; target user record remains untouched in DB. | `tests/integration/test_users_rbac.py::test_non_admin_delete_forbidden` | `PASS` |
| **TC-04** | `US-02` / `AC-04` | `E2E` | Enforce rate-limit lockout on repeated failed attempts | 1. Submit 5 invalid login requests within 60s window. 2. Submit 6th request with valid credentials. 3. Inspect lockout header. | Returns `429 Too Many Requests` with `Retry-After` header and zero session issued. | `tests/e2e/test_auth_rate_limit.py::test_lockout_on_burst_failures` | `PASS` |
