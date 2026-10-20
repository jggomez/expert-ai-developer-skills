"""Unit tests for Windows compatibility primitives across locking, paths, project_resolver, and cli."""

from __future__ import annotations

import errno
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from agent_meter import cli, locking, paths, project_resolver
from agent_meter.paths import AppHome
from agent_meter.project_resolver import (
    UNASSIGNED,
    PathCache,
    ProjectResolver,
    ProjectsConfig,
)


class _DictCache(PathCache):
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, path_hash: str) -> str | None:
        return self.data.get(path_hash)

    def put(self, path_hash: str, project_id: str) -> None:
        self.data[path_hash] = project_id


def _empty_projects_config() -> ProjectsConfig:
    return ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={})


# ----------------------------------------------------------------------------- locking.py


def test_locking_msvcrt_acquire_and_unlock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When fcntl is None, locking falls back to msvcrt.locking on byte 0."""
    # Arrange
    calls: list[tuple[str, int, int, int]] = []
    fake_msvcrt = ModuleType("msvcrt")
    fake_msvcrt.LK_NBLCK = 2  # type: ignore[attr-defined]
    fake_msvcrt.LK_UNLCK = 0  # type: ignore[attr-defined]

    def fake_locking(fd: int, mode: int, nbytes: int) -> None:
        pos = os.lseek(fd, 0, os.SEEK_CUR)
        calls.append(("locking", mode, nbytes, pos))

    fake_msvcrt.locking = fake_locking  # type: ignore[attr-defined]
    monkeypatch.setattr(locking, "fcntl", None)
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    lock_file = tmp_path / "lock"

    # Act
    with locking.store_lock(lock_file, exclusive=True, timeout_s=0.1):
        pass

    # Assert
    assert calls == [
        ("locking", 2, 1, 0),
        ("locking", 0, 1, 0),
    ]


def test_locking_msvcrt_contention_raises_lock_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When msvcrt.locking raises OSError/PermissionError, store_lock times out with LockTimeout."""
    # Arrange
    fake_msvcrt = ModuleType("msvcrt")
    fake_msvcrt.LK_NBLCK = 2  # type: ignore[attr-defined]
    fake_msvcrt.LK_UNLCK = 0  # type: ignore[attr-defined]

    def fake_locking(fd: int, mode: int, nbytes: int) -> None:
        raise PermissionError(errno.EACCES, "File already locked")

    fake_msvcrt.locking = fake_locking  # type: ignore[attr-defined]
    monkeypatch.setattr(locking, "fcntl", None)
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    lock_file = tmp_path / "lock"

    # Act & Assert
    with (
        pytest.raises(locking.LockTimeout, match="store busy: no shared lock"),
        locking.store_lock(lock_file, exclusive=False, timeout_s=0.01),
    ):
        pass


# ----------------------------------------------------------------------------- paths.py


def test_app_home_resolve_uses_userprofile_when_home_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AppHome.resolve falls back to USERPROFILE when HOME and AGENT_METER_HOME are unset."""
    # Arrange
    monkeypatch.delenv("AGENT_METER_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    # Act
    home = AppHome.resolve()

    # Assert
    assert home.root == (tmp_path / ".agent-meter").resolve()
    assert home.marker.is_file()


def test_read_secret_works_without_os_fchmod(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """read_secret does not fail on platforms where os.fchmod is absent (Windows)."""
    # Arrange
    home = AppHome.resolve(str(tmp_path / "home"))
    secret_bytes = paths.load_secret(home)
    monkeypatch.delattr(os, "fchmod", raising=False)

    # Act
    read_back = paths.read_secret(home)

    # Assert
    assert read_back == secret_bytes


def test_fsync_dir_is_noop_on_windows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """_fsync_dir returns immediately when os.name == 'nt' without calling os.open on the directory."""
    # Arrange
    with monkeypatch.context() as m:
        m.setattr(os, "name", "nt")

        def forbid_open(*args: Any, **kwargs: Any) -> int:
            raise AssertionError("os.open should not be called on Windows in _fsync_dir")

        m.setattr(os, "open", forbid_open)

        # Act & Assert
        paths._fsync_dir(tmp_path)


def test_load_secret_windows_link_fallback_to_replace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When os.link fails with OSError on Windows and secret does not exist, load_secret falls back to os.replace."""
    # Arrange
    home = AppHome.resolve(str(tmp_path / "home"))

    def failing_link(src: Any, dst: Any) -> None:
        raise OSError(errno.EINVAL, "Hard links not supported on this filesystem")

    with monkeypatch.context() as m:
        m.setattr(os, "name", "nt")
        m.setattr(os, "link", failing_link)

        # Act
        data = paths.load_secret(home)

    # Assert
    assert len(data) == paths.SECRET_BYTES
    assert home.secret.read_bytes() == data


