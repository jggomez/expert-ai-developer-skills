# Rule: Conventional Commits & Git Branching Constraints

**Identifier**: `conventional-commits`  
**Purpose**: Enforce clean, semantic, and standardized commit histories and prevent accidental commits or pushes directly to protected branches.

---

## 1. Branch Safety Constraints

### Protected Branches
Direct modifications to the following branches are strictly prohibited:
* `main` / `master`
* `develop` / `dev`
* `release/*`

### Standard Branch Naming
All changes must be developed in isolated feature, bugfix, or hotfix branches. Branch names must follow this convention:
* `feature/issue-ID-short-description` (e.g., `feature/102-user-auth`)
* `bugfix/issue-ID-short-description` (e.g., `bugfix/45-db-leak`)
* `hotfix/issue-ID-short-description` (e.g., `hotfix/911-auth-exploit`)
* `docs/short-description` (e.g., `docs/api-readme`)

---

## 2. Commit Message Specification

All commit messages must adhere to the **Conventional Commits 1.0.0** specification.

### Format
```text
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Commit Types
* **`feat`**: A new feature for the user, not a new feature for a build script.
* **`fix`**: A bug fix for the user, not a fix to a build script.
* **`docs`**: Changes to the documentation.
* **`style`**: Formatting, missing semi-colons, etc.; no production code change.
* **`refactor`**: Refactoring production code, e.g. renaming a variable.
* **`perf`**: Code changes that improve performance.
* **`test`**: Adding missing tests, refactoring tests; no production code change.
* **`build`**: Changes that affect the build system or external dependencies (example scopes: gulp, broccoli, npm, poetry).
* **`ci`**: Changes to our CI configuration files and scripts (example scopes: GitHub Actions, Travis, GitLab CI).
* **`chore`**: Other changes that don't modify src or test files.
* **`revert`**: Reverts a previous commit.

### Rules of Thumb
1. Use the imperative mood in the description ("add feature" instead of "added feature" or "adds feature").
2. Do not capitalize the first letter of the description.
3. Do not end the description with a period.
4. Limit the first line to 72 characters or fewer.

---

## 3. Commit Body and Footers

### Breaking Changes
Breaking changes must start with `BREAKING CHANGE:` in the body or footer, or include a `!` after the type/scope on the first line (e.g., `feat(api)!: modify authentication response schema`).
The description of the breaking change must state what broke and how to migrate:

```text
feat(auth): migrate user token structure to JWT

BREAKING CHANGE: The local storage token format has changed. Users must log in again to acquire a valid JWT.
```

### Referencing Issues
Include issue numbers in the footer using the syntax `Closes #<issue>` or `Fixes #<issue>`:

```text
fix(parser): resolve ast infinite loop on empty input

Fixes #143
```

---

## 4. Git Workflows and Commit Size

* **Atomic Commits**: Group only related changes into a single commit. Do not combine database schema changes with UI layout adjustments.
* **No Large/Staged Diffs**: AI agents must avoid running `git add .` indiscriminately. Stage files selectively using `git add <path>` to keep commits clean.
* **Pull Requests**: Pull Requests should contain a descriptive title matching the conventional commits style and a markdown description detailing the changes, testing completed, and migration details if applicable.
