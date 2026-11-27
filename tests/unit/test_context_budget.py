"""Tests for the senior-dev context-budget hook (Claude Code UserPromptSubmit).

Long sessions carry their whole history into every prompt: measured usage showed a few sessions
of 1,000+ calls holding most of the spend, each prompt starting at 200k+ tokens. The hook reads
the session's last recorded usage and, past a threshold, tells the user and the agent to save
context and start a new session. It never blocks a prompt.
"""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOK = os.path.join(ROOT, "plugins", "claude", "senior-dev", "hooks", "context-budget.js")
HOOKS_JSON = os.path.join(ROOT, "plugins", "claude", "senior-dev", "hooks.json")

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required")


def _transcript(tmp_path, context_tokens, name="session.jsonl"):
    """A transcript whose last assistant turn used `context_tokens` of context."""
    lines = [
        {"type": "user", "message": {"role": "user", "content": "hi"}},
        {"type": "assistant", "message": {"role": "assistant", "usage": {
            "input_tokens": 10, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 0,
            "output_tokens": 5}}},
        {"type": "assistant", "message": {"role": "assistant", "usage": {
            "input_tokens": 100, "cache_read_input_tokens": context_tokens - 600,
            "cache_creation_input_tokens": 500, "output_tokens": 50}}},
        {"type": "system", "subtype": "stop_hook_summary"},
    ]
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return path


def _run(tmp_path, transcript, session="s1"):
    payload = {"hook_event_name": "UserPromptSubmit", "session_id": session, "cwd": str(tmp_path),
               "transcript_path": str(transcript), "prompt": "next task"}
    env = dict(os.environ, TMPDIR=str(tmp_path))
    return subprocess.run(["node", HOOK], input=json.dumps(payload), capture_output=True, text=True,
                          timeout=15, env=env)


def _context(result):
    return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"] if result.stdout.strip() else ""


def test_a_small_session_gets_nothing(tmp_path):
    # Arrange
    transcript = _transcript(tmp_path, 80_000)
    # Act
    result = _run(tmp_path, transcript)
    # Assert
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_a_session_past_200k_is_told_to_save_context_and_start_fresh(tmp_path):
    # Arrange
    transcript = _transcript(tmp_path, 230_000)
    # Act
    result = _run(tmp_path, transcript)
    # Assert
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert "230k" in output["systemMessage"]
    assert "context-capture" in _context(result)
    assert "new session" in _context(result)


def test_the_notice_is_given_once_per_level(tmp_path):
    # Arrange
    transcript = _transcript(tmp_path, 230_000)
    _run(tmp_path, transcript)
    # Act
    again = _run(tmp_path, transcript)
    # Assert
    assert again.returncode == 0
    assert again.stdout.strip() == ""


def test_passing_300k_gives_a_stronger_second_notice(tmp_path):
    # Arrange
    _run(tmp_path, _transcript(tmp_path, 230_000))
    # Act
    result = _run(tmp_path, _transcript(tmp_path, 320_000, name="later.jsonl"))
    # Assert
    assert result.returncode == 0
    assert "320k" in json.loads(result.stdout)["systemMessage"]
    assert "now" in _context(result)


def test_another_session_is_measured_on_its_own(tmp_path):
    # Arrange
    _run(tmp_path, _transcript(tmp_path, 230_000), session="s1")
    # Act
    result = _run(tmp_path, _transcript(tmp_path, 230_000, name="other.jsonl"), session="s2")
    # Assert
    assert "230k" in json.loads(result.stdout)["systemMessage"]


@pytest.mark.parametrize("transcript", ["missing.jsonl", None])
def test_a_missing_transcript_never_blocks(tmp_path, transcript):
    # Arrange
    path = tmp_path / transcript if transcript else ""
    # Act
    result = _run(tmp_path, path)
    # Assert
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_the_hook_is_registered_on_user_prompt_submit():
    # Arrange
    with open(HOOKS_JSON, encoding="utf-8") as handle:
        hooks = json.load(handle)["hooks"]
    # Act
    commands = [hook["command"] for entry in hooks.get("UserPromptSubmit", []) for hook in entry["hooks"]]
    # Assert
    assert any("context-budget.js" in command for command in commands)
