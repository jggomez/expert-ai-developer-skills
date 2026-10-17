"""File primitives shared by the settings merger and the scheduler.

- ``HomeLike``: the subset of ``paths.AppHome`` (contracts §3.6) these modules need, so they
  stay testable without the store layer.
- ``atomic_write``: temp file in the same directory, ``fsync``, ``os.replace``, explicit mode.
- ``install.json`` (contracts §5) load/save helpers.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Final, Protocol

__all__ = [
    "MANIFEST_VERSION",
    "HomeLike",
    "ManifestError",
    "atomic_write",
    "load_manifest",
    "save_manifest",
    "sha256_hex",
]

MANIFEST_VERSION: Final = 1


class HomeLike(Protocol):
    """Read-only view of ``paths.AppHome`` used by ``setup`` and ``scheduler``."""

    @property
    def root(self) -> Path: ...

    @property
    def backups_dir(self) -> Path: ...

    @property
    def install_manifest(self) -> Path: ...

    @property
    def logs_dir(self) -> Path: ...


class ManifestError(RuntimeError):
    """``install.json`` exists but cannot be used; it is never overwritten blindly."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path: Path, data: bytes, *, mode: int) -> None:
    """Replace ``path`` with ``data`` atomically; readers see the old or the new bytes, never a mix."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()
        raise
    _fsync_directory(path.parent)


def load_manifest(home: HomeLike) -> dict[str, Any] | None:
    """The parsed ``install.json``, or ``None`` when setup never recorded anything."""
    path = home.install_manifest
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ManifestError(
            f"{path} is not valid JSON ({exc}); fix or remove it by hand"
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("files", []), list):
        raise ManifestError(
            f"{path} does not have the install.json layout (contracts §5)"
        )
    data.setdefault("version", MANIFEST_VERSION)
    data.setdefault("files", [])
    return data


def save_manifest(home: HomeLike, manifest: dict[str, Any]) -> None:
    """Write ``install.json`` (0600), or delete it once it records nothing."""
    path = home.install_manifest
    if not manifest.get("files") and not manifest.get("scheduler"):
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
        return
    text = json.dumps(manifest, indent=2, sort_keys=False) + "\n"
    atomic_write(path, text.encode(), mode=0o600)
