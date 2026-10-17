"""macOS launchd user agent (``~/Library/LaunchAgents/dev.agentmeter.collect.plist``).

``RunAtLoad`` starts a collection at login, and launchd runs a missed ``StartInterval`` once
after wake, which covers reboot and sleep (PF-05).
"""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Final

from agent_meter.scheduler._base import (
    INTERVAL_S,
    SchedulerEnv,
    require_ok,
    scheduled_argv,
)
from agent_meter.setup._files import HomeLike, atomic_write

__all__ = ["LABEL", "install", "is_loaded", "plist_path", "render_plist", "uninstall"]

LABEL: Final = "dev.agentmeter.collect"
_PLIST_MODE: Final = 0o644


def plist_path(env: SchedulerEnv) -> Path:
    return env.user_home / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _domain(env: SchedulerEnv) -> str:
    return f"gui/{env.uid}"


def render_plist(home: HomeLike, executable: Path) -> bytes:
    log = str(home.logs_dir / "scheduler.log")
    return plistlib.dumps(
        {
            "Label": LABEL,
            "ProgramArguments": scheduled_argv(executable),
            "EnvironmentVariables": {"AGENT_METER_HOME": str(home.root)},
            "StartInterval": INTERVAL_S,
            "RunAtLoad": True,
            "ProcessType": "Background",
            "LowPriorityIO": True,
            "Nice": 10,
            "StandardOutPath": log,
            "StandardErrorPath": log,
        }
    )


def is_loaded(env: SchedulerEnv) -> bool:
    return env.runner(["launchctl", "print", f"{_domain(env)}/{LABEL}"]).returncode == 0


def _bootout(env: SchedulerEnv) -> None:
    result = env.runner(["launchctl", "bootout", f"{_domain(env)}/{LABEL}"])
    require_ok(result, f"launchctl bootout {LABEL}")


def install(home: HomeLike, executable: Path, env: SchedulerEnv) -> bool:
    """Write the plist and (re)load the agent; ``False`` when already installed unchanged."""
    path = plist_path(env)
    content = render_plist(home, executable)
    loaded = is_loaded(env)
    current = path.read_bytes() if path.exists() else None
    if current == content and loaded:
        return False
    home.logs_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write(path, content, mode=_PLIST_MODE)
    if loaded:
        _bootout(env)
    result = env.runner(["launchctl", "bootstrap", _domain(env), str(path)])
    require_ok(result, f"launchctl bootstrap {path}")
    return True


def uninstall(env: SchedulerEnv) -> bool:
    """Unload the agent and delete its plist; ``False`` when nothing was installed."""
    path = plist_path(env)
    loaded = is_loaded(env)
    if loaded:
        _bootout(env)
    if path.exists():
        path.unlink()
        return True
    return loaded
