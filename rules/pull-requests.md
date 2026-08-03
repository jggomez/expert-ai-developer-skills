---
trigger: model_decision
description: Guidelines and quality gates for Pull Request creation, line-change thresholds, and self-review checklists.
---

# Rule: Pull Request Standards & AI Agent Self-Audit

**Identifier**: `pull-requests`

## 1. PR Scope & Size Constraints

* **MUST** keep Pull Requests under **200 lines of changed code** (excluding lockfiles and auto-generated assets).
* **MUST** cover exactly one logical concern per PR. **MUST NOT** mix refactoring or styling with feature PRs.
* **NEVER** include speculative classes, stubs, or unused helper functions in PR diffs.

## 2. Mandatory Self-Audit Checklist

Before creating or requesting a PR, agents **MUST** verify:
- [ ] **No Debug Artifacts**: **NEVER** commit `print()`, `console.log()`, debug stubs, or dead commented code.
- [ ] **Unused Imports**: Remove all redundant imports or unused symbols introduced by your changes.
- [ ] **Linting & Formatting**: **MUST** pass workspace linters (`ruff`, `black`, `prettier`) with 0 errors.
- [ ] **Secrets Prevention**: Confirm zero API keys, passwords, certificates, or `.env` files are staged.
- [ ] **Empirical Test Evidence**: Confirm 100% test suite pass with runtime log evidence.

## 3. Mandatory PR Description Layout

```markdown
## 📋 Description
[Rationale and concise summary of changes]

## 🚀 Type of Change
- [ ] `feat` / `fix` / `refactor` / `docs` / `test` / `chore`

## 🔗 Related Issue
Closes #<id>

## 🧪 Verification Plan
* **Automated Tests**: [Exact test command and pass output]
* **Manual Verification**: [Steps and log/UI verification]
```
