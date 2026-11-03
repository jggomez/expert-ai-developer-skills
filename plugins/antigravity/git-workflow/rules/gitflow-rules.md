---
trigger: always_on
description: Git invariants - protected branches, scope drift, Conventional Commits, atomic staging, clean merges and concise fail-honest pull requests.
---

# Gitflow Rules

- **Protected branches**: never stage, commit or push on `main`, `master`, `develop` or `dev`. Before editing, check `git symbolic-ref --short HEAD`; on a protected branch create `feat/<slug>`, `fix/<slug>` or `refactor/<slug>` and tell the user.
- **Scope Drift**: on a feature branch, if a request is unrelated to it, ask (`ask_question`) whether to create `feat/<new-slug>` or continue here; never pile unrelated changes on one branch.
- **Conventional Commits**: `<type>(<scope>): <description>`, imperative, lowercase, no trailing period. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `build`, `ci`.
- **Atomic staging**: `git add <files>`; never `git add .` on a dirty tree.
- **Clean tree**: never finish with conflict markers or an unfinished merge or rebase.
- **Pull requests** (`<= 40` lines): Summary, Key Changes, Verification (exact commands and exit codes, link `docs/<feature-name>/test-matrix.md` when it exists). Disclose any `BLOCKED` or `SKIPPED` check with its reason; never tick an untested box.
