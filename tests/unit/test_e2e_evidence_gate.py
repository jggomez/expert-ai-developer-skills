"""Tests for plugins/claude/senior-dev/hooks/e2e-evidence-gate.js (SubagentStop).

The gate must make it impossible for e2e-blackbox-tester to report PASSED/REJECTED without
real browser activity recorded in its own transcript (tool results come from the harness,
not from the model), while honest BLOCKED/SKIPPED verdicts always pass.
"""
import json
import os
import shutil
import struct
import subprocess

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOK = os.path.join(ROOT, "plugins", "claude", "senior-dev", "hooks", "e2e-evidence-gate.js")
NAV = "mcp__plugin_senior-dev_playwright__browser_navigate"
SHOT = "mcp__plugin_senior-dev_playwright__browser_take_screenshot"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
VIEWPORT_WIDTHS = (375, 768, 1280, 1920)

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required")


def _tool_use(tool_id, name, tool_input):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]}}


def _tool_result(tool_id, is_error=False, text="ok"):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_id, "is_error": is_error, "content": text}]}}


def _run(tmp_path, entries, last_message, agent_type="senior-dev:e2e-blackbox-tester", active=False):
    transcript = tmp_path / "agent.jsonl"
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    payload = {
        "hook_event_name": "SubagentStop",
        "cwd": str(tmp_path),
        "agent_id": "agent-123",
        "agent_type": agent_type,
        "agent_transcript_path": str(transcript),
        "last_assistant_message": last_message,
        "stop_hook_active": active,
    }
    env = dict(os.environ, TMPDIR=str(tmp_path))
    return subprocess.run(["node", HOOK], input=json.dumps(payload), capture_output=True, text=True,
                          timeout=30, env=env)


def _real_png(width):
    header = struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, 10)
    return b"\x89PNG\r\n\x1a\n" + header + b"\x00" * 200


def _write_evidence(root, requests=None):
    """Screenshots for every viewport, plus the manifest of a run against a real backend."""
    evidence = root / "docs" / "checkout" / "evidence"
    evidence.mkdir(parents=True)
    for width in VIEWPORT_WIDTHS:
        (evidence / f"home-{width}.png").write_bytes(_real_png(width))
    default = [{"method": "GET", "url": "http://localhost:3000/api/items", "status": 200,
                "resourceType": "fetch", "remote": True}]
    (evidence / "run-a.json").write_text(json.dumps({
        "version": 1, "pages": ["http://localhost:3000/"], "requests": default if requests is None else requests,
        "dataChecks": [{"kind": "source-on-screen", "detail": "item 42 is listed"}]}))
    return evidence


def _real_session(tmp_path, screenshot_path=None):
    shot_input = {"filename": str(screenshot_path)} if screenshot_path else {}
    return [
        _tool_use("t1", NAV, {"url": "http://localhost:3000"}),
        _tool_result("t1", text="Page URL: http://localhost:3000"),
        _tool_use("t2", SHOT, shot_input),
        _tool_result("t2", text="Took the viewport screenshot"),
    ]


def test_passed_without_any_browser_call_is_blocked(tmp_path):
    # Arrange: the agent only "talked" about testing
    entries = [_tool_use("t1", "Read", {"file_path": "README.md"}), _tool_result("t1")]
    # Act
    result = _run(tmp_path, entries, "Verdict: PASSED. All 4 viewports look great.")
    # Assert
    assert result.returncode == 2
    assert "browser_navigate" in result.stderr


def test_passed_with_failed_navigation_is_blocked(tmp_path):
    # Arrange
    entries = [_tool_use("t1", NAV, {"url": "http://localhost:3000"}),
               _tool_result("t1", is_error=True, text="net::ERR_CONNECTION_REFUSED"),
               _tool_use("t2", SHOT, {}), _tool_result("t2")]
    # Act
    result = _run(tmp_path, entries, "Verdict: PASSED")
    # Assert
    assert result.returncode == 2


