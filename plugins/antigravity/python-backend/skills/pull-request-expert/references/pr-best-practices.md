# Pull Request & Commit Best Practices

This guide outlines standards for writing commit messages, partitioning pull requests, and performing self-reviews to streamline code integration.

---

## 1. Conventional Commits Specification
All commits must follow the Conventional Commits structure to enable automated changelogs and semver versioning:

```
<type>(<optional scope>): <description>

[optional body]

[optional footer(s)]
```

### Common Commit Types
* **`feat`**: A new user-facing feature.
* **`fix`**: A bug fix.
* **`docs`**: Changes to documentation only.
* **`style`**: Formatting, missing semi-colons, no code changes.
* **`refactor`**: Code restructuring without behavior changes.
* **`test`**: Adding missing tests or correcting existing ones.
* **`chore`**: Maintenance, updating dependencies, build configuration.

### Example Commit Message
```
feat(auth): add google oauth2 login provider

Implemented authentication gateway configuration and added route /auth/google
to fetch user profiles.

Closes #142
```

---

## 2. Pull Request Partitioning Rules
To ensure high-quality reviews and fast deployment cycles:
1. **Keep it Small**: Ideal PR size is **under 200 lines of changed code**. Large PRs lead to superficial reviews.
2. **One Logical Change**: Do not mix a new feature with refactoring of another module or updating formatting across the repo.
3. **Atomic Changes**: Ensure the branch compiles and all tests pass on every single commit. Do not push broken intermediate commits.

---

## 3. Self-Review Checklist
Before assigning reviewers to a PR, the author must:
- [ ] Run `git diff` locally to check for debug print statements (`print()`, `console.log()`).
- [ ] Run the project's linter and format checker.
- [ ] Execute all unit and integration tests locally.
- [ ] Ensure all relative file links in updated markdowns are correct.
