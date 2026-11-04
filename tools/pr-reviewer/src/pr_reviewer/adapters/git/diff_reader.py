"""Read diffs with the git command."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")


class GitDiffReader:
    def __init__(self, repo: Path):
        self._repo = repo

    def read(self, base: str, head: str) -> str:
        """Return the three-dot diff between two commits.

        External diff drivers and textconv are disabled because both can be
        configured to run commands, and the repository content is untrusted.
        """
        for sha in (base, head):
            if not _SHA.fullmatch(sha):
                raise ValueError(f"Expected a full commit SHA, got {sha!r}")
        completed = subprocess.run(
            [
                "git",
                "-c",
                "core.quotePath=false",
                "diff",
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--find-renames",
                f"{base}...{head}",
            ],
            cwd=self._repo,
            check=True,
            capture_output=True,
        )
        # Decoded from bytes: text mode would turn a lone CR in a file into a new line.
        return completed.stdout.decode("utf-8", "replace")
