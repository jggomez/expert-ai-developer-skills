# Configuring Git Hooks for Commit Quality

Git hooks automate quality gates locally by running validation scripts before commits or pushes are completed.

---

## 1. Setting Up a Local `commit-msg` Hook
A `commit-msg` hook intercepts the commit process, taking the path to the temporary commit message file as its first parameter. If the hook exits with a non-zero code, the commit is rejected.

### Step 1: Create the Hook File
In your repository, create a file at `.git/hooks/commit-msg`:

```bash
touch .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

### Step 2: Write the Hook Shell Script
Populate `.git/hooks/commit-msg` with the following shell command to delegate checks to our Python validator:

```bash
#!/bin/sh
# Delegate commit message checking to the Python validator
python3 ./skills/commit-expert/scripts/validate_commit_msg.py "$1"
```

---

## 2. Using `pre-commit` Framework
For larger teams, it is recommended to manage hooks using the `pre-commit` framework:

1. **Install pre-commit**:
   ```bash
   pip install pre-commit
   ```
2. **Create `.pre-commit-config.yaml`**:
   ```yaml
   repos:
     - repo: https://github.com/compilerla/conventional-pre-commit
       rev: v3.1.0
       hooks:
         - id: conventional-pre-commit
           stages: [commit-msg]
   ```
3. **Install the hooks**:
   ```bash
   pre-commit install --hook-type commit-msg
   ```
