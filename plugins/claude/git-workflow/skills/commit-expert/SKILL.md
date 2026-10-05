---
name: commit-expert
description: Guidelines, best practices, and script validators to verify commit message formats and configure local git commit hooks.
---

# Commit Expert Skill

## Overview
This skill enforces high-quality, readable, and bisectable Git commit histories. It acts as a Git Version Control Specialist and History Architect, ensuring that all commits follow the 7 rules of git messaging, utilize standard Conventional Commits prefixes, maintain atomic boundaries, and validate formatting through automated hook scripts aligned with deterministic branch gates.

## When to Use
### Trigger Scenarios
- Authoring commit messages for staged code changes.
- Setting up or validating local git `commit-msg` hooks.
- Squashing, interactive rebasing, or cleaning up messy commit histories before PR submission.
- Enforcing Conventional Commits standards and branch naming alignment across an engineering team.

### When NOT to Use
- **Authoring Pull Request descriptions or branch reviews**: Route to `pull-request-expert`.
- **Pre-commit quality and linting checks**: Route to `build-and-ci-gates`.
- **Writing application source code**: Route to `code-implementer`.

## Process
### Phase 1: Conventional Commits Specification & Regex Standard
Structure every commit message following the 7 rules of git commit messages and the formal Conventional Commits standard:
1. **Canonical Commit Pattern**:
   ```regex
   ^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._-]+\))?: .+$
   ```
2. **Permitted Types**:
   - `feat`: A new user-facing feature or API capability.
   - `fix`: A bug fix for existing functionality.
   - `docs`: Documentation-only additions or modifications.
   - `style`: Formatting, missing semicolons, whitespace changes with zero code logic alterations.
   - `refactor`: Code change that neither fixes a bug nor adds a feature.
   - `perf`: Code change that improves runtime performance or memory usage.
   - `test`: Adding missing tests or correcting existing tests.
   - `build`: Changes affecting the build system, packaging, or external dependencies.
   - `ci`: Changes to CI configuration files and automation scripts.
   - `chore`: Auxiliary tasks, housekeeping, tool updates.
   - `revert`: Reverting a previous commit.

3. **Branch Gate Alignment (`gitflow-branch-gate.js`)**:
   - Every commit must strictly align with the active branch prefix enforced by `gitflow-branch-gate.js`:
     * Branches prefixed with `feat/*` or `feature/*` must carry commits typed `feat` (or supporting `test`, `docs`).
     * Branches prefixed with `fix/*`, `bugfix/*`, or `hotfix/*` must carry commits typed `fix`.
     * Direct commits to protected branches (`main`, `master`, `develop`, `release/*`) are blocked by `gitflow-branch-gate.js`.

4. **Formatting Constraints**:
   - **Subject Line**: `<type>(<scope>): <imperative summary>` (50 characters maximum, imperative mood, NO trailing period).
   - **Body (when context is required)**: Separated by a blank line, wrapped at 72 characters, explaining *what* and *why*.

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
- *"Audit the recent 5 commit messages on this branch against the Conventional Commits regex and Gitflow rules."*
- *"Help me set up a local commit-msg git hook to block non-conventional commit messages."*

### Host Execution Instructions
- **Claude Code**: Validate commit message files before running `git commit`, ensuring compatibility with `gitflow-branch-gate.js`.
- **Antigravity**: Ensure that every commit created during the COMMIT phase complies with Conventional Commits and branch rules.

## Red Flags
- Commits violating the Conventional Commits regex `^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)...`.
- Vague commit subjects like "fixes", "updates", "wip", or "changes".
- Exceeding 50 characters on the subject line or ending with a trailing period.
- Committing directly to protected branches (`main`, `master`, `develop`) without feature branches.
- Blending multiple unrelated tasks into one giant commit.
- Using past tense (*"added feature"*) instead of imperative mood (*"add feature"*).

## Verification
- [ ] Commit message conforms to `^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._-]+\))?: .+$`.
- [ ] Commit type aligns with active branch type enforced by `gitflow-branch-gate.js`.
- [ ] Subject is under 50 characters, uses imperative mood, and has no period.
- [ ] Blank line separates subject and body.
- [ ] Automated validation script passes:
  ```bash
  python3 ./skills/commit-expert/scripts/validate_commit_msg.py .git/COMMIT_EDITMSG
  ```

## References
- [Git Commit Best Practices & Guidelines](references/commit-guidelines.md)
- [Configuring Git Hooks for Commit Quality](references/git-hooks-setup.md)
