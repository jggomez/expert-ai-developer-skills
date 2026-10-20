"""Windows Task Scheduler backend using ``schtasks.exe`` (runs every 15 minutes)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Final

from agent_meter.scheduler._base import (
    COLLECT_ARGS,
    SchedulerEnv,
    require_ok,
)
from agent_meter.setup._files import HomeLike

__all__ = [
    "TASK_NAME",
    "available",
    "install",
    "is_loaded",
    "render_command",
    "uninstall",
]

TASK_NAME: Final = "com.agent-meter.collect"


def available(env: SchedulerEnv) -> bool:
    return env.which("schtasks") is not None


def render_command(home: HomeLike, executable: Path) -> str:
    return subprocess.list2cmdline(
        [str(executable), "--home", str(home.root), *COLLECT_ARGS]
    )


def is_loaded(env: SchedulerEnv) -> bool:
    result = env.runner(["schtasks", "/Query", "/TN", TASK_NAME])
    return result.returncode == 0


def install(home: HomeLike, executable: Path, env: SchedulerEnv) -> bool:
    """Create or update the 15-minute scheduled task; ``False`` when already up to date."""
    tr = render_command(home, executable)
    query = env.runner(["schtasks", "/Query", "/TN", TASK_NAME, "/V", "/FO", "LIST"])
    if query.returncode == 0 and tr in (query.stdout or ""):
        return False
    require_ok(
        env.runner(
            [
                "schtasks",
                "/Create",
                "/F",
                "/SC",
                "MINUTE",
                "/MO",
                "15",
                "/TN",
                TASK_NAME,
                "/TR",
                tr,
            ]
        ),
        "schtasks /Create",
    )
    return True


def uninstall(env: SchedulerEnv) -> bool:
    if not is_loaded(env):
        return False
    require_ok(
        env.runner(["schtasks", "/Delete", "/F", "/TN", TASK_NAME]),
        "schtasks /Delete",
    )
    return True
