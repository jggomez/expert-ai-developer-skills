#!/usr/bin/env python3
import os
import subprocess
import sys

class PreCommitQualityGate:
    """Pre-commit hook wrapper that runs quality gates: tests, static analysis, and best practices."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.failed = False

    def log_section(self, title: str):
        print(f"\n========================================================")
        print(f"🔍 [Quality Gate] {title}")
        print(f"========================================================")

    def get_staged_files(self) -> list:
        try:
            output = subprocess.check_output(
                ["git", "diff", "--cached", "--name-only"], cwd=self.workspace_path
            ).decode("utf-8").strip()
            return [os.path.join(self.workspace_path, f) for f in output.split("\n") if f]
        except Exception:
            return []

    def run_static_analysis(self, staged_files: list):
        self.log_section("Running Static Analysis & Format Checks")
        python_files = [f for f in staged_files if f.endswith(".py")]
        markdown_files = [f for f in staged_files if f.endswith(".md")]
        
        # 1. Run Ruff/Black if present on staged python files
        if python_files:
            print(f"Staged Python files found: {len(python_files)}")
            # Try to run ruff check
            try:
                subprocess.check_call(["ruff", "check"] + python_files, stderr=subprocess.DEVNULL)
                print(" - Ruff lint check: PASSED")
            except FileNotFoundError:
                print(" - Ruff linter not found. Skipping.")
            except subprocess.CalledProcessError:
                print(" - Ruff lint check: FAILED")
                self.failed = True
                
            # Try to run black format check
            try:
                subprocess.check_call(["black", "--check"] + python_files, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(" - Black format check: PASSED")
            except FileNotFoundError:
                print(" - Black formatter not found. Skipping.")
            except subprocess.CalledProcessError:
                print(" - Black format check: FAILED (Code is not formatted. Run 'black' on your changes.)")
                self.failed = True

        # 2. Run local secret scanning on staged python files
        secret_scanner = os.path.join(self.workspace_path, "skills/security-audit/scripts/secret_scanner.py")
        if os.path.exists(secret_scanner) and python_files:
            try:
                subprocess.check_call([sys.executable, secret_scanner], stdout=subprocess.DEVNULL)
                print(" - Secret scanner: PASSED")
            except subprocess.CalledProcessError:
                print(" - Secret scanner: FAILED (Vulnerability or credentials leaked in staged files!)")
                self.failed = True

        # 3. Run doc link validation on staged markdown files
        doc_validator = os.path.join(self.workspace_path, "skills/documentation-expert/scripts/validate_docs.py")
        if os.path.exists(doc_validator) and markdown_files:
            try:
                subprocess.check_call([sys.executable, doc_validator], stdout=subprocess.DEVNULL)
                print(" - Markdown & link validator: PASSED")
            except subprocess.CalledProcessError:
                print(" - Markdown & link validator: FAILED")
                self.failed = True

        if not python_files and not markdown_files:
            print("No staged Python or Markdown files to analyze.")

    def run_unit_tests(self):
        self.log_section("Executing Test Suite")
        
        # 1. Look for verify_tests.py
        verify_tests = os.path.join(self.workspace_path, "skills/test-driven-development/scripts/verify_tests.py")
        if os.path.exists(verify_tests):
            try:
                subprocess.check_call([sys.executable, verify_tests])
                print(" - Test suite execution: PASSED")
                return
            except subprocess.CalledProcessError:
                print(" - Test suite execution: FAILED")
                self.failed = True
                return

        # 2. Fallback to standard pytest or unittest
        try:
            subprocess.check_call(["pytest"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(" - Pytest suite: PASSED")
        except FileNotFoundError:
            try:
                subprocess.check_call([sys.executable, "-m", "unittest", "discover"], stdout=subprocess.DEVNULL)
                print(" - Unittest discover suite: PASSED")
            except subprocess.CalledProcessError:
                print(" - Unittest suite: FAILED")
                self.failed = True
        except subprocess.CalledProcessError:
            print(" - Pytest suite: FAILED")
            self.failed = True

    def execute_gate(self):
        staged = self.get_staged_files()
        if not staged:
            print("No staged changes found. Skipping pre-commit quality gate.")
            sys.exit(0)
            
        self.run_static_analysis(staged)
        self.run_unit_tests()
        
        if self.failed:
            print("\n❌ Quality Gate: REJECTED. Commits cannot be finalized until quality checks pass.")
            sys.exit(1)
        else:
            print("\n✅ Quality Gate: APPROVED. Proceeding with commit.")
            sys.exit(0)

if __name__ == "__main__":
    workspace = os.getcwd()
    gate = PreCommitQualityGate(workspace)
    gate.execute_gate()
