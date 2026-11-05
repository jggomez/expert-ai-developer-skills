"""The packaged app's entry point and Windows notifications."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from agent_meter import notify
from agent_meter.app import desktop
from agent_meter.paths import AppHome


def test_self_test_reads_every_screen_on_an_empty_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    home = AppHome.resolve(str(tmp_path / "home"))

    # Act
    desktop.self_test(home)

    # Assert
    assert home.db.exists()


def test_windows_notice_never_puts_text_on_the_command_line(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr(notify.sys, "platform", "win32")
    monkeypatch.setattr(notify.shutil, "which", lambda _name: "powershell.exe")

    # Act
    command = notify._command("it's over", "$5 ‘left’; rm x")

    # Assert
    assert command is not None
    assert "over" not in " ".join(command)
    script = base64.b64decode(command[-1]).decode("utf-16-le")
    assert "'it''s over'" in script
    assert "'$5 ''left''; rm x'" in script
