---
trigger: always_on
description: Gitflow engineering rules enforcing Branch Protection, auto-branching, proactive Scope Drift detection via ask_question, Conventional Commits, Atomic Staging, and concise Fail-Honest Pull Request descriptions.
---

# Gitflow Workflow Rules, Commit & PR Standards

**Identifier**: `gitflow-rules`

## 1. Branch Protection & Automatic Feature Branch Provisioning
- **Protected Base Branches**: `main`, `master`, `develop`, and `dev` are strictly protected; committing, staging, or pushing directly to them is **STRICTLY PROHIBITED**.
- **State 0 Auto-Branching Gate**: Inspect the active branch via `git symbolic-ref --short HEAD` before any code modification. If on a protected base branch, automatically create and switch to a Conventional branch (`git checkout -b feat/<descriptive-slug>`, `fix/<slug>`, `refactor/<slug>`) and notify the user.
- **Merge Invariant**: Code reaches `main` or `develop` exclusively via reviewed Pull Requests with verified checks.

## 2. Proactive Scope Drift Detection (`ask_question`)
- **Scope Drift Guard**: When already on an active feature branch, if a new user prompt introduces orthogonal or unrelated domain functionality, **NEVER** silently accumulate unrelated changes on the current branch.
- **Interactive Modal**: Pause and prompt the user via `ask_question` with explicit options: (1) create and switch to a new dedicated branch (`feat/<new-slug>`), or (2) continue on the current branch with explicit user approval.

## 3. Conventional Commits Standards
- Format every commit message as `<type>(<optional-scope>): <description>` (with optional body and footers):
  - Imperative mood, lowercase description, no trailing period (e.g., `feat(auth): implement token refresh rotation`).
  - Allowed types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `build`, `ci`.

## 4. Concise & Fail-Honest Pull Request Standards (`<= 40 lines`)
- **Zero-Fluff PR Cap**: Keep Pull Request descriptions concise and scannable (`<= 40 lines`), covering *Summary*, *Key Changes*, and *Verification Proof*.
- **Empirical Evidence & Matrix Link**: Link `docs/<feature-name>/test-matrix.md` (when applicable) alongside exact test commands and exit codes.
- **Fail-Honest Gate Disclosure**: Transparently disclose any `BLOCKED` or `SKIPPED` verification gates (e.g., Playwright E2E checks without a live server/Chromium binary or missing external credentials) with the exact blocker reason — **never** claim or check off untested gates as passed.

## 5. Working Tree Cleanliness & Merge Safety
- **Atomic Staging**: Stage files selectively (`git add <file1> <file2>`); **NEVER** run blanket `git add .` on dirty workspaces so scratch files, logs, or secrets are never staged.
- **Merge & Workspace Hygiene**: Never leave conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`), unresolved merge states (`UU`, `AA`), or unexpected dangling rebase states at session completion.
