# QA Test Matrix: <feature-name>

## 1. Execution Summary
- **Change**: `C-02` (add login rate limit); earlier: `C-01: TC-01..TC-03 PASS @ abc1234`
- **Affected run**: `pytest tests/e2e/test_auth_rate_limit.py -v` -> exit `0`
- **Last full run**: `def5678`, exit `0` (skip the next full run while the tree is unchanged)
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

## 3. Completion Proof
- **Requirements**: `AC-01..AC-04` -> `TC-01..TC-04` `PASS`; missing: none
- **Tests**: affected `pytest tests/e2e/test_auth_rate_limit.py` exit `0`; full `pytest tests/` exit `0`
- **Build**: `uv build` exit `0`
- **Static checks**: `ruff check src/auth` exit `0`; `mypy src/auth` exit `0`
- **Images**: `docs/user-auth/evidence/login-375x812.png` (+3 viewports); `check_evidence.py` exit `0`
- **Wiring**: `GET /api/login` on the running backend, no mocks, exit `0`; `check_fake_data.py` exit `0`
- **Verdict**: `DONE`
