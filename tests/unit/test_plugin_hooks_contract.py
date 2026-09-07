"""Contract and behavioral tests for plugin lifecycle hooks across both hosts.

Verifies that hooks output the exact expected JSON schema on Google Antigravity
(top-level `{"decision": "allow"|"deny"|"ask"}`) and Claude Code
(`hookSpecificOutput` with `permissionDecision` or clean empty output).
Skipped when `node` is unavailable.
"""
import json
import os
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GIT_GATE = os.path.join(REPO_ROOT, "plugins", "git-workflow", "hooks", "gitflow-branch-gate.js")
PYTHON_PRE_GATE = os.path.join(REPO_ROOT, "plugins", "python-backend", "hooks", "pre-tool-gate.js")
PYTHON_STOP_GATE = os.path.join(REPO_ROOT, "plugins", "python-backend", "hooks", "stop-gate.js")
FLUTTER_PRE_GATE = os.path.join(REPO_ROOT, "plugins", "senior-dev-flutter", "hooks", "flutter-pre-tool-gate.js")
FLUTTER_STOP_GATE = os.path.join(REPO_ROOT, "plugins", "senior-dev-flutter", "hooks", "flutter-stop-gate.js")

HOST_VARS = ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "CLAUDECODE", "ANTIGRAVITY", "AGY_PLUGIN_ROOT")


def run_hook(script_path, payload, env_extra=None, cwd=None):
    env = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["node", script_path],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd or REPO_ROOT,
    )


def git_init(path, branch="main"):
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "ci@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "CI"], cwd=path, check=True)
    (path / "README.md").write_text("hello")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=path, check=True)


# ==============================================================================
# 1. Gitflow Branch Gate (plugins/git-workflow)
# ==============================================================================

def test_gitflow_gate_antigravity_allows_safe_command(tmp_path):
    git_init(tmp_path, "main")
    payload = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "git status", "Cwd": str(tmp_path)},
        },
        "workspacePaths": [str(tmp_path)],
    }
    r = run_hook(GIT_GATE, payload, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out == {"decision": "allow"}


def test_gitflow_gate_antigravity_denies_commit_on_protected_branch(tmp_path):
    git_init(tmp_path, "main")
    payload = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "git commit -m 'feat: test'", "Cwd": str(tmp_path)},
        },
        "workspacePaths": [str(tmp_path)],
    }
    r = run_hook(GIT_GATE, payload, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out["decision"] == "deny"
    assert "Gitflow Safety Blocked" in out["reason"]


def test_gitflow_gate_claude_allows_safe_command(tmp_path):
    git_init(tmp_path, "main")
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "cwd": str(tmp_path),
    }
    r = run_hook(GIT_GATE, payload, env_extra={"CLAUDE_PLUGIN_ROOT": "x"}, cwd=str(tmp_path))
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_gitflow_gate_claude_denies_commit_on_protected_branch(tmp_path):
    git_init(tmp_path, "main")
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m 'feat: test'"},
        "cwd": str(tmp_path),
    }
    r = run_hook(GIT_GATE, payload, env_extra={"CLAUDE_PLUGIN_ROOT": "x"}, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Gitflow Safety Blocked" in out["hookSpecificOutput"]["permissionDecisionReason"]


# ==============================================================================
# 2. Python Backend PreTool Gate (plugins/python-backend)
# ==============================================================================

def test_python_pre_gate_antigravity_allows_safe_command(tmp_path):
    payload = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "pytest tests/unit", "Cwd": str(tmp_path)},
        },
        "workspacePaths": [str(tmp_path)],
    }
    r = run_hook(PYTHON_PRE_GATE, payload, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out == {"decision": "allow"}


def test_python_pre_gate_antigravity_asks_on_deploy(tmp_path):
    payload = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "gcloud run deploy my-service", "Cwd": str(tmp_path)},
        },
        "workspacePaths": [str(tmp_path)],
    }
    r = run_hook(PYTHON_PRE_GATE, payload, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out["decision"] == "ask"
    assert "Deployment operation" in out["reason"]


def test_python_pre_gate_antigravity_asks_on_mcp_cloudrun(tmp_path):
    payload = {
        "toolCall": {
            "name": "call_mcp_tool",
            "args": {"ServerName": "cloudrun", "ToolName": "deploy_local_folder"},
        },
        "workspacePaths": [str(tmp_path)],
    }
    r = run_hook(PYTHON_PRE_GATE, payload, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out["decision"] == "ask"
    assert "Cloud Run deployment via MCP" in out["reason"]


def test_python_pre_gate_claude_asks_on_mcp_cloudrun(tmp_path):
    payload = {
        "tool_name": "mcp__cloudrun__deploy_local_folder",
        "tool_input": {},
        "cwd": str(tmp_path),
    }
    r = run_hook(PYTHON_PRE_GATE, payload, env_extra={"CLAUDE_PLUGIN_ROOT": "x"}, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out["hookSpecificOutput"]["permissionDecision"] == "ask"


# ==============================================================================
# 3. Flutter PreTool Gate (plugins/senior-dev-flutter)
# ==============================================================================

def test_flutter_pre_gate_antigravity_allows_safe_command(tmp_path):
    git_init(tmp_path, "main")
    (tmp_path / "pubspec.yaml").write_text("name: demo\n")
    payload = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "flutter test", "Cwd": str(tmp_path)},
        },
        "workspacePaths": [str(tmp_path)],
    }
    r = run_hook(FLUTTER_PRE_GATE, payload, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out == {"decision": "allow"}


def test_flutter_pre_gate_claude_allows_safe_command(tmp_path):
    git_init(tmp_path, "main")
    (tmp_path / "pubspec.yaml").write_text("name: demo\n")
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "flutter test"},
        "cwd": str(tmp_path),
    }
    r = run_hook(FLUTTER_PRE_GATE, payload, env_extra={"CLAUDE_PLUGIN_ROOT": "x"}, cwd=str(tmp_path))
    assert r.returncode == 0
    assert r.stdout.strip() == ""


# ==============================================================================
# 4. Stop Gates (python-backend & senior-dev-flutter)
# ==============================================================================

def test_python_stop_gate_antigravity_clean_allows(tmp_path):
    payload = {"workspacePaths": [str(tmp_path)]}
    r = run_hook(PYTHON_STOP_GATE, payload, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out == {"decision": "allow"}


def test_flutter_stop_gate_antigravity_non_flutter_allows(tmp_path):
    payload = {"workspacePaths": [str(tmp_path)]}
    r = run_hook(FLUTTER_STOP_GATE, payload, cwd=str(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out == {"decision": "allow"}
