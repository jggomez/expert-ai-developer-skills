# Workflow: Test Suite Execution & Coverage Verification

**Identifier**: `test-execution-workflow`  
**Purpose**: Step-by-step playbook to locate, configure, run, and audit unit, integration, and coverage tests in any project workspace to guarantee code correctness.

---

## 1. Prerequisites
* Project dependencies and test requirements are installed (`pip install -r requirements-dev.txt`, `npm install`, etc.).
* Database or external service mocks are configured or running (e.g. docker-compose for test database).

---

## 2. Step-by-Step Workflow

```mermaid
graph TD
    A[Start: Code Modified] --> B[Step 1: Locate Test Directory]
    B --> C[Step 2: Identify Test Runner]
    C --> D[Step 3: Run Targeted Tests]
    D -->|Fails| E[Step 4: Debug Failing Tests]
    E --> D
    D -->|Passes| F[Step 5: Run Full Suite]
    F -->|Fails| E
    F -->|Passes| G[Step 6: Verify Code Coverage]
    G -->|Below Threshold| H[Add Missing Assertions/Tests]
    H --> D
    G -->|Passes| I[End: Test Quality Gate Passed]
```

### Step 1: Locate Test Directory
* Find where tests are stored (usually `tests/`, `spec/`, or files ending in `*.test.js`, `test_*.py`).
* Verify that test files map to the implementation files modified (e.g., `tests/test_auth.py` matches `src/auth.py`).

### Step 2: Identify Test Runner & Configuration
* Look for runner configuration files in the root:
  * Python: `pytest.ini`, `setup.cfg`, `pyproject.toml`
  * JS/TS: `jest.config.js`, `vitest.config.ts`
  * Go: `go.mod`
* Identify the exact test runner execution command.

### Step 3: Run Targeted Tests (Fast Feedback Loop)
* Run only the tests covering the specific files you changed to save time:
  ```bash
  # Python (pytest)
  pytest tests/test_auth.py -k "test_login"
  # Node.js (Jest)
  npx jest tests/auth.test.js -t "should login user"
  ```

### Step 4: Debug Failing Tests
If a test fails, follow this diagnosis sequence:
1. **Examine Assertions**: Read the traceback output. Isolate whether it is a value assertion mismatch, a Type/Attribute error, or a timeout.
2. **Review Mocks**: If the test hits an external API or database, ensure the request is properly mocked (e.g., `pytest-mock`, `nock`, `msw`).
3. **Isolate Code**: Run the failing test in verbose mode with stdout capturing enabled:
   ```bash
   # Python (show stdout and tracebacks)
   pytest tests/test_auth.py -s -vv
   # Node.js (run with debug environment flags)
   node --inspect-brk node_modules/.bin/jest --runInBand
   ```
4. **Fix & Re-run**: Make targeted adjustments in the source code or mock files, and re-run the targeted test.

### Step 5: Run the Full Test Suite
* Once targeted tests pass, run the global project suite to verify no regressions were introduced elsewhere:
  ```bash
  # Python
  pytest tests/
  # Node.js
  npm test
  ```

### Step 6: Verify Code Coverage
* Execute coverage reporting to check that new statements, branches, and functions are covered:
  ```bash
  # Python
  pytest --cov=src --cov-report=term-missing
  # Node.js
  npm run coverage
  ```
* Ensure code coverage remains above the project threshold (minimum recommended is **80%** on new files).

---

## 3. Quality Gate & Verification

The testing workflow is considered successful only when:
- [ ] 100% of tests pass (0 failures, 0 errors, 0 pending regressions).
- [ ] Code coverage threshold is met and verified.
- [ ] Test execution logs are outputted and validated.
- [ ] Temporary test databases, docker containers, or cache files are shut down and cleaned up.
