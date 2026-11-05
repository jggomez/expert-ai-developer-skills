"""Actuators change one known setting of a host, only after a preview, and can always be undone."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_meter.paths import AppHome
from agent_meter.setup import actuators, settings_merge
from agent_meter.setup.actuators import (
    ActuatorError,
    apply_change,
    list_changes,
    plan_change,
    undo_change,
)

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
ORIGINAL = {"model": "opus", "theme": "dark", "hooks": {"Stop": []}}


@pytest.fixture()
def home(tmp_path: Path) -> AppHome:
    return AppHome.resolve(str(tmp_path / "meter"))


@pytest.fixture()
def settings(tmp_path: Path) -> Path:
    path = tmp_path / "user" / ".claude" / "settings.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(ORIGINAL, indent=4), encoding="utf-8")
    return path


@pytest.fixture()
def targets(settings: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    found = {"claude": settings, "antigravity": tmp_path / "user" / ".gemini" / "antigravity-cli" / "settings.json"}
    monkeypatch.setattr(settings_merge, "MANAGED_SETTINGS_PATHS", ())
    monkeypatch.setattr(actuators, "target_paths", lambda: found)
    return found


def test_a_preview_changes_nothing_and_shows_the_exact_change(targets: dict[str, Path], settings: Path) -> None:
    before = settings.read_bytes()

    plan = plan_change("claude.model", "sonnet")

    assert settings.read_bytes() == before
    assert (plan.old_value, plan.new_value, plan.changed) == ("opus", "sonnet", True)
    assert '-  "model": "opus"' in plan.diff
    assert '+  "model": "sonnet"' in plan.diff


def test_apply_writes_only_that_key_and_keeps_the_rest(targets: dict[str, Path], settings: Path, home: AppHome) -> None:
    apply_change(plan_change("claude.model", "sonnet"), home, now=NOW)

    assert json.loads(settings.read_text()) == {**ORIGINAL, "model": "sonnet"}


def test_apply_keeps_a_backup_of_the_original_bytes(targets: dict[str, Path], settings: Path, home: AppHome) -> None:
    before = settings.read_bytes()

    change = apply_change(plan_change("claude.model", "sonnet"), home, now=NOW)

    assert Path(change["backup"]).read_bytes() == before


def test_a_nested_key_is_created_and_undo_removes_what_it_created(targets: dict[str, Path], settings: Path, home: AppHome) -> None:
    before = settings.read_bytes()
    action = actuators.ACTIONS["claude.autocompact"]

    change = apply_change(plan_change("claude.autocompact", action.values[0]), home, now=NOW)
    assert json.loads(settings.read_text())["env"] == {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": action.values[0]}

    undo_change(change["id"], home, now=NOW)
    assert settings.read_bytes() == before


def test_undo_restores_the_file_byte_for_byte(targets: dict[str, Path], settings: Path, home: AppHome) -> None:
    before = settings.read_bytes()
    change = apply_change(plan_change("claude.model", "sonnet"), home, now=NOW)

    undo_change(change["id"], home, now=NOW)

    assert settings.read_bytes() == before
    assert list_changes(home)[0]["undone_at"] is not None


def test_undo_keeps_edits_made_after_the_change(targets: dict[str, Path], settings: Path, home: AppHome) -> None:
    change = apply_change(plan_change("claude.model", "sonnet"), home, now=NOW)
    edited = json.loads(settings.read_text()) | {"theme": "light"}
    settings.write_text(json.dumps(edited), encoding="utf-8")

    undo_change(change["id"], home, now=NOW)

    assert json.loads(settings.read_text()) == {**ORIGINAL, "theme": "light"}


def test_undo_refuses_when_the_key_itself_was_changed_later(targets: dict[str, Path], settings: Path, home: AppHome) -> None:
    change = apply_change(plan_change("claude.model", "sonnet"), home, now=NOW)
    settings.write_text(json.dumps({**ORIGINAL, "model": "haiku"}), encoding="utf-8")

    with pytest.raises(ActuatorError) as caught:
        undo_change(change["id"], home, now=NOW)

    assert caught.value.code == "changed_since"
    assert json.loads(settings.read_text())["model"] == "haiku"


def test_undo_twice_is_refused(targets: dict[str, Path], home: AppHome) -> None:
    change = apply_change(plan_change("claude.model", "sonnet"), home, now=NOW)
    undo_change(change["id"], home, now=NOW)

    with pytest.raises(ActuatorError) as caught:
        undo_change(change["id"], home, now=NOW)

    assert caught.value.code == "already_undone"


def test_a_file_changed_after_the_preview_is_not_overwritten(targets: dict[str, Path], settings: Path, home: AppHome) -> None:
    plan = plan_change("claude.model", "sonnet")
    settings.write_text(json.dumps({**ORIGINAL, "theme": "light"}), encoding="utf-8")

    with pytest.raises(ActuatorError) as caught:
        apply_change(plan, home, now=NOW)

    assert caught.value.code == "stale"
    assert json.loads(settings.read_text())["theme"] == "light"
    assert list_changes(home) == []


@pytest.mark.parametrize("content", ["{not json", "[1, 2]", '{"model": "a", "model": "b"}'])
def test_a_file_that_is_not_safe_to_edit_is_refused(targets: dict[str, Path], settings: Path, content: str) -> None:
    settings.write_text(content, encoding="utf-8")

    with pytest.raises(ActuatorError) as caught:
        plan_change("claude.model", "sonnet")

    assert caught.value.code == "refused"
    assert settings.read_text() == content


def test_unknown_actions_and_values_are_refused(targets: dict[str, Path]) -> None:
    with pytest.raises(ActuatorError) as unknown:
        plan_change("claude.permissions", "bypass")
    with pytest.raises(ActuatorError) as value:
        plan_change("claude.model", "gpt-9")

    assert (unknown.value.code, value.value.code) == ("unknown_action", "unknown_value")


def test_a_key_set_by_a_managed_policy_is_refused(targets: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = tmp_path / "managed-settings.json"
    policy.write_text('{"model": "opus"}', encoding="utf-8")
    monkeypatch.setattr(settings_merge, "MANAGED_SETTINGS_PATHS", (policy,))

    with pytest.raises(ActuatorError) as caught:
        plan_change("claude.model", "sonnet")

    assert caught.value.code == "managed"


def test_antigravity_is_never_created_when_it_is_not_installed(targets: dict[str, Path]) -> None:
    with pytest.raises(ActuatorError) as caught:
        plan_change("antigravity.model", "Gemini 4 Argon (High)", observed=("Gemini 4 Argon (High)",))

    assert caught.value.code == "not_installed"
    assert not targets["antigravity"].exists()


def test_antigravity_only_offers_models_seen_in_your_data(targets: dict[str, Path], home: AppHome) -> None:
    path = targets["antigravity"]
    path.parent.mkdir(parents=True)
    path.write_text('{"model": "Gemini 4 Argon (High)"}', encoding="utf-8")

    with pytest.raises(ActuatorError) as unseen:
        plan_change("antigravity.model", "Made Up", observed=("Gemini 4 Argon (Low)",))
    apply_change(plan_change("antigravity.model", "Gemini 4 Argon (Low)", observed=("Gemini 4 Argon (Low)",)), home, now=NOW)

    assert unseen.value.code == "unknown_value"
    assert json.loads(path.read_text())["model"] == "Gemini 4 Argon (Low)"


def test_gemini_cli_settings_are_never_a_target() -> None:
    assert not [p for p in actuators.target_paths().values() if p.parent.name == ".gemini"]


def test_no_change_when_the_value_is_already_set(targets: dict[str, Path], settings: Path, home: AppHome) -> None:
    plan = plan_change("claude.model", "opus")

    assert plan.changed is False
    with pytest.raises(ActuatorError) as caught:
        apply_change(plan, home, now=NOW)
    assert caught.value.code == "no_change"


def test_settings_are_written_with_the_same_permissions(targets: dict[str, Path], settings: Path, home: AppHome) -> None:
    settings.chmod(0o640)

    apply_change(plan_change("claude.model", "sonnet"), home, now=NOW)

    assert settings.stat().st_mode & 0o777 == 0o640
