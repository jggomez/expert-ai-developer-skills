"""Live updates: watch transcript folders and collect only after something changed."""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Final

from agent_meter.model import Host
from agent_meter.readers.base import default_roots

__all__ = ["TranscriptWatcher", "signature", "watched_folders"]

POLL_INTERVAL_S: Final = 1.0
_SUFFIXES: Final = (".jsonl", ".db", ".db-wal", ".pb")
_LOG = logging.getLogger(__name__)


def watched_folders(roots: dict[Host, Path] | None = None) -> list[Path]:
    selected = default_roots() if roots is None else roots
    folders: list[Path] = []
    for host, root in selected.items():
        names = ("projects",) if host is Host.CLAUDE_CODE else ("conversations", "brain")
        folders += [root / name for name in names]
    return folders


def signature(folders: Iterable[Path]) -> tuple[int, int]:
    """File count and newest modification time: cheap, and either one changes on new activity."""
    count = 0
    newest = 0
    for folder in folders:
        for current, _dirs, names in os.walk(folder):
            for name in names:
                if name.endswith(_SUFFIXES):
                    try:
                        newest = max(newest, os.stat(os.path.join(current, name)).st_mtime_ns)
                    except OSError:  # removed between listing and stat; the next pass sees it
                        continue
                    count += 1
    return count, newest


class TranscriptWatcher(threading.Thread):
    def __init__(self, folders: list[Path], on_change: Callable[[], None]) -> None:
        super().__init__(daemon=True, name="agent-meter-watcher")
        self._folders = folders
        self._on_change = on_change
        self._stop_event = threading.Event()
        self._last = signature(folders)

    def poll_once(self) -> bool:
        current = signature(self._folders)
        if current == self._last:
            return False
        self._last = current
        try:
            self._on_change()
        except Exception:
            _LOG.exception("live refresh failed")
        return True

    def run(self) -> None:
        while not self._stop_event.wait(POLL_INTERVAL_S):
            self.poll_once()

    def stop(self) -> None:
        self._stop_event.set()
