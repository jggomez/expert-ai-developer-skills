"""Shared types for the scheduler backends: injectable process runner and environment."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, Protocol

__all__ = [
    "COLLECT_ARGS",
    "INTERVAL_S",
    "Kind",
    "Runner",
    "SchedulerEnv",
    "SchedulerError",
    "SchedulerUnsupported",
    "default_runner",
    "require_ok",
    "scheduled_argv",
]

Kind = Literal["launchd", "systemd", "cron", "schtasks"]
INTERVAL_S: Final = 900
COLLECT_ARGS: Final = ("collect", "--scheduled", "--quiet")
_RUN_TIMEOUT_S: Final = 30


class SchedulerError(RuntimeError):
    """A scheduler command failed; the message carries the command's stderr."""


class SchedulerUnsupported(SchedulerError):
    """No supported scheduler on this machine (e.g. Windows, Linux without systemd or cron)."""


class Runner(Protocol):
    def __call__(
        self, args: Sequence[str], *, input: str | None = None
    ) -> subprocess.CompletedProcess[str]: ...


def default_runner(
    args: Sequence[str], *, input: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a command without a shell; a missing binary or a timeout becomes a failed result."""
    argv = list(args)
    try:
        return subprocess.run(
            argv,
            input=input,
            capture_output=True,
            text=True,
            timeout=_RUN_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            argv, 127, "", f"{argv[0]}: command not found"
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            argv, 124, "", f"{argv[0]}: timed out after {_RUN_TIMEOUT_S}s"
        )


@dataclass(frozen=True, slots=True)
class SchedulerEnv:
    platform: str
    user_home: Path
    uid: int
    runner: Runner
    which: Callable[[str], str | None]

    @classmethod
    def current(cls) -> SchedulerEnv:
        return cls(
            platform=sys.platform,
            user_home=Path.home(),
            uid=os.getuid() if hasattr(os, "getuid") else 0,
            runner=default_runner,
            which=shutil.which,
        )


def require_ok(result: subprocess.CompletedProcess[str], what: str) -> None:
    if result.returncode != 0:
        detail = (
            result.stderr or result.stdout or ""
        ).strip() or f"exit code {result.returncode}"
        raise SchedulerError(f"{what} failed: {detail}")


def scheduled_argv(executable: Path) -> list[str]:
    return [str(executable), *COLLECT_ARGS]
