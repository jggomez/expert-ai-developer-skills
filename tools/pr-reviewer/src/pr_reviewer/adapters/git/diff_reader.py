"""Read diffs with the git command."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")


def _require_sha(sha: str) -> None:
    if not _SHA.fullmatch(sha):
        raise ValueError(f"Expected a full commit SHA, got {sha!r}")


class GitDiffReader:
    def __init__(self, repo: Path):
        self._repo = repo

    def read_file(self, commit: str, path: str) -> str:
        """Read a file as it is in a commit, whatever the checkout holds."""
        _require_sha(commit)
        completed = subprocess.run(
            ["git", "cat-file", "blob", f"{commit}:{path}"],
            cwd=self._repo,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise ValueError(f"{path} does not exist in the base commit {commit[:7]}")
        return completed.stdout.decode("utf-8", "replace")

    def read(self, base: str, head: str) -> str:
        """Return the three-dot diff between two commits.

        External diff drivers and textconv are disabled because both can be
        configured to run commands, and the repository content is untrusted.
        """
        _require_sha(base)
        _require_sha(head)
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
