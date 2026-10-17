"""The ``HostReader`` port and reader discovery helpers (contracts §3.1)."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Final, Protocol, runtime_checkable

from agent_meter.model import (
    Host,
    ReaderOptions,
    SessionUnit,
    UnitBatch,
    UntrackedRecord,
)

__all__ = [
    "HostReader",
    "available_readers",
    "default_roots",
    "host_from_transcript_path",
]

_ANTIGRAVITY_DIRS: Final = {
    "antigravity-cli": Host.ANTIGRAVITY_CLI,
    "antigravity-ide": Host.ANTIGRAVITY_IDE,
    "antigravity": Host.ANTIGRAVITY_APP,
}


@runtime_checkable
class HostReader(Protocol):
    host: Host
    root: Path

    def discover(self) -> Iterator[SessionUnit]:
        """Stat-only enumeration of session units; never parses content."""
        ...

    def find_unit(self, session_or_conversation_id: str) -> SessionUnit | None:
        """The unit containing this session/conversation id (a child id maps to its root unit)."""
        ...

    def read_unit(self, unit: SessionUnit, options: ReaderOptions) -> UnitBatch:
        """Parse one unit; data errors become diagnostics and never raise."""
        ...

    def untracked(self) -> list[UntrackedRecord]:
        """Conversations whose usage cannot be recovered (BR-22)."""
        ...

    def earliest_available(self) -> date | None:
        """Earliest date still retained by the host (BR-15, for ``doctor``)."""
        ...


def default_roots() -> dict[Host, Path]:
    """Host data roots: ``$CLAUDE_CONFIG_DIR`` or ``~/.claude``, and the three Antigravity roots."""
    home = Path(os.environ.get("HOME") or Path.home())
    claude = os.environ.get("CLAUDE_CONFIG_DIR")
    gemini = home / ".gemini"
    return {
        Host.CLAUDE_CODE: Path(claude) if claude else home / ".claude",
        Host.ANTIGRAVITY_CLI: gemini / "antigravity-cli",
        Host.ANTIGRAVITY_IDE: gemini / "antigravity-ide",
        Host.ANTIGRAVITY_APP: gemini / "antigravity",
    }


def available_readers(roots: Mapping[Host, Path] | None = None) -> list[HostReader]:
    """Readers for every host whose root directory exists, in ``Host`` declaration order."""
    from agent_meter.readers.antigravity import AntigravityReader
    from agent_meter.readers.claude_code import ClaudeCodeReader

    selected = default_roots() if roots is None else dict(roots)
    readers: list[HostReader] = []
    for host in Host:
        root = selected.get(host)
        if root is None or not root.is_dir():
            continue
        readers.append(
            ClaudeCodeReader(root)
            if host is Host.CLAUDE_CODE
            else AntigravityReader(host, root)
        )
    return readers


def host_from_transcript_path(path: str) -> Host | None:
    """Infer the host from a hook ``transcript_path``/``transcriptPath`` value."""
    if not path:
        return None
    parts = PurePosixPath(path).parts
    for part in parts:
        if part in _ANTIGRAVITY_DIRS:
            return _ANTIGRAVITY_DIRS[part]
    if path.endswith(".jsonl") and ("projects" in parts or ".claude" in parts):
        return Host.CLAUDE_CODE
    return None
