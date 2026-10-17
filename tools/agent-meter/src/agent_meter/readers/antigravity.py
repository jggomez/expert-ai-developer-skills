"""Antigravity reader for the CLI, IDE and app roots (ADR §3.2–§3.5).

Canonical usage is ``conversations/<id>.db`` → ``gen_metadata`` (decoded in
``_agy_decode``); the step timeline comes from ``steps``; transcripts are read only for
tool names and as a usage fallback for conversations without a database. Databases are
opened ``mode=ro`` + ``query_only``; ``cli.log`` and ``*.pb`` contents are never read.
"""

from __future__ import annotations

import bisect
import json
import logging
import sqlite3
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Final

from agent_meter.model import (
    CallRecord,
    DiagnosticKind,
    FileFingerprint,
    Host,
    ReaderOptions,
    SessionRecord,
    SessionUnit,
    TaskRecord,
    UnitBatch,
    UntrackedReason,
    UntrackedRecord,
)
from agent_meter.readers._agy_decode import (
    ERROR_MESSAGE,
    GEN_FORMAT,
    KNOWN_DB_SHAPE,
    NON_RESULT_KINDS,
    PLANNER,
    TRANSCRIPT_FORMAT,
    USER_INPUT,
    GenCall,
    Step,
    Tool,
    count,
    fallback_calls,
    owned_parent,
    read_database,
    read_transcript,
    ro_connect,
    step_ts,
    workspace_from_summary,
)
from agent_meter.readers._common import (
    DATA_ERRORS,
    DiagnosticCollector,
    RunDraft,
    TaskDraft,
    assemble,
    description_hash,
    fingerprint_file,
    safe_label,
    shape_fingerprint,
)

__all__ = [
    "ANTIGRAVITY_HOSTS",
    "KNOWN_FORMATS",
    "SUBAGENTS_REL",
    "TRANSCRIPT_REL",
    "AntigravityReader",
    "format_fingerprint",
]

_LOG = logging.getLogger(__name__)

ANTIGRAVITY_HOSTS: Final = frozenset(
    {Host.ANTIGRAVITY_CLI, Host.ANTIGRAVITY_IDE, Host.ANTIGRAVITY_APP}
)
TRANSCRIPT_REL: Final = Path(".system_generated/logs/transcript_full.jsonl")
SUBAGENTS_REL: Final = Path(".system_generated/subagents")
_UNKNOWN_AGENT: Final = "(unknown)"
_PARENT_SCAN_ROWS: Final = 50


def format_fingerprint(tokens: Iterable[str]) -> str:
    return shape_fingerprint(["host:antigravity", *tokens])


KNOWN_FORMATS: Final[frozenset[str]] = frozenset(
    {
        format_fingerprint([f"fmt:{GEN_FORMAT}", *KNOWN_DB_SHAPE]),
        format_fingerprint([f"fmt:{TRANSCRIPT_FORMAT}"]),
        format_fingerprint(
            [f"fmt:{GEN_FORMAT}", f"fmt:{TRANSCRIPT_FORMAT}", *KNOWN_DB_SHAPE]
        ),
    }
)


# ----------------------------------------------------------------------------- shapes


@dataclass(slots=True)
class _Conversation:
    cid: str
    timeline: list[Step] = field(default_factory=list)
    calls: list[GenCall] = field(default_factory=list)
    transcript: list[Step] | None = None
    workspace: str | None = None


@dataclass(frozen=True, slots=True)
class _SpawnInfo:
    spawn_step_index: int | None = None
    type_name: str | None = None
    role: str | None = None


@dataclass(frozen=True, slots=True)
class _Summary:
    parent: str | None
    agent_name: str | None
    workspace: str | None


@dataclass(slots=True)
class _Index:
    db_ids: set[str]
    pb_ids: set[str]
    transcript_ids: set[str]
    parents: dict[str, str]

    @property
    def known(self) -> set[str]:
        return self.db_ids | self.transcript_ids

    def root_of(self, cid: str) -> str:
        seen = {cid}
        current = cid
        while current in self.parents:
            current = self.parents[current]
            if current in seen:
                return cid
            seen.add(current)
        return current

    def descendants(self, root: str) -> list[str]:
        return _bfs(root, self.parents)[0]


