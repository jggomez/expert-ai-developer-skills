---
name: pull-request-expert
description: Guidelines, conventional commits specifications, templates, and script validators to verify branches and pull request descriptions across languages.
---

# Pull Request Expert Skill

## Overview
This skill guides the preparation, partitioning, description authoring, and quality verification of Pull Requests (PRs). It acts as a Lead Release Engineer and Git Coordinator, ensuring that branches adhere to naming standards, changes remain atomic and reviewable (<200-400 lines), commit histories conform to Conventional Commits, and PR descriptions provide complete context with testing proof.

## When to Use
### Trigger Scenarios
- Preparing a feature, fix, or chore branch for pull request submission.
- Auditing local branch names and recent commit history against project conventions.
- Generating comprehensive Pull Request descriptions using standard markdown templates.
- Conducting pre-submission self-reviews to verify test results and eliminate stray debug code.

### When NOT to Use
- **Formatting a single local commit message**: Route to `commit-expert`.
- **Configuring CI/CD pipelines or pre-commit hooks**: Route to `build-and-ci-gates`.
- **Conducting formal security release compliance**: Route to `compliance-verifier`.

## Process
### Phase 1: PR Scope Partitioning & Branch Naming
1. Ensure the branch delivers exactly one cohesive capability. Keep total diffs under 200–400 lines whenever possible to facilitate thorough human review.
2. Adhere to structured branch naming:
   - `feat/<issue-id>-<short-description>`
   - `fix/<issue-id>-<short-description>`
   - `refactor/<short-description>`
   - `chore/<short-description>`

### Phase 2: Automated Branch & History Audit
Scan the active branch and recent commits to verify compliance:
```bash
python3 ./skills/pull-request-expert/scripts/validate_pr_content.py
```
The script validates branch naming patterns and ensures that commits on the branch adhere to Conventional Commits specifications.

### Phase 3: Self-Review & PR Description Authoring
1. Review the full `git diff` to identify left-over debug statements, temporary comments, or unformatted files.
2. Generate the PR description using the template:
   - **Summary**: Concise explanation of *why* the change is needed and *what* was implemented.
   - **Key Changes**: Bulleted list of architectural and functional edits.
   - **Verification & Testing**: Exact commands run and empirical test outcomes.
   - **Checklist**: Self-review confirmation (tests added, docs updated, linter clean).

## Usage
### Commands & Automation Scripts
```bash
# Audit active branch name and recent commit history
python3 ./skills/pull-request-expert/scripts/validate_pr_content.py
```

### Example Prompts
- *"Audit this branch and its commit history before I open a pull request."*
- *"Draft a pull request description for our new payment webhook implementation."*
- *"Help me split this large 800-line change into two smaller, reviewable pull requests."*

### Host Execution Instructions
- **Claude Code**: Run `validate_pr_content.py` via bash, then generate the PR summary markdown.
- **Antigravity**: Validate branch state before generating PR documentation.

## Red Flags
- Opening massive (>500 lines) PRs combining unrelated features, refactorings, and dependency updates.
- Branch names like `temp`, `fix1`, or `work` that obscure context.
- Empty or single-sentence PR descriptions ("Fixed bug") without test evidence.
- Submitting PRs with failing unit tests, linter warnings, or left-over `console.log` / `print` debug statements.

## Verification
- [ ] Branch naming conforms to standard convention (`feat/...`, `fix/...`, etc.).
- [ ] Automated validation script passes:
  ```bash
  python3 ./skills/pull-request-expert/scripts/validate_pr_content.py
  ```
- [ ] Full diff reviewed; zero stray debug statements or unformatted code.
- [ ] PR description includes summary, testing evidence, and verified checklist.

## References
- [Pull Request & Commit Best Practices](references/pr-best-practices.md)
- [PULL_REQUEST_TEMPLATE.md](templates/PULL_REQUEST_TEMPLATE.md)

