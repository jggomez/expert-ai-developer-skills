# Git Hooks Automation Reference

Git hooks allow you to execute verification scripts automatically during git lifecycle events (like commits or pushes). This enforces code quality gates and branch policies locally before code ever reaches remote repositories.

---

## 1. Pre-Commit Hook (`.git/hooks/pre-commit`)
This hook runs format and style checks automatically before any commit is finalized.

Save the following content to `.git/hooks/pre-commit` and run `chmod +x .git/hooks/pre-commit`:

```bash
#!/bin/bash

# Target verification scripts
CHECK_SCRIPT="./build-and-ci-gates/scripts/run_checks.py"

if [ -f "$CHECK_SCRIPT" ]; then
    echo "Running build validation gates..."
    python3 "$CHECK_SCRIPT"
    RESULT=$?
    if [ $RESULT -ne 0 ]; then
        echo "Error: Code quality checks failed. Commit aborted."
        exit 1
    fi
else
    echo "Warning: Build validation script not found. Skipping formatting checks."
fi

exit 0
```

---

## 2. Pre-Push Hook (`.git/hooks/pre-push`)
This hook runs all unit and integration tests automatically before any code is pushed to remote repositories.

Save the following content to `.git/hooks/pre-push` and run `chmod +x .git/hooks/pre-push`:

```bash
#!/bin/bash

# Target verification scripts
TEST_SCRIPT="./test-driven-development/scripts/verify_tests.py"

if [ -f "$TEST_SCRIPT" ]; then
    echo "Running test suite before push..."
    python3 "$TEST_SCRIPT"
    RESULT=$?
    if [ $RESULT -ne 0 ]; then
        echo "Error: Test suite failed. Push aborted."
        exit 1
    fi
else
    echo "Warning: Test verification script not found. Skipping tests."
fi

exit 0
```

---

## 3. Gitflow Branch Safety Hook (`.git/hooks/pre-push`)
To prevent direct pushes to `main` or `develop` (forcing developer workflows to use feature/bugfix branches and Pull Requests), add this block to your `pre-push` hook:

```bash
#!/bin/bash

protected_branch="main"
current_branch=$(git symbolic-ref --short HEAD)

if [ "$current_branch" = "$protected_branch" ]; then
    echo "Error: Direct pushes to '$protected_branch' are prohibited by branch policy."
    echo "Please create a feature branch and submit a Pull Request."
    exit 1
fi
```
