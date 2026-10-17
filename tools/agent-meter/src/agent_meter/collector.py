"""Incremental, idempotent ingest of every host (ADR §3.3, contracts §3.8).

Units whose stat fingerprint is unchanged are skipped (no-change run ≤ 2 s); a changed
unit is fully re-parsed and upserted. Project identity is resolved here from the
transient ``workspace_path`` (which is never stored). Host end-of-task/session signals
from hooks are persisted as ``meta`` markers so later re-ingests keep the task ``done``.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from datetime import time as dtime
from pathlib import Path
from typing import Final, Literal

from agent_meter.config import Config, host_defaults, settings_for_store
from agent_meter.locking import LockTimeout
from agent_meter.model import (
    Diagnostic,
    DiagnosticKind,
    Host,
    ProjectRef,
    ReaderOptions,
    SessionUnit,
    TaskStatus,
    UnitBatch,
)
from agent_meter.paths import AppHome, SecretCorruptError, load_secret
from agent_meter.pricing import PricingError, PricingTable, load_pricing
from agent_meter.project_resolver import (
    ProjectResolver,
    ProjectsConfig,
    ProjectsConfigError,
    load_projects_config,
)
from agent_meter.readers.base import HostReader, available_readers, default_roots
from agent_meter.store import UNASSIGNED_ID, ApplyStats, Store

__all__ = ["BATCH_UNITS", "CollectResult", "Signal", "collect", "reader_roots"]

_LOG = logging.getLogger(__name__)

BATCH_UNITS: Final = 50
Signal = Literal["session-end", "task-end"]
_EMPTY_STATS: Final = ApplyStats(
    units=0, calls_changed=0, tasks_changed=0, runs_changed=0, sessions_changed=0, diagnostics=0
)


@dataclass(frozen=True, slots=True)
class CollectResult:
    status: Literal["ok", "locked", "error"]
    stats: ApplyStats | None
    duration_ms: int
    diagnostics: tuple[Diagnostic, ...]
    units_skipped_unchanged: int
    message: str | None = None


def reader_roots(cfg: Config) -> dict[Host, Path]:
    """Data root per enabled host: ``[hosts.<h>].root`` overrides the default location."""
    defaults = default_roots()
    roots: dict[Host, Path] = {}
    for host in Host:
        host_cfg = cfg.host(host)
        if not host_cfg.enabled:
            continue
        roots[host] = host_cfg.root or defaults[host]
    return roots


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _add_stats(a: ApplyStats, b: ApplyStats) -> ApplyStats:
    return ApplyStats(
        units=a.units + b.units,
        calls_changed=a.calls_changed + b.calls_changed,
        tasks_changed=a.tasks_changed + b.tasks_changed,
        runs_changed=a.runs_changed + b.runs_changed,
        sessions_changed=a.sessions_changed + b.sessions_changed,
        diagnostics=a.diagnostics + b.diagnostics,
    )


def _load_pricing(home: AppHome) -> tuple[PricingTable | None, str | None]:
    try:
        return load_pricing(home.pricing_local), None
    except PricingError as exc:
        _LOG.warning("pricing.local.yaml invalid; keeping the previous price table")
        return None, "; ".join(exc.errors)


def _marker_key(kind: Signal, host: Host, session_id: str) -> str:
    return f"{kind}:{host.value}:{session_id}"


class _Ingest:
    """One collect run against an open, exclusively locked store."""

    def __init__(self, store: Store, resolver: ProjectResolver, options: ReaderOptions, cfg: Config) -> None:
        self.store = store
        self.resolver = resolver
        self.options = options
        self.cfg = cfg
        self.refs: dict[str, ProjectRef] = {}
        self.pending: list[UnitBatch] = []
        self.stats = _EMPTY_STATS
        self.diagnostics: list[Diagnostic] = []
        self.skipped = 0
        self.known_formats: dict[Host, frozenset[str]] = {}

    def read(self, reader: HostReader, unit: SessionUnit) -> UnitBatch:
        try:
            return reader.read_unit(unit, self.options)
        except Exception as exc:  # a reader bug must not abort the whole run (NFR-07)
            _LOG.warning("reader failed on a unit: %s", type(exc).__name__)
            from agent_meter.readers._common import unit_hash

            diagnostic = Diagnostic(
                host=unit.host,
                kind=DiagnosticKind.CORRUPT,
                unit_hash=unit_hash(unit.unit_id),
                file_kind=unit.files[0].kind if unit.files else "unit",
                error_class=type(exc).__name__,
            )
            return UnitBatch(
                unit=unit, sessions=(), tasks=(), agent_runs=(), calls=(), tool_uses=(),
                diagnostics=(diagnostic,), format_fingerprint="",
            )

    def attach_projects(self, batch: UnitBatch) -> UnitBatch:
        """Resolve each session's workspace to a project id and stamp it on every record."""
        by_session: dict[str, str] = {}
        sessions = []
        for session in batch.sessions:
            ref = self.resolver.resolve(session.workspace_path)
            self.refs[ref.project_id] = ref
            by_session[session.session_id] = ref.project_id
            sessions.append(replace(session, workspace_path=None, project_id=ref.project_id))

        def pid(session_id: str) -> str:
            return by_session.get(session_id, UNASSIGNED_ID)

        return replace(
            batch,
            sessions=tuple(sessions),
            tasks=tuple(replace(t, project_id=pid(t.session_id)) for t in batch.tasks),
            agent_runs=tuple(replace(r, project_id=pid(r.session_id)) for r in batch.agent_runs),
            calls=tuple(replace(c, project_id=pid(c.session_id)) for c in batch.calls),
        )

    def _marker(self, kind: Signal, host: Host, session_id: str) -> datetime | None:
        value = self.store.get_meta(_marker_key(kind, host, session_id))
        return datetime.fromisoformat(value) if value else None

    def apply_signals(self, batch: UnitBatch) -> UnitBatch:
        """BR-14: a host end signal closes the last task (and the session for SessionEnd)."""
        host = batch.unit.host
        sessions = list(batch.sessions)
        tasks = list(batch.tasks)
        for index, session in enumerate(sessions):
            ended = self._marker("session-end", host, session.session_id)
            task_end = self._marker("task-end", host, session.session_id)
            closing = max((m for m in (ended, task_end) if m is not None), default=None)
            if ended is not None and session.ended_at <= ended:
                sessions[index] = replace(session, status="closed")
            if closing is None:
                continue
            own = [i for i, t in enumerate(tasks) if t.session_id == session.session_id]
            if not own:
                continue
            last = max(own, key=lambda i: (tasks[i].seq_in_session, tasks[i].started_at))
            task = tasks[last]
            if task.status == TaskStatus.IN_PROGRESS and task.ended_at <= closing:
                tasks[last] = replace(task, status=TaskStatus.DONE)
        return replace(batch, sessions=tuple(sessions), tasks=tuple(tasks))

    def add(self, reader: HostReader, unit: SessionUnit) -> None:
        batch = self.apply_signals(self.attach_projects(self.read(reader, unit)))
        self.diagnostics.extend(batch.diagnostics)
        self.pending.append(batch)
        if len(self.pending) >= BATCH_UNITS:
            self.flush()

    def flush(self) -> None:
        if not self.pending:
            return
        stats = self.store.apply_batches(self.pending, known_formats=self.known_formats, now=self.options.now)
        self.stats = _add_stats(self.stats, stats)
        self.pending = []


