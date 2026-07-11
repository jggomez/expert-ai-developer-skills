#!/usr/bin/env python3
import os
import sys
import subprocess

def run_linters_and_formatters(root_dir="."):
    print(f"Running automated lint and format checks in {os.path.abspath(root_dir)}...")
    issues = 0
    
    # 1. Python Project Checks
    pyproject = os.path.join(root_dir, "pyproject.toml")
    requirements = os.path.join(root_dir, "requirements.txt")
    
    if os.path.exists(pyproject) or os.path.exists(requirements) or any(f.endswith('.py') for f in os.listdir(root_dir) if os.path.isfile(f)):
        # Check formatting with black
        try:
            print("Checking Python formatting (black)...")
            res = subprocess.run(["black", "--check", "."], cwd=root_dir)
            if res.returncode != 0:
                print("❌ Python files are not properly formatted (run 'black .')")
                issues += 1
            else:
                print("✅ Python formatting is clean.")
        except FileNotFoundError:
            print("ℹ️ 'black' not installed. Skipping formatting check.")
            
        # Check linting with ruff or flake8
        try:
            print("Running Python linter (ruff)...")
            res = subprocess.run(["ruff", "check", "."], cwd=root_dir)
            if res.returncode != 0:
                print("❌ Linting issues detected by ruff.")
                issues += 1
            else:
                print("✅ Linter reports no issues.")
        except FileNotFoundError:
            try:
                print("Ruff not found. Running flake8...")
                res = subprocess.run(["flake8", "."], cwd=root_dir)
                if res.returncode != 0:
                    print("❌ Linting issues detected by flake8.")
                    issues += 1
            except FileNotFoundError:
                print("ℹ️ No Python linter (ruff/flake8) found. Skipping linting.")

    # 2. Node.js Project Checks
    pkg_json = os.path.join(root_dir, "package.json")
    if os.path.exists(pkg_json):
        # Run prettier formatting check
        try:
            print("Checking Node.js formatting (prettier)...")
            res = subprocess.run(["npx", "prettier", "--check", "."], cwd=root_dir)
            if res.returncode != 0:
                print("❌ JS/TS files are not formatted (run 'npx prettier --write .')")
                issues += 1
            else:
                print("✅ JS/TS formatting is clean.")
        except FileNotFoundError:
            pass
            
        # Run eslint
        try:
            print("Running Node.js linter (eslint)...")
            res = subprocess.run(["npx", "eslint", "."], cwd=root_dir)
            if res.returncode != 0:
                print("❌ ESLint detected issues.")
                issues += 1
            else:
                print("✅ ESLint reports no issues.")
        except FileNotFoundError:
            pass

    # 3. Go Project Checks
    go_mod = os.path.join(root_dir, "go.mod")
    if os.path.exists(go_mod):
        print("Checking Go formatting (gofmt)...")
        res = subprocess.run(["gofmt", "-l", "."], cwd=root_dir, capture_output=True, text=True)
        if res.stdout.strip():
            print(f"❌ Unformatted Go files:\n{res.stdout}")
            issues += 1
        else:
            print("✅ Go formatting is clean.")
            
        print("Running Go linter (go vet)...")
        res = subprocess.run(["go", "vet", "./..."], cwd=root_dir)
        if res.returncode != 0:
            print("❌ Go vet reported issues.")
            issues += 1
        else:
            print("✅ Go vet reports no issues.")

    # 4. Rust Project Checks
    cargo_toml = os.path.join(root_dir, "Cargo.toml")
    if os.path.exists(cargo_toml):
        print("Checking Rust formatting (cargo fmt)...")
        res = subprocess.run(["cargo", "fmt", "--", "--check"], cwd=root_dir)
        if res.returncode != 0:
            print("❌ Rust files are not formatted (run 'cargo fmt')")
            issues += 1
        else:
            print("✅ Rust formatting is clean.")
            
        print("Running Rust linter (cargo clippy)...")
        res = subprocess.run(["cargo", "clippy", "--", "-D", "warnings"], cwd=root_dir)
        if res.returncode != 0:
            print("❌ Clippy reported warnings or errors.")
            issues += 1
        else:
            print("✅ Clippy reports no issues.")

    return issues

if __name__ == "__main__":
    total_issues = run_linters_and_formatters()
    if total_issues > 0:
        print(f"\n❌ Build checks failed with {total_issues} code gates failing.")
        sys.exit(1)
    else:
        print("\n✅ All build code gates passed successfully!")
        sys.exit(0)
