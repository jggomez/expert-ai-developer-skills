"""Cron fallback for Linux without a user systemd: one crontab line managed by a marker."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Final

from agent_meter.scheduler._base import (
    COLLECT_ARGS,
    SchedulerEnv,
    SchedulerError,
    require_ok,
)
from agent_meter.setup._files import HomeLike

__all__ = ["MARKER", "available", "install", "is_loaded", "render_line", "uninstall"]

MARKER: Final = "# agent-meter"


def _cron_escape(text: str) -> str:
    """Cron turns an unescaped ``%`` into a newline."""
    return text.replace("%", "\\%")


def render_line(home: HomeLike, executable: Path) -> str:
    command = " ".join(
        [
            f"AGENT_METER_HOME={shlex.quote(str(home.root))}",
            shlex.quote(str(executable)),
            *COLLECT_ARGS,
        ]
    )
    return f"*/15 * * * * {_cron_escape(command)} {MARKER}"


def available(env: SchedulerEnv) -> bool:
    return env.which("crontab") is not None


def _is_ours(line: str) -> bool:
    return line.rstrip().endswith(MARKER)


def _read(env: SchedulerEnv) -> list[str]:
    result = env.runner(["crontab", "-l"])
    if result.returncode == 0:
        return result.stdout.splitlines()
    if "no crontab" in (result.stderr or "").lower():
        return []
    detail = (result.stderr or "").strip() or f"exit code {result.returncode}"
    raise SchedulerError(f"crontab -l failed: {detail}")


def _write(env: SchedulerEnv, lines: list[str]) -> None:
    text = "".join(f"{line}\n" for line in lines)
    require_ok(env.runner(["crontab", "-"], input=text), "crontab -")


def is_loaded(env: SchedulerEnv) -> bool:
    return any(_is_ours(line) for line in _read(env))


def install(home: HomeLike, executable: Path, env: SchedulerEnv) -> bool:
    """Replace our marked line (keeping every other line); ``False`` when unchanged."""
    line = render_line(home, executable)
    lines = _read(env)
    ours = [item for item in lines if _is_ours(item)]
    if ours == [line]:
        return False
    _write(env, [item for item in lines if not _is_ours(item)] + [line])
    return True


def uninstall(env: SchedulerEnv) -> bool:
    lines = _read(env)
    kept = [item for item in lines if not _is_ours(item)]
    if len(kept) == len(lines):
        return False
    _write(env, kept)
    return True