def _bfs(root: str, parents: Mapping[str, str | None]) -> tuple[list[str], set[str]]:
    """Descendants of ``root`` in breadth-first order (parents before children)."""
    children: dict[str, list[str]] = {}
    for kid, parent in parents.items():
        children.setdefault(parent or root, []).append(kid)
    order: list[str] = []
    seen = {root}
    queue = deque(sorted(children.get(root, [])))
    while queue:
        cid = queue.popleft()
        if cid in seen:
            continue
        seen.add(cid)
        order.append(cid)
        queue.extend(sorted(children.get(cid, [])))
    return order, seen


# ----------------------------------------------------------------------------- reader


class AntigravityReader:
    """``HostReader`` for one Antigravity data root (CLI, IDE or app)."""

    def __init__(self, host: Host, root: Path) -> None:
        if host not in ANTIGRAVITY_HOSTS:
            raise ValueError(f"{host} is not an Antigravity host")
        self.host = host
        self.root = root

    # -- paths

    def db_path(self, cid: str) -> Path:
        return self.root / "conversations" / f"{cid}.db"

    def transcript_path(self, cid: str) -> Path:
        return self.root / "brain" / cid / TRANSCRIPT_REL

    def _subagents_dir(self, cid: str) -> Path:
        return self.root / "brain" / cid / SUBAGENTS_REL

    def _summaries_path(self) -> Path:
        return self.root / "conversation_summaries.db"

    # -- metadata sources (ids and allowlisted columns only)

    def summaries(self, members: Iterable[str] | None = None) -> dict[str, _Summary]:
        """Allowlisted ``conversation_summaries`` columns (never ``title``/``preview``)."""
        path = self._summaries_path()
        if not path.is_file():
            return {}
        query = (
            "SELECT conversation_id, parent_conversation_id, agent_name, workspace_uris "
            "FROM conversation_summaries"
        )
        try:
            with closing(ro_connect(path)) as con:
                rows = con.execute(query).fetchall()
        except sqlite3.Error as exc:
            _LOG.warning("antigravity summaries unreadable: %s", type(exc).__name__)
            return {}
        wanted = set(members) if members is not None else None
        return {
            cid: _Summary(
                parent=parent if isinstance(parent, str) and parent else None,
                agent_name=agent if isinstance(agent, str) and agent else None,
                workspace=workspace_from_summary(uris),
            )
            for cid, parent, agent, uris in rows
            if isinstance(cid, str) and (wanted is None or cid in wanted)
        }

    def spawn_infos(
        self, parent: str, diags: DiagnosticCollector | None = None
    ) -> dict[str, _SpawnInfo]:
        """``brain/<parent>/.system_generated/subagents/*.json`` keyed by child id."""
        directory = self._subagents_dir(parent)
        if not directory.is_dir():
            return {}
        infos: dict[str, _SpawnInfo] = {}
        for path in sorted(directory.glob("*.json")):
            try:
                obj = json.loads(path.read_bytes())
            except DATA_ERRORS as exc:
                if diags is not None:
                    diags.add(
                        DiagnosticKind.CORRUPT, "agy_subagents", type(exc).__name__
                    )
                continue
            if not isinstance(obj, dict) or not isinstance(
                obj.get("conversationId"), str
            ):
                continue
            descriptor = obj.get("subagentDescriptor")
            descriptor = descriptor if isinstance(descriptor, Mapping) else {}
            role = descriptor.get("role")
            infos[obj["conversationId"]] = _SpawnInfo(
                spawn_step_index=count(obj.get("spawnStepIndex")),
                type_name=safe_label(descriptor.get("typeName")),
                role=role if isinstance(role, str) and role else None,
            )
        return infos

    def parent_from_db(self, cid: str) -> str | None:
        """Fallback parent: ``parent_cascade_id`` on the conversation's own rows."""
        if not self.db_path(cid).is_file():
            return None
        try:
            return owned_parent(self.db_path(cid), _PARENT_SCAN_ROWS)
        except sqlite3.Error as exc:
            _LOG.debug("antigravity parent lookup failed: %s", type(exc).__name__)
            return None

    def conversation(
        self, cid: str, diags: DiagnosticCollector, shape: set[str]
    ) -> _Conversation:
        """DB timeline/calls when decodable, else the transcript fallback."""
        conv = _Conversation(
            cid=cid, transcript=read_transcript(self.transcript_path(cid), diags)
        )
        try:
            db = read_database(self.host, cid, self.db_path(cid), diags, shape)
        except DATA_ERRORS as exc:
            diags.add(DiagnosticKind.CORRUPT, "agy_db", type(exc).__name__)
            _LOG.warning(
                "antigravity conversation db unreadable: %s", type(exc).__name__
            )
            db = None
        if db is not None:
            conv.timeline, conv.calls, conv.workspace = db.steps, db.calls, db.workspace
        elif conv.transcript is not None:
            shape.add(f"fmt:{TRANSCRIPT_FORMAT}")
            conv.timeline = list(conv.transcript)
            conv.calls = fallback_calls(self.host, cid, conv.transcript)
        return conv

    # -- index and discovery (stat + id columns only)

    def _index(self) -> _Index:
        conversations = self.root / "conversations"
        brain = self.root / "brain"
        has_conversations = conversations.is_dir()
        db_ids = (
            {p.stem for p in conversations.glob("*.db")} if has_conversations else set()
        )
        pb_ids = (
            {p.stem for p in conversations.glob("*.pb")} if has_conversations else set()
        )
        brain_dirs = sorted(brain.iterdir()) if brain.is_dir() else []
        transcript_ids = {d.name for d in brain_dirs if (d / TRANSCRIPT_REL).is_file()}
        known = db_ids | transcript_ids
        summaries = self.summaries()
        parents = {cid: s.parent for cid, s in summaries.items() if s.parent}
        for parent_dir in brain_dirs:
            for kid in self.spawn_infos(parent_dir.name):
                parents.setdefault(kid, parent_dir.name)
        if self._summaries_path().is_file():
            for cid in sorted(db_ids - set(summaries) - set(parents)):
                if (parent := self.parent_from_db(cid)) is not None:
                    parents[cid] = parent
        valid = {
            k: p for k, p in parents.items() if k in known and p in known and k != p
        }
        index = _Index(db_ids, pb_ids, transcript_ids, valid)
        for cid in [c for c in valid if index.root_of(c) == c]:  # break cycles
            index.parents.pop(cid, None)
        return index

    def _member_files(self, cid: str) -> list[FileFingerprint]:
        candidates: list[tuple[Path, str]] = [
            (self.db_path(cid), "agy_db"),
            (self.root / "conversations" / f"{cid}.db-wal", "agy_wal"),
            (self.transcript_path(cid), "agy_transcript"),
        ]
        sub_dir = self._subagents_dir(cid)
        if sub_dir.is_dir():
            candidates.extend(
                (p, "agy_subagents") for p in sorted(sub_dir.glob("*.json"))
            )
        return [
            fingerprint
            for path, kind in candidates
            if path.is_file()
            and (fingerprint := fingerprint_file(self.root, path, kind)) is not None
        ]

    def _unit(self, index: _Index, root: str) -> SessionUnit:
        members = index.descendants(root)
        return SessionUnit(
            host=self.host,
            unit_id=root,
            root=self.root,
            files=tuple(f for cid in (root, *members) for f in self._member_files(cid)),
            member_ids=tuple(sorted(members)),
        )

    def discover(self) -> Iterator[SessionUnit]:
        if not self.root.is_dir():
            return
        index = self._index()
        for root in sorted(cid for cid in index.known if cid not in index.parents):
            yield self._unit(index, root)

    def find_unit(self, session_or_conversation_id: str) -> SessionUnit | None:
        if not self.root.is_dir():
            return None
        index = self._index()
        if session_or_conversation_id not in index.known:
            return None
        return self._unit(index, index.root_of(session_or_conversation_id))

    # -- untracked history (BR-22) and retention (BR-15)

    def _has_transcript_usage(self, cid: str) -> bool:
        steps = read_transcript(self.transcript_path(cid), DiagnosticCollector()) or []
        return any(s.kind == PLANNER and s.tokens is not None for s in steps)

    def untracked(self) -> list[UntrackedRecord]:
        if not self.root.is_dir():
            return []
        index = self._index()
        records: list[UntrackedRecord] = []
        for cid in sorted(index.pb_ids - index.db_ids):
            if cid in index.transcript_ids and self._has_transcript_usage(cid):
                continue
            try:
                mtime = (self.root / "conversations" / f"{cid}.pb").stat().st_mtime
            except OSError as exc:
                _LOG.debug("legacy blob vanished: %s", type(exc).__name__)
                continue
            seen = datetime.fromtimestamp(mtime, tz=UTC).date()
            records.append(
                UntrackedRecord(cid, self.host, UntrackedReason.LEGACY_PB, seen, seen)
            )
        for cid in sorted(index.transcript_ids - index.db_ids - index.pb_ids):
            steps = (
                read_transcript(self.transcript_path(cid), DiagnosticCollector()) or []
            )
            if any(s.kind == PLANNER and s.tokens is not None for s in steps):
                continue
            stamps = sorted(s.ts for s in steps if s.ts is not None)
            if stamps:
                records.append(
                    UntrackedRecord(
                        cid,
                        self.host,
                        UntrackedReason.NO_USAGE_DATA,
                        stamps[0].date(),
                        stamps[-1].date(),
                    )
                )
        return records

    def _first_db_step(self, cid: str) -> datetime | None:
        query = (
            "SELECT metadata FROM steps WHERE metadata IS NOT NULL ORDER BY idx LIMIT 1"
        )
        try:
            with closing(ro_connect(self.db_path(cid))) as con:
                row = con.execute(query).fetchone()
        except sqlite3.Error as exc:
            _LOG.debug("antigravity earliest scan failed: %s", type(exc).__name__)
            return None
        return step_ts(row[0]) if row and isinstance(row[0], bytes) else None

    def earliest_available(self) -> date | None:
        if not self.root.is_dir():
            return None
        index = self._index()
        stamps = [
            ts for cid in sorted(index.db_ids) if (ts := self._first_db_step(cid))
        ]
        for cid in sorted(index.transcript_ids - index.db_ids):
            steps = (
                read_transcript(self.transcript_path(cid), DiagnosticCollector()) or []
            )
            stamps.extend(s.ts for s in steps if s.ts is not None)
        return min(stamps).date() if stamps else None

    # -- parsing

    def read_unit(self, unit: SessionUnit, options: ReaderOptions) -> UnitBatch:
        shape: set[str] = set()
        try:
            return _UnitAssembler(self, unit, options, shape).build()
        except DATA_ERRORS as exc:
            _LOG.warning("antigravity unit unreadable: %s", type(exc).__name__)
            diags = DiagnosticCollector()
            unreadable = isinstance(exc, OSError)
            kind = DiagnosticKind.UNREADABLE if unreadable else DiagnosticKind.CORRUPT
            diags.add(kind, "agy_db", type(exc).__name__)
            return UnitBatch(
                unit=unit,
                sessions=(),
                tasks=(),
                agent_runs=(),
                calls=(),
                tool_uses=(),
                diagnostics=diags.build(self.host, unit.unit_id),
                format_fingerprint=format_fingerprint(shape),
            )


