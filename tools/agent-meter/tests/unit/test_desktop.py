"""The packaged app's entry point and Windows notifications."""

from __future__ import annotations

import base64
import importlib.util
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


def test_failures_are_grouped_by_message_for_public_annotations(tmp_path: Path) -> None:
    # Arrange
    spec = importlib.util.spec_from_file_location("report", Path(__file__).parents[2] / "packaging" / "report_test_failures.py")
    assert spec is not None and spec.loader is not None
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    results = tmp_path / "results.xml"
    results.write_text(
        '<testsuites><testsuite>'
        '<testcase classname="a" name="one"><failure message="same&#10;cause"/></testcase>'
        '<testcase classname="a" name="two"><failure message="same&#10;cause"/></testcase>'
        '<testcase classname="b" name="three"><error message="other"/></testcase>'
        '<testcase classname="b" name="fine"/>'
        '</testsuite></testsuites>', encoding="utf-8",
    )

    # Act
    lines = report.annotations(report.failures(results))

    # Assert
    assert lines == ["::error title=All 3 failed::a.one: same%0Acause%0Aa.two: same%0Acause%0Ab.three: other", "::error title=2 like a.one::same%0Acause",
                     "::error title=1 like b.three::other"]