def test_user_home_candidates_includes_userprofile_and_handles_missing_getuid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """_user_home_candidates includes USERPROFILE and guards os.getuid() when absent."""
    # Arrange
    win_profile = tmp_path / "win_user"
    win_profile.mkdir()
    monkeypatch.setenv("USERPROFILE", str(win_profile))
    monkeypatch.delattr(os, "getuid", raising=False)

    # Act
    candidates = paths._user_home_candidates()

    # Assert
    assert os.path.realpath(str(win_profile)) in candidates


# ----------------------------------------------------------------------------- project_resolver.py


def test_project_resolver_strips_leading_slash_from_windows_drive_file_uri() -> None:
    """ProjectResolver._to_directory strips leading slash before drive letter in file:///C:/... URIs."""
    # Arrange & Act
    result = ProjectResolver._to_directory("file:///C:/Users/alice/repo")

    # Assert
    assert result is not None
    assert not result.startswith("/C:")
    assert "C:" in result


def test_is_under_supports_windows_backslash_separators() -> None:
    """_is_under matches child paths separated by either forward slash or backslash."""
    # Arrange & Act & Assert
    assert project_resolver._is_under(r"C:\Users\alice\repo\sub", r"C:\Users\alice\repo")
    assert project_resolver._is_under(r"C:\Users\alice\repo", r"C:\Users\alice\repo\\")
    assert not project_resolver._is_under(r"C:\Users\alice\repo2", r"C:\Users\alice\repo")


def test_worktree_prefix_supports_windows_backslashes() -> None:
    """_worktree_prefix detects worktree segments in backslash-separated Windows paths and preserves separators."""
    # Arrange
    win_wt = r"C:\Users\alice\repo\.claude\worktrees\wt-1"

    # Act
    prefix = ProjectResolver._worktree_prefix(win_wt)

    # Assert
    assert prefix == r"C:\Users\alice\repo"


def test_project_resolver_includes_temp_and_tmp_env_roots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """ProjectResolver treats paths under TEMP and TMP environment variables as unassigned."""
    # Arrange
    win_temp = tmp_path / "AppData" / "Local" / "Temp"
    win_temp.mkdir(parents=True)
    scratch_dir = win_temp / "scratch_work"
    scratch_dir.mkdir()
    monkeypatch.setenv("TEMP", str(win_temp))
    monkeypatch.delenv("TMPDIR", raising=False)

    resolver = ProjectResolver(
        _DictCache(),
        _empty_projects_config(),
        home=tmp_path / "home",
    )

    # Act
    ref = resolver.resolve(str(scratch_dir))

    # Assert
    assert ref == UNASSIGNED


# ----------------------------------------------------------------------------- cli.py


def test_cli_current_project_uses_userprofile_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """cli._current_project falls back to USERPROFILE when HOME is unset."""
    # Arrange
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    class _FakeStore:
        def path_cache(self) -> PathCache:
            return _DictCache()

    ctx = cli.Ctx(home=AppHome.resolve(str(tmp_path / ".agent-meter")), quiet=True)

    # Act
    project_id = cli._current_project(ctx, _FakeStore())  # type: ignore[arg-type]

    # Assert
    assert project_id == UNASSIGNED.project_id
