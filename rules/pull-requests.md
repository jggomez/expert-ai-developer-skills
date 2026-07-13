# Rule: Pull Request Standards & AI Agent Self-Audit

**Identifier**: `pull-requests`  
**Purpose**: Enforce clean, high-quality, and reviewable Pull Requests (PRs) by integrating atomic change workflows, strict self-review guidelines, and verification rules aligned with Antigravity and Karpathy developer guidelines.

---

## 1. Pull Request Size & Partitioning (Surgical Changes)

To ensure rapid review times and prevent superficial code audits:
* **The 200-Line Limit**: Try to keep Pull Requests under **200 lines of changed code** (excluding auto-generated lockfiles, assets, or migrations).
* **Single Logical Concern**: A PR must deliver *exactly one* user story, feature, or bug fix. Do not mix unrelated refactoring, styling changes, or package updates with feature development.
* **No Speculative Code**: Do not include abstract classes, empty interfaces, or unused helper structures in anticipation of future requirements. Write only the minimum code required to solve the task at hand.

---

## 2. Mandatory Self-Review Checklist for Agents

AI agents must audit their own code diff before declaring a task complete or requesting a Pull Request.

### Clean Code Audit
- [ ] **No Leftover Debugging Code**: Scan for debug prints (`print()`, `console.log()`), test assertion stubs, or commented-out blocks of old code.
- [ ] **Unused Imports & Dead Code**: Remove all imports, variables, functions, or classes that *your specific changes* made redundant. Do not modify pre-existing, adjacent dead code unless instructed.
- [ ] **Style & Formatting**: Verify that changed files comply with the workspace formatters (e.g., `ruff`, `black`, `prettier`) and have 0 linter warnings.

### Configuration & Secret Scanning
- [ ] **Credentials Exposure**: Scan the diff using a secrets scanner to ensure no passwords, client keys, private certificates, or database credentials are being committed.
- [ ] **Workspace Isolation**: Ensure no local config files (`.env`, `google-services.json`, local database seeds, SQLite files) are included in the git staging index.

---

## 3. Pull Request Template Requirements

Every Pull Request must provide a descriptive body following this standard markdown layout:

```markdown
## 📋 Description
[Provide a clear and concise description of the changes introduced by this PR. Explain the rationale and how it solves the underlying issue.]

## 🚀 Type of Change
- [ ] 🌟 New Feature (`feat`)
- [ ] 🐛 Bug Fix (`fix`)
- [ ] 🛠️ Refactoring (`refactor`)
- [ ] 📚 Documentation Update (`docs`)
- [ ] 🧪 Adding/Correcting Tests (`test`)
- [ ] 🧹 Maintenance/Dependencies (`chore`)

## 🔗 Related Issue
[Link the issue resolved by this PR, e.g. Closes #123 or Fixes #456.]

## 🧪 Verification Plan
### Automated Tests
* Describe the exact test suite command run and its result (e.g., `pytest tests/auth/ -v` passed with 100% success).
### Manual Verification
* [List steps taken to verify UI or API behavior manually, including browser logs, console outputs, or API response snapshots.]
```

---

## 4. Branch and Push Constraints (Branch Safety)

* **Isolated Branches**: Never commit or push directly to `main`, `master`, or `develop`. All development must occur on separate branch names prefixed with `feature/`, `bugfix/`, or `hotfix/`.
* **Atomic History**: Keep commit messages semantic (Conventional Commits). Avoid vague messages like `fix`, `update`, `working`, or `wip`.
* **Fast-Forward & Rebase**: Ensure your feature branch is rebased against the latest target branch (`develop` or `main`) before final verification to resolve any merge conflicts beforehand.
