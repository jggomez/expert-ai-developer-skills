---
name: build-and-ci-gates
description: Implements linters, code formatters, and automated build pipelines (CI/CD) to prevent syntax errors, enforce style consistency, and prevent failing builds from being merged. Use this skill when asked to add linters, configure docker builds, or set up GitHub Actions workflows.
---

# Build and CI Gates Skill

## Overview
This skill establishes automated build pipelines, code quality gates, and Continuous Integration (CI/CD) workflows. It acts as a Build Automation and CI/CD Engineer, ensuring that code styling, linting, typing, and test suites are enforced deterministically by automated systems rather than subjective human debate, blocking defective code before it ever merges.

## When to Use
### Trigger Scenarios
- Running comprehensive local code quality, formatting, and linting checks before committing.
- Configuring or updating CI/CD pipelines (e.g., GitHub Actions workflows).
- Installing local git pre-commit hooks to block defective commits fail-closed.
- Designing containerized multi-stage Docker builds with minimal security attack surface.

### When NOT to Use
- **Authoring unit tests and mocks**: Route to `test-driven-development`.
- **Writing application feature code**: Route to `python-expert` or `code-implementer`.
- **Stand-alone security penetration reviews**: Route to `security-audit`.
- **Diagnosing code design smells**: Route to `code-smells-expert`.

## Process
### Phase 1: Local Code Verification
Before submitting code changes or opening PRs, execute automated formatting and lint checks:
```bash
python3 ./skills/build-and-ci-gates/scripts/run_checks.py
```
If formatting or linting checks fail, immediately fix them using automated tools (e.g., `ruff format`, `black .`, `eslint --fix`).

### Phase 2: Pipeline Integration (CI/CD)
Configure pipeline definitions using pinned versions and deterministic environments:
1. **GitHub Actions**: Scaffold or update `.github/workflows/ci.yml` using the CI template reference.
2. **Containerization**: Use multi-stage `Dockerfile` builds to produce minimal, non-root runner images.
3. **Configuration Pinning**: Pin all linter and formatter settings (`pyproject.toml`, `.eslintrc.json`, `pubspec.yaml`) in repository root.

### Phase 3: Git Hook Automation (Pre-Commit Gate)
Install the automated pre-commit gate to intercept syntax errors, failing tests, or secret leaks locally:
1. Symlink or copy the hook script to `.git/hooks/pre-commit`:
   ```bash
   python3 ./skills/build-and-ci-gates/scripts/pre_commit_quality_gate.py
   ```
2. Ensure the hook fails closed—aborting the commit immediately if any check fails.

## Usage
### Commands & Automation Scripts
```bash
# Run local code verification checks (lint, format, basic tests)
python3 ./skills/build-and-ci-gates/scripts/run_checks.py

# Run pre-commit quality gate check directly
python3 ./skills/build-and-ci-gates/scripts/pre_commit_quality_gate.py
```

### Example Prompts
- *"Set up a GitHub Actions workflow that runs linting, type checks, and tests on every pull request."*
- *"Configure pre-commit hooks to prevent unformatted code or secret leaks from being committed."*
- *"Create a multi-stage Dockerfile for our Python service that runs as a non-root user."*

### Host Execution Instructions
- **Claude Code**: Run `run_checks.py` in the workspace terminal before generating pull requests.
- **Antigravity**: Verify that CI gate checks pass prior to declaring build completion.

## Red Flags
- Committing code without running local linter and formatter gates.
- Configuring pre-commit hooks that fail open (allowing broken commits when tools are missing).
- Building Docker images running as root or leaving compilers and build tools in production images.
- Bypassing CI quality gates with force-pushes or `--no-verify` flags.

## Verification
- [ ] Automated check runner passes cleanly with zero errors:
  ```bash
  python3 ./skills/build-and-ci-gates/scripts/run_checks.py
  ```
- [ ] Pre-commit hook executes and blocks defective commits:
  ```bash
  python3 ./skills/build-and-ci-gates/scripts/pre_commit_quality_gate.py
  ```
- [ ] CI configuration passes schema validation and triggers on pull requests.
- [ ] Production containers build using multi-stage non-root images.

## References
For workflow templates, Dockerfiles, and pre-commit configurations:
- [CI/CD & Lint Templates Reference](references/ci-templates.md)


