"""Desktop app services and live watcher (Phase 4), without any GUI."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agent_meter.app.services import AppApi
from agent_meter.app.watcher import TranscriptWatcher, signature, watched_folders
from agent_meter.config import load_config
from agent_meter.locking import store_lock
from agent_meter.model import Host
from agent_meter.paths import AppHome
from agent_meter.pricing import load_pricing
from agent_meter.project_resolver import ProjectsConfig
from agent_meter.setup import settings_merge
from agent_meter.store import Store
from tests.fixtures.records import make_batch, make_project, ts

NOW = ts(600) + timedelta(minutes=5)


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AppHome]:
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    meter = AppHome.resolve(str(tmp_path / "h"))
    with Store.open(meter, read_only=False, lock_timeout_s=1.0) as opened:
        opened.migrate()
        opened.load_reference_data(
            pricing=load_pricing(None), host_defaults={},
            projects=ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={}),
            project_refs=[make_project()], settings={"timezone": "UTC"},
        )
        opened.apply_batches([make_batch()])
    yield meter


def api(home: AppHome, now: datetime = NOW) -> AppApi:
    return AppApi(home, clock=lambda: now)


def test_overview_lists_a_recent_session_as_json_safe_data(home: AppHome) -> None:
    AppApi(home).save_setting("budget.monthly_usd", "100")

    data = api(home).overview()

    assert json.loads(json.dumps(data)) == data
    (session,) = data["sessions"]
    assert session["minutes_ago"] == 5
    assert session["context_tokens"] > 0
    assert data["budgets"][0]["period"] == "this month"


def test_overview_hides_sessions_idle_for_too_long(home: AppHome) -> None:
    assert api(home, NOW + timedelta(hours=1)).overview()["sessions"] == []


def test_a_held_store_reports_busy_instead_of_failing(home: AppHome, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent_meter.app.services.READ_LOCK_S", 0.05)

    with store_lock(home.lock, exclusive=True, timeout_s=1.0):
        assert api(home).overview() == {"busy": True}


def test_only_listed_settings_can_change(home: AppHome) -> None:
    refused = AppApi(home).save_setting("timezone", "UTC")
    saved = AppApi(home).save_setting("budget.daily_usd", "25")
    invalid = AppApi(home).save_setting("budget.daily_usd", "not money")

    assert refused["ok"] is False
    assert saved == {"ok": True}
    assert invalid["ok"] is False
    assert str(load_config(home).budget.daily_usd) == "25"


def test_settings_return_current_values_and_diagnostics(home: AppHome) -> None:
    AppApi(home).save_setting("budget.plan_monthly_usd", "20")

    data = AppApi(home).settings()

    assert data["values"]["budget.plan_monthly_usd"] == "20"
    assert {"status", "check", "message"} <= set(data["checks"][0])


def test_watcher_reacts_only_when_a_transcript_changes(tmp_path: Path) -> None:
    transcript = tmp_path / "projects" / "s.jsonl"
    transcript.parent.mkdir()
    transcript.write_text("{}\n", encoding="utf-8")
    changes: list[int] = []
    watcher = TranscriptWatcher([tmp_path / "projects"], lambda: changes.append(1))

    idle = watcher.poll_once()
    (tmp_path / "projects" / "note.txt").write_text("ignored", encoding="utf-8")
    still_idle = watcher.poll_once()
    os.utime(transcript, ns=(1, signature([tmp_path / "projects"])[1] + 1_000_000))
    changed = watcher.poll_once()

    assert (idle, still_idle, changed) == (False, False, True)
    assert changes == [1]


def test_a_failed_refresh_does_not_stop_the_watcher(tmp_path: Path) -> None:
    folder = tmp_path / "projects"
    folder.mkdir()

    def fail() -> None:
        raise RuntimeError("boom")

    watcher = TranscriptWatcher([folder], fail)
    (folder / "s.jsonl").write_text("{}\n", encoding="utf-8")

    assert watcher.poll_once() is True


def test_watched_folders_cover_each_host(tmp_path: Path) -> None:
    roots = {Host.CLAUDE_CODE: tmp_path / "c", Host.ANTIGRAVITY_CLI: tmp_path / "a"}

    assert watched_folders(roots) == [tmp_path / "c" / "projects", tmp_path / "a" / "conversations", tmp_path / "a" / "brain"]


def test_brain_folders_watch_only_the_transcript(tmp_path: Path) -> None:
    logs = tmp_path / "brain" / "c1" / ".system_generated" / "logs"
    logs.mkdir(parents=True)
    (logs / "transcript_full.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "brain" / "c1" / "notes.jsonl").write_text("{}\n", encoding="utf-8")

    assert signature([tmp_path / "brain"])[0] == 1


def test_spanish_reaches_budgets_and_diagnostics(home: AppHome) -> None:
    app = api(home)
    app.set_language("es")
    app.save_setting("budget.monthly_usd", "100")

    overview = app.overview()
    settings = app.settings()

    assert overview["budgets"][0]["period"] == "este mes"
    assert overview["budgets"][0]["label"] == "Todos los proyectos"
    assert {check["check"] for check in settings["checks"]} >= {"configuración", "programador"}
    assert {"OK", "WARN", "FAIL"} >= {check["status"] for check in settings["checks"]}


def test_a_rejected_setting_is_explained_in_spanish(home: AppHome) -> None:
    app = api(home)
    app.set_language("es")

    assert "no es un número decimal" in app.save_setting("budget.monthly_usd", "abc")["error"]


def test_history_rolls_up_by_day_month_project_and_session(home: AppHome) -> None:
    data = api(home).history()

    assert json.loads(json.dumps(data)) == data
    assert data["totals"]["sessions"] == len(data["sessions"]) == 1
    assert data["by_day"][-1]["calls"] == data["totals"]["calls"]
    assert data["by_month"][0]["cost_usd"] == data["totals"]["cost_usd"]
    assert data["projects"][0]["share_pct"] == "100.0"


def test_history_filters_by_project_but_keeps_the_project_list(home: AppHome) -> None:
    data = api(home).history(0, "someone-else")

    assert data["totals"]["calls"] == 0
    assert data["sessions"] == []
    assert len(data["projects"]) == 1


def test_history_period_excludes_older_days(home: AppHome) -> None:
    data = api(home, NOW + timedelta(days=30)).history(7)

    assert data["totals"]["calls"] == 0
    assert len(data["by_day"]) == 7


def test_saved_figures_are_shown_while_a_collect_holds_the_store(home: AppHome, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent_meter.app.services.READ_LOCK_S", 0.01)
    first = api(home).overview()

    with store_lock(home.lock, exclusive=True, timeout_s=1.0):
        again = api(home).overview()  # a new instance: the figures survive a restart of the app

    assert again["stale"] is True
    assert again["today_usd"] == first["today_usd"]


def test_a_broken_saved_file_does_not_stop_the_app(home: AppHome) -> None:
    home.state_dir.mkdir(parents=True, exist_ok=True)
    (home.state_dir / "app-cache.json").write_text("not json")

    assert "today_usd" in api(home).overview()


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def gapped_watcher(folder: Path, runs: list[int], clock: Clock) -> TranscriptWatcher:
    return TranscriptWatcher([folder], lambda: runs.append(1), min_gap_s=30.0, clock=clock)


def change(folder: Path, name: str) -> None:
    (folder / name).write_text("{}")


def test_a_second_change_waits_for_the_gap_and_is_not_lost(tmp_path: Path) -> None:
    runs: list[int] = []
    clock = Clock()
    watcher = gapped_watcher(tmp_path, runs, clock)

    change(tmp_path, "a.jsonl")
    assert watcher.poll_once() is True
    change(tmp_path, "b.jsonl")
    clock.now += 29
    assert watcher.poll_once() is False
    assert len(runs) == 1

    clock.now += 1
    assert watcher.poll_once() is True
    assert len(runs) == 2


def test_the_gap_counts_from_the_end_of_a_slow_collect(tmp_path: Path) -> None:
    clock = Clock()
    runs: list[int] = []

    def slow_collect() -> None:
        runs.append(1)
        clock.now += 80

    watcher = TranscriptWatcher([tmp_path], slow_collect, min_gap_s=30.0, clock=clock)
    change(tmp_path, "a.jsonl")
    watcher.poll_once()
    change(tmp_path, "b.jsonl")
    clock.now += 29

    assert watcher.poll_once() is False


def test_the_gap_still_applies_after_a_failed_collect(tmp_path: Path) -> None:
    clock = Clock()

    def failing_collect() -> None:
        raise OSError("disk")

    watcher = TranscriptWatcher([tmp_path], failing_collect, min_gap_s=30.0, clock=clock)
    change(tmp_path, "a.jsonl")
    assert watcher.poll_once() is True
    change(tmp_path, "b.jsonl")

    assert watcher.poll_once() is False


def test_nothing_runs_when_nothing_changed(tmp_path: Path) -> None:
    runs: list[int] = []
    clock = Clock()
    watcher = gapped_watcher(tmp_path, runs, clock)
    clock.now += 100

    assert watcher.poll_once() is False
    assert runs == []


@pytest.fixture()
def claude_settings(home: AppHome, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "user" / ".claude" / "settings.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"model": "opus"}', encoding="utf-8")
    monkeypatch.setattr(settings_merge, "MANAGED_SETTINGS_PATHS", ())
    return path


def test_actions_show_the_current_value(home: AppHome, claude_settings: Path) -> None:
    actions = {a["id"]: a for a in api(home).actions()["actions"]}

    assert actions["claude.model"]["current"] == "opus"
    assert actions["claude.effort.opus"]["current"] is None


def test_effort_goes_to_the_per_model_setting(home: AppHome, claude_settings: Path) -> None:
    app = api(home)
    plan = app.preview("claude.effort.opus", "high")

    assert app.apply_action("claude.effort.opus", "high", plan["before_sha256"])["ok"] is True
    assert json.loads(claude_settings.read_text())["modelSettings"]["claude-opus-5-5"] == {"effortLevel": "high"}


def test_apply_refuses_if_the_file_differs_from_the_preview(home: AppHome, claude_settings: Path) -> None:
    app = api(home)
    plan = app.preview("claude.model", "sonnet")
    claude_settings.write_text('{"model": "opus", "theme": "dark"}', encoding="utf-8")

    result = app.apply_action("claude.model", "sonnet", plan["before_sha256"])

    assert result == {"ok": False, "code": "stale"}
    assert json.loads(claude_settings.read_text())["model"] == "opus"


def test_a_change_appears_in_history_and_can_be_undone(home: AppHome, claude_settings: Path) -> None:
    app = api(home)
    plan = app.preview("claude.model", "sonnet")
    change_id = app.apply_action("claude.model", "sonnet", plan["before_sha256"])["id"]

    (change,) = app.changes()["changes"]
    undone = app.undo_action(change_id)

    assert change["new_value"] == "sonnet"
    assert change["effect"] == {"enough": False, "tasks_after": 0}
    assert undone == {"ok": True}
    assert json.loads(claude_settings.read_text())["model"] == "opus"


def test_insights_suggest_only_known_actions(home: AppHome) -> None:
    from agent_meter.app.services import _INSIGHT_ACTIONS
    from agent_meter.setup.actuators import ACTIONS

    for action_id, value in _INSIGHT_ACTIONS.values():
        assert value in ACTIONS[action_id].values
