#!/usr/bin/env python3
import os
import sys
import subprocess

def run_tests_with_coverage(root_dir="."):
    print(f"Checking test coverage in {os.path.abspath(root_dir)}...")
    
    # 1. Node.js project (Jest, Vitest)
    pkg_json = os.path.join(root_dir, "package.json")
    if os.path.exists(pkg_json):
        print("Detected Node.js project. Running npm test with coverage...")
        # Check if there is a coverage script or pass --coverage
        cmd = ["npm", "test", "--", "--coverage", "--watchAll=false"]
        return run_command(cmd, root_dir)
        
    # 2. Python project (pytest-cov)
    pyproject = os.path.join(root_dir, "pyproject.toml")
    requirements = os.path.join(root_dir, "requirements.txt")
    tests_dir = os.path.join(root_dir, "tests")
    
    if os.path.exists(pyproject) or os.path.exists(requirements) or os.path.isdir(tests_dir):
        # Try running pytest with coverage
        try:
            # Check if pytest-cov is available
            result = subprocess.run(["pytest", "--cov", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                print("Running pytest with coverage...")
                return run_command(["pytest", "--cov=.", "tests/"], root_dir)
            else:
                print("pytest-cov not detected. Running regular pytest...")
                return run_command(["pytest"], root_dir)
        except FileNotFoundError:
            # Fallback to standard unittest
            print("pytest not found. Running python3 -m unittest...")
            return run_command(["python3", "-m", "unittest", "discover", "-s", "tests"], root_dir)
            
    # 3. Go project (go test -cover)
    go_mod = os.path.join(root_dir, "go.mod")
    if os.path.exists(go_mod):
        print("Detected Go project. Running go test with coverage...")
        return run_command(["go", "test", "-coverprofile=coverage.out", "./..."], root_dir)
        
    # 4. Rust project (cargo tarpaulin or cargo test)
    cargo_toml = os.path.join(root_dir, "Cargo.toml")
    if os.path.exists(cargo_toml):
        # Try cargo-tarpaulin if available, otherwise regular cargo test
        try:
            subprocess.run(["cargo", "tarpaulin", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Detected Rust project. Running cargo tarpaulin...")
            return run_command(["cargo", "tarpaulin"], root_dir)
        except FileNotFoundError:
            print("Detected Rust project. Running cargo test...")
            return run_command(["cargo", "test"], root_dir)
            
    print("❌ No test suite runner detected to compute coverage.")
    return 1

def run_command(cmd, cwd):
    try:
        result = subprocess.run(cmd, cwd=cwd)
        if result.returncode == 0:
            print(f"✅ Test run completed successfully: {' '.join(cmd)}")
        else:
            print(f"❌ Test run failed with exit code {result.returncode}")
        return result.returncode
    except Exception as e:
        print(f"Error executing command {' '.join(cmd)}: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_tests_with_coverage()
    sys.exit(exit_code)
