"""Actuators: change one known setting of a host, after a preview, with undo and a record of the change.

Only the keys in ``ACTIONS`` can be changed, to the values listed there. Each change reuses the rules
of ``settings_merge``: valid JSON only, a backup of the original bytes, an atomic write and a refusal
when the file changed after the preview. ``~/.gemini/settings.json`` belongs to Gemini CLI and is
never a target. Open and resumed sessions can keep their current model, so changes are described as
applying to new sessions.
"""

from __future__ import annotations

import copy
import difflib
import json
import os
import shlex
import shutil
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from agent_meter.paths import AppHome, atomic_write_text
from agent_meter.setup import hosts, settings_merge
from agent_meter.setup._files import atomic_write, sha256_hex

__all__ = ["ACTIONS", "ERROR_CODES", "Action", "ActuatorError", "ChangePlan", "action_options", "apply_change", "current_value", "list_changes",
           "plan_change", "target_paths", "undo_change"]

CHANGES_NAME: Final = "changes.json"
_NEW_FILE_MODE: Final = 0o600
_EFFORTS: Final = ("low", "medium", "high", "xhigh")


ERROR_CODES: Final = ("already_undone", "changed_since", "managed", "no_change", "not_installed", "refused", "stale",
                      "unknown_action", "unknown_change", "unknown_value")


class ActuatorError(Exception):
    """``code`` is stable, so the app can explain the refusal in the user's language."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


@dataclass(frozen=True, slots=True)
class Action:
    id: str
    target: str  # a key of ``target_paths``
    key: tuple[str, ...]
    values: tuple[str, ...]  # empty when the choices come from the user's own data
    command_object: bool = False  # stored as {"type": "command", "command": value}


ACTIONS: Final[dict[str, Action]] = {
    action.id: action
    for action in (
        Action("claude.model", "claude", ("model",), ("opus", "sonnet", "haiku")),
        # The top-level effortLevel does not count for Opus 5.5, so effort is set per model.
        Action("claude.effort.opus", "claude", ("modelSettings", "claude-opus-5-5", "effortLevel"), _EFFORTS),
        Action("claude.effort.sonnet", "claude", ("modelSettings", "claude-sonnet-5-5", "effortLevel"), _EFFORTS),
        Action("claude.autocompact", "claude", ("env", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"), ("60", "70", "80")),
        Action("claude.statusline", "claude", ("statusLine",), (), command_object=True),
        Action("antigravity.model", "antigravity", ("model",), ()),
    )
}


@dataclass(frozen=True, slots=True)
class ChangePlan:
    action: Action
    file: Path
    before_sha256: str | None
    after_text: str
    old_value: str | None
    new_value: str
    diff: str
    changed: bool


def target_paths() -> dict[str, Path]:
    user_home = Path(os.environ.get("HOME") or Path.home())
    return {
        "claude": hosts.claude_settings_path(user_home, os.environ),
        "antigravity": user_home / ".gemini" / "antigravity-cli" / "settings.json",
    }


def _read_key(data: dict[str, Any], key: tuple[str, ...]) -> str | None:
    node: Any = data
    for part in key:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    if isinstance(node, dict) and node.get("type") == "command":
        node = node.get("command")
    return None if node is None else str(node)


def statusline_command() -> str | None:
    """The status line runs the installed command, which the packaged app alone does not provide."""
    binary = shutil.which("agent-meter")
    if binary is None:
        return None
    quoted = f'"{binary}"' if os.name == "nt" else shlex.quote(binary)
    return f"{quoted} statusline"


def action_options(action: Action, observed: Sequence[str] = ()) -> tuple[str, ...]:
    if action.command_object:
        command = statusline_command()
        return () if command is None else (command,)
    return action.values or tuple(observed)


def _store_value(action: Action, value: str) -> str | dict[str, str]:
    return {"type": "command", "command": value} if action.command_object else value


def _write_key(data: dict[str, Any], key: tuple[str, ...], value: str | dict[str, str]) -> None:
    node = data
    for part in key[:-1]:
        child = node.setdefault(part, {})
        if not isinstance(child, dict):
            raise ActuatorError("refused", f"{part} is not an object")
        node = child
    node[key[-1]] = value


def _remove_key(data: dict[str, Any], key: tuple[str, ...]) -> None:
    """Remove the key and any parent left empty, which is what the change created."""
    parents = [data]
    for part in key[:-1]:
        parents.append(parents[-1][part])
    del parents[-1][key[-1]]
    for parent, part in zip(reversed(parents[:-1]), reversed(key[:-1]), strict=True):
        if parent[part]:
            break
        del parent[part]


def _load(path: Path) -> tuple[Path, bytes | None, dict[str, Any]]:
    try:
        real, raw = settings_merge._read_target(path)
        return real, raw, settings_merge._parse_object(real, raw)
    except settings_merge.SettingsRefused as exc:
        raise ActuatorError("refused", str(exc)) from exc


def _check_managed(real: Path, action: Action) -> None:
    if action.target != "claude":
        return
    try:
        settings_merge._check_managed_policy(real)
    except settings_merge.SettingsRefused as exc:
        raise ActuatorError("managed", str(exc)) from exc
    for policy in settings_merge.MANAGED_SETTINGS_PATHS:
        if not policy.exists():
            continue
        data = settings_merge._loads_object(policy.read_bytes())
        if isinstance(data, dict) and _read_key(data, action.key) is not None:
            raise ActuatorError("managed", f"{policy} sets {'.'.join(action.key)}")


def current_value(action: Action) -> str | None:
    """The value now in the host's file, or ``None`` when it is unset or the file cannot be read."""
    path = target_paths()[action.target]
    try:
        return _read_key(_load(path)[2], action.key)
    except ActuatorError:
        return None


