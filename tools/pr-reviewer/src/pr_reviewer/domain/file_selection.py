"""Decide which changed files the agent reviews."""

from __future__ import annotations

import fnmatch
import re
from pathlib import PurePosixPath

from pr_reviewer.domain.diff_parser import parse_diff
from pr_reviewer.domain.models import DiffBundle, FileDiff, OmittedFile

DEFAULT_MAX_CHARS = 240_000

DEFAULT_EXCLUDE = (
    "*.lock",
    "*.lockb",
    "package-lock.json",
    "pnpm-lock.yaml",
    "go.sum",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.snap",
    "*.svg",
    "*.g.dart",
    "*.freezed.dart",
    "*.pb.go",
    "*_pb2.py",
    "*_pb2_grpc.py",
    "dist/*",
    "*/dist/*",
    "build/*",
    "*/build/*",
    "vendor/*",
    "*/vendor/*",
    "node_modules/*",
    "*/node_modules/*",
)

_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|(^|/)test_|_test\.|\.test\.|\.spec\.")


def is_excluded(path: str, patterns: tuple[str, ...] | list[str]) -> bool:
    """Match a pattern against the whole path or the file name."""
    name = PurePosixPath(path).name
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in patterns)


def _priority(file: FileDiff) -> tuple[bool, int]:
    return (bool(_TEST_PATH.search(file.path)), len(file.patch))


def build_bundle(
    text: str,
    *,
    base: str,
    head: str,
    exclude: list[str],
    max_chars: int = DEFAULT_MAX_CHARS,
) -> DiffBundle:
    """Choose the files to review: source first, then smallest, within the size budget."""
    patterns = [*DEFAULT_EXCLUDE, *exclude]
    selected: list[FileDiff] = []
    omitted: list[OmittedFile] = []

    candidates: list[FileDiff] = []
    for file in parse_diff(text):
        if file.deleted:
            omitted.append(OmittedFile(path=file.path, reason="deleted"))
        elif file.binary:
            omitted.append(OmittedFile(path=file.path, reason="binary"))
        elif is_excluded(file.path, patterns):
            omitted.append(OmittedFile(path=file.path, reason="excluded"))
        elif file.commentable_lines:
            candidates.append(file)

    used = 0
    for file in sorted(candidates, key=_priority):
        if used + len(file.patch) <= max_chars:
            selected.append(file)
            used += len(file.patch)
        else:
            omitted.append(OmittedFile(path=file.path, reason="size-limit"))

    return DiffBundle(base=base, head=head, files=selected, omitted=omitted)
