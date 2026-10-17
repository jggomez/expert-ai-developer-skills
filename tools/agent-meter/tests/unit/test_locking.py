"""Unit tests for the advisory store lock (``fcntl.flock``)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from agent_meter.locking import LockTimeout, store_lock


def test_exclusive_lock_blocks_second_writer(tmp_path: Path) -> None:
    lock = tmp_path / "lock"

    with store_lock(lock, exclusive=True, timeout_s=1.0):
        started = time.monotonic()
        with pytest.raises(LockTimeout), store_lock(lock, exclusive=True, timeout_s=0.2):
            pass
        waited = time.monotonic() - started

    assert 0.15 <= waited < 1.0


def test_shared_locks_coexist_but_block_writer(tmp_path: Path) -> None:
    lock = tmp_path / "lock"

    with store_lock(lock, exclusive=False, timeout_s=0.5), store_lock(
        lock, exclusive=False, timeout_s=0.5
    ), pytest.raises(LockTimeout), store_lock(lock, exclusive=True, timeout_s=0.1):
        pass


def test_lock_released_after_exception(tmp_path: Path) -> None:
    lock = tmp_path / "lock"

    with pytest.raises(RuntimeError), store_lock(lock, exclusive=True, timeout_s=0.5):
        raise RuntimeError("boom")

    with store_lock(lock, exclusive=True, timeout_s=0.1):
        acquired = True

    assert acquired
    assert issubclass(LockTimeout, TimeoutError)
