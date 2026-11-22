"""Workspace daemon sidecar: watches only .py files under WORKSPACE_ROOT and runs ruff on changes."""
import importlib.util
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(REPO_ROOT, "sidecars", "workspace-daemon", "daemon_monitor.py")


def _load(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_DAEMON_STATE", str(tmp_path / "state"))
    spec = importlib.util.spec_from_file_location("daemon_monitor", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_refuses_to_start_without_workspace_root(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "WORKSPACE_ROOT"}
    env["WORKSPACE_DAEMON_STATE"] = str(tmp_path / "state")
    r = subprocess.run([sys.executable, SCRIPT], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    assert r.returncode == 2
    assert "WORKSPACE_ROOT" in r.stderr
    assert not (tmp_path / "workspace_daemon.log").exists()


def test_first_scan_only_records_then_change_triggers_ruff_on_py(tmp_path, monkeypatch):
    # Arrange
    module = _load(tmp_path, monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    py_file = project / "app.py"
    js_file = project / "app.js"
    py_file.write_text("x=1\n")
    js_file.write_text("let x\n")
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0))
    watcher = module.WorkspaceWatcher(str(project))
    # Act: first scan records files without touching them
    watcher.scan_files()
    assert calls == []
    os.utime(py_file, (py_file.stat().st_atime, py_file.stat().st_mtime + 5))
    os.utime(js_file, (js_file.stat().st_atime, js_file.stat().st_mtime + 5))
    watcher.scan_files()
    # Assert: only the Python file is formatted and linted
    assert calls == [["ruff", "format", str(py_file)], ["ruff", "check", "--fix", str(py_file)]]


def test_remaining_lint_is_reported_as_issues_not_failure(tmp_path, monkeypatch, caplog):
    module = _load(tmp_path, monkeypatch)
    results = iter([0, 1])
    monkeypatch.setattr(module.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, next(results)))
    watcher = module.WorkspaceWatcher(str(tmp_path))
    with caplog.at_level("INFO"):
        watcher._run_quality_tools(str(tmp_path / "a.py"))
    assert "lint issues remain" in caplog.text
    assert "failed" not in caplog.text
