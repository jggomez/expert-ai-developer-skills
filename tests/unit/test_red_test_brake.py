"""Tests for the senior-dev red-test brake (Claude Code PostToolUse / PostToolUseFailure on Bash).

Measured runs showed implementers re-running failing tests 5+ times (flutter-implementer: 13.5 test
runs and 4.7 failures per run). The brake counts consecutive failed test commands per agent and, from
the third one, tells the agent to stop, report the failing test and what blocks it. A passing test
run resets the count. It never blocks a tool call.
"""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOK = os.path.join(ROOT, "plugins", "claude", "senior-dev", "hooks", "red-test-brake.js")
HOOKS_JSON = os.path.join(ROOT, "plugins", "claude", "senior-dev", "hooks.json")

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required")


def _run(tmp_path, command, failed, agent_id="impl-1", session="s1"):
    payload = {"session_id": session, "cwd": str(tmp_path), "tool_name": "Bash",
               "tool_input": {"command": command}}
    if agent_id:
        payload.update(agent_id=agent_id, agent_type="senior-dev-flutter:flutter-implementer")
    if failed:
        payload.update(hook_event_name="PostToolUseFailure", is_interrupt=False,
                       error="Exit code 1\n2 tests failed")
    else:
        payload.update(hook_event_name="PostToolUse", tool_response={"stdout": "All tests passed", "stderr": ""})
    env = dict(os.environ, TMPDIR=str(tmp_path))
    return subprocess.run(["node", HOOK], input=json.dumps(payload), capture_output=True, text=True,
                          timeout=15, env=env)


def _context(result):
    return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"] if result.stdout.strip() else ""


def test_two_failing_test_runs_say_nothing(tmp_path):
    # Arrange
    _run(tmp_path, "flutter test test/cart_test.dart", failed=True)
    # Act
    result = _run(tmp_path, "flutter test test/cart_test.dart", failed=True)
    # Assert
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


@pytest.mark.parametrize("command", [
    "flutter test", "uv run pytest tests/unit -q", "npm test", "npx vitest run", "go test ./...",
    "cd app && python -m pytest -x", "dart test", "cargo test",
])
def test_the_third_failing_test_run_tells_the_agent_to_stop(tmp_path, command):
    # Arrange
    _run(tmp_path, command, failed=True)
    _run(tmp_path, command, failed=True)
    # Act
    result = _run(tmp_path, command, failed=True)
    # Assert
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure"
    assert "3 test runs in a row failed" in _context(result)
    assert "stop" in _context(result).lower()


def test_a_passing_run_resets_the_count(tmp_path):
    # Arrange
    _run(tmp_path, "pytest", failed=True)
    _run(tmp_path, "pytest", failed=True)
    _run(tmp_path, "pytest", failed=False)
    # Act
    result = _run(tmp_path, "pytest", failed=True)
    # Assert
    assert result.stdout.strip() == ""


def test_each_agent_has_its_own_count(tmp_path):
    # Arrange
    _run(tmp_path, "pytest", failed=True, agent_id="a")
    _run(tmp_path, "pytest", failed=True, agent_id="a")
    # Act
    result = _run(tmp_path, "pytest", failed=True, agent_id="b")
    # Assert
    assert result.stdout.strip() == ""


def test_the_main_session_is_counted_too(tmp_path):
    # Arrange
    for _ in range(2):
        _run(tmp_path, "npm test", failed=True, agent_id=None)
    # Act
    result = _run(tmp_path, "npm test", failed=True, agent_id=None)
    # Assert
    assert "3 test runs in a row failed" in _context(result)


@pytest.mark.parametrize("command", ["git status", "ls tests/", "cat test_results.txt", "echo pytest"])
def test_commands_that_are_not_test_runs_are_ignored(tmp_path, command):
    # Arrange
    for _ in range(3):
        result = _run(tmp_path, command, failed=True)
    # Assert
    assert result.stdout.strip() == ""


def test_an_interrupted_run_does_not_count(tmp_path):
    # Arrange
    payload = {"session_id": "s1", "agent_id": "x", "hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
               "tool_input": {"command": "pytest"}, "is_interrupt": True, "error": "Interrupted"}
    env = dict(os.environ, TMPDIR=str(tmp_path))
    for _ in range(3):
        result = subprocess.run(["node", HOOK], input=json.dumps(payload), capture_output=True, text=True,
                                timeout=15, env=env)
    # Assert
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_a_broken_payload_never_fails_the_tool(tmp_path):
    # Act
    result = subprocess.run(["node", HOOK], input="not json", capture_output=True, text=True, timeout=15,
                            env=dict(os.environ, TMPDIR=str(tmp_path)))
    # Assert
    assert result.returncode == 0


def test_the_hook_is_registered_on_both_bash_events():
    # Arrange
    with open(HOOKS_JSON, encoding="utf-8") as handle:
        hooks = json.load(handle)["hooks"]
    # Act / Assert
    for event in ("PostToolUse", "PostToolUseFailure"):
        entries = [entry for entry in hooks.get(event, []) if entry.get("matcher") == "Bash"]
        assert any("red-test-brake.js" in hook["command"] for entry in entries for hook in entry["hooks"]), event
