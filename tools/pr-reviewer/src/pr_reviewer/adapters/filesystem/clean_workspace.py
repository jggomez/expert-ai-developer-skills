"""Build the directory the agent is allowed to read.

Agent harnesses discover instruction files such as AGENTS.md, GEMINI.md or
.agents/ in their workspace, so a pull request could inject instructions by
adding one. Symlinks could also point file tools outside the workspace. The
agent therefore never sees the checkout, only this filtered copy.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

_BLOCKED_DIRS = frozenset(
    {".git", ".agents", ".agent", "_agents", "_agent", ".gemini", ".claude", ".antigravity-plugin"}
)
_BLOCKED_FILES = frozenset({"agents.md", "agent.md", "gemini.md", "claude.md", ".antigravityignore"})


def _ignored(directory: str, names: Iterable[str]) -> set[str]:
    root = Path(directory)
    ignored: set[str] = set()
    for name in names:
        path = root / name
        lowered = name.lower()
        if path.is_symlink() or lowered in _BLOCKED_FILES or (lowered in _BLOCKED_DIRS and path.is_dir()):
            ignored.add(name)
    return ignored


def build_clean_workspace(repo: Path, dest: Path) -> Path:
    """Copy `repo` to `dest` without instruction files, git metadata or symlinks."""
    shutil.copytree(repo, dest, ignore=_ignored, symlinks=True)
    return dest.resolve()
