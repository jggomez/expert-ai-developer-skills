"""Behavioral tests for the senior-dev-flutter plugin's two Node hooks.

`flutter-stop-gate.js` shells out to `dart`; those tests put a fake `dart` on
PATH so they run without a real Dart SDK. Skipped when `node` is unavailable.
"""
import json
import os
import shutil
import stat
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")

HOOKS = os.path.abspath("plugins/senior-dev-flutter/hooks")
PRE = os.path.join(HOOKS, "flutter-pre-tool-gate.js")
STOP = os.path.join(HOOKS, "flutter-stop-gate.js")
HOST_VARS = ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "CLAUDECODE", "ANTIGRAVITY")


def run_hook(script, payload, env_extra=None, cwd=None, path_prefix=None):
    env = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
    if path_prefix:
        env["PATH"] = path_prefix + os.pathsep + env.get("PATH", "")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["node", script], input=json.dumps(payload),
        capture_output=True, text=True, env=env, cwd=cwd,
    )


def git_init(path, branch="main"):
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.co"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    (path / "pubspec.yaml").write_text(
        "name: demo\nenvironment:\n  sdk: '>=3.5.0 <4.0.0'\n"
        "dependencies:\n  flutter:\n    sdk: flutter\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=path, check=True)


def fake_dart(tmp_path, analyze_exit):
    d = tmp_path / "fakebin"
    d.mkdir(exist_ok=True)
    script = d / "dart"
    script.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        '  --version) echo "Dart SDK version: 3.5.0 (stable)"; exit 0;;\n'
        f'  analyze) echo "  info - lib/x.dart:1:1 - unused_import"; exit {analyze_exit};;\n'
        "  *) exit 0;;\n"
        "esac\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return str(d)


# --------------------------------------------------------------------------
# flutter-pre-tool-gate.js
# --------------------------------------------------------------------------

def test_pre_denies_store_build_on_protected_branch(tmp_path):
    git_init(tmp_path, "main")
    r = run_hook(PRE, {"tool_name": "Bash",
                       "tool_input": {"command": "flutter build appbundle --release"},
                       "cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    out = json.loads(r.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "release branch" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_pre_denies_major_bump_antigravity_shape(tmp_path):
    git_init(tmp_path, "develop")
    r = run_hook(PRE, {"toolCall": {"name": "run_command",
                                    "args": {"command": "dart pub upgrade --major-versions"}},
                       "workspacePaths": [str(tmp_path)]})
    out = json.loads(r.stdout)
    assert out["decision"] == "deny"
    assert "ADR" in out["reason"]


def test_pre_allows_apk_build_and_feature_branch(tmp_path):
    git_init(tmp_path, "main")
    r = run_hook(PRE, {"tool_name": "Bash",
                       "tool_input": {"command": "flutter build apk"},
                       "cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert r.returncode == 0 and r.stdout.strip() == ""

    subprocess.run(["git", "switch", "-qc", "feature/x"], cwd=tmp_path, check=True)
    r = run_hook(PRE, {"tool_name": "Bash",
                       "tool_input": {"command": "flutter build ipa"},
                       "cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_pre_ignores_non_flutter_repo(tmp_path):
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    r = run_hook(PRE, {"tool_name": "Bash",
                       "tool_input": {"command": "flutter build appbundle"},
                       "cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_pre_ignores_non_shell_tool(tmp_path):
    git_init(tmp_path, "main")
    r = run_hook(PRE, {"tool_name": "Read", "tool_input": {"file_path": "x"},
                       "cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert r.returncode == 0 and r.stdout.strip() == ""


# --------------------------------------------------------------------------
# flutter-stop-gate.js
# --------------------------------------------------------------------------

def test_stop_noop_when_not_a_flutter_repo(tmp_path):
    (tmp_path / "readme.md").write_text("hi")
    r = run_hook(STOP, {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_stop_noop_when_dart_missing(tmp_path):
    git_init(tmp_path, "main")
    # PATH without dart (but keep node's dir)
    node_dir = os.path.dirname(shutil.which("node"))
    env = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
    env["PATH"] = node_dir
    env["CLAUDE_PLUGIN_ROOT"] = "x"
    r = subprocess.run(["node", STOP], input=json.dumps({"cwd": str(tmp_path)}),
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_stop_allows_when_dart_analyze_clean(tmp_path):
    git_init(tmp_path, "main")
    binp = fake_dart(tmp_path, analyze_exit=0)
    r = run_hook(STOP, {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"},
                 path_prefix=binp)
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_stop_blocks_when_dart_analyze_fails_claude_code(tmp_path):
    git_init(tmp_path, "main")
    binp = fake_dart(tmp_path, analyze_exit=1)
    r = run_hook(STOP, {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"},
                 path_prefix=binp)
    assert r.returncode == 2                       # blocks the stop
    assert "dart analyze` is not clean" in r.stderr
    assert "flutter test" in r.stderr


def test_stop_blocks_when_dart_analyze_fails_antigravity(tmp_path):
    git_init(tmp_path, "main")
    binp = fake_dart(tmp_path, analyze_exit=1)
    r = run_hook(STOP, {"cwd": str(tmp_path)}, path_prefix=binp)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["decision"] == "continue"
    assert "dart analyze" in out["reason"]
