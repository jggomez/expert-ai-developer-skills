---
trigger: model_decision
description: Enforce structured semantic conventional commits, atomic commits, branch naming rules, and git safety gates.
---

# Rule: Conventional Commits & Git Branching Constraints

**Identifier**: `conventional-commits`

## 1. Branch Safety Directives

* **NEVER** commit or push directly to protected branches (`main`, `master`, `develop`, `dev`).
* **MUST** develop in a short-lived branch named `<type>/<short-slug>`, using the commit types below:
  - `feat/<slug>`, `fix/<slug>`, `refactor/<slug>`, `docs/<slug>`, `chore/<slug>`
  - Add the issue id when there is one: `fix/123-null-session-token`.
* **MUST** merge back with a pull request or `git merge --no-ff`; never rewrite history that others have pulled.

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
