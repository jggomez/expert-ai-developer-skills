"""Advisory store lock (ADR §3.9): ``fcntl.flock`` on ``~/.agent-meter/lock``.

Writers take ``LOCK_EX`` and readers ``LOCK_SH``; DuckDB itself forbids a reader while
another process writes, so every store user goes through this lock first. On Windows,
where ``fcntl`` is unavailable, ``msvcrt.locking`` on byte 0 is used as a fallback.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows
    _fcntl = None  # type: ignore[assignment]

fcntl: Any = _fcntl

__all__ = ["POLL_INTERVAL_S", "LockTimeout", "store_lock"]

POLL_INTERVAL_S: Final = 0.05


class LockTimeout(TimeoutError):
    """The store lock could not be acquired within the wait budget."""


def _try_lock(fd: int, *, exclusive: bool) -> bool:
    if fcntl is not None:
        operation = (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB
        try:
            fcntl.flock(fd, operation)
            return True
        except BlockingIOError:
            return False
    import msvcrt

    msvcrt_mod: Any = msvcrt
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt_mod.locking(fd, msvcrt_mod.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def _unlock(fd: int) -> None:
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return
    import msvcrt

    msvcrt_mod: Any = msvcrt
    os.lseek(fd, 0, os.SEEK_SET)
    msvcrt_mod.locking(fd, msvcrt_mod.LK_UNLCK, 1)


@contextmanager
def store_lock(path: Path, *, exclusive: bool, timeout_s: float) -> Iterator[None]:
    """Hold an exclusive or shared lock on ``path``; poll every 50 ms until ``timeout_s``."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    deadline = time.monotonic() + max(timeout_s, 0.0)
    try:
        while not _try_lock(fd, exclusive=exclusive):
            if time.monotonic() >= deadline:
                kind = "exclusive" if exclusive else "shared"
                raise LockTimeout(f"store busy: no {kind} lock within {timeout_s:g}s")
            time.sleep(POLL_INTERVAL_S)
        try:
            yield
        finally:
            _unlock(fd)
    finally:
        os.close(fd)
