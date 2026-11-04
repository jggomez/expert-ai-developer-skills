"""Use case: turn two commits into the set of files to review."""

from __future__ import annotations

from pr_reviewer.application.ports import DiffReader
from pr_reviewer.domain.file_selection import DEFAULT_MAX_CHARS, build_bundle
from pr_reviewer.domain.models import DiffBundle


def prepare_diff(
    reader: DiffReader,
    *,
    base: str,
    head: str,
    exclude: list[str],
    max_chars: int = DEFAULT_MAX_CHARS,
) -> DiffBundle:
    text = reader.read(base, head)
    return build_bundle(text, base=base, head=head, exclude=exclude, max_chars=max_chars)
