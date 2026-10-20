"""Consent-first merge of agent-meter hooks into host settings files (ADR §3.10, BR-18/19).

Files touched (and no others):
- Claude Code ``~/.claude/settings.json`` (or ``$CLAUDE_CONFIG_DIR/settings.json``): one matcher
  group each under ``hooks.SessionEnd[]`` and ``hooks.Stop[]``.
- Antigravity ``~/.gemini/config/hooks.json``: one named hook with a ``Stop`` handler list.
  ``~/.gemini/settings.json`` belongs to Gemini CLI and is never edited.

Rules:
- ``plan_*`` is pure: it reads the file (following symlinks) and returns a ``MergePlan`` showing
  the exact JSON to add. It refuses invalid JSON, non-object roots, files owned by another
  user and enterprise-managed Claude policies (``SettingsRefused``); the caller then offers
  scheduler-only.
- ``apply`` backs the file up (0600) before writing, writes atomically and records the change
  in ``install.json``. A plan whose file changed since planning raises ``PlanStale``.
- ``uninstall`` restores the backup byte-for-byte only when the file is unchanged since setup,
  otherwise removes exactly the recorded entries and keeps the user's later edits (BR-19).
"""

from __future__ import annotations

import copy
import difflib
import json
import os
import shlex
import stat
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal

from agent_meter.setup._files import (
    MANIFEST_VERSION,
    HomeLike,
    atomic_write,
    load_manifest,
    save_manifest,
    sha256_hex,
)

__all__ = [
    "ANTIGRAVITY_HOOK_NAME",
    "HOOK_TIMEOUT_S",
    "MANAGED_SETTINGS_PATHS",
    "MergePlan",
    "PlanStale",
    "RefusalReason",
    "RegistrationStatus",
    "SettingsRefused",
    "Target",
    "antigravity_command",
    "apply",
    "claude_commands",
    "command_prefix",
    "plan_antigravity",
    "plan_claude",
    "registration_status",
    "render_preview",
    "uninstall",
]

Target = Literal["claude-code", "antigravity"]
RefusalReason = Literal["invalid_json", "not_object", "managed", "not_owner"]
RegistrationStatus = Literal["registered", "partial", "absent", "unreadable"]

HOOK_TIMEOUT_S: Final = 10
ANTIGRAVITY_HOOK_NAME: Final = "agent-meter"
MANAGED_SETTINGS_PATHS: tuple[Path, ...] = (
    Path("/Library/Application Support/ClaudeCode/managed-settings.json"),
    Path("/etc/claude-code/managed-settings.json"),
    Path("C:/ProgramData/ClaudeCode/managed-settings.json"),
)
_NEW_FILE_MODE: Final = 0o600
_CLAUDE_EVENTS: Final = (("SessionEnd", "session-end"), ("Stop", "task-end"))
_CLAUDE_SUFFIXES: Final = {
    event: f" hook --host claude-code --event {flag}" for event, flag in _CLAUDE_EVENTS
}
_ANTIGRAVITY_SUFFIX: Final = " hook --host antigravity --event task-end"


@dataclass(frozen=True, slots=True)
class MergePlan:
    file: Path
    existed: bool
    before_sha256: str | None
    after_text: str
    added: tuple[dict[str, Any], ...]
    changed: bool
    target: Target


class SettingsRefused(Exception):
    """The file must not be edited; the wizard offers scheduler-only instead (BR-18)."""

    def __init__(self, reason: RefusalReason, file: Path, detail: str) -> None:
        super().__init__(f"refusing to edit {file}: {detail}")
        self.reason: RefusalReason = reason
        self.file = file


class PlanStale(RuntimeError):
    """The file changed between ``plan_*`` and ``apply``; plan again and re-confirm."""


class _DuplicateKey(ValueError):
    pass


# --------------------------------------------------------------------------- commands


def command_prefix(executable: Path) -> str:
    """Shell-safe absolute executable used at the start of every hook command."""
    if os.name == "nt":
        return subprocess.list2cmdline([str(executable)])
    return shlex.quote(str(executable))


