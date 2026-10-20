"""Periodic ``agent-meter collect --scheduled --quiet`` every 15 minutes (ADR §3.10 "Scheduler").

Backends: macOS launchd user agent, Linux systemd user timer, cron fallback. Every operation is
idempotent and records its state in ``install.json`` under ``"scheduler"`` (contracts §5).
Process execution goes through ``SchedulerEnv.runner`` so tests never touch the real system.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from agent_meter.scheduler import cron, launchd, schtasks, systemd
from agent_meter.scheduler._base import (
    Kind,
    Runner,
    SchedulerEnv,
    SchedulerError,
    SchedulerUnsupported,
    default_runner,
)
from agent_meter.setup._files import (
    MANIFEST_VERSION,
    HomeLike,
    load_manifest,
    save_manifest,
)

__all__ = [
    "NO_CHANGES",
    "Kind",
    "Runner",
    "SchedulerEnv",
    "SchedulerError",
    "SchedulerUnsupported",
    "default_runner",
    "detect_kind",
    "install",
    "status",
    "uninstall",
]

NO_CHANGES = "(no changes)"
_DESCRIPTION = "runs `agent-meter collect --scheduled --quiet` every 15 min"


def detect_kind(env: SchedulerEnv) -> Kind | None:
    """launchd on macOS; systemd user timer on Linux when available, else cron; schtasks on win32."""
    if env.platform == "darwin":
        return "launchd"
    if env.platform.startswith("linux"):
        if systemd.available(env):
            return "systemd"
        if cron.available(env):
            return "cron"
    if env.platform == "win32" and schtasks.available(env):
        return "schtasks"
    return None


def _location(kind: Kind, env: SchedulerEnv) -> str:
    if kind == "launchd":
        return str(launchd.plist_path(env))
    if kind == "systemd":
        return str(systemd.unit_dir(env) / systemd.TIMER)
    if kind == "schtasks":
        return f"schtasks:{schtasks.TASK_NAME}"
    return "crontab"


def _install_backend(
    kind: Kind, home: HomeLike, executable: Path, env: SchedulerEnv
) -> bool:
    if kind == "launchd":
        return launchd.install(home, executable, env)
    if kind == "systemd":
        return systemd.install(home, executable, env)
    if kind == "schtasks":
        return schtasks.install(home, executable, env)
    return cron.install(home, executable, env)


def _uninstall_backend(kind: Kind, env: SchedulerEnv) -> bool:
    if kind == "launchd":
        return launchd.uninstall(env)
    if kind == "systemd":
        return systemd.uninstall(env)
    if kind == "schtasks":
        return schtasks.uninstall(env)
    return cron.uninstall(env)


def _is_loaded(kind: Kind, env: SchedulerEnv) -> bool:
    if kind == "launchd":
        return launchd.is_loaded(env)
    if kind == "systemd":
        return systemd.is_loaded(env)
    if kind == "schtasks":
        return schtasks.is_loaded(env)
    return cron.is_loaded(env)


def _unsupported(env: SchedulerEnv) -> SchedulerUnsupported:
    return SchedulerUnsupported(
        f"no supported scheduler on platform {env.platform!r} (launchd, systemd user timer, "
        "cron or schtasks); run `agent-meter collect` manually or from your own scheduler"
    )


def install(
    home: HomeLike, executable: Path, *, env: SchedulerEnv | None = None
) -> str:
    """Install (or update) the periodic collector; returns a one-line description of the outcome."""
    if not executable.is_absolute():
        raise ValueError(
            f"the scheduler needs an absolute executable path, got {executable}"
        )
    env = env or SchedulerEnv.current()
    kind = detect_kind(env)
    if kind is None:
        raise _unsupported(env)
    changed = _install_backend(kind, home, executable, env)
    location = _location(kind, env)
    manifest = load_manifest(home) or {"version": MANIFEST_VERSION, "files": []}
    manifest["scheduler"] = {"kind": kind, "path": location}
    save_manifest(home, manifest)
    if not changed:
        return f"{kind} scheduler already installed at {location} {NO_CHANGES}"
    return f"{kind} scheduler installed at {location}: {_DESCRIPTION}"


_KINDS: dict[str, Kind] = {
    "launchd": "launchd",
    "systemd": "systemd",
    "cron": "cron",
    "schtasks": "schtasks",
}


def _recorded_kind(manifest: dict[str, Any] | None) -> Kind | None:
    recorded = manifest.get("scheduler") if manifest else None
    kind = recorded.get("kind") if isinstance(recorded, dict) else None
    return _KINDS.get(kind) if isinstance(kind, str) else None


def uninstall(home: HomeLike, *, env: SchedulerEnv | None = None) -> str:
    """Remove the periodic collector recorded in ``install.json`` (or the platform default)."""
    env = env or SchedulerEnv.current()
    manifest = load_manifest(home)
    kind = _recorded_kind(manifest) or detect_kind(env)
    removed = kind is not None and _uninstall_backend(kind, env)
    if manifest is not None and "scheduler" in manifest:
        del manifest["scheduler"]
        save_manifest(home, manifest)
    if kind is None or not removed:
        return "no scheduler installed (nothing to remove)"
    return f"{kind} scheduler removed ({_location(kind, env)})"


def status(
    *, env: SchedulerEnv | None = None
) -> Literal["loaded", "not_loaded", "unsupported"]:
    """For ``doctor``: whether the platform scheduler currently has agent-meter loaded."""
    env = env or SchedulerEnv.current()
    kind = detect_kind(env)
    if kind is None:
        return "unsupported"
    return "loaded" if _is_loaded(kind, env) else "not_loaded"