# ----------------------------------------------------------------------------- assembly


class _Segmentation:
    """Root-conversation task boundaries: each ``USER_INPUT`` step opens a task (ADR §3.5)."""

    def __init__(self, host: Host, root: _Conversation) -> None:
        self._prefix = f"{host.value}:{root.cid}"
        timeline = sorted(root.timeline, key=lambda s: s.idx)
        anchors = [s for s in timeline if s.kind == USER_INPUT] or timeline[:1]
        self._starts = [s.idx for s in anchors] or [0]
        self._start_ts = [(s.ts, s.idx) for s in anchors if s.ts is not None]

    def _task(self, start_idx: int) -> str:
        return f"{self._prefix}:{start_idx}"

    def first_task(self) -> str:
        return self._task(self._starts[0])

    def task_for_idx(self, idx: int) -> str:
        """Steps before the first ``USER_INPUT`` (inherited prefixes) join the first task."""
        position = bisect.bisect_right(self._starts, idx) - 1
        return self._task(self._starts[max(position, 0)])

    def task_for_ts(self, ts: datetime | None) -> str:
        if ts is None:
            return self.first_task()
        eligible = [idx for start_ts, idx in self._start_ts if start_ts <= ts]
        return self._task(max(eligible)) if eligible else self.first_task()


