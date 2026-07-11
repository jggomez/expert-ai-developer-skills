# Git Commit Best Practices & Guidelines

A clean git commit history is critical for repository health, code auditing, and automatic generation of changelogs. This guide details standards for commit messages and committing habits.

---

## 1. The Seven Rules of a Great Commit Message
Follow these rules to write clear, informative commits (based on Chris Beams' standards):
1. **Separate subject from body** with a blank line.
2. **Limit the subject line to 50 characters**.
3. **Capitalize the subject line** (unless using Conventional Commit prefix rules).
4. **Do not end the subject line with a period**.
5. **Use the imperative mood** in the subject line (e.g., "Add OAuth provider" instead of "Added OAuth provider").
6. **Wrap the body at 72 characters**.
7. **Use the body to explain what and why**, not how (the diff shows how).

---

## 2. Conventional Commits Standard
Subject lines should follow the format: `<type>(<scope>): <subject>`

### Primary Commit Types
- **`feat`**: Adds a new capability to the codebase.
- **`fix`**: Repairs a bug in the code.
- **`docs`**: Updates markdown guides or inline docstrings.
- **`style`**: Corrects code indentation, missing semicolons, or whitespaces without editing logic.
- **`refactor`**: Reorganizes code patterns to improve architecture without altering behavior.
- **`test`**: Introduces new test files or upgrades existing assertions.
- **`chore`**: Updates external dependencies, build pipelines, or configuration files.

---

## 3. Atomic Commits & Rebasing
- **Atomic Commits**: Each commit must contain exactly one logical change. Never bundle unrelated changes (e.g. fixing a typo in billing and adding a feature in auth) in a single commit.
- **Bisectability**: Every commit should compile and pass tests. This allows using `git bisect` to locate regressions.
- **Interactive Rebase**: Use `git rebase -i` to clean up local commits (squash, reword, fixup) before pushing them to the remote origin.
