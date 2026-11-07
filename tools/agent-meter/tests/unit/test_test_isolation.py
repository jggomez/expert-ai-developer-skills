"""Tests must never write to the real user's agent-meter home."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from agent_meter import hook
from agent_meter.paths import AppHome


def test_default_home_is_inside_the_test_user_home(_isolated_user_home: Path) -> None:
    root = AppHome.resolve().root

    assert root == _isolated_user_home / ".agent-meter"


def test_hook_failure_log_stays_in_the_test_home(_isolated_user_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_argv: list[str]) -> None:
        raise OSError("spawn failed")

    monkeypatch.setattr(hook, "_spawn_worker", fail)
    payload = b'{"session_id": "s-1", "hook_event_name": "Stop"}'

    code = hook.hook_main(["--host", "claude-code", "--event", "task-end"], io.BytesIO(payload), io.StringIO())

    assert code == 0
    log = _isolated_user_home / ".agent-meter" / "logs" / "hook.log"
    assert log.read_text(encoding="utf-8").split()[1:] == ["error", "OSError"]
