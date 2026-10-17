"""L3 lifecycle through the real CLI wiring: setup -> registered hook -> collect -> summary -> report -> uninstall.

Covers SU-01..04 and HK-01/03/04 end to end (the unit suite covers them per module with fakes).
Pre-existing user files carry unrelated hooks, including Gemini CLI's ``BeforeTool`` ->
``rtk-hook-gemini.sh`` in ``~/.gemini/settings.json``, which agent-meter must never touch.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import time
from pathlib import Path

import pytest

from agent_meter import cli
from agent_meter.locking import store_lock
from tests.fixtures.canary import CANARY
from tests.fixtures.scenarios import CLAUDE_SESSION_ID
from tests.qa.conftest import FakeRunner, QAWorld

CLAUDE_SETTINGS = {
    "model": "opus",
    "permissions": {"allow": ["Bash(ls:*)"]},
    "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "guard.sh"}]}]},
}
AGY_HOOKS = {"user-guard": {"enabled": True, "BeforeTool": [{"type": "command", "command": "agy-guard.sh"}]}}
GEMINI_SETTINGS = {
    "hooks": {"BeforeTool": [{"matcher": "run_shell_command",
                              "hooks": [{"type": "command", "command": "~/.gemini/hooks/rtk-hook-gemini.sh"}]}]},
}


def _write_json(path: Path, obj: object) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, indent=4) + "\n").encode()
    path.write_bytes(data)
    return data


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    out = capsys.readouterr()
    return code, out.out + out.err


def _agent_meter_commands(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            command = node.get("command")
            if isinstance(command, str) and " hook --host " in command:
                found.append(command)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(json.loads(text))
    return found


def _wait_lock_free(world: QAWorld, timeout_s: float = 30.0) -> None:
    """Deterministic wait until the detached worker released the store lock."""
    with store_lock(world.meter.lock, exclusive=True, timeout_s=timeout_s):
        return


def test_l3_setup_hook_collect_report_uninstall_restores_bytes(
    qa_world: QAWorld, capsys: pytest.CaptureFixture[str], fake_scheduler: FakeRunner,
    no_network: list[object], tmp_path: Path,
) -> None:
    # Arrange: user files that exist before agent-meter
    claude_settings = qa_world.user / ".claude" / "settings.json"
    agy_hooks = qa_world.user / ".gemini" / "config" / "hooks.json"
    gemini_settings = qa_world.user / ".gemini" / "settings.json"
    claude_before = _write_json(claude_settings, CLAUDE_SETTINGS)
    agy_before = _write_json(agy_hooks, AGY_HOOKS)
    gemini_before = _write_json(gemini_settings, GEMINI_SETTINGS)

    # Act 1: setup (local, non-interactive, hooks + scheduler) — SU-04 zero network
    code, out = _run(capsys, "setup", "--local", "--yes")

    # Assert 1: merged, backed up, unrelated hooks preserved (SU-02)
    assert code == 0, out
    assert no_network == []
    assert gemini_settings.read_bytes() == gemini_before
    claude_after = json.loads(claude_settings.read_text(encoding="utf-8"))
    assert claude_after["model"] == "opus" and claude_after["permissions"] == CLAUDE_SETTINGS["permissions"]
    assert claude_after["hooks"]["PreToolUse"] == CLAUDE_SETTINGS["hooks"]["PreToolUse"]
    assert {"SessionEnd", "Stop"} <= set(claude_after["hooks"])
    agy_after = json.loads(agy_hooks.read_text(encoding="utf-8"))
    assert agy_after["user-guard"] == AGY_HOOKS["user-guard"]
    assert all(isinstance(v, dict) for v in agy_after.values())  # no top-level scalars (Track 12 bug)
    assert len(_agent_meter_commands(claude_settings)) == 2
    assert len(_agent_meter_commands(agy_hooks)) == 1
    backups = sorted(p.read_bytes() for p in qa_world.meter.backups_dir.iterdir())
    assert claude_before in backups and agy_before in backups
    assert any(c[:2] == ["launchctl", "bootstrap"] for c in fake_scheduler.calls)
    assert CANARY not in out

    # Act 2: second setup is a no-op (SU-01)
    snapshot = (claude_settings.read_bytes(), agy_hooks.read_bytes())
    backup_names = sorted(p.name for p in qa_world.meter.backups_dir.iterdir())
    code2, out2 = _run(capsys, "setup", "--local", "--yes")
    assert code2 == 0, out2
    assert (claude_settings.read_bytes(), agy_hooks.read_bytes()) == snapshot
    assert sorted(p.name for p in qa_world.meter.backups_dir.iterdir()) == backup_names

    # Act 3: execute the exact registered Claude Stop command as the host would (HK-01/03/04)
    stop_cmd = next(c for c in _agent_meter_commands(claude_settings) if "task-end" in c)
    qa_world.meter.last_summary.unlink(missing_ok=True)
    payload = json.dumps({"session_id": CLAUDE_SESSION_ID, "hook_event_name": "Stop",
                          "last_assistant_message": CANARY, "cwd": "/Users/dev/work/demo-repo"}).encode()
    done = subprocess.run(shlex.split(stop_cmd), input=payload, capture_output=True, env=qa_world.env(),
                          timeout=30, check=False)
    deadline = time.monotonic() + 30
    while not qa_world.meter.last_summary.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    _wait_lock_free(qa_world)
    assert done.returncode == 0 and done.stdout == b"" and CANARY.encode() not in done.stderr
    assert qa_world.meter.last_summary.read_text(encoding="utf-8").startswith("[agent-meter] demo-repo")

    # Act 4: the registered Antigravity command prints exactly {} (HK-03)
    agy_cmd = _agent_meter_commands(agy_hooks)[0]
    agy_payload = json.dumps({
        "conversationId": "c-root", "fullyIdle": True, "terminationReason": "completed",
        "transcriptPath": str(qa_world.agy_root / "brain" / "c-root" / ".system_generated" / "logs"
                              / "transcript_full.jsonl"),
        "workspacePaths": ["/Users/dev/work/demo-repo"], "prompt": CANARY,
    }).encode()
    qa_world.meter.last_summary.unlink()
    agy_done = subprocess.run(shlex.split(agy_cmd), input=agy_payload, capture_output=True,
                              env=qa_world.env(), timeout=30, check=False)
    deadline = time.monotonic() + 30
    while not qa_world.meter.last_summary.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    _wait_lock_free(qa_world)
    assert agy_done.returncode == 0 and agy_done.stdout == b"{}\n"
    assert "Antigravity" in qa_world.meter.last_summary.read_text(encoding="utf-8")

    # Act 5: summary + report over what the hooks ingested
    code_last, last_out = _run(capsys, "last", "--json")
    report = tmp_path / "r.html"
    code_rep, _ = _run(capsys, "report", "--out", str(report))
    assert code_last == 0 and json.loads(last_out)["calls"] > 0
    assert code_rep == 0 and CANARY not in report.read_text(encoding="utf-8")

    # Act 6: uninstall restores both files byte-for-byte (SU-03), data kept
    code_un, out_un = _run(capsys, "uninstall")
    assert code_un == 0, out_un
    assert claude_settings.read_bytes() == claude_before
    assert agy_hooks.read_bytes() == agy_before
    assert gemini_settings.read_bytes() == gemini_before
    assert qa_world.meter.db.exists()
    assert any(c[:2] == ["launchctl", "bootout"] or c[:2] == ["launchctl", "print"] for c in fake_scheduler.calls)


def test_l3_uninstall_without_prior_files_deletes_what_setup_created(
    qa_world: QAWorld, capsys: pytest.CaptureFixture[str],
) -> None:
    claude_settings = qa_world.user / ".claude" / "settings.json"
    agy_hooks = qa_world.user / ".gemini" / "config" / "hooks.json"
    assert not claude_settings.exists() and not agy_hooks.exists()

    assert _run(capsys, "setup", "--local", "--yes", "--triggers", "hooks", "--no-backfill")[0] == 0
    assert claude_settings.exists() and agy_hooks.exists()
    assert _run(capsys, "uninstall", "--keep-scheduler")[0] == 0

    assert not claude_settings.exists()
    assert not agy_hooks.exists()


def test_l3_uninstall_after_user_edit_keeps_user_changes(
    qa_world: QAWorld, capsys: pytest.CaptureFixture[str],
) -> None:
    claude_settings = qa_world.user / ".claude" / "settings.json"
    _write_json(claude_settings, CLAUDE_SETTINGS)
    assert _run(capsys, "setup", "--local", "--yes", "--triggers", "hooks", "--no-backfill")[0] == 0
    edited = json.loads(claude_settings.read_text(encoding="utf-8"))
    edited["theme"] = "dark"
    claude_settings.write_text(json.dumps(edited, indent=2), encoding="utf-8")

    assert _run(capsys, "uninstall", "--keep-scheduler")[0] == 0

    final = json.loads(claude_settings.read_text(encoding="utf-8"))
    assert final["theme"] == "dark"
    assert final["hooks"]["PreToolUse"] == CLAUDE_SETTINGS["hooks"]["PreToolUse"]
    assert _agent_meter_commands(claude_settings) == []