def _diff(before: dict[str, Any], after: dict[str, Any], path: Path) -> str:
    lines = difflib.unified_diff(
        settings_merge._dump(before).splitlines(), settings_merge._dump(after).splitlines(),
        fromfile=str(path), tofile=str(path), lineterm="", n=1,
    )
    return "\n".join(lines)


def plan_change(action_id: str, value: str, *, observed: Sequence[str] = ()) -> ChangePlan:
    """Pure: reads the file and shows the change. ``observed`` lists choices taken from the user's data."""
    action = ACTIONS.get(action_id)
    if action is None:
        raise ActuatorError("unknown_action", action_id)
    if value not in action_options(action, observed):
        raise ActuatorError("unknown_value", value)
    path = target_paths()[action.target]
    if action.target == "antigravity" and not path.exists():
        raise ActuatorError("not_installed", str(path))
    real, raw, data = _load(path)
    _check_managed(real, action)
    after = copy.deepcopy(data)
    _write_key(after, action.key, _store_value(action, value))
    old = _read_key(data, action.key)
    return ChangePlan(
        action=action, file=real, before_sha256=None if raw is None else sha256_hex(raw),
        after_text=settings_merge._dump(after), old_value=old, new_value=value, diff=_diff(data, after, real),
        changed=old != value,
    )


def _changes_path(home: AppHome) -> Path:
    return home.root / CHANGES_NAME


def list_changes(home: AppHome) -> list[dict[str, Any]]:
    """Newest first."""
    try:
        found: list[dict[str, Any]] = json.loads(_changes_path(home).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    return list(reversed(found))


def _save_changes(home: AppHome, changes: list[dict[str, Any]]) -> None:
    """``changes`` is newest first, as ``list_changes`` returns it."""
    atomic_write_text(_changes_path(home), json.dumps(list(reversed(changes)), indent=1))


def _read_raw(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _write_settings(path: Path, payload: bytes, raw: bytes | None) -> None:
    mode = _NEW_FILE_MODE if raw is None else stat.S_IMODE(path.stat().st_mode)
    atomic_write(path, payload, mode=mode)


def apply_change(plan: ChangePlan, home: AppHome, *, now: datetime | None = None) -> dict[str, Any]:
    if not plan.changed:
        raise ActuatorError("no_change")
    moment = now or datetime.now(UTC)
    raw = _read_raw(plan.file)
    if (None if raw is None else sha256_hex(raw)) != plan.before_sha256:
        raise ActuatorError("stale", str(plan.file))
    backup = settings_merge._write_backup(home, plan.action.target, raw, moment)
    payload = plan.after_text.encode("utf-8")
    _write_settings(plan.file, payload, raw)
    changes = list_changes(home)
    change = {
        "id": f"{moment.strftime('%Y%m%dT%H%M%S%f')}-{len(changes)}", "action": plan.action.id, "file": str(plan.file),
        "applied_at": moment.isoformat(), "old_value": plan.old_value, "new_value": plan.new_value,
        "backup": str(backup), "file_existed": raw is not None, "after_sha256": sha256_hex(payload), "undone_at": None,
    }
    _save_changes(home, [change, *changes])
    return change


def _revert_key(change: dict[str, Any], action: Action, path: Path, raw: bytes | None) -> None:
    """The file has other edits since the change, so put back only the key that changed."""
    _real, _raw, data = _load(path)
    if _read_key(data, action.key) != change["new_value"]:
        raise ActuatorError("changed_since", str(path))
    if change["old_value"] is None:
        _remove_key(data, action.key)
    else:
        _write_key(data, action.key, _store_value(action, str(change["old_value"])))
    _write_settings(path, settings_merge._dump(data).encode("utf-8"), raw)


def undo_change(change_id: str, home: AppHome, *, now: datetime | None = None) -> dict[str, Any]:
    changes = list_changes(home)
    change = next((c for c in changes if c["id"] == change_id), None)
    if change is None:
        raise ActuatorError("unknown_change", change_id)
    if change["undone_at"] is not None:
        raise ActuatorError("already_undone", change_id)
    path = Path(change["file"])
    raw = _read_raw(path)
    if raw is not None and sha256_hex(raw) == change["after_sha256"]:
        if change["file_existed"]:
            _write_settings(path, Path(change["backup"]).read_bytes(), raw)
        else:
            path.unlink()
    else:
        _revert_key(change, ACTIONS[change["action"]], path, raw)
    change["undone_at"] = (now or datetime.now(UTC)).isoformat()
    _save_changes(home, changes)
    return change
