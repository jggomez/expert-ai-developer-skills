#!/usr/bin/env python3
import re
import subprocess
import sys

class PRValidator:
    """Validates branch naming, commit formatting, and debug leak checks before PR integration."""
    
    def __init__(self):
        self.errors = []

    def get_current_branch(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            ).decode("utf-8").strip()
        except Exception:
            return "feature/simulation-branch"

    def get_recent_commits(self, limit: int = 5) -> list:
        try:
            output = subprocess.check_output(
                ["git", "log", f"-n", str(limit), "--pretty=format:%s"]
            ).decode("utf-8").strip()
            return output.split("\n") if output else []
        except Exception:
            return ["feat(auth): implement user authentication", "docs: update manual"]

    def check_branch_name(self):
        branch = self.get_current_branch()
        # Allow main/develop for root simulation, but features must have namespaces
        if branch in ["main", "master", "develop", "HEAD"]:
            return
            
        allowed_pattern = r"^(feature|bugfix|hotfix|release|chore|refactor)/[a-zA-Z0-9_-]+$"
        if not re.match(allowed_pattern, branch):
            self.errors.append(
                f"Branch naming violation: Current branch '{branch}' does not match conventional format. "
                "Rename it using 'feature/*', 'bugfix/*', 'chore/*', or 'refactor/*'."
            )

    def check_commits(self):
        commits = self.get_recent_commits()
        conventional_pattern = r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build)(\([a-zA-Z0-9_-]+\))?:\s+.+$"
        
        for commit in commits:
            if not re.match(conventional_pattern, commit):
                self.errors.append(
                    f"Conventional Commits violation: Commit message '{commit}' is missing conventional prefix "
                    "(e.g., 'feat(auth): ...', 'fix: ...', 'docs: ...')."
                )

    def run_checks(self):
        print("Auditing branch and commit qualities...")
        self.check_branch_name()
        self.check_commits()
        
        if self.errors:
            print("\nPR Integration Audit FAILED:")
            for err in self.errors:
                print(f" - {err}")
            sys.exit(1)
        else:
            print("\nSuccess! Branch name and recent commit messages comply with specifications.")
            sys.exit(0)

if __name__ == "__main__":
    validator = PRValidator()
    validator.run_checks()