class _UnitAssembler:
    """Builds one ``UnitBatch``: root tasks, child agent runs, deduplicated calls."""

    def __init__(
        self,
        reader: AntigravityReader,
        unit: SessionUnit,
        options: ReaderOptions,
        shape: set[str],
    ) -> None:
        self._reader = reader
        self._host = reader.host
        self._unit = unit
        self._options = options
        self._shape = shape
        self._diags = DiagnosticCollector()
        self._drafts: dict[str, TaskDraft] = {}
        self._calls: dict[str, tuple[GenCall, str, str]] = {}

    # -- draft helpers

    def _task(self, task_id: str) -> TaskDraft:
        return self._drafts.setdefault(task_id, TaskDraft(task_id=task_id))

    def _main_run(self, task_id: str) -> RunDraft:
        runs = self._task(task_id).runs
        run_id = f"{task_id}:main"
        if run_id not in runs:
            runs[run_id] = RunDraft(run_id, "main", None, 0)
        return runs[run_id]

    def _keep_call(self, call: GenCall, task_id: str, run_id: str) -> None:
        """Within a unit the lowest ``owner_rank`` wins (owned ``"0"`` before copies)."""
        current = self._calls.get(call.call_id)
        if current is None or call.owner_rank < current[0].owner_rank:
            self._calls[call.call_id] = (call, task_id, run_id)

    # -- build

    def build(self) -> UnitBatch:
        root_id = self._unit.unit_id
        members = list(self._unit.member_ids)
        summaries = self._reader.summaries([root_id, *members])
        root = self._reader.conversation(root_id, self._diags, self._shape)
        segmentation = _Segmentation(self._host, root)
        self._place_root(root, segmentation)
        spawn = self._spawn_index(root_id, members)
        parents = self._parents(root_id, members, summaries, spawn)
        self._place_children(root_id, parents, spawn, summaries, segmentation)
        tasks, runs, tools = assemble(
            self._host, root_id, self._drafts.values(), self._options
        )
        calls = sorted(
            (self._call_record(c, root_id, t, r) for c, t, r in self._calls.values()),
            key=lambda c: (c.ts, c.call_id),
        )
        summary = summaries.get(root_id)
        workspace = (summary.workspace if summary else None) or root.workspace
        return UnitBatch(
            unit=self._unit,
            sessions=self._session(root_id, workspace, tasks),
            tasks=tuple(tasks),
            agent_runs=tuple(runs),
            calls=tuple(calls),
            tool_uses=tuple(tools),
            diagnostics=self._diags.build(self._host, root_id),
            format_fingerprint=format_fingerprint(self._shape),
        )

    def _place_root(self, root: _Conversation, segmentation: _Segmentation) -> None:
        """One main run per root task; calls attach to the task of step ``last+1``."""
        for step in root.timeline:
            _apply_step(step, self._main_run(segmentation.task_for_idx(step.idx)))
        for call in root.calls:
            task_id = segmentation.task_for_idx(call.step_idx)
            run = self._main_run(task_id)
            _apply_call(call, run)
            self._keep_call(call, task_id, run.agent_run_id)
        _apply_tools(root, lambda idx: self._main_run(segmentation.task_for_idx(idx)))

    def _spawn_index(
        self, root_id: str, members: Sequence[str]
    ) -> dict[str, tuple[str, _SpawnInfo]]:
        spawn: dict[str, tuple[str, _SpawnInfo]] = {}
        for holder in (root_id, *members):
            for kid, info in self._reader.spawn_infos(holder, self._diags).items():
                spawn.setdefault(kid, (holder, info))
        return spawn

    def _parents(
        self,
        root_id: str,
        members: Sequence[str],
        summaries: Mapping[str, _Summary],
        spawn: Mapping[str, tuple[str, _SpawnInfo]],
    ) -> dict[str, str]:
        """Summary parent → spawn JSON holder → ``parent_cascade_id`` → unit root."""
        in_unit = {root_id, *members}
        parents: dict[str, str] = {}
        for cid in members:
            summary = summaries.get(cid)
            candidates = (
                summary.parent if summary else None,
                spawn[cid][0] if cid in spawn else None,
            )
            parent = next((p for p in candidates if p in in_unit), None)
            if parent is None:
                fallback = self._reader.parent_from_db(cid)
                parent = fallback if fallback in in_unit else root_id
            parents[cid] = parent
        return parents

    def _place_children(
        self,
        root_id: str,
        parents: Mapping[str, str],
        spawn: Mapping[str, tuple[str, _SpawnInfo]],
        summaries: Mapping[str, _Summary],
        segmentation: _Segmentation,
    ) -> None:
        """Children roll up to the parent task containing ``spawnStepIndex`` (ADR §3.5)."""
        order, seen = _bfs(root_id, parents)
        order.extend(sorted(cid for cid in parents if cid not in seen))
        child_task: dict[str, str] = {}
        depth: dict[str, int] = {root_id: 0}
        for cid in order:
            conv = self._reader.conversation(cid, self._diags, self._shape)
            parent = parents[cid]
            info = spawn[cid][1] if cid in spawn else _SpawnInfo()
            if parent == root_id:
                if info.spawn_step_index is not None:
                    task_id = segmentation.task_for_idx(info.spawn_step_index)
                else:
                    first = min(
                        (s.ts for s in conv.timeline if s.ts is not None), default=None
                    )
                    task_id = segmentation.task_for_ts(first)
                parent_run = f"{task_id}:main"
            else:
                task_id = child_task.get(parent, segmentation.first_task())
                parent_run = f"{self._host.value}:agent:{parent}"
            child_task[cid] = task_id
            depth[cid] = depth.get(parent, 0) + 1
            run = RunDraft(
                agent_run_id=f"{self._host.value}:agent:{cid}",
                agent_type=_agent_type(summaries.get(cid), info),
                parent_agent_run_id=parent_run,
                spawn_depth=depth[cid],
                description_hash=(
                    description_hash(self._options.description_salt, info.role)
                    if info.role
                    else None
                ),
            )
            self._task(task_id).runs[run.agent_run_id] = run
            self._place_child_conversation(conv, task_id, run)

    def _place_child_conversation(
        self, conv: _Conversation, task_id: str, run: RunDraft
    ) -> None:
        for step in conv.timeline:
            _apply_step(step, run)
        for call in conv.calls:
            _apply_call(call, run)
            self._keep_call(call, task_id, run.agent_run_id)
        _apply_tools(conv, lambda _idx: run)

    # -- records

    def _call_record(
        self, call: GenCall, session_id: str, task_id: str, run_id: str
    ) -> CallRecord:
        return CallRecord(
            call_id=call.call_id,
            host=self._host,
            session_id=session_id,
            task_id=task_id,
            agent_run_id=run_id,
            ts=call.ts,
            model=call.model,
            model_label=call.model_label,
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            thinking_tokens=call.thinking_tokens,
            cache_write_5m_tokens=call.cache_write_tokens,
            cache_write_1h_tokens=call.cache_write_tokens,
            cache_read_tokens=call.cache_read_tokens,
            latency_ms=call.latency_ms,
            speed=None,
            inference_geo=None,
            is_error=call.is_error,
            source_format=call.source_format,
            owner_rank=call.owner_rank,
        )

    def _session(
        self, session_id: str, workspace: str | None, tasks: Sequence[TaskRecord]
    ) -> tuple[SessionRecord, ...]:
        if not tasks:
            return ()
        ended = max(t.ended_at for t in tasks)
        stale = (
            self._options.now - ended
        ).total_seconds() > self._options.stale_after_s
        return (
            SessionRecord(
                session_id=session_id,
                host=self._host,
                workspace_path=workspace,
                started_at=min(t.started_at for t in tasks),
                ended_at=ended,
                status="closed" if stale else "open",
                host_version=None,
                owner_rank="0",
            ),
        )


