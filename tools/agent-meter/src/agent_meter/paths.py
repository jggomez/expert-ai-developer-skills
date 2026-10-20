"""Locations of every agent-meter file (contracts §3.6). Standard library only.

The application home is ``--home`` > ``$AGENT_METER_HOME`` > ``~/.agent-meter``. When
agent-meter creates it, the directory gets mode ``0700`` and a marker file
``.agent-meter-home``; an existing directory is only re-chmodded when it holds the marker,
so pointing ``--home`` at a foreign directory never changes its permissions.

Purge rule (``uninstall --purge``, H-1): the root is refused when it is the filesystem
root, the user's home directory, an ancestor of it, a mount point or a symbolic link, and
when it holds any entry outside the known agent-meter set. A root must carry the marker,
except a legacy home created by builds that predate the marker: it is accepted when it
holds at least one known entry and nothing else. Only known entries are deleted, then the
root is removed with ``rmdir``.

This module is imported by the hook fast path, so it must never import third-party
packages.
"""

from __future__ import annotations

import errno
import os
import secrets
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = [
    "HOME_ENV",
    "HOME_MARKER",
    "KNOWN_HOME_ENTRIES",
    "SECRET_BYTES",
    "AppHome",
    "SecretCorruptError",
    "UnsafePurgeError",
    "atomic_write_text",
    "is_known_home_entry",
    "load_secret",
    "plan_purge",
    "purge_home",
    "read_secret",
]

HOME_ENV: Final = "AGENT_METER_HOME"
HOME_MARKER: Final = ".agent-meter-home"
SECRET_BYTES: Final = 32
_DIR_MODE: Final = 0o700
_FILE_MODE: Final = 0o600
_TEMP_SUFFIX: Final = ".tmp"

_DB_NAME: Final = "meter.duckdb"
_LOCK_NAME: Final = "lock"
_CONFIG_NAME: Final = "config.toml"
_PROJECTS_NAME: Final = "projects.yaml"
_PRICING_LOCAL_NAME: Final = "pricing.local.yaml"
_SECRET_NAME: Final = "secret"
_INSTALL_NAME: Final = "install.json"
_LAST_SUMMARY_NAME: Final = "last-summary.txt"
_REPORT_NAME: Final = "report.html"
_STATE_DIR_NAME: Final = "state"
_LOGS_DIR_NAME: Final = "logs"
_BACKUPS_DIR_NAME: Final = "backups"
_OUTBOX_DIR_NAME: Final = "outbox"

KNOWN_HOME_ENTRIES: Final[frozenset[str]] = frozenset({
    HOME_MARKER,
    _DB_NAME,
    f"{_DB_NAME}.wal",
    f"{_DB_NAME}{_TEMP_SUFFIX}",
    _LOCK_NAME,
    _CONFIG_NAME,
    _PROJECTS_NAME,
    _PRICING_LOCAL_NAME,
    _SECRET_NAME,
    _INSTALL_NAME,
    _LAST_SUMMARY_NAME,
    _REPORT_NAME,
    _STATE_DIR_NAME,
    _LOGS_DIR_NAME,
    _BACKUPS_DIR_NAME,
    _OUTBOX_DIR_NAME,
})
"""Every top-level name agent-meter may create in its home (plus ``*.tmp`` atomic-write files)."""
_FOREIGN_NAMES_SHOWN: Final = 3


class UnsafePurgeError(Exception):
    """``uninstall --purge`` refused because the target is not provably an agent-meter home."""


class SecretCorruptError(Exception):
    """``~/.agent-meter/secret`` exists but is not a valid salt; it is never silently regenerated."""


def is_known_home_entry(name: str) -> bool:
    """True when ``name`` is a top-level entry agent-meter itself creates in its home."""
    return name in KNOWN_HOME_ENTRIES or (name.startswith(".") and name.endswith(_TEMP_SUFFIX))


