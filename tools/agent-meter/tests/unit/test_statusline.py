"""The Claude Code status line and the setting that turns it on."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from agent_meter.config import load_config
from agent_meter.paths import AppHome
from agent_meter.setup import actuators
from agent_meter.statusline import render_statusline, save_today

NOW = datetime(2026, 11, 5, 12, tzinfo=UTC)
TODAY = date(2026, 11, 5)
PAYLOAD = json.dumps({"cost": {"total_cost_usd": 1.2345}, "context_window": {"used_percentage": 37.6}})


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppHome:
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    return AppHome.resolve(str(tmp_path / "home"))


def test_line_shows_session_today_and_context(home: AppHome) -> None:
    # Arrange
    cfg = replace(load_config(home), timezone="UTC")
    save_today(home, TODAY, "46.2")

    # Act
    line = render_statusline(PAYLOAD, home, cfg, now=NOW)

    # Assert
    assert line == "$1.23 session · $46.20 today · 38% context"


def test_line_follows_the_chosen_language(home: AppHome) -> None:
    # Arrange
    cfg = replace(load_config(home), timezone="UTC", language="es")
    save_today(home, TODAY, "1234.5")

    # Act
    line = render_statusline(PAYLOAD, home, cfg, now=NOW)

    # Assert
    assert line == "$1,23 sesión · $1.234,50 hoy · 38% contexto"


def test_figure_from_another_day_is_left_out(home: AppHome) -> None:
    # Arrange
    cfg = replace(load_config(home), timezone="UTC")
    save_today(home, date(2026, 11, 4), "99")

    # Act & Assert
    assert "today" not in render_statusline(PAYLOAD, home, cfg, now=NOW)


@pytest.mark.parametrize("raw", ["", "not json", "[]", '{"cost": "x"}', '{"cost": {"total_cost_usd": "x"}}'])
def test_bad_input_never_fails(home: AppHome, raw: str) -> None:
    assert render_statusline(raw, home, replace(load_config(home), timezone="UTC"), now=NOW) == ""


def test_setting_needs_the_installed_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Arrange
    monkeypatch.setattr(actuators.shutil, "which", lambda _name: None)
    monkeypatch.setattr(actuators, "target_paths", lambda: {"claude": tmp_path / "settings.json", "antigravity": tmp_path / "no.json"})

    # Act
    options = actuators.action_options(actuators.ACTIONS["claude.statusline"])

    # Assert
    assert options == ()
    with pytest.raises(actuators.ActuatorError):
        actuators.plan_change("claude.statusline", "anything")


def test_setting_writes_a_command_object_and_undo_restores_a_custom_line(
    home: AppHome, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    # Arrange
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"statusLine": {"type": "command", "command": "mine"}}), encoding="utf-8")
    original = path.read_bytes()
    monkeypatch.setattr(actuators.shutil, "which", lambda _name: "/opt/my tools/agent-meter")
    monkeypatch.setattr(actuators, "target_paths", lambda: {"claude": path, "antigravity": tmp_path / "no.json"})
    command = actuators.statusline_command()
    assert command is not None

    # Act
    plan = actuators.plan_change("claude.statusline", command)
    change = actuators.apply_change(plan, home, now=NOW)

    # Assert
    assert plan.old_value == "mine"
    assert json.loads(path.read_text(encoding="utf-8"))["statusLine"] == {"type": "command", "command": command}
    assert actuators.current_value(actuators.ACTIONS["claude.statusline"]) == command
    actuators.undo_change(change["id"], home, now=NOW)
    assert path.read_bytes() == original


def test_estimated_status_line_appears_in_the_app_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(actuators.shutil, "which", lambda _name: "/usr/bin/agent-meter")

    options = actuators.action_options(actuators.ACTIONS["claude.statusline"])

    assert len(options) == 1
    assert options[0].endswith("/usr/bin/agent-meter statusline") or options[0] == '"/usr/bin/agent-meter" statusline'
