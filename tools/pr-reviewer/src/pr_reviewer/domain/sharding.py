"""Split a large diff into groups that one agent each can review well."""

from __future__ import annotations

import math

from pr_reviewer.domain.models import DiffBundle, FileDiff

DEFAULT_MAX_SHARDS = 4
SHARD_TARGET_CHARS = 60_000


def split_into_shards(bundle: DiffBundle, max_shards: int = DEFAULT_MAX_SHARDS) -> list[DiffBundle]:
    """Keep neighboring paths together, because related changes tend to share a directory."""
    total = sum(len(file.patch) for file in bundle.files)
    if total <= SHARD_TARGET_CHARS or max_shards <= 1 or len(bundle.files) <= 1:
        return [bundle]
    target = max(SHARD_TARGET_CHARS, math.ceil(total / max_shards))

    groups: list[list[FileDiff]] = [[]]
    used = 0
    for file in sorted(bundle.files, key=lambda f: f.path):
        if groups[-1] and used + len(file.patch) > target and len(groups) < max_shards:
            groups.append([])
            used = 0
        groups[-1].append(file)
        used += len(file.patch)
    return [bundle.model_copy(update={"files": group, "omitted": []}) for group in groups]
