---
trigger: model_decision
description: Enforce structured semantic conventional commits, atomic commits, branch naming rules, and git safety gates.
---

# Rule: Conventional Commits & Git Branching Constraints

**Identifier**: `conventional-commits`

## 1. Branch Safety Directives

* **NEVER** commit or push directly to protected branches (`main`, `master`, `develop`, `release/*`).
* **MUST** develop in isolated branches using mandatory naming conventions:
  - `feature/<issue-id>-<short-description>`
  - `bugfix/<issue-id>-<short-description>`
  - `hotfix/<issue-id>-<short-description>`
  - `docs/<short-description>`

## 2. Conventional Commit Format

**Format**: `<type>(<scope>): <description>`

| Type | Purpose | Mandatory Rules |
| :--- | :--- | :--- |
| `feat` | New user-facing capability | **MUST** use lowercase imperative mood ("add", not "added"). |
| `fix` | User-facing bug fix | **MUST NOT** capitalize first letter. **MUST NOT** end with a period. |
| `docs` | Documentation updates | Header length **MUST NOT** exceed 72 characters. |
| `refactor`| Code change without behavior change | **MUST NOT** mix refactoring with new feature commits. |
| `test` | Adding/refactoring tests | **MUST NOT** contain production code edits. |
| `chore` | Build, dependencies, tool configs | **MUST** specify scope (e.g. `chore(deps)`). |

## 3. Commit Integrity & Safety

* **Breaking Changes**: **MUST** include `BREAKING CHANGE:` in body/footer or append `!` (e.g. `feat(auth)!: token schema change`).
* **Issue References**: **MUST** append `Closes #<id>` or `Fixes #<id>` in footers when resolving issues.
* **Atomic Staging**: **NEVER** run `git add .` indiscriminately. **MUST** stage files selectively (`git add <path>`).