# ----------------------------------------------------------------------------- run accounting


def _agent_type(summary: _Summary | None, info: _SpawnInfo) -> str:
    """``conversation_summaries.agent_name``, else the spawn descriptor type, else unknown."""
    from_summary = safe_label(summary.agent_name) if summary is not None else None
    return from_summary or info.type_name or _UNKNOWN_AGENT


def _apply_step(step: Step, run: RunDraft) -> None:
    if step.ts is not None:
        run.events.append(step.ts)
    if step.kind == ERROR_MESSAGE:
        run.errors += 1


def _apply_call(call: GenCall, run: RunDraft) -> None:
    run.events.append(call.ts)
    if call.latency_ms:
        run.extra.append((call.ts, call.ts + timedelta(milliseconds=call.latency_ms)))


def _apply_tools(conv: _Conversation, run_for: Callable[[int], RunDraft]) -> None:
    """Tool counts from the transcript; with no transcript the runs are marked untracked.

    Result steps after a ``PLANNER_RESPONSE`` are matched to its tool calls in order; a
    result with status ``ERROR`` counts as a tool error (and a test failure for tests).
    """
    if conv.transcript is None:
        for step in conv.timeline:
            run_for(step.idx).tools_untracked = True
        return
    pending: deque[tuple[RunDraft, Tool]] = deque()
    for step in conv.transcript:
        if step.kind == PLANNER:
            run = run_for(step.idx)
            pending.clear()
            for tool in step.tools:
                run.record_tool(tool.label)
                if tool.file_digest is not None:
                    run.files.add(tool.file_digest)
                run.test_runs += int(tool.is_test)
                pending.append((run, tool))
        elif step.kind not in NON_RESULT_KINDS and pending:
            owner, tool = pending.popleft()
            if step.has_error:
                owner.record_tool_error(tool.label)
                owner.test_failures += int(tool.is_test)