@dataclass(frozen=True, slots=True)
class AppHome:
    root: Path

    @property
    def db(self) -> Path:
        return self.root / _DB_NAME

    @property
    def lock(self) -> Path:
        return self.root / _LOCK_NAME

    @property
    def config(self) -> Path:
        return self.root / _CONFIG_NAME

    @property
    def projects(self) -> Path:
        return self.root / _PROJECTS_NAME

    @property
    def pricing_local(self) -> Path:
        return self.root / _PRICING_LOCAL_NAME

    @property
    def secret(self) -> Path:
        return self.root / _SECRET_NAME

    @property
    def install_manifest(self) -> Path:
        return self.root / _INSTALL_NAME

    @property
    def state_dir(self) -> Path:
        return self.root / _STATE_DIR_NAME

    @property
    def snapshot(self) -> Path:
        return self.state_dir / "snapshot.json"

    @property
    def notified(self) -> Path:
        return self.state_dir / "notified.json"

    @property
    def last_summary(self) -> Path:
        return self.root / _LAST_SUMMARY_NAME

    @property
    def logs_dir(self) -> Path:
        return self.root / _LOGS_DIR_NAME

    @property
    def backups_dir(self) -> Path:
        return self.root / _BACKUPS_DIR_NAME

    @property
    def outbox_dir(self) -> Path:
        return self.root / _OUTBOX_DIR_NAME

    @property
    def report(self) -> Path:
        return self.root / _REPORT_NAME

    @property
    def marker(self) -> Path:
        return self.root / HOME_MARKER

    @classmethod
    def resolve(cls, cli_home: str | None = None) -> AppHome:
        """``--home`` wins over ``$AGENT_METER_HOME``, which wins over ``~/.agent-meter``."""
        chosen = cli_home or os.environ.get(HOME_ENV)
        if chosen:
            root = Path(chosen).expanduser()
        else:
            user_home = (
                os.environ.get("HOME")
                or os.environ.get("USERPROFILE")
                or str(Path.home())
            )
            root = Path(user_home) / ".agent-meter"
        home = cls(root=Path(os.path.abspath(root)))
        try:
            home.root.mkdir(parents=True, mode=_DIR_MODE)
        except FileExistsError:
            # An existing directory is only tightened when agent-meter marked it as its own.
            if home.marker.is_file():
                os.chmod(home.root, _DIR_MODE)
            return home
        fd = os.open(home.marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _FILE_MODE)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("agent-meter home directory; see 'agent-meter uninstall --purge'\n")
        os.chmod(home.root, _DIR_MODE)
        return home

    def ensure_dir(self, directory: Path) -> Path:
        """Create one of the home sub-directories with mode ``0700`` and return it."""
        directory.mkdir(parents=True, exist_ok=True, mode=_DIR_MODE)
        return directory


