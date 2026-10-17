"""Unit tests for the safety rules of ``paths`` (H-1 purge guard, home marker, secret handling)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from agent_meter import paths
from agent_meter.paths import (
    HOME_MARKER,
    SECRET_BYTES,
    AppHome,
    SecretCorruptError,
    UnsafePurgeError,
    is_known_home_entry,
    load_secret,
    plan_purge,
    purge_home,
    read_secret,
)

# ----------------------------------------------------------------------------- marker and mode


def test_resolve_creates_marker_and_0700_for_a_new_home(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "new-home"

    # Act
    home = AppHome.resolve(str(target))

    # Assert
    assert (home.root / HOME_MARKER).is_file()
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o700


def test_resolve_never_changes_the_mode_of_an_existing_foreign_dir(tmp_path: Path) -> None:
    # Arrange
    foreign = tmp_path / "Documents"
    foreign.mkdir()
    os.chmod(foreign, 0o755)
    (foreign / "thesis.txt").write_text("chapter 1", encoding="utf-8")

    # Act
    home = AppHome.resolve(str(foreign))

    # Assert
    assert stat.S_IMODE(os.stat(foreign).st_mode) == 0o755
    assert not (home.root / HOME_MARKER).exists()


def test_resolve_restores_0700_on_an_existing_marked_home(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))
    os.chmod(home.root, 0o755)

    # Act
    AppHome.resolve(str(home.root))

    # Assert
    assert stat.S_IMODE(os.stat(home.root).st_mode) == 0o700


def test_known_entries_cover_every_home_path_and_temp_files(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))
    top_level = [home.db, home.lock, home.config, home.projects, home.pricing_local, home.secret,
                 home.install_manifest, home.last_summary, home.state_dir, home.logs_dir,
                 home.backups_dir, home.outbox_dir, home.report, home.root / HOME_MARKER]

    # Act
    known = [is_known_home_entry(path.name) for path in top_level]

    # Assert
    assert all(known)
    assert is_known_home_entry("meter.duckdb.wal")
    assert is_known_home_entry(".config.toml.ab12cd.tmp")
    assert not is_known_home_entry("thesis.txt")
    assert not is_known_home_entry("Documents")


# ----------------------------------------------------------------------------- purge refusals


def _point_home_at(monkeypatch: pytest.MonkeyPatch, user_home: Path) -> None:
    monkeypatch.setenv("HOME", str(user_home))


def test_plan_purge_refuses_filesystem_root() -> None:
    # Arrange
    home = AppHome(root=Path("/"))

    # Act / Assert
    with pytest.raises(UnsafePurgeError, match="filesystem root"):
        plan_purge(home)


def test_plan_purge_refuses_the_user_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    user_home = tmp_path / "user"
    user_home.mkdir()
    _point_home_at(monkeypatch, user_home)

    # Act / Assert
    with pytest.raises(UnsafePurgeError, match="home directory"):
        plan_purge(AppHome(root=user_home))


def test_plan_purge_refuses_an_ancestor_of_the_user_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    user_home = tmp_path / "users" / "me"
    user_home.mkdir(parents=True)
    _point_home_at(monkeypatch, user_home)

    # Act / Assert
    with pytest.raises(UnsafePurgeError, match="contains your home directory"):
        plan_purge(AppHome(root=tmp_path / "users"))


def test_plan_purge_refuses_a_mount_point(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))
    monkeypatch.setattr(paths.os.path, "ismount", lambda candidate: str(candidate) == str(home.root))

    # Act / Assert
    with pytest.raises(UnsafePurgeError, match="mount point"):
        plan_purge(home)


def test_plan_purge_refuses_a_dir_with_a_foreign_entry(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))
    home.config.write_text("timezone = 'UTC'\n", encoding="utf-8")
    (home.root / "thesis.txt").write_text("chapter 1", encoding="utf-8")

    # Act / Assert
    with pytest.raises(UnsafePurgeError, match=r"thesis\.txt"):
        plan_purge(home)


def test_plan_purge_refuses_an_unmarked_dir_without_known_entries(tmp_path: Path) -> None:
    # Arrange
    empty = tmp_path / "empty"
    empty.mkdir()

    # Act / Assert
    with pytest.raises(UnsafePurgeError, match="not an agent-meter home"):
        plan_purge(AppHome(root=empty))


def test_plan_purge_refuses_a_symlinked_root(tmp_path: Path) -> None:
    # Arrange
    real = AppHome.resolve(str(tmp_path / "real"))
    link = tmp_path / "link"
    link.symlink_to(real.root, target_is_directory=True)

    # Act / Assert
    with pytest.raises(UnsafePurgeError, match="symbolic link"):
        plan_purge(AppHome(root=link))


# ----------------------------------------------------------------------------- purge success


def test_purge_home_deletes_a_genuine_home(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))
    home.config.write_text("timezone = 'UTC'\n", encoding="utf-8")
    home.db.write_bytes(b"duck")
    home.ensure_dir(home.logs_dir)
    (home.logs_dir / "cli.log").write_text("collect ok\n", encoding="utf-8")
    (home.root / ".projects.yaml.x1y2.tmp").write_text("", encoding="utf-8")

    # Act
    deleted = purge_home(home)

    # Assert
    assert not home.root.exists()
    assert home.root / HOME_MARKER in deleted
    assert tmp_path.exists()


def test_purge_home_accepts_a_legacy_home_without_marker(tmp_path: Path) -> None:
    # Arrange
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    home = AppHome(root=legacy)
    home.db.write_bytes(b"duck")
    home.config.write_text("timezone = 'UTC'\n", encoding="utf-8")

    # Act
    purge_home(home)

    # Assert
    assert not legacy.exists()


def test_purge_home_unlinks_symlinked_entries_without_following_them(tmp_path: Path) -> None:
    # Arrange
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    home = AppHome.resolve(str(tmp_path / "h"))
    home.logs_dir.symlink_to(outside, target_is_directory=True)

    # Act
    purge_home(home)

    # Assert
    assert not home.root.exists()
    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep"


# ----------------------------------------------------------------------------- secret (L-4)


def test_load_secret_refuses_to_regenerate_a_corrupt_salt(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))
    home.secret.write_bytes(b"short")
    os.chmod(home.secret, 0o600)

    # Act / Assert
    with pytest.raises(SecretCorruptError, match="anonymized ids would change"):
        load_secret(home)
    assert home.secret.read_bytes() == b"short"


def test_load_secret_tightens_a_readable_secret_to_0600(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))
    original = load_secret(home)
    os.chmod(home.secret, 0o644)

    # Act
    again = load_secret(home)

    # Assert
    assert again == original
    assert stat.S_IMODE(os.stat(home.secret).st_mode) == 0o600


def test_load_secret_creation_is_atomic_and_leaves_no_temp_files(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))

    # Act
    created = load_secret(home)

    # Assert
    assert len(created) == SECRET_BYTES
    assert sorted(p.name for p in home.root.iterdir()) == sorted([HOME_MARKER, home.secret.name])
    assert stat.S_IMODE(os.stat(home.secret).st_mode) == 0o600


def test_load_secret_keeps_a_salt_created_concurrently(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: another process publishes its salt between our temp write and our publish
    home = AppHome.resolve(str(tmp_path / "h"))
    winner = b"w" * SECRET_BYTES

    def lose_the_race(_src: str, dst: str) -> None:
        Path(dst).write_bytes(winner)
        os.chmod(dst, 0o600)
        raise FileExistsError(dst)

    monkeypatch.setattr(paths.os, "link", lose_the_race)

    # Act
    salt = load_secret(home)

    # Assert
    assert salt == winner
    assert [p.name for p in home.root.iterdir() if p.name.endswith(".tmp")] == []


def test_read_secret_reports_missing_without_creating(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))

    # Act
    missing = read_secret(home)

    # Assert
    assert missing is None
    assert not home.secret.exists()
