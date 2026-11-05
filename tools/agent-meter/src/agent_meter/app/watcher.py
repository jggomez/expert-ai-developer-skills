"""Live updates: watch transcript folders and collect only after something changed."""

from __future__ import annotations

import contextlib
import logging
import os
import threading
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Final

from agent_meter.model import Host
from agent_meter.readers.antigravity import TRANSCRIPT_REL
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
    stamps = [stamp for path in _candidates(folders) if (stamp := _modified_ns(path)) is not None]
    return len(stamps), max(stamps, default=0)


def _candidates(folders: Iterable[Path]) -> Iterator[str]:
    for folder in folders:
        if folder.name == "brain":  # each conversation holds thousands of unrelated working files
            with contextlib.suppress(OSError):
                for entry in os.scandir(folder):
                    yield os.path.join(entry.path, TRANSCRIPT_REL)
            continue
        for current, _dirs, names in os.walk(folder):
            yield from (os.path.join(current, name) for name in names if name.endswith(_SUFFIXES))


def _modified_ns(path: str) -> int | None:
    try:
        return os.stat(path).st_mtime_ns
    except OSError:  # missing, or removed since it was listed; the next pass sees it
        return None


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
