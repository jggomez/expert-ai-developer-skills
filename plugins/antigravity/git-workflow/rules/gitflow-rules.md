---
trigger: always_on
description: Gitflow engineering rules enforcing branch isolation, Conventional Commits format, and clean working tree invariants.
---

# Gitflow Workflow Rules & Commit Standards

**Identifier**: `gitflow-rules`

## 1. Branch Safety Invariant
- **Protected Branches**: `main`, `master`, and `develop` represent stable release environments. Committing, adding, or pushing directly to these branches is strictly prohibited.
- **Feature Branches**: All work must be conducted on isolated branches prefixed with `feature/`, `bugfix/`, or `chore/` (e.g. `feature/user-auth`, `bugfix/issue-42`).
- **Merge Invariant**: Code enters `main` or `develop` exclusively through validated Pull Requests with passing CI checks.

## 2. Conventional Commits Standards
Every commit message must follow the Conventional Commits specification:
```
<type>(<optional scope>): <description>

[optional body]

[optional footer(s)]
```
- **Allowed Types**:
  - `feat`: A new feature for the user.
  - `fix`: A bug fix.
  - `refactor`: Code change that neither fixes a bug nor adds a feature.
  - `test`: Adding missing tests or correcting existing tests.
  - `docs`: Documentation only changes.
  - `chore`: Build process, dependencies, or auxiliary tool changes.
  - `perf`: A code change that improves performance.

## 3. Working Tree Cleanliness Invariant
- Never complete a session leaving uncommitted merge conflicts (`<<<<<<< HEAD`), unresolved rebase states, or uncommitted WIP files without explicit user instruction.