def test_passed_without_screenshot_is_blocked(tmp_path):
    # Arrange
    entries = [_tool_use("t1", NAV, {"url": "http://localhost:3000"}), _tool_result("t1")]
    # Act
    result = _run(tmp_path, entries, "Verdict: PASSED")
    # Assert
    assert result.returncode == 2
    assert "browser_take_screenshot" in result.stderr


def test_passed_with_real_navigation_and_screenshot_is_allowed(tmp_path):
    # Arrange
    shot = _write_evidence(tmp_path) / "home-375.png"
    # Act
    result = _run(tmp_path, _real_session(tmp_path, shot), "Verdict: PASSED")
    # Assert
    assert result.returncode == 0, result.stderr


def test_claimed_screenshot_file_missing_on_disk_is_blocked(tmp_path):
    # Arrange
    missing = tmp_path / "docs" / "checkout" / "evidence" / "375x812.png"
    # Act
    result = _run(tmp_path, _real_session(tmp_path, missing), "Verdict: REJECTED - form overflows")
    # Assert
    assert result.returncode == 2
    assert "375x812.png" in result.stderr


def test_fake_png_is_blocked(tmp_path):
    # Arrange
    fake = tmp_path / "docs" / "checkout" / "evidence" / "375x812.png"
    fake.parent.mkdir(parents=True)
    fake.write_text("not really a screenshot")
    # Act
    result = _run(tmp_path, _real_session(tmp_path, fake), "Verdict: PASSED")
    # Assert
    assert result.returncode == 2


def test_rejected_with_a_single_real_screenshot_is_allowed(tmp_path):
    # Arrange: a failing run does not need the full evidence set
    shot = tmp_path / "docs" / "checkout" / "evidence" / "375x812.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(PNG_BYTES)
    # Act
    result = _run(tmp_path, _real_session(tmp_path, shot), "Verdict: REJECTED - empty list")
    # Assert
    assert result.returncode == 0, result.stderr


def test_passed_with_screenshots_but_no_data_proof_is_blocked(tmp_path):
    # Arrange: the browser ran, but no request ever reached a server
    evidence = _write_evidence(tmp_path, requests=[])
    # Act
    result = _run(tmp_path, _real_session(tmp_path, evidence / "home-375.png"), "Verdict: PASSED")
    # Assert
    assert result.returncode == 2
    assert "real data request" in result.stderr


def test_playwright_test_run_via_bash_counts_as_evidence(tmp_path):
    # Arrange: the scripted route (npx playwright test) instead of the MCP
    _write_evidence(tmp_path)
    entries = [_tool_use("t1", "Bash", {"command": "npx playwright test tests/e2e"}),
               _tool_result("t1", text="4 passed (6.1s)")]
    # Act
    result = _run(tmp_path, entries, "Verdict: PASSED")
    # Assert
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("message", [
    "Verdict: BLOCKED - Chromium could not launch: missing libnss3",
    "Verdict: SKIPPED - mobile-only target, no web UI",
])
def test_honest_negative_verdicts_are_allowed(tmp_path, message):
    # Arrange / Act
    result = _run(tmp_path, [], message)
    # Assert
    assert result.returncode == 0


def test_missing_verdict_is_blocked(tmp_path):
    # Arrange / Act
    result = _run(tmp_path, _real_session(tmp_path), "Looks fine to me.")
    # Assert
    assert result.returncode == 2
    assert "PASSED" in result.stderr and "BLOCKED" in result.stderr


def test_other_subagents_are_ignored(tmp_path):
    # Arrange / Act
    result = _run(tmp_path, [], "Verdict: PASSED", agent_type="senior-dev:qa-tester")
    # Assert
    assert result.returncode == 0


def test_retry_limit_downgrades_to_unverified_notice(tmp_path):
    # Arrange: the agent keeps claiming PASSED without evidence
    for active in (False, True, True):
        assert _run(tmp_path, [], "Verdict: PASSED", active=active).returncode == 2
    # Act
    result = _run(tmp_path, [], "Verdict: PASSED", active=True)
    # Assert
    assert result.returncode == 0
    assert "UNVERIFIED" in json.loads(result.stdout)["systemMessage"]