def atomic_write_text(path: Path, text: str, *, mode: int = _FILE_MODE) -> None:
    """Write ``text`` via a same-directory temp file, ``fsync`` and ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=_DIR_MODE)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def read_secret(home: AppHome) -> bytes | None:
    """The existing local salt, or ``None`` when it was never created. Never creates or rewrites it.

    A readable-by-others secret is tightened to ``0600``. A salt of the wrong length raises
    :class:`SecretCorruptError`: regenerating it would silently change every description hash
    and anonymized id, so the user must restore it (or delete it knowingly).
    """
    try:
        fd = os.open(home.secret, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as handle:
        if (
            hasattr(os, "fchmod")
            and stat.S_IMODE(os.fstat(handle.fileno()).st_mode) != _FILE_MODE
        ):
            os.fchmod(handle.fileno(), _FILE_MODE)
        data = handle.read(SECRET_BYTES + 1)
    if len(data) != SECRET_BYTES:
        raise SecretCorruptError(
            f"secret corrupt; anonymized ids would change ({home.secret} holds {len(data)} bytes, "
            f"expected {SECRET_BYTES}); restore it from a backup, or delete it to start new ids"
        )
    return data


def load_secret(home: AppHome) -> bytes:
    """The local salt (32 random bytes, mode ``0600``), created on first use; never uploaded.

    Creation is atomic and never clobbers: the salt goes to a same-directory temp file opened
    with ``O_CREAT | O_EXCL``, is ``fsync``-ed, then published with ``os.link`` (which fails if
    the target exists, unlike ``os.replace``). A process that loses a creation race therefore
    adopts the winner's salt instead of overwriting it.
    """
    existing = read_secret(home)
    if existing is not None:
        return existing
    data = secrets.token_bytes(SECRET_BYTES)
    tmp_path = home.root / f".{_SECRET_NAME}.{secrets.token_hex(6)}{_TEMP_SUFFIX}"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _FILE_MODE)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, _FILE_MODE)
        try:
            os.link(tmp_path, home.secret)
        except FileExistsError:
            winner = read_secret(home)
            if winner is None:
                raise
            return winner
        except OSError as exc:
            if (
                os.name == "nt"
                and exc.errno != errno.EEXIST
                and not home.secret.exists()
            ):
                os.replace(tmp_path, home.secret)
            else:
                raise
        _fsync_dir(home.root)
        return data
    finally:
        tmp_path.unlink(missing_ok=True)


def _fsync_dir(directory: Path) -> None:
    if os.name == "nt":
        return
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _user_home_candidates() -> set[str]:
    """Every spelling of the user's home: ``$HOME``, ``$USERPROFILE``, ``~`` and the passwd entry (real paths)."""
    spellings = [
        os.environ.get("HOME", ""),
        os.environ.get("USERPROFILE", ""),
        os.path.expanduser("~"),
    ]
    candidates = {os.path.realpath(value) for value in spellings if value and value != "~"}
    if not hasattr(os, "getuid"):
        return candidates
    try:
        import pwd
    except ImportError:
        return candidates  # no passwd database on this platform: $HOME and "~" are the checks
    try:
        candidates.add(os.path.realpath(pwd.getpwuid(os.getuid()).pw_dir))
    except KeyError:
        return candidates  # uid without a passwd entry (containers): $HOME and "~" are the checks
    return candidates


def _refuse_dangerous_location(root: Path) -> str:
    """Raise :class:`UnsafePurgeError` for locations that must never be purged; return the real path."""
    if root.is_symlink():
        raise UnsafePurgeError(f"{root} is a symbolic link")
    real = os.path.realpath(root)
    if os.path.dirname(real) == real:
        raise UnsafePurgeError(f"{root} is the filesystem root")
    for user_home in _user_home_candidates():
        if real == user_home:
            raise UnsafePurgeError(f"{root} is your home directory")
        if os.path.commonpath([real, user_home]) == real:
            raise UnsafePurgeError(f"{root} contains your home directory")
    if os.path.ismount(real):
        raise UnsafePurgeError(f"{root} is a mount point")
    if not os.path.isdir(real):
        raise UnsafePurgeError(f"{root} is not a directory")
    return real


def plan_purge(home: AppHome) -> list[Path]:
    """Validate ``home`` for ``uninstall --purge`` and return the entries that would be deleted.

    Never deletes anything. Raises :class:`UnsafePurgeError` with a user-facing reason.
    """
    _refuse_dangerous_location(home.root)
    entries = sorted(home.root.iterdir(), key=lambda entry: entry.name)
    foreign = [entry.name for entry in entries if not is_known_home_entry(entry.name)]
    if foreign:
        shown = ", ".join(foreign[:_FOREIGN_NAMES_SHOWN])
        more = f" and {len(foreign) - _FOREIGN_NAMES_SHOWN} more" if len(foreign) > _FOREIGN_NAMES_SHOWN else ""
        raise UnsafePurgeError(f"{home.root} holds entries agent-meter did not create: {shown}{more}")
    if not home.marker.is_file() and not entries:
        raise UnsafePurgeError(f"{home.root} is not an agent-meter home (no {HOME_MARKER} marker, no data)")
    return entries


def purge_home(home: AppHome) -> list[Path]:
    """Delete only the known agent-meter entries of ``home``, then ``rmdir`` the root.

    The marker is removed last so an interrupted purge can be re-run. Symbolic links are
    unlinked, never followed. Returns the deleted top-level entries.
    """
    entries = plan_purge(home)
    ordered = [entry for entry in entries if entry.name != HOME_MARKER]
    ordered += [entry for entry in entries if entry.name == HOME_MARKER]
    for entry in ordered:
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    home.root.rmdir()
    return entries
