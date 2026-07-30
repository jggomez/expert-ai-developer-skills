import os
import sys
import subprocess
import pytest

def test_validate_commit_msg_script(tmp_path):
    """Tests validate_commit_msg.py with valid and invalid commit messages."""
    script_path = os.path.abspath("skills/commit-expert/scripts/validate_commit_msg.py")
    assert os.path.exists(script_path), "validate_commit_msg.py missing!"
    
    # 1. Valid Conventional Commit message
    valid_file = tmp_path / "valid_commit.txt"
    valid_file.write_text("feat(auth): add google sign in support\n\nDetailed body description.", encoding="utf-8")
    
    res_valid = subprocess.run([sys.executable, script_path, str(valid_file)], capture_output=True, text=True)
    assert res_valid.returncode == 0, f"Expected 0 for valid commit, got {res_valid.returncode}. Output:\n{res_valid.stdout}\n{res_valid.stderr}"
    
    # 2. Invalid commit message (no conventional prefix)
    invalid_file = tmp_path / "invalid_commit.txt"
    invalid_file.write_text("added google sign in support", encoding="utf-8")
    
    res_invalid = subprocess.run([sys.executable, script_path, str(invalid_file)], capture_output=True, text=True)
    assert res_invalid.returncode != 0, "Expected non-zero return code for invalid commit message format!"

def test_secret_scanner_script(tmp_path):
    """Tests secret_scanner.py detection of fake API secrets."""
    script_path = os.path.abspath("skills/security-audit/scripts/secret_scanner.py")
    assert os.path.exists(script_path), "secret_scanner.py missing!"
    
    # Create clean directory
    clean_dir = tmp_path / "clean_proj"
    clean_dir.mkdir()
    (clean_dir / "app.py").write_text("def hello(): return 'world'", encoding="utf-8")
    
    res_clean = subprocess.run([sys.executable, script_path, str(clean_dir)], capture_output=True, text=True)
    assert res_clean.returncode == 0, "Expected exit code 0 for clean codebase"
    
    # Create leaked secret file
    dirty_dir = tmp_path / "dirty_proj"
    dirty_dir.mkdir()
    (dirty_dir / "config.py").write_text("AWS_SECRET_ACCESS_KEY = 'AKIA1234567890123456'", encoding="utf-8")
    
    res_dirty = subprocess.run([sys.executable, script_path, str(dirty_dir)], capture_output=True, text=True)
    assert res_dirty.returncode != 0, "Expected non-zero exit code when secrets are detected!"

def test_run_tests_script_detection(tmp_path):
    """Tests run_tests.py test suite auto-detection logic."""
    script_path = os.path.abspath("skills/refactoring-code-expert/scripts/run_tests.py")
    assert os.path.exists(script_path), "run_tests.py missing!"
    
    # 1. Project with no test setup -> should exit with code 1
    empty_dir = tmp_path / "empty_proj"
    empty_dir.mkdir()
    
    res_empty = subprocess.run([sys.executable, script_path], cwd=str(empty_dir), capture_output=True, text=True)
    assert res_empty.returncode != 0, "Expected non-zero exit code when no test framework detected"
