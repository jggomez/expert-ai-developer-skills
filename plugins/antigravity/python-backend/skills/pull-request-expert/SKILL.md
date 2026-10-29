---
name: pull-request-expert
description: Prepare, audit, and author concise (<= 40 lines), Fail-Honest Pull Requests with Conventional Commits validation, docs/<feature-name>/test-matrix.md links, and transparent BLOCKED/SKIPPED gate disclosure.
---

# Pull Request Expert Skill

## Overview
This skill guides branch partitioning, commit history auditing, and authoring concise, high-signal Pull Request (PR) descriptions (`<= 40 lines`). Acting as a Lead Release Engineer, it enforces reviewable diffs (`< 200–400 LOC`), Conventional Commits, empirical links to `docs/<feature-name>/test-matrix.md`, and **Fail-Honest** disclosure of any `BLOCKED` or `SKIPPED` verification gates.

## When to Use
### Trigger Scenarios
- Preparing a feature, fix, refactor, or chore branch for Pull Request submission.
- Auditing branch naming and commit messages against Conventional Commits standards.
- Authoring Zero-Fluff PR descriptions (`<= 40 lines`) backed by empirical test evidence.
- Performing pre-PR self-review to catch debug leftovers and verify honest gate statuses.

### When NOT to Use
- **Validating a single local commit message**: Route to `commit-expert`.
- **Authoring CI/CD workflow YAML**: Route to `build-and-ci-gates`.
- **Formal OWASP & architectural sign-off**: Route to `compliance-verifier`.

## Process
### Phase 1: Scope Partitioning & Branch Naming
Keep each PR focused on one cohesive capability (`< 200–400 LOC` when feasible) on a Conventional branch (`feat/<slug>`, `fix/<slug>`, `refactor/<slug>`, `chore/<slug>`).

### Phase 2: Automated Branch & Commit History Audit
Verify branch naming and Conventional Commit compliance across branch commits:
```bash
python3 ./skills/pull-request-expert/scripts/validate_pr_content.py
```

### Phase 3: Self-Review & Concise Fail-Honest PR Description (`<= 40 lines`)
1. Inspect `git diff` to remove stray debug statements (`print`, `console.log`), dead code, or secret leaks.
2. Author a Zero-Fluff PR description strictly `<= 40 lines`:
   - **Summary & Key Changes**: 2–5 bullets stating *why* and *what* changed.
   - **Verification & Test Matrix**: Exact commands executed with exit codes, linking `docs/<feature-name>/test-matrix.md` when present.
   - **Fail-Honest Gate Status**: Explicitly disclose any `BLOCKED` or `SKIPPED` verification gates (e.g., E2E browser checks without a live server/Chromium or unavailable staging env) and why — **never** check off or claim untested checks passed.

## Usage
### Commands & Automation Scripts
```bash
# Validate active branch name and Conventional Commits history
python3 ./skills/pull-request-expert/scripts/validate_pr_content.py
```

### Host Execution Instructions
- **Claude Code**: Run `validate_pr_content.py` via Bash, review `git diff`, and draft the `<= 40 lines` PR body.
- **Antigravity**: Run `validate_pr_content.py` via `run_command` and verify honest `PASSED`/`BLOCKED`/`SKIPPED` evidence before drafting the PR.

## Red Flags
- Bloated PR descriptions (`> 40 lines`) or massive multi-topic diffs (`> 500 LOC`).
- Claiming E2E, integration, or manual checks passed when they were `BLOCKED` or `SKIPPED`.
- Omitting `docs/<feature-name>/test-matrix.md` links or empirical test command output.
- Non-standard branch names (`temp`, `fix1`) or leftover debug prints in the diff.

## Verification
- [ ] Branch name and commit history pass validation (`exit code 0`):
  ```bash
  python3 ./skills/pull-request-expert/scripts/validate_pr_content.py
  ```
- [ ] PR description is strictly `<= 40 lines` and links `docs/<feature-name>/test-matrix.md` (when applicable).
- [ ] Every `BLOCKED` or `SKIPPED` gate is transparently disclosed with zero fabricated checkmarks.
- [ ] Full `git diff` is free of debug statements, conflict markers, and secrets.

## References
- [Pull Request & Commit Best Practices](references/pr-best-practices.md)
- [PULL_REQUEST_TEMPLATE.md](templates/PULL_REQUEST_TEMPLATE.md)
