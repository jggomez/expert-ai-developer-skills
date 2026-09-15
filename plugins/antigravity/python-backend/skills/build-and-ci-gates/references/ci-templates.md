# CI/CD, Linting & Build Templates Reference

This reference provides production-ready configuration blueprints to enforce quality gates during local builds and remote CI processes.

---

## 1. Multi-Stage Dockerfile Blueprint (Python Example)
Use multi-stage builds to produce minimal, secure, and performant container images.

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential

COPY requirements.txt .
RUN pip install --user --no-warn-script-location --no-cache-dir -r requirements.txt

# Stage 2: Final minimal execution image
FROM python:3.11-slim AS runner

WORKDIR /app
# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000

# Run as non-root user for security
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "main.py"]
```

---

## 2. GitHub Actions CI Pipeline Configuration
Enforce linting, formatting, and test validation on every pull request.

```yaml
# .github/workflows/ci.yml
name: Continuous Integration Gate

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout Code
      uses: actions/checkout@v3

    # (Example for Python - adapt to project language)
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'

    - name: Install Lint & Test Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install ruff black pytest pytest-cov

    - name: Check Code Formatting (Black)
      run: black --check .

    - name: Run Linter (Ruff)
      run: ruff check .

    - name: Execute Test Suite with Coverage
      run: pytest --cov=. --cov-fail-under=80
```

---

## 3. Linter & Formatter Config Configurations

### 3.1 Python (pyproject.toml)
```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "W", "C90"]
ignore = []
```

### 3.2 JavaScript/TypeScript (.eslintrc.json)
```json
{
  "env": {
    "browser": true,
    "es2021": true,
    "node": true
  },
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "parser": "@typescript-eslint/parser",
  "plugins": [
    "@typescript-eslint"
  ],
  "rules": {
    "no-console": "warn",
    "semi": ["error", "always"]
  }
}
```
