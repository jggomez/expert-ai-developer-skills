# Workflow: Staging, Committing & Pushing Code

**Identifier**: `commit-workflow`  
**Purpose**: Playbook to guide developers and agents on how to selectively stage changes, write semantic commit messages, validate syntax, and safely push work to version control using subagent delegation and Gitflow safety gates.

---

## 1. Prerequisites
* Current code is fully working and verified locally via linting/tests.
* Development must be active on an isolated branch (e.g., `feature/name`), never on `main`.

---

## 2. Subagent Delegation & Role Boundaries
- **Role Boundary**: The Lead Orchestrator delegates commit verification, Conventional Commit validation, and branch gate checks to `compliance-verifier`.
- **Subagent Delegation across Runners**:
  * **Google Antigravity Runner**:
    ```python
    invoke_subagent(
        name="compliance-verifier",
        prompt="Verify commit message syntax and branch safety compliance for staged changes."
    )
    ```
  * **Anthropic Claude Code Runner**:
    ```python
    Agent(
        agent="compliance-verifier",
        prompt="Verify commit message syntax and branch safety compliance for staged changes."
    )
    ```
- **Primary Skills**: `commit-expert`, `compliance-verifier`, `git-workflow`.

---

## 3. Step-by-Step Workflow

```mermaid
graph TD
    A[Start: Code Modified] --> B[Step 1: Check Git Status]
    B --> C[Step 2: Inspect Changes / Diff]
    C --> D[Step 3: Selective Staging]
    D --> E[Step 4: Validate Commit Message]
    E --> F[Step 5: Execute Commit & Run Hooks]
    F -->|Hook Fails| G[Fix Issues & Re-stage]
    G --> D
    F -->|Hook Passes| H[Step 6: Pull & Push to Origin]
```

### Step 1: Check Git Status
* Inspect what files have been changed, created, or deleted:
  ```bash
  git status
  ```

### Step 2: Inspect Changes (Diff Check)
* Review the exact line modifications to ensure no experimental code, print statements, or secrets are staged:
  ```bash
  git diff
  ```

### Step 3: Selective Staging
* **Rule**: Avoid `git add .` or `git add -A` unless all changes are strictly related to the same atomic commit. Stage files individually:
  ```bash
  git add path/to/changed_file.py
  git add tests/test_changed_file.py
  ```

### Step 4: Validate Commit Message
* Run the Conventional Commit message validator:
  ```bash
  python3 skills/commit-expert/scripts/validate_commit_msg.py .git/COMMIT_EDITMSG
  ```
* Ensure the message follows the Conventional Commit regex:
  * Pattern: `^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._-]+\))?: .+$`
  * **Header**: `<type>(<scope>): <description>` (max 50 chars, lowercase, imperative mood, no ending period).
  * **Body (Optional)**: Detail *Why* the change was made (wrapped at 72 chars).
  * **Footer (Optional)**: Link issue numbers (`Closes #14`).

### Step 5: Execute Commit and Run Hooks
* Run the commit command:
  ```bash
  git commit -m "feat(auth): add google oauth provider integration"
  ```
* **Gitflow Hook Validation**: The `PreToolUse` hook (`gitflow-branch-gate.js`) blocks commits if executed directly on `main` or `develop`.
* If pre-commit hooks fail:
  1. Read the hook error output.
  2. Fix formatting/linting issues in the codebase.
  3. Re-stage the modified files using `git add`.
  4. Run the commit command again.

### Step 6: Safely Push Changes
* Synchronize with remote origin. Pull with rebase before pushing to resolve simple head changes:
  ```bash
  git pull origin feature/your-branch-name --rebase
  git push origin feature/your-branch-name
  ```

---

## 4. Quality Gate & Verification

Before executing `git push`, verify:
- [ ] No local configuration files (e.g. `.env`, keys) are listed in `git status` under "Changes to be committed".
- [ ] The commit message starts with a standard type: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
- [ ] Commit message conforms to `^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)...`.
- [ ] Pre-commit hooks run successfully and return exit code `0`.
