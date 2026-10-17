"""Advisory store lock (ADR §3.9): ``fcntl.flock`` on ``~/.agent-meter/lock``.

Writers take ``LOCK_EX`` and readers ``LOCK_SH``; DuckDB itself forbids a reader while
another process writes, so every store user goes through this lock first.
"""

from __future__ import annotations

import fcntl
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

__all__ = ["POLL_INTERVAL_S", "LockTimeout", "store_lock"]

POLL_INTERVAL_S: Final = 0.05


class LockTimeout(TimeoutError):
    """The store lock could not be acquired within the wait budget."""


@contextmanager
def store_lock(path: Path, *, exclusive: bool, timeout_s: float) -> Iterator[None]:
    """Hold an exclusive or shared lock on ``path``; poll every 50 ms until ``timeout_s``."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    operation = (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB
    deadline = time.monotonic() + max(timeout_s, 0.0)
    try:
        while True:
            try:
                fcntl.flock(fd, operation)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    kind = "exclusive" if exclusive else "shared"
                    raise LockTimeout(f"store busy: no {kind} lock within {timeout_s:g}s") from exc
                time.sleep(POLL_INTERVAL_S)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
