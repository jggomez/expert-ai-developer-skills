"""Linux systemd user timer (``~/.config/systemd/user/agent-meter-collect.{service,timer}``).

``OnCalendar=*:0/15`` with ``Persistent=true`` runs a missed slot once after sleep or power-off
(PF-05); ``OnBootSec`` also starts a collection shortly after boot.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from agent_meter.scheduler._base import (
    COLLECT_ARGS,
    SchedulerEnv,
    require_ok,
)
from agent_meter.setup._files import HomeLike, atomic_write

__all__ = [
    "SERVICE",
    "TIMER",
    "available",
    "install",
    "is_loaded",
    "render_service",
    "render_timer",
    "uninstall",
    "unit_dir",
]

SERVICE: Final = "agent-meter-collect.service"
TIMER: Final = "agent-meter-collect.timer"
_UNIT_MODE: Final = 0o644


def unit_dir(env: SchedulerEnv) -> Path:
    return env.user_home / ".config" / "systemd" / "user"


def _quote(value: str) -> str:
    """systemd unit quoting: double quotes, backslash escapes and ``%%`` for specifiers."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return f'"{escaped}"'


def render_service(home: HomeLike, executable: Path) -> str:
    return "\n".join(
        [
            "[Unit]",
            "Description=agent-meter: collect Claude Code and Antigravity usage",
            "",
            "[Service]",
            "Type=oneshot",
            f"Environment={_quote(f'AGENT_METER_HOME={home.root}')}",
            f"ExecStart={_quote(str(executable))} {' '.join(COLLECT_ARGS)}",
            "Nice=10",
            "IOSchedulingClass=idle",
            "",
        ]
    )


def render_timer() -> str:
    return "\n".join(
        [
            "[Unit]",
            "Description=Run agent-meter collect every 15 minutes",
            "",
            "[Timer]",
            "OnBootSec=2min",
            "OnCalendar=*:0/15",
            "Persistent=true",
            f"Unit={SERVICE}",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )


def available(env: SchedulerEnv) -> bool:
    if env.which("systemctl") is None:
        return False
    return env.runner(["systemctl", "--user", "show-environment"]).returncode == 0


def is_loaded(env: SchedulerEnv) -> bool:
    return env.runner(["systemctl", "--user", "is-active", TIMER]).returncode == 0


def _systemctl(env: SchedulerEnv, *args: str) -> None:
    require_ok(
        env.runner(["systemctl", "--user", *args]), f"systemctl --user {' '.join(args)}"
    )


def install(home: HomeLike, executable: Path, env: SchedulerEnv) -> bool:
    """Write both units, reload and ``enable --now`` the timer; ``False`` when unchanged."""
    directory = unit_dir(env)
    wanted = {
        directory / SERVICE: render_service(home, executable).encode(),
        directory / TIMER: render_timer().encode(),
    }
    stale = {
        path: data
        for path, data in wanted.items()
        if not path.exists() or path.read_bytes() != data
    }
    if not stale and is_loaded(env):
        return False
    for path, data in stale.items():
        atomic_write(path, data, mode=_UNIT_MODE)
    if stale:
        _systemctl(env, "daemon-reload")
    _systemctl(env, "enable", "--now", TIMER)
    return True


def uninstall(env: SchedulerEnv) -> bool:
    """Disable the timer and delete both units; ``False`` when nothing was installed."""
    directory = unit_dir(env)
    paths = [directory / SERVICE, directory / TIMER]
    present = [path for path in paths if path.exists()]
    loaded = is_loaded(env)
    if not present and not loaded:
        return False
    if (directory / TIMER).exists() or loaded:
        _systemctl(env, "disable", "--now", TIMER)
    for path in present:
        path.unlink()
    _systemctl(env, "daemon-reload")
    return True
