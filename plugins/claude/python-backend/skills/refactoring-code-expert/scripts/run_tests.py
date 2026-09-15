#!/usr/bin/env python3
import os
import sys
import subprocess

def detect_and_run_tests(root_dir="."):
    """Detects the test suite runner and runs the project's tests."""
    print(f"Detecting test suite in {os.path.abspath(root_dir)}...")
    
    # 1. Node.js (package.json)
    pkg_json = os.path.join(root_dir, "package.json")
    if os.path.exists(pkg_json):
        print("Detected Node.js project. Running npm test...")
        return run_command(["npm", "test"], root_dir)
        
    # 2. Python (pytest, unittest, or pyproject.toml)
    pyproject = os.path.join(root_dir, "pyproject.toml")
    requirements = os.path.join(root_dir, "requirements.txt")
    tests_dir = os.path.join(root_dir, "tests")
    
    if os.path.exists(pyproject) or os.path.exists(requirements) or os.path.exists(tests_dir):
        # Prefer pytest if installed, fallback to unittest
        try:
            subprocess.run(["pytest", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Detected Python project with pytest. Running pytest...")
            return run_command(["pytest"], root_dir)
        except FileNotFoundError:
            print("Detected Python project. Running python3 -m unittest...")
            return run_command(["python3", "-m", "unittest", "discover", "-s", "tests"], root_dir)
            
    # 3. Go (go.mod)
    go_mod = os.path.join(root_dir, "go.mod")
    if os.path.exists(go_mod):
        print("Detected Go project. Running go test ./...")
        return run_command(["go", "test", "./..."], root_dir)
        
    # 4. Rust (Cargo.toml)
    cargo_toml = os.path.join(root_dir, "Cargo.toml")
    if os.path.exists(cargo_toml):
        print("Detected Rust project. Running cargo test...")
        return run_command(["cargo", "test"], root_dir)
        
    # Fallback search for a tests/ folder
    if os.path.isdir(tests_dir):
        print("Found a tests/ directory. Running fallback python3 -m unittest...")
        return run_command(["python3", "-m", "unittest", "discover", "-s", "tests"], root_dir)
        
    print("❌ No recognizable test suite detected in the project.")
    return 1

def run_command(cmd, cwd):
    try:
        # Run command with outputs piped to console
        result = subprocess.run(cmd, cwd=cwd)
        if result.returncode == 0:
            print(f"✅ Tests passed successfully: {' '.join(cmd)}")
        else:
            print(f"❌ Tests failed with exit code {result.returncode}: {' '.join(cmd)}")
        return result.returncode
    except Exception as e:
        print(f"❌ Error running command {' '.join(cmd)}: {e}")
        return 1

if __name__ == "__main__":
    exit_code = detect_and_run_tests()
    sys.exit(exit_code)