def claude_commands(prefix: str) -> dict[str, str]:
    """Hook command per Claude Code event (``SessionEnd`` → session-end, ``Stop`` → task-end)."""
    return {event: f"{prefix}{suffix}" for event, suffix in _CLAUDE_SUFFIXES.items()}


def antigravity_command(prefix: str) -> str:
    return f"{prefix}{_ANTIGRAVITY_SUFFIX}"


def _handler(command: str) -> dict[str, Any]:
    return {"type": "command", "command": command, "timeout": HOOK_TIMEOUT_S}


# --------------------------------------------------------------------------- reading


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(f"duplicate key {key!r}")
        result[key] = value
    return result


def _loads_object(raw: bytes) -> object:
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicates)


def _read_target(path: Path) -> tuple[Path, bytes | None]:
    real = Path(os.path.realpath(path))
    try:
        st = real.stat()
    except FileNotFoundError:
        return real, None
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        raise SettingsRefused("not_owner", real, "the file is owned by another user")
    return real, real.read_bytes()


def _parse_object(real: Path, raw: bytes | None) -> dict[str, Any]:
    if raw is None:
        return {}
    try:
        data = _loads_object(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise SettingsRefused("invalid_json", real, f"not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise SettingsRefused("not_object", real, "the JSON root is not an object")
    return data


def _check_managed_policy(real: Path) -> None:
    for policy in MANAGED_SETTINGS_PATHS:
        if real == Path(os.path.realpath(policy)):
            raise SettingsRefused(
                "managed", real, "this is an enterprise-managed settings file"
            )
        if not policy.exists():
            continue
        try:
            data = _loads_object(policy.read_bytes())
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise SettingsRefused(
                "managed", real, f"managed policy {policy} cannot be verified ({exc})"
            ) from exc
        if isinstance(data, dict) and data.get("allowManagedHooksOnly") is True:
            raise SettingsRefused(
                "managed", real, f"managed policy {policy} sets allowManagedHooksOnly"
            )


def _commands_in(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        command = obj.get("command")
        if isinstance(command, str):
            found.append(command)
        for value in obj.values():
            found.extend(_commands_in(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_commands_in(item))
    return found


def _dump(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _build_plan(
    target: Target,
    real: Path,
    raw: bytes | None,
    after: dict[str, Any],
    added: list[dict[str, Any]],
) -> MergePlan:
    changed = bool(added)
    after_text = _dump(after) if changed else (raw or b"").decode("utf-8")
    return MergePlan(
        file=real,
        existed=raw is not None,
        before_sha256=None if raw is None else sha256_hex(raw),
        after_text=after_text,
        added=tuple(added),
        changed=changed,
        target=target,
    )


# --------------------------------------------------------------------------- planning


def _check_claude_shape(
    real: Path, data: dict[str, Any], events: Iterable[str]
) -> None:
    hooks = data.get("hooks")
    if "hooks" in data and not isinstance(hooks, dict):
        raise SettingsRefused("not_object", real, "'hooks' is not an object")
    for event in events:
        if (
            isinstance(hooks, dict)
            and event in hooks
            and not isinstance(hooks[event], list)
        ):
            raise SettingsRefused("not_object", real, f"'hooks.{event}' is not a list")


def _add_claude_event(
    after: dict[str, Any], event: str, command: str
) -> dict[str, Any] | None:
    """Append one matcher group for ``event`` unless ``command`` is already registered there."""
    created: list[str] = []
    hooks = after.get("hooks")
    if not isinstance(hooks, dict):
        hooks = after["hooks"] = {}
        created.append("hooks")
    handlers = hooks.get(event)
    if isinstance(handlers, list) and command in _commands_in(handlers):
        return None
    if not isinstance(handlers, list):
        handlers = hooks[event] = []
        created.append(f"hooks.{event}")
    group = {"hooks": [_handler(command)]}
    handlers.append(group)
    return {
        "kind": "claude-code",
        "event": event,
        "command": command,
        "value": copy.deepcopy(group),
        "created": created,
    }


def plan_claude(settings_path: Path, command_prefix: str) -> MergePlan:
    """Plan the Claude Code ``SessionEnd`` + ``Stop`` hook registration (idempotent)."""
    real, raw = _read_target(settings_path)
    _check_managed_policy(real)
    data = _parse_object(real, raw)
    commands = claude_commands(command_prefix)
    _check_claude_shape(real, data, commands)
    after = copy.deepcopy(data)
    added = [
        entry
        for event, command in commands.items()
        if (entry := _add_claude_event(after, event, command)) is not None
    ]
    return _build_plan("claude-code", real, raw, after, added)


def _free_hook_name(data: dict[str, Any]) -> str:
    if ANTIGRAVITY_HOOK_NAME not in data:
        return ANTIGRAVITY_HOOK_NAME
    suffix = 2
    while f"{ANTIGRAVITY_HOOK_NAME}-{suffix}" in data:
        suffix += 1
    return f"{ANTIGRAVITY_HOOK_NAME}-{suffix}"


def plan_antigravity(hooks_path: Path, command_prefix: str) -> MergePlan:
    """Plan the Antigravity named ``Stop`` hook in ``~/.gemini/config/hooks.json`` (idempotent)."""
    real, raw = _read_target(hooks_path)
    data = _parse_object(real, raw)
    for key, value in data.items():
        if not isinstance(value, dict):
            raise SettingsRefused(
                "not_object",
                real,
                f"top-level key {key!r} is not a named-hook object; Antigravity rejects such files",
            )
    command = antigravity_command(command_prefix)
    if any(command in _commands_in(spec.get("Stop")) for spec in data.values()):
        return _build_plan("antigravity", real, raw, data, [])

    name = _free_hook_name(data)
    spec = {"enabled": True, "Stop": [_handler(command)]}
    after = copy.deepcopy(data)
    after[name] = spec
    entry = {
        "kind": "antigravity",
        "name": name,
        "command": command,
        "value": copy.deepcopy(spec),
    }
    return _build_plan("antigravity", real, raw, after, [entry])


# --------------------------------------------------------------------------- preview


def _entry_location(entry: dict[str, Any]) -> str:
    if entry.get("kind") == "claude-code":
        return f"hooks.{entry['event']}[]"
    return f"named hook {entry['name']!r}"


def render_preview(plan: MergePlan, home: HomeLike) -> str:
    """Human-readable consent preview: the exact JSON added, the backup location and a diff."""
    if not plan.changed:
        return f"{plan.file}: no changes (agent-meter hooks already registered)"
    lines = [f"{plan.file}{'' if plan.existed else ' (new file)'}"]
    if plan.existed:
        lines.append(
            f"  a backup of the current file is written to {home.backups_dir}/ first"
        )
    lines.append("  will add:")
    for entry in plan.added:
        lines.append(f"    {_entry_location(entry)}:")
        lines.extend(
            f"      {row}" for row in json.dumps(entry["value"], indent=2).splitlines()
        )
    before = plan.file.read_text(encoding="utf-8") if plan.existed else ""
    diff = difflib.unified_diff(
        before.splitlines(),
        plan.after_text.splitlines(),
        fromfile=f"{plan.file} (current)",
        tofile=f"{plan.file} (after setup)",
        lineterm="",
    )
    lines.append("  diff:")
    lines.extend(diff)
    return "\n".join(lines)


# --------------------------------------------------------------------------- apply


def _write_backup(
    home: HomeLike, plan: MergePlan, raw: bytes | None, now: datetime
) -> Path:
    home.backups_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    extension = ".json" if raw is not None else ".absent"
    attempt = 0
    while True:
        suffix = "" if attempt == 0 else f"-{attempt}"
        candidate = home.backups_dir / f"{plan.target}-{stamp}{suffix}{extension}"
        try:
            fd = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            attempt += 1
            continue
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw or b"")
            handle.flush()
            os.fsync(handle.fileno())
        return candidate


def _entry_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    location = str(entry.get("event") or entry.get("name") or "")
    return str(entry.get("kind", "")), location, str(entry.get("command", ""))


def _record_install(
    home: HomeLike, plan: MergePlan, backup: Path, post_sha256: str
) -> None:
    manifest = load_manifest(home) or {"version": MANIFEST_VERSION, "files": []}
    files: list[dict[str, Any]] = manifest["files"]
    path = str(plan.file)
    previous = next((rec for rec in files if rec.get("path") == path), None)
    entries: list[dict[str, Any]] = (
        list(previous.get("entries", [])) if previous else []
    )
    known = {_entry_key(entry) for entry in entries}
    entries.extend(entry for entry in plan.added if _entry_key(entry) not in known)
    record = {
        "path": path,
        "backup": str(backup),
        "existed": plan.existed,
        "post_sha256": post_sha256,
        "entries": entries,
    }
    manifest["files"] = [rec for rec in files if rec.get("path") != path] + [record]
    save_manifest(home, manifest)


def apply(plan: MergePlan, home: HomeLike, *, now: datetime | None = None) -> None:
    """Back up, write atomically and record the change in ``install.json``; no-op when unchanged."""
    if not plan.changed:
        return
    try:
        raw: bytes | None = plan.file.read_bytes()
    except FileNotFoundError:
        raw = None
    current_sha = None if raw is None else sha256_hex(raw)
    if current_sha != plan.before_sha256:
        raise PlanStale(
            f"{plan.file} changed after the preview was shown; run setup again"
        )
    mode = _NEW_FILE_MODE if raw is None else stat.S_IMODE(plan.file.stat().st_mode)
    backup = _write_backup(home, plan, raw, now or datetime.now(UTC))
    payload = plan.after_text.encode("utf-8")
    atomic_write(plan.file, payload, mode=mode)
    _record_install(home, plan, backup, sha256_hex(payload))


# --------------------------------------------------------------------------- uninstall


def _without_command(handlers: list[Any], command: str) -> tuple[list[Any], bool]:
    """Drop handlers running ``command`` (flat or inside matcher groups emptied by the removal)."""
    kept: list[Any] = []
    removed = False
    for item in handlers:
        if isinstance(item, dict) and item.get("command") == command:
            removed = True
            continue
        inner = item.get("hooks") if isinstance(item, dict) else None
        if isinstance(inner, list):
            remaining = [
                h
                for h in inner
                if not (isinstance(h, dict) and h.get("command") == command)
            ]
            if len(remaining) != len(inner):
                removed = True
                if not remaining:
                    continue
                item = {**item, "hooks": remaining}
        kept.append(item)
    return kept, removed


def _remove_claude_entry(data: dict[str, Any], entry: dict[str, Any]) -> bool:
    hooks = data.get("hooks")
    event = str(entry["event"])
    if not isinstance(hooks, dict) or not isinstance(hooks.get(event), list):
        return False
    hooks[event], removed = _without_command(hooks[event], str(entry["command"]))
    return removed


def _remove_antigravity_entry(data: dict[str, Any], entry: dict[str, Any]) -> bool:
    name = str(entry["name"])
    spec = data.get(name)
    if not isinstance(spec, dict) or not isinstance(spec.get("Stop"), list):
        return False
    spec["Stop"], removed = _without_command(spec["Stop"], str(entry["command"]))
    if not spec["Stop"]:
        del spec["Stop"]
    if set(spec) <= {"enabled"}:
        del data[name]
    return removed


def _drop_created_containers(data: dict[str, Any], created: Iterable[str]) -> None:
    hooks = data.get("hooks")
    for dotted in sorted(set(created), key=lambda item: -item.count(".")):
        if dotted.startswith("hooks.") and isinstance(hooks, dict):
            event = dotted.split(".", 1)[1]
            if hooks.get(event) == []:
                del hooks[event]
        elif dotted == "hooks" and hooks == {}:
            del data["hooks"]


def _remove_entries(data: dict[str, Any], entries: Sequence[dict[str, Any]]) -> bool:
    removed = False
    created: list[str] = []
    for entry in entries:
        if entry.get("kind") == "claude-code":
            removed |= _remove_claude_entry(data, entry)
            created.extend(str(item) for item in entry.get("created", []))
        elif entry.get("kind") == "antigravity":
            removed |= _remove_antigravity_entry(data, entry)
    _drop_created_containers(data, created)
    return removed


def _backup_is_clean(
    backup: Path, existed: bool, entries: Sequence[dict[str, Any]]
) -> bool:
    """True when restoring ``backup`` cannot bring back any agent-meter entry."""
    if not existed:
        return True
    try:
        commands = set(_commands_in(_loads_object(backup.read_bytes())))
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    return not any(entry.get("command") in commands for entry in entries)


def _remove_from_current(
    path: Path, raw: bytes, mode: int, record: dict[str, Any]
) -> tuple[str, bool]:
    """BR-19 edited-file branch: drop only our entries and keep every later user edit."""
    backup = record["backup"]
    try:
        data = _loads_object(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        return (
            f"skipped {path}: not valid JSON ({exc}); remove the agent-meter entries by hand "
            f"(backup kept at {backup})",
            True,
        )
    if not isinstance(data, dict):
        return (
            f"skipped {path}: the JSON root is not an object (backup kept at {backup})",
            True,
        )
    if not _remove_entries(data, list(record.get("entries", []))):
        return f"no agent-meter entries left in {path} (backup kept at {backup})", False
    if not data and not record.get("existed"):
        path.unlink()
        return f"removed {path} (only agent-meter entries were left)", False
    atomic_write(path, _dump(data).encode("utf-8"), mode=mode)
    return (
        f"removed agent-meter entries from {path}; your later edits were kept "
        f"(backup kept at {backup})",
        False,
    )


def _uninstall_file(record: dict[str, Any]) -> tuple[str, bool]:
    """Undo one recorded settings file; returns ``(action, keep_record)``."""
    path = Path(str(record["path"]))
    backup = Path(str(record["backup"]))
    existed = bool(record.get("existed"))
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return f"skipped {path}: the file no longer exists (nothing to remove)", False
    mode = stat.S_IMODE(path.stat().st_mode)
    unchanged = sha256_hex(raw) == record.get("post_sha256")
    if not unchanged or not _backup_is_clean(
        backup, existed, record.get("entries", [])
    ):
        return _remove_from_current(path, raw, mode, record)
    if existed:
        atomic_write(path, backup.read_bytes(), mode=mode)
        return f"restored {path} byte-for-byte from {backup}", False
    path.unlink()
    return f"removed {path} (it did not exist before setup)", False


def uninstall(home: HomeLike) -> list[str]:
    """Undo every recorded settings change per BR-19; returns the actions taken."""
    manifest = load_manifest(home)
    if manifest is None:
        return []
    actions: list[str] = []
    remaining: list[dict[str, Any]] = []
    for record in manifest["files"]:
        action, keep = _uninstall_file(record)
        actions.append(action)
        if keep:
            remaining.append(record)
    manifest["files"] = remaining
    save_manifest(home, manifest)
    return actions


# --------------------------------------------------------------------------- doctor


def registration_status(path: Path, target: Target) -> RegistrationStatus:
    """Whether agent-meter hooks are registered in ``path`` (any executable location)."""
    try:
        data = _loads_object(Path(os.path.realpath(path)).read_bytes())
    except FileNotFoundError:
        return "absent"
    except (OSError, UnicodeDecodeError, ValueError):
        return "unreadable"
    if not isinstance(data, dict):
        return "unreadable"
    if target == "claude-code":
        hooks = data.get("hooks")
        found = [
            event
            for event, suffix in _CLAUDE_SUFFIXES.items()
            if isinstance(hooks, dict)
            and any(cmd.endswith(suffix) for cmd in _commands_in(hooks.get(event)))
        ]
        if len(found) == len(_CLAUDE_SUFFIXES):
            return "registered"
        return "partial" if found else "absent"
    enabled = any(
        isinstance(spec, dict)
        and spec.get("enabled", True) is not False
        and any(
            cmd.endswith(_ANTIGRAVITY_SUFFIX) for cmd in _commands_in(spec.get("Stop"))
        )
        for spec in data.values()
    )
    return "registered" if enabled else "absent"
