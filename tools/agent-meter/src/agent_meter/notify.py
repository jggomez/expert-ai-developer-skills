"""Desktop notifications: macOS ``osascript``, Linux ``notify-send``, Windows PowerShell (contracts §3.8).

Text is passed as argv (never interpolated into a script or a shell). ``notify`` returns
``False`` when notifications are unavailable or fail, and never raises.
"""

from __future__ import annotations

import base64
import logging
import re
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


_BALLOON: Final = (
    "Add-Type -AssemblyName System.Windows.Forms; "
    "$icon = New-Object System.Windows.Forms.NotifyIcon; "
    "$icon.Icon = [System.Drawing.SystemIcons]::Information; "
    "$icon.Visible = $true; "
    "$icon.ShowBalloonTip(3000, {title}, {body}, [System.Windows.Forms.ToolTipIcon]::None); "
    "Start-Sleep -Seconds 3; "
    "$icon.Dispose()"
)


def _powershell_text(value: str) -> str:
    """A single-quoted literal; PowerShell also treats curly quotes as quotes."""
    return "'" + re.sub("['\u2018\u2019\u201a\u201b]", "''", value) + "'"


def _windows_command(binary: str, title: str, body: str) -> list[str]:
    script = _BALLOON.format(title=_powershell_text(title), body=_powershell_text(body))
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return [binary, "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encoded]


def _command(title: str, body: str) -> list[str] | None:
    if sys.platform == "darwin":
        binary = shutil.which("osascript")
        return [binary, *_OSASCRIPT, title, body] if binary else None
    if sys.platform.startswith("linux"):
        binary = shutil.which("notify-send")
        return [binary, "--app-name=agent-meter", title, body] if binary else None
    if sys.platform == "win32":
        binary = shutil.which("powershell")
        return _windows_command(binary, title, body) if binary else None
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
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _LOG.debug("notification failed: %s", type(exc).__name__)
        return False
    return completed.returncode == 0
