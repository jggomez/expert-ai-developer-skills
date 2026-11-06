"""Projects screen, automatic rules, tray text and the update check, without any GUI."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from agent_meter.app.projects import (
    ProjectInputError,
    project_changes,
    valid_hours,
    valid_period,
)
from agent_meter.app.services import AppApi
from agent_meter.app.tray import tray_text
from agent_meter.app.updates import check_for_update, newest_release
from agent_meter.paths import AppHome
from agent_meter.pricing import load_pricing
from agent_meter.project_resolver import ProjectsConfig, load_projects_config
from agent_meter.setup import actuators, auto_rules
from agent_meter.store import Store
from tests.fixtures.records import make_batch, make_project

NOW = datetime(2026, 11, 5, 12, tzinfo=UTC)
TODAY = date(2026, 11, 5)
OVER = [{"key": "month:all", "level": "over", "label": "All projects", "period": "this month"}]


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AppHome]:
    user = tmp_path / "user"
    (user / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(user))
    yield AppHome.resolve(str(tmp_path / "home"))


@pytest.fixture()
def api(home: AppHome) -> AppApi:
    with Store.open(home, read_only=False, lock_timeout_s=5) as store:
        store.migrate()
        store.load_reference_data(pricing=load_pricing(home.pricing_local), host_defaults={},
                                  projects=ProjectsConfig({}, {}, (), {}), project_refs=[make_project()],
                                  settings={"timezone": "UTC"})
        store.apply_batches([make_batch()])
    return AppApi(home, clock=lambda: NOW)


def _project_id(api: AppApi) -> str:
    return str(api.projects()["projects"][0]["project_id"])


def test_saved_project_details_reach_the_store_and_the_file(api: AppApi, home: AppHome) -> None:
    # Arrange
    project = _project_id(api)

    # Act
    result = api.save_project(project, {"name": "Shop", "client": "Acme", "billing": "hourly", "rate": "80.50", "currency": "usd"})

    # Assert
    assert result == {"ok": True}
    saved = api.projects()["projects"][0]
    assert (saved["name"], saved["client"], saved["billing"], saved["currency"]) == ("Shop", "Acme", "hourly", "USD")
    assert Decimal(saved["rate"]) == Decimal("80.50")
    assert load_projects_config(home.projects).projects[project].client == "Acme"


def test_empty_boxes_clear_saved_details(api: AppApi) -> None:
    # Arrange
    project = _project_id(api)
    api.save_project(project, {"client": "Acme", "billing": "fixed", "fixed_price": "100"})

    # Act
    api.save_project(project, {})

    # Assert
    saved = api.projects()["projects"][0]
    assert (saved["client"], saved["billing"], saved["fixed_price"]) == (None, None, None)


def test_tag_and_hours_can_be_set_and_removed(api: AppApi) -> None:
    # Arrange
    project = _project_id(api)

    # Act
    tagged = api.set_project_tag(project, " sprint-4 ")
    added = api.set_project_hours(project, "2026-10", "12.5")

    # Assert
    assert tagged["ok"] and added["ok"]
    saved = api.projects()["projects"][0]
    assert saved["tag"] == "sprint-4"
    assert [entry["period"] for entry in saved["hours"]] == ["2026-10"]

    assert api.remove_project_hours(project, "2026-10")["ok"]
    assert api.set_project_tag(project, "")["ok"]
    saved = api.projects()["projects"][0]
    assert saved["hours"] == [] and saved["tag"] is None


def test_unknown_project_changes_nothing(api: AppApi, home: AppHome) -> None:
    assert api.save_project("nope", {"client": "x"}) == {"ok": False, "code": "unknown_project"}
    assert not home.projects.exists()


@pytest.mark.parametrize(
    ("fields", "code"),
    [({"rate": "abc"}, "invalid_amount"), ({"rate": "-1"}, "invalid_amount"), ({"rate": "NaN"}, "invalid_amount"),
     ({"billing": "weekly"}, "invalid_billing"), ({"currency": "US"}, "invalid_currency")],
)
def test_bad_project_input_is_refused(fields: dict[str, Any], code: str) -> None:
    with pytest.raises(ProjectInputError) as caught:
        project_changes(fields)
    assert caught.value.code == code


@pytest.mark.parametrize("period", ["2026-13", "2026", "2026-1", "2026-10-01", "2026-10\n"])
def test_bad_months_are_refused(period: str) -> None:
    with pytest.raises(ProjectInputError):
        valid_period(period)


def test_hours_are_required() -> None:
    with pytest.raises(ProjectInputError):
        valid_hours("")


def _claude_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"model": "opus", "keep": 1}), encoding="utf-8")
    monkeypatch.setattr(actuators, "target_paths", lambda: {"claude": path, "antigravity": tmp_path / "missing.json"})
    return path


def test_rules_are_off_until_turned_on(home: AppHome, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    path = _claude_settings(tmp_path, monkeypatch)

    # Act
    fired = auto_rules.evaluate(home, OVER, today=TODAY, now=NOW)

    # Assert
    assert fired == []
    assert json.loads(path.read_text(encoding="utf-8"))["model"] == "opus"


def test_rule_changes_only_the_model_and_can_be_undone(home: AppHome, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    path = _claude_settings(tmp_path, monkeypatch)
    original = path.read_bytes()
    auto_rules.set_rule(home, "monthly_budget_sonnet", True)

    # Act
    fired = auto_rules.evaluate(home, OVER, today=TODAY, now=NOW)

    # Assert
    assert json.loads(path.read_text(encoding="utf-8")) == {"model": "sonnet", "keep": 1}
    actuators.undo_change(fired[0].change_id, home, now=NOW)
    assert path.read_bytes() == original


def test_undone_rule_waits_for_the_next_period(home: AppHome, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    _claude_settings(tmp_path, monkeypatch)
    auto_rules.set_rule(home, "monthly_budget_sonnet", True)
    first = auto_rules.evaluate(home, OVER, today=TODAY, now=NOW)
    actuators.undo_change(first[0].change_id, home, now=NOW)

    # Act
    same_month = auto_rules.evaluate(home, OVER, today=date(2026, 11, 20), now=NOW)
    next_month = auto_rules.evaluate(home, OVER, today=date(2026, 12, 1), now=NOW)

    # Assert
    assert same_month == []
    assert len(next_month) == 1


def test_rule_ignores_budgets_that_are_not_over(home: AppHome, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    _claude_settings(tmp_path, monkeypatch)
    auto_rules.set_rule(home, "monthly_budget_sonnet", True)

    # Act
    warned = auto_rules.evaluate(home, [{**OVER[0], "level": "warn"}], today=TODAY, now=NOW)
    other = auto_rules.evaluate(home, [{**OVER[0], "key": "day:all"}], today=TODAY, now=NOW)

    # Assert
    assert warned == [] and other == []


def test_damaged_rules_file_turns_every_rule_off(home: AppHome, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    _claude_settings(tmp_path, monkeypatch)
    (home.root / auto_rules.STATE_NAME).write_text("{broken", encoding="utf-8")

    # Act & Assert
    assert auto_rules.enabled_rules(home) == []
    assert auto_rules.evaluate(home, OVER, today=TODAY, now=NOW) == []


def test_tray_shows_today_and_only_budgets_that_need_attention() -> None:
    # Arrange
    overview = {"today_usd": "1234.50", "month_usd": "2000.00", "budgets": [
        {"level": "ok", "label": "All projects", "period": "today"},
        {"level": "over", "label": "All projects", "period": "este mes"},
    ]}

    # Act
    title, lines = tray_text(overview, "es")

    # Assert
    assert title == "$1.234,50"
    assert len(lines) == 3
    assert "este mes" in lines[2]


def test_tray_stays_empty_while_the_store_is_busy() -> None:
    assert tray_text({"busy": True}, "en") == ("", [])


PAGE = "https://github.com/jggomez/expert-ai-developer-skills/releases/tag/"


def _release(tag: str, **extra: Any) -> dict[str, Any]:
    return {"tag_name": tag, "html_url": PAGE + tag, **extra}


def test_only_this_tools_published_releases_count() -> None:
    # Arrange
    releases = [_release("pr-reviewer-v9.0.0"), _release("agent-meter-v0.2.0"), _release("agent-meter-v0.10.0"),
                _release("agent-meter-v9.0.0", draft=True), _release("agent-meter-v8.0.0", prerelease=True),
                {"tag_name": "agent-meter-v7.0.0", "html_url": "https://example.com/"}]

    # Act
    newest = newest_release(releases)

    # Assert
    assert newest is not None
    assert newest["version"] == "0.10.0"


def test_update_notice_only_for_a_newer_version() -> None:
    assert check_for_update("0.1.0", lambda: [_release("agent-meter-v0.2.0")])["newer"] is True
    assert check_for_update("0.2.0", lambda: [_release("agent-meter-v0.2.0")])["newer"] is False
    assert check_for_update("0.1.0", list)["newer"] is False


def test_update_check_failure_is_reported_not_raised() -> None:
    def offline() -> list[dict[str, Any]]:
        raise OSError("no network")

    assert check_for_update("0.1.0", offline) == {"ok": False}


def test_only_release_pages_can_be_opened(api: AppApi) -> None:
    assert api.open_release("https://example.com/") == {"ok": False}
