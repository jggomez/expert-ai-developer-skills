---
name: commit-expert
description: Guidelines, best practices, and script validators to verify commit message formats and configure local git commit hooks.
---

# Commit Expert Skill

## Overview
This skill enforces high-quality, readable, and bisectable Git commit histories. It acts as a Git Version Control Specialist and History Architect, ensuring that all commits follow the 7 rules of git messaging, utilize standard Conventional Commits prefixes, maintain atomic boundaries, and validate formatting through automated hook scripts.

## When to Use
### Trigger Scenarios
- Authoring commit messages for staged code changes.
- Setting up or validating local git `commit-msg` hooks.
- Squashing, interactive rebasing, or cleaning up messy commit histories before PR submission.
- Enforcing Conventional Commits standards across an engineering team.

### When NOT to Use
- **Authoring Pull Request descriptions or branch reviews**: Route to `pull-request-expert`.
- **Pre-commit quality and linting checks**: Route to `build-and-ci-gates`.
- **Writing application source code**: Route to `code-implementer`.

## Process
### Phase 1: Conventional Commits Message Formulation
Structure every commit message following the 7 rules of git commit messages:
1. **Subject Line**:
   - Format: `<type>(<scope>): <imperative summary>` (e.g. `feat(auth): add refresh token endpoint`).
   - Limit subject to 50 characters maximum.
   - Do NOT end the subject line with a period.
   - Use the imperative mood (*"Fix billing typo"* instead of *"Fixed billing typo"* or *"Fixes billing typo"*).
2. **Body (when context is required)**:
   - Separate subject from body with a single blank line.
   - Wrap body lines at 72 characters.
   - Explain *what* and *why*, not *how*.

### Phase 2: Atomic Staging & Clean History
1. Stage only logically cohesive changes in a single commit (one feature, fix, or refactor per commit).
2. Use interactive rebase (`git rebase -i HEAD~N`) to squash intermediate "wip" or fixup commits before pushing.

### Phase 3: Automated Validation
Validate the commit message format using the automated validator script:
```bash
python3 ./skills/commit-expert/scripts/validate_commit_msg.py .git/COMMIT_EDITMSG
```

## Usage
### Commands & Automation Scripts
```bash
# Validate a specific commit message file or git edit message
python3 ./skills/commit-expert/scripts/validate_commit_msg.py .git/COMMIT_EDITMSG
```

### Example Prompts
- *"Format a Conventional Commit message for these staged authentication changes."*
- *"Audit the recent 5 commit messages on this branch against the 7 rules of git."*
- *"Help me set up a local commit-msg git hook to block non-conventional commit messages."*

### Host Execution Instructions
- **Claude Code**: Validate commit message files before running `git commit`.
- **Antigravity**: Ensure that every commit created during the COMMIT phase of Loop Engineering complies with Conventional Commits.

## Red Flags
- Vague commit subjects like "fixes", "updates", "wip", or "changes".
- Exceeding 50 characters on the subject line or ending with a trailing period.
- Blending multiple unrelated tasks (e.g. a bug fix and an unrelated refactor) into one giant commit.
- Using past tense (*"added feature"*) instead of imperative mood (*"add feature"*).

## Verification
- [ ] Commit message conforms to `<type>(<scope>): <summary>`.
- [ ] Subject is under 50 characters, uses imperative mood, and has no period.
- [ ] Blank line separates subject and body.
- [ ] Automated validation script passes:
  ```bash
  python3 ./skills/commit-expert/scripts/validate_commit_msg.py .git/COMMIT_EDITMSG
  ```

## References
- [Git Commit Best Practices & Guidelines](references/commit-guidelines.md)
- [Configuring Git Hooks for Commit Quality](references/git-hooks-setup.md)