def _known_formats(host: Host) -> frozenset[str]:
    if host is Host.CLAUDE_CODE:
        from agent_meter.readers.claude_code import KNOWN_FORMATS as CLAUDE_FORMATS

        return CLAUDE_FORMATS
    from agent_meter.readers.antigravity import KNOWN_FORMATS as AGY_FORMATS

    return AGY_FORMATS


def _latest_mtime_ns(unit: SessionUnit) -> int:
    return max((f.mtime_ns for f in unit.files), default=0)


def _select_readers(
    cfg: Config, readers: Sequence[HostReader] | None, hosts: Collection[Host] | None
) -> list[HostReader]:
    chosen = list(readers) if readers is not None else available_readers(reader_roots(cfg))
    return [r for r in chosen if (hosts is None or r.host in hosts) and cfg.host(r.host).enabled]


def _units(reader: HostReader, only: tuple[Host, str] | None) -> list[SessionUnit]:
    if only is None:
        return list(reader.discover())
    host, session_id = only
    if reader.host is not host:
        return []
    unit = reader.find_unit(session_id)
    return [unit] if unit is not None else []


def collect(
    home: AppHome,
    cfg: Config,
    *,
    hosts: Collection[Host] | None = None,
    since: date | None = None,
    full: bool = False,
    only: tuple[Host, str] | None = None,
    lock_timeout_s: float = 60.0,
    readers: Sequence[HostReader] | None = None,
    now: datetime | None = None,
    signal: Signal | None = None,
) -> CollectResult:
    """Ingest every enabled host (or one unit with ``only``); returns ``locked`` if the store is busy."""
    started = time.monotonic()
    moment = now or datetime.now(UTC)
    try:
        projects = load_projects_config(home.projects)
        salt = load_secret(home)
    except (ProjectsConfigError, SecretCorruptError) as exc:
        return CollectResult("error", None, _elapsed_ms(started), (), 0, message=str(exc))
    pricing, pricing_error = _load_pricing(home)
    selected = _select_readers(cfg, readers, hosts)
    since_ns = int(datetime.combine(since, dtime.min, tzinfo=UTC).timestamp() * 1e9) if since else None
    try:
        store = Store.open(home, read_only=False, lock_timeout_s=lock_timeout_s)
    except LockTimeout:
        return CollectResult("locked", None, _elapsed_ms(started), (), 0)
    with store:
        store.migrate()
        ingest = _Ingest(store, _resolver(store, projects), _options(cfg, moment, salt), cfg)
        ingest.known_formats = {r.host: _known_formats(r.host) for r in selected}
        for reader in selected:
            for unit in _units(reader, only):
                if signal is not None and only is not None and unit.unit_id == only[1]:
                    store.set_meta(_marker_key(signal, unit.host, unit.unit_id), moment.isoformat())
                if since_ns is not None and _latest_mtime_ns(unit) < since_ns:
                    continue
                if not full and signal is None and store.unit_fingerprint(unit.host, unit.unit_id) == unit.fingerprint:
                    ingest.skipped += 1
                    continue
                ingest.add(reader, unit)
            if only is None:
                store.record_untracked(reader.untracked())
        ingest.flush()
        _finish(store, home, cfg, projects, pricing, pricing_error, list(ingest.refs.values()), moment)
    return CollectResult(
        "ok", ingest.stats, _elapsed_ms(started), tuple(ingest.diagnostics), ingest.skipped
    )


