"""Workspace path → project identity (ADR §3.7, BR-07/BR-08, contracts §3.5).

A project is keyed by its normalized ``origin`` remote (``git:<16 hex>``), else by the
real path of the main repository or directory (``path:<16 hex>``), else
``(unassigned)``. Only path *hashes* are ever handed to the store (``PathCache``).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Final, Literal, Protocol
from urllib.parse import unquote, urlsplit

import yaml

from agent_meter.model import ProjectRef

__all__ = [
    "DEFAULT_TEMP_ROOTS",
    "UNASSIGNED",
    "PathCache",
    "ProjectOverride",
    "ProjectResolver",
    "ProjectsConfig",
    "ProjectsConfigError",
    "load_projects_config",
    "normalize_remote",
    "path_hash",
    "save_projects_config",
]

_LOG = logging.getLogger(__name__)

UNASSIGNED_ID: Final = "(unassigned)"
UNASSIGNED: Final = ProjectRef(
    project_id=UNASSIGNED_ID,
    kind="unassigned",
    display_name=UNASSIGNED_ID,
    remote_url=None,
)
DEFAULT_TEMP_ROOTS: Final = (
    "/tmp",
    "/private/tmp",
    "/var/folders",
    "/private/var/folders",
)
_WORKTREE_SEGMENTS: Final = ("/.claude/worktrees/", "/.worktrees/", "/worktrees/")
_SCP_REMOTE: Final = re.compile(r"^(?:[^@/\s]+@)?(?P<host>[^:/\s@]+):(?P<path>[^\s]+)$")
_TOP_KEYS: Final = frozenset({"version", "projects", "paths", "ignore", "merges"})
_OVERRIDE_KEYS: Final = frozenset(
    {"display_name", "client", "billing", "rate", "fixed_price", "currency"}
)
_BILLING: Final = ("hourly", "fixed")
_AMBIGUOUS: Final = "?"


class PathCache(Protocol):
    def get(self, path_hash: str) -> str | None: ...

    def put(self, path_hash: str, project_id: str) -> None: ...


@dataclass(frozen=True, slots=True)
class ProjectOverride:
    display_name: str | None = None
    client: str | None = None
    billing: Literal["hourly", "fixed"] | None = None
    rate: Decimal | None = None
    fixed_price: Decimal | None = None
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectsConfig:
    projects: Mapping[str, ProjectOverride]
    path_aliases: Mapping[str, str]
    ignore: tuple[str, ...]
    merges: Mapping[str, str]  # old project_id → surviving project_id


class ProjectsConfigError(ValueError):
    """``projects.yaml`` is invalid; ``errors`` lists every problem found."""

    errors: list[str]

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) or "invalid projects.yaml")


# ----------------------------------------------------------------------------- pure helpers


def normalize_remote(url: str) -> str | None:
    """Credential-free ``host/owner/repo`` for SSH, SCP-like and HTTP(S) remotes.

    Local paths and ``file://`` remotes return ``None`` (they are not portable identities).
    """
    text = url.strip()
    if not text:
        return None
    if "://" in text:
        parts = urlsplit(text)
        if parts.scheme.lower() == "file":
            return None
        host = parts.hostname or ""
        path = parts.path
    else:
        match = _SCP_REMOTE.match(text)
        if match is None:
            return None
        host, path = match.group("host").lower(), match.group("path")
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")].rstrip("/")
    if not host or not path:
        return None
    return f"{host}/{path}"


def _real(path: str) -> str:
    return os.path.realpath(os.path.abspath(path))


def path_hash(path: str) -> str:
    """SHA-256 hex of the real (or absolute, if missing) path."""
    return hashlib.sha256(_real(path).encode("utf-8")).hexdigest()


def _location_key(kind: str, name: str) -> str:
    """Hashed relocation-index key (only hashes reach the store, like ``path_hash``)."""
    return hashlib.sha256(f"{kind}:{name}".encode()).hexdigest()


def _short(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _is_under(path: str, root: str) -> bool:
    root = root.rstrip("/") or "/"
    return path == root or path.startswith(root + "/")


def _kind_of(project_id: str) -> Literal["remote", "path", "unassigned"]:
    if project_id.startswith("git:"):
        return "remote"
    if project_id.startswith("path:"):
        return "path"
    return "unassigned"


# ----------------------------------------------------------------------------- resolver


class ProjectResolver:
    """Resolve workspace paths (plain or ``file://``) to ``ProjectRef`` values."""

    def __init__(
        self,
        cache: PathCache,
        config: ProjectsConfig,
        *,
        home: Path,
        git_timeout_s: float = 2.0,
        temp_roots: Sequence[str] | None = None,
    ) -> None:
        self._cache = cache
        self._config = config
        self._git_timeout_s = git_timeout_s
        self._home = {os.path.abspath(home), _real(str(home))}
        roots = (
            [*DEFAULT_TEMP_ROOTS, os.environ.get("TMPDIR", "")]
            if temp_roots is None
            else list(temp_roots)
        )
        self._temp_roots = tuple(
            {
                form
                for root in roots
                if root and root.strip("/")
                for form in (os.path.abspath(root), _real(root))
            }
        )
        self._ignore = tuple(
            {form for p in config.ignore for form in (os.path.abspath(p), _real(p))}
        )
        self._aliases = sorted(
            ((os.path.abspath(p), pid) for p, pid in config.path_aliases.items()),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        self._memo: dict[str, ProjectRef] = {}
        self._known: dict[str, ProjectRef] = {}

    def resolve(self, path: str | None) -> ProjectRef:
        directory = self._to_directory(path)
        if directory is None:
            return UNASSIGNED
        if directory not in self._memo:
            self._memo[directory] = self._apply_config(
                self._resolve_directory(directory)
            )
        return self._memo[directory]

    # -- input handling

    @staticmethod
    def _to_directory(path: str | None) -> str | None:
        if path is None or not path.strip():
            return None
        text = path.strip()
        if text.lower().startswith("file://"):
            text = unquote(urlsplit(text).path)
            if not text:
                return None
        return os.path.normpath(os.path.abspath(text))

    def _is_unassigned(self, directory: str) -> bool:
        forms = {directory, _real(directory)}
        if "/" in forms or forms & self._home:
            return True
        return any(
            _is_under(form, root)
            for form in forms
            for root in (*self._temp_roots, *self._ignore)
        )

    # -- resolution steps

    def _resolve_directory(self, directory: str) -> ProjectRef:
        if self._is_unassigned(directory):
            return UNASSIGNED
        for prefix, project_id in self._aliases:
            if _is_under(directory, prefix):
                return self._ref_from_id(project_id, directory)
        if os.path.isdir(directory):
            ref = self._resolve_git(directory) or self._path_ref(directory)
            self._cache.put(path_hash(directory), ref.project_id)
            self._index_existing(directory, ref)
            return ref
        cached = self._cache.get(path_hash(directory))
        if cached is not None:
            return self._ref_from_id(cached, directory)
        worktree_prefix = self._worktree_prefix(directory)
        if worktree_prefix is not None:
            return self._resolve_directory(worktree_prefix)
        return self._relocated(directory)

    # -- moved directories (BR-07): a path that no longer exists keeps the project of the
    # folder it was moved to, matched by folder name (unique among existing folders) or by
    # ``parent/name`` among other vanished locations.

    def _index_existing(self, directory: str, ref: ProjectRef) -> None:
        self._known[ref.project_id] = ref
        key = _location_key("dir", os.path.basename(directory))
        previous = self._cache.get(key)
        if previous is None:
            self._cache.put(key, ref.project_id)
        elif previous not in (ref.project_id, _AMBIGUOUS):
            self._cache.put(key, _AMBIGUOUS)

    def _relocated(self, directory: str) -> ProjectRef:
        moved_to = self._cache.get(_location_key("dir", os.path.basename(directory)))
        if moved_to is not None and moved_to != _AMBIGUOUS:
            return self._known.get(moved_to) or self._ref_from_id(moved_to, directory)
        tail = "/".join(directory.rstrip("/").split("/")[-2:])
        gone_key = _location_key("gone", tail)
        seen = self._cache.get(gone_key)
        if seen is not None:
            return self._ref_from_id(seen, directory)
        ref = self._path_ref(directory)
        self._cache.put(gone_key, ref.project_id)
        return ref

    @staticmethod
    def _worktree_prefix(directory: str) -> str | None:
        candidate = directory + "/"
        positions = [
            candidate.find(seg) for seg in _WORKTREE_SEGMENTS if seg in candidate
        ]
        if not positions:
            return None
        prefix = candidate[: min(positions)]
        return prefix or None

    def _resolve_git(self, directory: str) -> ProjectRef | None:
        out = self._git(
            directory,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
            "--show-toplevel",
        )
        lines = out.splitlines() if out else []
        if len(lines) < 2:
            return None
        common_dir, toplevel = lines[0].strip(), lines[1].strip()
        main_repo = (
            os.path.dirname(common_dir)
            if os.path.basename(common_dir) == ".git"
            else toplevel
        )
        remote = self._git(main_repo, "remote", "get-url", "origin")
        normalized = normalize_remote(remote) if remote else None
        if normalized is None:
            return self._path_ref(main_repo)
        return ProjectRef(
            project_id="git:" + _short(normalized),
            kind="remote",
            display_name=normalized.rsplit("/", 1)[-1],
            remote_url=normalized,
        )

    def _git(self, cwd: str, *args: str) -> str | None:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
        try:
            completed = subprocess.run(
                ["git", "-C", cwd, *args],
                capture_output=True,
                text=True,
                timeout=self._git_timeout_s,
                env=env,
                stdin=subprocess.DEVNULL,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("git %s unavailable: %s", args[0], type(exc).__name__)
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.strip() or None

    @staticmethod
    def _path_ref(directory: str) -> ProjectRef:
        real = _real(directory)
        return ProjectRef(
            project_id="path:" + _short(real),
            kind="path",
            display_name=os.path.basename(real) or real,
            remote_url=None,
        )

    @staticmethod
    def _ref_from_id(project_id: str, directory: str) -> ProjectRef:
        kind = _kind_of(project_id)
        if kind == "unassigned":
            return UNASSIGNED
        return ProjectRef(
            project_id=project_id,
            kind=kind,
            display_name=os.path.basename(directory) or directory,
            remote_url=None,
        )

    def _apply_config(self, ref: ProjectRef) -> ProjectRef:
        project_id = ref.project_id
        visited = {project_id}
        while project_id in self._config.merges:
            target = self._config.merges[project_id]
            if target in visited:
                break
            visited.add(target)
            project_id = target
        if project_id == UNASSIGNED_ID:
            return UNASSIGNED
        override = self._config.projects.get(project_id)
        display_name = (
            override.display_name
            if override and override.display_name
            else ref.display_name
        )
        if project_id == ref.project_id:
            return ProjectRef(project_id, ref.kind, display_name, ref.remote_url)
        return ProjectRef(project_id, _kind_of(project_id), display_name, None)


# ----------------------------------------------------------------------------- projects.yaml


def _empty_config() -> ProjectsConfig:
    return ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={})


def _money(value: Any, where: str, errors: list[str]) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        errors.append(f"{where}: money must be a quoted decimal string")
        return None
    try:
        amount = Decimal(str(value).strip())
    except InvalidOperation:
        errors.append(f"{where}: {value!r} is not a valid decimal")
        return None
    if not amount.is_finite() or amount < 0:
        errors.append(f"{where}: {value!r} must be a non-negative decimal")
        return None
    return amount


def _optional_str(
    body: Mapping[str, Any], key: str, where: str, errors: list[str]
) -> str | None:
    value = body.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{where}.{key}: must be a string")
        return None
    return value


def _parse_override(
    project_id: Any, body: Any, errors: list[str]
) -> ProjectOverride | None:
    where = f"projects.{project_id}"
    if not isinstance(project_id, str) or not isinstance(body, Mapping):
        errors.append(f"{where}: must map a project id string to a mapping")
        return None
    unknown = [k for k in body if k not in _OVERRIDE_KEYS]
    errors.extend(f"{where}: unknown key {k!r}" for k in unknown)
    billing = body.get("billing")
    if billing is not None and billing not in _BILLING:
        errors.append(f"{where}.billing: must be one of {list(_BILLING)}")
        billing = None
    rate = (
        _money(body["rate"], f"{where}.rate", errors)
        if body.get("rate") is not None
        else None
    )
    fixed = (
        _money(body["fixed_price"], f"{where}.fixed_price", errors)
        if body.get("fixed_price") is not None
        else None
    )
    return ProjectOverride(
        display_name=_optional_str(body, "display_name", where, errors),
        client=_optional_str(body, "client", where, errors),
        billing=billing,
        rate=rate,
        fixed_price=fixed,
        currency=_optional_str(body, "currency", where, errors),
    )


def _string_map(value: Any, where: str, errors: list[str]) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        errors.append(f"{where}: must be a mapping of strings to strings")
        return {}
    return dict(value)


def load_projects_config(path: Path) -> ProjectsConfig:
    """Parse ``projects.yaml``; a missing or empty file yields an empty config."""
    if not path.exists():
        return _empty_config()
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProjectsConfigError(
            [f"{path.name}: invalid YAML ({type(exc).__name__})"]
        ) from exc
    if doc is None:
        return _empty_config()
    if not isinstance(doc, Mapping):
        raise ProjectsConfigError([f"{path.name}: document must be a mapping"])
    errors: list[str] = [f"unknown key {k!r}" for k in doc if k not in _TOP_KEYS]
    if doc.get("version") != 1:
        errors.append(f"version must be 1, got {doc.get('version')!r}")
    projects_raw = doc.get("projects") or {}
    if not isinstance(projects_raw, Mapping):
        errors.append("projects: must be a mapping")
        projects_raw = {}
    projects: dict[str, ProjectOverride] = {}
    for project_id, body in projects_raw.items():
        override = _parse_override(project_id, body, errors)
        if override is not None:
            projects[project_id] = override
    ignore_raw = doc.get("ignore") or []
    if not isinstance(ignore_raw, list) or not all(
        isinstance(p, str) for p in ignore_raw
    ):
        errors.append("ignore: must be a list of paths")
        ignore_raw = []
    config = ProjectsConfig(
        projects=projects,
        path_aliases=_string_map(doc.get("paths"), "paths", errors),
        ignore=tuple(ignore_raw),
        merges=_string_map(doc.get("merges"), "merges", errors),
    )
    if errors:
        raise ProjectsConfigError([f"{path.name}: {e}" for e in errors])
    return config


def _override_doc(override: ProjectOverride) -> dict[str, Any]:
    doc: dict[str, Any] = {}
    for key in ("display_name", "client", "billing", "currency"):
        value = getattr(override, key)
        if value is not None:
            doc[key] = value
    for key in ("rate", "fixed_price"):
        value = getattr(override, key)
        if value is not None:
            doc[key] = format(value, "f")
    return doc


def save_projects_config(cfg: ProjectsConfig, path: Path) -> None:
    """Write ``projects.yaml`` atomically (temp file in the same directory + ``os.replace``)."""
    doc: dict[str, Any] = {
        "version": 1,
        "projects": {pid: _override_doc(o) for pid, o in sorted(cfg.projects.items())},
        "paths": dict(sorted(cfg.path_aliases.items())),
        "ignore": list(cfg.ignore),
        "merges": dict(sorted(cfg.merges.items())),
    }
    text = yaml.safe_dump(
        doc, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
