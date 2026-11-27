"""A map of the areas a pull request touched, built from the diff.

The model only describes areas the diff already has: its paths are matched to areas computed
here, and anything that matches no area is dropped. The text it writes stays untrusted and is
sanitized where it is rendered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath

from pr_reviewer.domain.models import (
    SEVERITY_RANK,
    DiffBundle,
    Finding,
    PullRequestSummary,
    Severity,
)

MAX_AREAS = 8
MAX_LINKS = 8
ROOT = "(root)"
OTHER = "other"


@dataclass
class Area:
    name: str
    added: int = 0
    deleted: int = 0
    files: int = 0
    what: str = ""
    severity: Severity | None = None


@dataclass
class ChangeMap:
    overview: str = ""
    areas: list[Area] = field(default_factory=list)
    links: list[tuple[int, int]] = field(default_factory=list)


def _folder(path: str) -> tuple[str, ...]:
    return PurePosixPath(path).parent.parts


def _prefix_depth(paths: list[str]) -> int:
    """How many leading folders to keep so that the files split into more than one area."""
    folders = [_folder(path) for path in paths]
    depth = 1
    while True:
        keys = {folder[:depth] for folder in folders}
        if len(keys) > 1 or all(len(folder) <= depth for folder in folders):
            return depth
        depth += 1


def _area_name(path: str, depth: int) -> str:
    folder = _folder(path)[:depth]
    return "/".join(folder) if folder else ROOT


def _line_counts(patch: str) -> tuple[int, int]:
    added = deleted = 0
    for line in patch.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1
    return added, deleted


def _group(bundle: DiffBundle) -> tuple[list[Area], dict[str, str]]:
    """Areas in name order, at most MAX_AREAS, plus the area of every file."""
    paths = [file.path for file in bundle.files]
    depth = _prefix_depth(paths) if paths else 1
    areas: dict[str, Area] = {}
    owner: dict[str, str] = {}
    for file in bundle.files:
        name = _area_name(file.path, depth)
        area = areas.setdefault(name, Area(name))
        added, deleted = _line_counts(file.patch)
        area.added, area.deleted, area.files = area.added + added, area.deleted + deleted, area.files + 1
        owner[file.path] = name
    if len(areas) > MAX_AREAS:
        by_size = sorted(areas.values(), key=lambda a: (-(a.added + a.deleted), a.name))
        kept = {a.name for a in by_size[: MAX_AREAS - 1]}
        other = Area(OTHER)
        for area in by_size[MAX_AREAS - 1 :]:
            other.added, other.deleted, other.files = other.added + area.added, other.deleted + area.deleted, other.files + area.files
        owner = {path: name if name in kept else OTHER for path, name in owner.items()}
        return [*sorted((areas[name] for name in kept), key=lambda a: a.name), other], owner
    return sorted(areas.values(), key=lambda a: a.name), owner


def _match(path: str, areas: list[Area], owner: dict[str, str]) -> int | None:
    """The area a model path names: a changed file, a folder inside one area, or one area's folder."""
    clean = path.strip().strip("/")
    index = {area.name: i for i, area in enumerate(areas)}
    if clean in owner:
        return index[owner[clean]]
    if clean in index:
        return index[clean]
    inside = {owner[p] for p in owner if p.startswith(clean + "/")}
    if len(inside) == 1:
        return index[inside.pop()]
    return None


def build_change_map(bundle: DiffBundle, summary: PullRequestSummary | None, findings: list[Finding]) -> ChangeMap:
    areas, owner = _group(bundle)
    index = {area.name: i for i, area in enumerate(areas)}
    for item in findings:
        if item.file not in owner:
            continue
        area = areas[index[owner[item.file]]]
        if area.severity is None or SEVERITY_RANK[item.severity] < SEVERITY_RANK[area.severity]:
            area.severity = item.severity
    if summary is None:
        return ChangeMap(areas=areas)
    for change in summary.changes:
        target = _match(change.path, areas, owner)
        if target is not None and not areas[target].what:
            areas[target].what = change.what
    links: list[tuple[int, int]] = []
    for link in summary.links:
        source, target = _match(link.source, areas, owner), _match(link.target, areas, owner)
        if source is None or target is None or source == target or (source, target) in links:
            continue
        links.append((source, target))
    return ChangeMap(overview=summary.overview, areas=areas, links=links[:MAX_LINKS])