def _resolver(store: Store, projects: ProjectsConfig) -> ProjectResolver:
    user_home = Path(os.environ.get("HOME") or Path.home())
    return ProjectResolver(store.path_cache(), projects, home=user_home)


def _options(cfg: Config, moment: datetime, salt: bytes) -> ReaderOptions:
    return ReaderOptions(
        now=moment,
        idle_threshold_s=cfg.idle_threshold_s,
        stale_after_s=cfg.stale_after_h * 3600,
        store_agent_descriptions=cfg.store_agent_descriptions,
        description_salt=salt,
    )


def _finish(
    store: Store,
    home: AppHome,
    cfg: Config,
    projects: ProjectsConfig,
    pricing: PricingTable | None,
    pricing_error: str | None,
    refs: list[ProjectRef],
    moment: datetime,
) -> None:
    store.load_reference_data(
        pricing=pricing,
        host_defaults=host_defaults(cfg),
        projects=projects,
        project_refs=refs,
        settings=settings_for_store(cfg),
    )
    if pricing_error is None:
        store.delete_meta("pricing_error")
    else:
        store.set_meta("pricing_error", pricing_error)
    store.recompute_dev_hours(cfg.timezone, cfg.dev_hours_merge_gap_min * 60)
    store.set_meta("last_collect_at", moment.isoformat())
    store.write_snapshot(home.snapshot, tz=cfg.timezone, now=moment)
