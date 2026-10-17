"""Desktop notifications: macOS ``osascript``, Linux ``notify-send`` (contracts §3.8).

Text is passed as argv (never interpolated into a script or a shell). ``notify`` returns
``False`` when notifications are unavailable or fail, and never raises.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from typing import Final

__all__ = ["NOTIFY_TIMEOUT_S", "notify"]

_LOG = logging.getLogger(__name__)

NOTIFY_TIMEOUT_S: Final = 5.0
_OSASCRIPT: Final = (
    "-e",
    "on run argv",
    "-e",
    "display notification (item 2 of argv) with title (item 1 of argv)",
    "-e",
    "end run",
)


def _command(title: str, body: str) -> list[str] | None:
    if sys.platform == "darwin":
        binary = shutil.which("osascript")
        return [binary, *_OSASCRIPT, title, body] if binary else None
    if sys.platform.startswith("linux"):
        binary = shutil.which("notify-send")
        return [binary, "--app-name=agent-meter", title, body] if binary else None
    return None


def notify(title: str, body: str) -> bool:
    """Show a desktop notification; ``False`` if unavailable or failed (never raises)."""
    command = _command(title, body)
    if command is None:
        return False
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=NOTIFY_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _LOG.debug("notification failed: %s", type(exc).__name__)
        return False
    return completed.returncode == 0
