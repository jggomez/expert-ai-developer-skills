"""Tests for the UI reality gate in universal-quality-gate.js (Stop, Claude Code and Antigravity).

A changed UI must carry no fake data and fresh proof that the real app was opened and used.
"""
import json
import os
import shutil
import struct
import subprocess
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOKS = [os.path.join(ROOT, "plugins", host, "senior-dev", "hooks", "universal-quality-gate.js")
         for host in ("claude", "antigravity")]
VIEWPORT_WIDTHS = (375, 768, 1280, 1920)

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required")


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t.co", *args], cwd=repo, check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git(project, "init", "-q")
    (project / "README.md").write_text("base\n")
    _git(project, "add", ".")
    _git(project, "commit", "-qm", "base")
    return project


def _write(repo, rel, text="x\n"):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _evidence(repo):
    evidence = repo / "docs" / "items" / "evidence"
    evidence.mkdir(parents=True)
    for width in VIEWPORT_WIDTHS:
        header = struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, 10)
        (evidence / f"home-{width}.png").write_bytes(b"\x89PNG\r\n\x1a\n" + header + b"\x00" * 200)
    (evidence / "run-a.json").write_text(json.dumps({
        "version": 1, "pages": ["http://localhost:3000/"],
        "requests": [{"method": "GET", "url": "http://localhost:3000/api/items", "status": 200,
                      "resourceType": "fetch", "remote": True}],
        "dataChecks": [{"kind": "source-on-screen", "detail": "item 42"}]}))
    return evidence


def _run(repo, hook=HOOKS[0], active=False):
    payload = {"hook_event_name": "Stop", "cwd": str(repo), "session_id": "s1", "stop_hook_active": active}
    env = dict(os.environ, TMPDIR=str(repo.parent))
    return subprocess.run(["node", hook], input=json.dumps(payload), capture_output=True, text=True, timeout=60,
                          env=env)


def _blocked(result):
    return result.returncode == 2 or '"block"' in result.stdout


@pytest.mark.parametrize("hook", HOOKS)
def test_changed_ui_without_evidence_is_blocked(repo, hook):
    # Arrange
    _write(repo, "src/Items.tsx", "export const Items = () => null;\n")
    # Act
    result = _run(repo, hook)
    # Assert
    assert _blocked(result), result.stdout + result.stderr
    assert "UI REALITY GATE" in result.stdout + result.stderr


def test_changed_ui_with_fresh_evidence_is_allowed(repo):
    # Arrange
    _write(repo, "src/Items.tsx", "export const Items = () => null;\n")
    old = time.time() - 30
    os.utime(repo / "src" / "Items.tsx", (old, old))
    _evidence(repo)
    # Act
    result = _run(repo)
    # Assert
    assert not _blocked(result), result.stdout + result.stderr


def test_evidence_older_than_the_ui_change_is_blocked(repo):
    # Arrange
    evidence = _evidence(repo)
    old = time.time() - 300
    for item in evidence.iterdir():
        os.utime(item, (old, old))
    _write(repo, "src/Items.tsx", "export const Items = () => null;\n")
    # Act
    result = _run(repo)
    # Assert
    assert _blocked(result), result.stdout + result.stderr
    assert "before the last change" in result.stdout + result.stderr


def test_fake_data_is_blocked_even_with_evidence(repo):
    # Arrange
    _write(repo, "src/Items.tsx", "const items = mockItems;\n")
    old = time.time() - 30
    os.utime(repo / "src" / "Items.tsx", (old, old))
    _evidence(repo)
    # Act
    result = _run(repo)
    # Assert
    assert _blocked(result), result.stdout + result.stderr
    assert "fake data" in result.stdout + result.stderr


@pytest.mark.parametrize("rel", ["src/api/items.py", "src/Items.test.tsx", "tests/e2e/items.spec.ts"])
def test_changes_outside_the_ui_are_not_gated(repo, rel):
    # Arrange
    _write(repo, rel)
    # Act
    result = _run(repo)
    # Assert
    assert "UI REALITY GATE" not in result.stdout + result.stderr


def test_a_mobile_only_flutter_change_is_out_of_scope(repo):
    # Arrange
    _write(repo, "lib/main.dart")
    # Act
    result = _run(repo)
    # Assert
    assert "UI REALITY GATE" not in result.stdout + result.stderr


def test_a_flutter_web_change_is_gated(repo):
    # Arrange
    _write(repo, "lib/main.dart")
    _write(repo, "web/index.html")
    # Act
    result = _run(repo)
    # Assert
    assert "UI REALITY GATE" in result.stdout + result.stderr


def test_the_retry_limit_says_the_ui_is_not_verified(repo):
    # Arrange
    _write(repo, "src/Items.tsx", "export const Items = () => null;\n")
    # Act
    for _ in range(3):
        _run(repo, active=True)
    result = _run(repo, active=True)
    # Assert
    assert "UI NOT verified" in result.stdout + result.stderr


def _give_up_on_unverified_ui(repo):
    """One turn changes the UI and the gate blocks it 3 times, then lets the turn end."""
    _write(repo, "src/Items.tsx", "export const Items = () => null;\n")
    for _ in range(3):
        _run(repo, active=True)
    _run(repo, active=True)


@pytest.mark.parametrize("hook", HOOKS)
def test_a_later_turn_that_leaves_the_ui_untouched_is_told_not_blocked(repo, hook):
    # Arrange: the UI stayed unverified in an earlier turn (the user has been told)
    _give_up_on_unverified_ui(repo)
    # Act: a new turn (a plain answer, or edits elsewhere) ends with the same UI files
    _write(repo, "src/api/items.py")
    result = _run(repo, hook, active=False)
    # Assert
    assert not _blocked(result), result.stdout + result.stderr
    assert "still NOT verified" in result.stdout + result.stderr


def test_a_later_turn_that_changes_the_ui_again_is_gated_again(repo):
    # Arrange
    _give_up_on_unverified_ui(repo)
    # Act: the new turn edits the UI
    _write(repo, "src/Items.tsx", "export const Items = () => <div />;\n")
    result = _run(repo, active=False)
    # Assert
    assert _blocked(result), result.stdout + result.stderr
    assert "block 1/3" in result.stdout + result.stderr


def test_fresh_evidence_in_a_later_turn_clears_the_notice(repo):
    # Arrange
    _give_up_on_unverified_ui(repo)
    old = time.time() - 30
    os.utime(repo / "src" / "Items.tsx", (old, old))
    _evidence(repo)
    # Act
    result = _run(repo, active=False)
    # Assert
    assert not _blocked(result), result.stdout + result.stderr
    assert "NOT verified" not in result.stdout + result.stderr


def test_the_gate_scans_from_the_git_root_when_the_shell_sits_in_a_subfolder(repo):
    # Arrange: the UI file lives at the root while the agent's cwd is a subfolder
    _write(repo, "src/Items.tsx", "export const Items = () => null;\n")
    sub = repo / "apps" / "api"
    sub.mkdir(parents=True)
    payload = {"hook_event_name": "Stop", "cwd": str(sub), "session_id": "s1", "stop_hook_active": False}
    # Act
    result = subprocess.run(["node", HOOKS[0]], input=json.dumps(payload), capture_output=True, text=True,
                            timeout=60, env=dict(os.environ, TMPDIR=str(repo.parent)))
    # Assert
    assert _blocked(result), result.stdout + result.stderr
    assert "UI REALITY GATE" in result.stdout + result.stderr
