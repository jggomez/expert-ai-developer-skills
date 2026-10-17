"""Tests for ``agent_meter.setup.settings_merge`` (ADR §3.10, BR-18/19; SU-01..03)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_meter.setup import settings_merge as sm
from agent_meter.setup.settings_merge import (
    MergePlan,
    PlanStale,
    SettingsRefused,
    apply,
    command_prefix,
    plan_antigravity,
    plan_claude,
    registration_status,
    render_preview,
    uninstall,
)

PREFIX = "/opt/bin/agent-meter"
CLAUDE_SESSION_END = f"{PREFIX} hook --host claude-code --event session-end"
CLAUDE_STOP = f"{PREFIX} hook --host claude-code --event task-end"
AGY_STOP = f"{PREFIX} hook --host antigravity --event task-end"
NOW = datetime(2026, 10, 16, 18, 42, 7, 123456, tzinfo=UTC)

UNRELATED_CLAUDE = {
    "model": "opus",
    "enabledPlugins": {"senior-dev@skills": True},
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": "~/bin/guard.sh"}],
            }
        ],
        "Stop": [{"hooks": [{"type": "command", "command": "say done"}]}],
    },
}
UNRELATED_AGY = {
    "rtk": {
        "enabled": True,
        "PreToolUse": [
            {
                "matcher": "run_shell_command",
                "hooks": [
                    {"type": "command", "command": "~/.gemini/hooks/rtk-hook-gemini.sh"}
                ],
            }
        ],
    }
}


@dataclass(frozen=True)
class FakeHome:
    root: Path

    @property
    def backups_dir(self) -> Path:
        return self.root / "backups"

    @property
    def install_manifest(self) -> Path:
        return self.root / "install.json"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"


@pytest.fixture
def home(tmp_path: Path) -> FakeHome:
    root = tmp_path / "agent-meter-home"
    root.mkdir(mode=0o700)
    return FakeHome(root)


@pytest.fixture
def no_managed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sm, "MANAGED_SETTINGS_PATHS", (tmp_path / "no-managed.json",))


def write_json(path: Path, obj: object, *, indent: int = 2) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(obj, indent=indent) + "\n").encode()
    path.write_bytes(raw)
    return raw


def commands_in(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        command = obj.get("command")
        if isinstance(command, str):
            found.append(command)
        for value in obj.values():
            found.extend(commands_in(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(commands_in(item))
    return found


def manifest(home: FakeHome) -> dict[str, object]:
    loaded: dict[str, object] = json.loads(home.install_manifest.read_text())
    return loaded


# --------------------------------------------------------------------------- plan_claude


@pytest.mark.usefixtures("no_managed")
def test_plan_claude_on_absent_file_adds_session_end_and_stop(tmp_path: Path) -> None:
    # Arrange
    settings = tmp_path / ".claude" / "settings.json"

    # Act
    plan = plan_claude(settings, PREFIX)

    # Assert
    after = json.loads(plan.after_text)
    assert plan.existed is False
    assert plan.before_sha256 is None
    assert plan.changed is True
    assert plan.target == "claude-code"
    assert after == {
        "hooks": {
            "SessionEnd": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": CLAUDE_SESSION_END,
                            "timeout": 10,
                        }
                    ]
                }
            ],
            "Stop": [
                {"hooks": [{"type": "command", "command": CLAUDE_STOP, "timeout": 10}]}
            ],
        }
    }
    assert [entry["event"] for entry in plan.added] == ["SessionEnd", "Stop"]
    assert plan.after_text.endswith("}\n")


@pytest.mark.usefixtures("no_managed")
def test_plan_claude_preserves_every_unrelated_key_and_hook(tmp_path: Path) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    raw = write_json(settings, UNRELATED_CLAUDE)

    # Act
    plan = plan_claude(settings, PREFIX)

    # Assert
    after = json.loads(plan.after_text)
    assert plan.existed is True
    assert plan.before_sha256 == hashlib.sha256(raw).hexdigest()
    assert after["model"] == "opus"
    assert after["enabledPlugins"] == {"senior-dev@skills": True}
    assert after["hooks"]["PreToolUse"] == UNRELATED_CLAUDE["hooks"]["PreToolUse"]  # type: ignore[index]
    assert after["hooks"]["Stop"][0] == {
        "hooks": [{"type": "command", "command": "say done"}]
    }
    assert commands_in(after["hooks"]["Stop"]) == ["say done", CLAUDE_STOP]
    assert commands_in(after["hooks"]["SessionEnd"]) == [CLAUDE_SESSION_END]


@pytest.mark.usefixtures("no_managed")
def test_plan_claude_skips_events_whose_command_is_already_present(
    tmp_path: Path,
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    write_json(
        settings,
        {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {"type": "command", "command": CLAUDE_STOP, "timeout": 30}
                        ]
                    }
                ]
            }
        },
    )

    # Act
    plan = plan_claude(settings, PREFIX)

    # Assert
    assert [entry["event"] for entry in plan.added] == ["SessionEnd"]
    assert commands_in(json.loads(plan.after_text)["hooks"]["Stop"]) == [CLAUDE_STOP]


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (b"{not json", "invalid_json"),
        (b"", "invalid_json"),
        (b'{"a": 1, "a": 2}', "invalid_json"),
        (b"[1, 2]", "not_object"),
        (b'{"hooks": []}', "not_object"),
        (b'{"hooks": {"Stop": {"oops": true}}}', "not_object"),
    ],
)
@pytest.mark.usefixtures("no_managed")
def test_plan_claude_refuses_unmergeable_files(
    tmp_path: Path, content: bytes, reason: str
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    settings.write_bytes(content)

    # Act
    with pytest.raises(SettingsRefused) as excinfo:
        plan_claude(settings, PREFIX)

    # Assert
    assert excinfo.value.reason == reason
    assert str(settings) in str(excinfo.value)
    assert settings.read_bytes() == content


@pytest.mark.parametrize(
    ("policy", "refused"),
    [
        (b'{"allowManagedHooksOnly": true}', True),
        (b'{"allowManagedHooksOnly": false, "model": "x"}', False),
        (b"{corrupt", True),
    ],
)
def test_plan_claude_honours_enterprise_managed_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, policy: bytes, refused: bool
) -> None:
    # Arrange
    managed = tmp_path / "managed-settings.json"
    managed.write_bytes(policy)
    monkeypatch.setattr(
        sm, "MANAGED_SETTINGS_PATHS", (tmp_path / "absent.json", managed)
    )
    settings = tmp_path / "settings.json"

    # Act / Assert
    if refused:
        with pytest.raises(SettingsRefused) as excinfo:
            plan_claude(settings, PREFIX)
        assert excinfo.value.reason == "managed"
    else:
        assert plan_claude(settings, PREFIX).changed is True


@pytest.mark.usefixtures("no_managed")
def test_plan_claude_refuses_a_file_owned_by_another_user(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    write_json(settings, {})
    monkeypatch.setattr(os, "getuid", lambda: settings.stat().st_uid + 1)

    # Act
    with pytest.raises(SettingsRefused) as excinfo:
        plan_claude(settings, PREFIX)

    # Assert
    assert excinfo.value.reason == "not_owner"


@pytest.mark.usefixtures("no_managed")
def test_plan_claude_follows_symlinks_and_apply_keeps_the_link(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    target = tmp_path / "dotfiles" / "claude-settings.json"
    write_json(target, {"model": "opus"})
    link = tmp_path / ".claude" / "settings.json"
    link.parent.mkdir()
    link.symlink_to(target)

    # Act
    plan = plan_claude(link, PREFIX)
    apply(plan, home, now=NOW)

    # Assert
    assert plan.file == target.resolve()
    assert link.is_symlink()
    assert json.loads(target.read_text())["model"] == "opus"
    assert CLAUDE_STOP in commands_in(json.loads(target.read_text()))


def test_command_prefix_quotes_paths_with_spaces() -> None:
    # Arrange
    executable = Path("/Users/me/My Tools/agent-meter")

    # Act
    prefix = command_prefix(executable)

    # Assert
    assert prefix == "'/Users/me/My Tools/agent-meter'"


# --------------------------------------------------------------------------- plan_antigravity


def test_plan_antigravity_creates_a_named_hook_without_top_level_scalars(
    tmp_path: Path,
) -> None:
    # Arrange
    hooks = tmp_path / ".gemini" / "config" / "hooks.json"

    # Act
    plan = plan_antigravity(hooks, PREFIX)

    # Assert
    after = json.loads(plan.after_text)
    assert plan.target == "antigravity"
    assert after == {
        "agent-meter": {
            "enabled": True,
            "Stop": [{"type": "command", "command": AGY_STOP, "timeout": 10}],
        }
    }
    assert all(isinstance(value, dict) for value in after.values())


def test_plan_antigravity_preserves_unrelated_named_hooks(tmp_path: Path) -> None:
    # Arrange
    hooks = tmp_path / "hooks.json"
    write_json(hooks, UNRELATED_AGY)

    # Act
    plan = plan_antigravity(hooks, PREFIX)

    # Assert
    after = json.loads(plan.after_text)
    assert after["rtk"] == UNRELATED_AGY["rtk"]
    assert list(after) == ["rtk", "agent-meter"]


def test_plan_antigravity_uses_a_free_name_when_agent_meter_is_taken(
    tmp_path: Path,
) -> None:
    # Arrange
    hooks = tmp_path / "hooks.json"
    write_json(hooks, {"agent-meter": {"enabled": False, "Stop": []}})

    # Act
    plan = plan_antigravity(hooks, PREFIX)

    # Assert
    after = json.loads(plan.after_text)
    assert after["agent-meter"] == {"enabled": False, "Stop": []}
    assert commands_in(after["agent-meter-2"]) == [AGY_STOP]
    assert plan.added[0]["name"] == "agent-meter-2"


def test_plan_antigravity_is_idempotent_when_command_exists_in_any_named_hook(
    tmp_path: Path,
) -> None:
    # Arrange
    hooks = tmp_path / "hooks.json"
    raw = write_json(
        hooks,
        {"mine": {"enabled": True, "Stop": [{"type": "command", "command": AGY_STOP}]}},
    )

    # Act
    plan = plan_antigravity(hooks, PREFIX)

    # Assert
    assert plan.changed is False
    assert plan.added == ()
    assert plan.after_text.encode() == raw


@pytest.mark.parametrize(
    "content",
    [b'{"description": "plugin hooks"}', b"[]", b"{bad"],
)
def test_plan_antigravity_refuses_files_antigravity_cannot_load(
    tmp_path: Path, content: bytes
) -> None:
    # Arrange
    hooks = tmp_path / "hooks.json"
    hooks.write_bytes(content)

    # Act / Assert
    with pytest.raises(SettingsRefused) as excinfo:
        plan_antigravity(hooks, PREFIX)
    assert excinfo.value.reason in {"not_object", "invalid_json"}


# --------------------------------------------------------------------------- apply


@pytest.mark.usefixtures("no_managed")
def test_apply_backs_up_original_bytes_then_writes_atomically_and_records_manifest(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    original = write_json(settings, UNRELATED_CLAUDE, indent=4)
    settings.chmod(0o640)
    plan = plan_claude(settings, PREFIX)

    # Act
    apply(plan, home, now=NOW)

    # Assert
    written = settings.read_bytes()
    assert written == plan.after_text.encode()
    assert stat.S_IMODE(settings.stat().st_mode) == 0o640
    backups = list(home.backups_dir.iterdir())
    assert [b.name for b in backups] == ["claude-code-20261016T184207123456Z.json"]
    assert backups[0].read_bytes() == original
    assert stat.S_IMODE(backups[0].stat().st_mode) == 0o600
    record = manifest(home)
    assert record["version"] == 1
    assert record["files"] == [
        {
            "path": str(settings.resolve()),
            "backup": str(backups[0]),
            "existed": True,
            "post_sha256": hashlib.sha256(written).hexdigest(),
            "entries": list(plan.added),
        }
    ]
    assert not list(tmp_path.glob(".settings.json.*"))


def test_apply_on_absent_file_writes_absent_marker_and_creates_parents(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    hooks = tmp_path / ".gemini" / "config" / "hooks.json"
    plan = plan_antigravity(hooks, PREFIX)

    # Act
    apply(plan, home, now=NOW)

    # Assert
    assert json.loads(hooks.read_text()) == json.loads(plan.after_text)
    backup = Path(str(manifest(home)["files"][0]["backup"]))  # type: ignore[index]
    assert backup.name == "antigravity-20261016T184207123456Z.absent"
    assert backup.read_bytes() == b""
    assert manifest(home)["files"][0]["existed"] is False  # type: ignore[index]


@pytest.mark.usefixtures("no_managed")
def test_apply_of_unchanged_plan_writes_nothing(tmp_path: Path, home: FakeHome) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    apply(plan_claude(settings, PREFIX), home, now=NOW)
    before = settings.read_bytes()
    second = plan_claude(settings, PREFIX)

    # Act
    apply(second, home, now=NOW)

    # Assert
    assert second.changed is False
    assert settings.read_bytes() == before
    assert len(list(home.backups_dir.iterdir())) == 1
    assert len(manifest(home)["files"]) == 1  # type: ignore[arg-type]


@pytest.mark.usefixtures("no_managed")
def test_apply_refuses_a_stale_plan(tmp_path: Path, home: FakeHome) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    write_json(settings, {"model": "opus"})
    plan = plan_claude(settings, PREFIX)
    edited = write_json(settings, {"model": "sonnet"})

    # Act
    with pytest.raises(PlanStale):
        apply(plan, home, now=NOW)

    # Assert
    assert settings.read_bytes() == edited
    assert not home.backups_dir.exists() or not list(home.backups_dir.iterdir())
    assert not home.install_manifest.exists()


@pytest.mark.usefixtures("no_managed")
def test_apply_never_overwrites_an_existing_backup(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    home.backups_dir.mkdir()
    taken = home.backups_dir / "claude-code-20261016T184207123456Z.json"
    taken.write_bytes(b"older backup")
    settings = tmp_path / "settings.json"
    write_json(settings, {})

    # Act
    apply(plan_claude(settings, PREFIX), home, now=NOW)

    # Assert
    assert taken.read_bytes() == b"older backup"
    assert len(list(home.backups_dir.iterdir())) == 2


# --------------------------------------------------------------------------- preview


@pytest.mark.usefixtures("no_managed")
def test_render_preview_shows_the_exact_json_added_and_the_backup_location(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    write_json(settings, UNRELATED_CLAUDE)
    plan = plan_claude(settings, PREFIX)

    # Act
    text = render_preview(plan, home)

    # Assert
    assert str(settings.resolve()) in text
    assert "hooks.SessionEnd[]" in text
    assert "hooks.Stop[]" in text
    assert f'+            "command": "{CLAUDE_STOP}",' in text
    assert str(home.backups_dir) in text
    assert '"say done"' not in [
        line[1:].strip() for line in text.splitlines() if line.startswith("+")
    ]


@pytest.mark.usefixtures("no_managed")
def test_render_preview_of_unchanged_plan_says_no_changes(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    apply(plan_claude(settings, PREFIX), home, now=NOW)

    # Act
    text = render_preview(plan_claude(settings, PREFIX), home)

    # Assert
    assert "no changes" in text


# --------------------------------------------------------------------------- uninstall (BR-19)


@pytest.mark.usefixtures("no_managed")
def test_uninstall_restores_original_bytes_when_file_is_unchanged(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    original = b'{\n    "model":   "opus"\n}'
    settings.write_bytes(original)
    apply(plan_claude(settings, PREFIX), home, now=NOW)

    # Act
    actions = uninstall(home)

    # Assert
    assert settings.read_bytes() == original
    assert any("restored" in action for action in actions)
    assert not home.install_manifest.exists()


def test_uninstall_deletes_a_file_that_did_not_exist_before_setup(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    hooks = tmp_path / ".gemini" / "config" / "hooks.json"
    apply(plan_antigravity(hooks, PREFIX), home, now=NOW)

    # Act
    actions = uninstall(home)

    # Assert
    assert not hooks.exists()
    assert any("removed" in action for action in actions)


@pytest.mark.usefixtures("no_managed")
def test_uninstall_after_user_edit_removes_only_our_entries_and_keeps_backup(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    write_json(settings, {"model": "opus"})
    apply(plan_claude(settings, PREFIX), home, now=NOW)
    edited = json.loads(settings.read_text())
    edited["theme"] = "dark"
    edited["hooks"]["Stop"].append(
        {"hooks": [{"type": "command", "command": "say later"}]}
    )
    write_json(settings, edited)
    backup = Path(str(manifest(home)["files"][0]["backup"]))  # type: ignore[index]

    # Act
    actions = uninstall(home)

    # Assert
    after = json.loads(settings.read_text())
    assert after == {
        "model": "opus",
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "say later"}]}]},
        "theme": "dark",
    }
    assert backup.exists()
    assert any("removed agent-meter entries" in action for action in actions)


@pytest.mark.usefixtures("no_managed")
def test_uninstall_after_user_edit_drops_containers_we_created(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    write_json(settings, {"model": "opus"})
    apply(plan_claude(settings, PREFIX), home, now=NOW)
    edited = json.loads(settings.read_text())
    edited["theme"] = "dark"
    write_json(settings, edited)

    # Act
    uninstall(home)

    # Assert
    assert json.loads(settings.read_text()) == {"model": "opus", "theme": "dark"}


@pytest.mark.usefixtures("no_managed")
def test_uninstall_keeps_containers_that_existed_before_setup(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    write_json(settings, {"hooks": {"Stop": []}})
    apply(plan_claude(settings, PREFIX), home, now=NOW)
    edited = json.loads(settings.read_text())
    edited["theme"] = "dark"
    write_json(settings, edited)

    # Act
    uninstall(home)

    # Assert
    assert json.loads(settings.read_text()) == {"hooks": {"Stop": []}, "theme": "dark"}


def test_uninstall_after_user_edit_of_antigravity_file_keeps_their_named_hooks(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    hooks = tmp_path / "hooks.json"
    apply(plan_antigravity(hooks, PREFIX), home, now=NOW)
    edited = json.loads(hooks.read_text())
    edited.update(UNRELATED_AGY)
    write_json(hooks, edited)

    # Act
    uninstall(home)

    # Assert
    assert json.loads(hooks.read_text()) == UNRELATED_AGY


@pytest.mark.usefixtures("no_managed")
def test_uninstall_skips_a_file_that_became_invalid_and_keeps_its_record(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    apply(plan_claude(settings, PREFIX), home, now=NOW)
    settings.write_bytes(b"{broken")

    # Act
    actions = uninstall(home)

    # Assert
    assert settings.read_bytes() == b"{broken"
    assert any(
        "skipped" in action and str(settings.resolve()) in action for action in actions
    )
    assert len(manifest(home)["files"]) == 1  # type: ignore[arg-type]


@pytest.mark.usefixtures("no_managed")
def test_uninstall_skips_a_file_the_user_deleted(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    write_json(settings, {})
    apply(plan_claude(settings, PREFIX), home, now=NOW)
    settings.unlink()

    # Act
    actions = uninstall(home)

    # Assert
    assert not settings.exists()
    assert any("no longer exists" in action for action in actions)


@pytest.mark.usefixtures("no_managed")
def test_uninstall_after_resetup_never_resurrects_our_own_entries(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange: user removes our Stop entry, setup runs again and re-adds only Stop.
    settings = tmp_path / "settings.json"
    write_json(settings, {"model": "opus"})
    apply(plan_claude(settings, PREFIX), home, now=NOW)
    edited = json.loads(settings.read_text())
    del edited["hooks"]["Stop"]
    write_json(settings, edited)
    apply(plan_claude(settings, PREFIX), home, now=datetime(2026, 10, 17, tzinfo=UTC))

    # Act
    uninstall(home)

    # Assert
    assert commands_in(json.loads(settings.read_text())) == []
    assert len(list(home.backups_dir.iterdir())) == 2


def test_uninstall_without_manifest_is_a_no_op(home: FakeHome) -> None:
    # Arrange / Act
    actions = uninstall(home)

    # Assert
    assert actions == []


@pytest.mark.usefixtures("no_managed")
def test_uninstall_preserves_scheduler_record(tmp_path: Path, home: FakeHome) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    apply(plan_claude(settings, PREFIX), home, now=NOW)
    record = manifest(home)
    record["scheduler"] = {"kind": "launchd", "path": "/x.plist"}
    home.install_manifest.write_text(json.dumps(record))

    # Act
    uninstall(home)

    # Assert
    assert manifest(home) == {
        "version": 1,
        "files": [],
        "scheduler": {"kind": "launchd", "path": "/x.plist"},
    }


# --------------------------------------------------------------------------- doctor helper


@pytest.mark.usefixtures("no_managed")
def test_registration_status_reports_registered_partial_absent_unreadable(
    tmp_path: Path,
) -> None:
    # Arrange
    claude = tmp_path / "settings.json"
    agy = tmp_path / "hooks.json"
    broken = tmp_path / "broken.json"
    broken.write_bytes(b"{")
    write_json(claude, json.loads(plan_claude(claude, PREFIX).after_text))
    partial = tmp_path / "partial.json"
    write_json(
        partial,
        {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": CLAUDE_STOP}]}]}},
    )

    # Act / Assert
    assert registration_status(claude, "claude-code") == "registered"
    assert registration_status(partial, "claude-code") == "partial"
    assert registration_status(agy, "antigravity") == "absent"
    assert registration_status(broken, "claude-code") == "unreadable"
    write_json(
        agy, json.loads(plan_antigravity(agy, "/elsewhere/agent-meter").after_text)
    )
    assert registration_status(agy, "antigravity") == "registered"


def test_merge_plan_is_frozen(tmp_path: Path) -> None:
    # Arrange
    plan = plan_antigravity(tmp_path / "hooks.json", PREFIX)

    # Act / Assert
    assert isinstance(plan, MergePlan)
    with pytest.raises(AttributeError):
        plan.changed = False  # type: ignore[misc]
    assert os.fspath(plan.file).endswith("hooks.json")
