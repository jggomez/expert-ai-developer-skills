"""Claude Code reader: ``<root>/projects/<slug>/<sessionId>.jsonl`` + ``<sessionId>/subagents/``.

Allowlist extraction only (ADR §3.13): each JSON line is reduced to a typed ``_Line``
holding ids, timestamps, usage counters, tool names, a *hash* of edited file paths and
a boolean "is a test command". Text, tool inputs/outputs and paths never leave here.
Segmentation and dedup follow ADR §3.5.
"""

from __future__ import annotations

import glob
import json
import logging
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final

from agent_meter.model import (
    CallRecord,
    DiagnosticKind,
    FileFingerprint,
    Host,
    ReaderOptions,
    SessionRecord,
    SessionUnit,
    UnitBatch,
    UntrackedRecord,
)
from agent_meter.readers._common import (
    DATA_ERRORS,
    DiagnosticCollector,
    RunDraft,
    TaskDraft,
    assemble,
    description_hash,
    fingerprint_file,
    is_test_command,
    iso_z,
    load_jsonl,
    parse_iso,
    path_digest,
    safe_label,
    shape_fingerprint,
)

__all__ = ["KNOWN_FORMATS", "ClaudeCodeReader", "format_fingerprint"]

_LOG = logging.getLogger(__name__)

HOST: Final = Host.CLAUDE_CODE
_PREFIX: Final = HOST.value
_SYNTHETIC_MODEL: Final = "<synthetic>"
_TIMELINE_TYPES: Final = frozenset({"user", "assistant", "system", "attachment"})
_EDIT_TOOLS: Final = {
    "Edit": "file_path",
    "Write": "file_path",
    "MultiEdit": "file_path",
    "NotebookEdit": "notebook_path",
}
_TEST_TOOLS: Final = frozenset({"Bash"})
_UNKNOWN_AGENT: Final = "(unknown)"
_AGENT_PREFIX: Final = f"{_PREFIX}:agent:"
_EARLIEST_SCAN_LINES: Final = 50


def format_fingerprint(source_formats: Sequence[str]) -> str:
    """Shape fingerprint of a unit: host plus the set of ``cc-<major.minor>`` versions seen."""
    return shape_fingerprint(
        ["host:claude-code", *(f"fmt:{f}" for f in source_formats)]
    )


KNOWN_FORMATS: Final[frozenset[str]] = frozenset({format_fingerprint(["cc-2.1"])})


def _source_format(version: object) -> str:
    if isinstance(version, str):
        parts = version.split(".")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"cc-{parts[0]}.{parts[1]}"
    return "cc-unknown"


def _count(value: object) -> int | None:
    """A token counter: non-negative ``int`` (not ``bool``), else unknown (``None``)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


@dataclass(frozen=True, slots=True)
class _Usage:
    input_tokens: int | None
    output_tokens: int | None
    thinking_tokens: int | None
    cache_write_5m: int | None
    cache_write_1h: int | None
    cache_read: int | None
    speed: str | None
    inference_geo: str | None
    unknown_iterations: bool


@dataclass(frozen=True, slots=True)
class _ToolUse:
    tool_id: str | None
    label: str
    file_digest: str | None
    is_test: bool


@dataclass(frozen=True, slots=True)
class _Line:
    type: str
    uuid: str | None
    parent_uuid: str | None
    prompt_id: str | None
    ts: datetime | None
    cwd: str | None
    version: str | None
    call_key: str | None
    model: str | None
    usage: _Usage | None
    is_api_error: bool
    tool_uses: tuple[_ToolUse, ...]
    tool_results: tuple[tuple[str, bool], ...]
    turn_duration_ms: int | None


def _usage(raw: Mapping[str, Any]) -> _Usage:
    cache_creation = raw.get("cache_creation")
    if isinstance(cache_creation, Mapping):
        write_5m = _count(cache_creation.get("ephemeral_5m_input_tokens", 0))
        write_1h = _count(cache_creation.get("ephemeral_1h_input_tokens", 0))
    elif "cache_creation_input_tokens" in raw:
        write_5m, write_1h = _count(raw.get("cache_creation_input_tokens")), 0
    else:
        write_5m = write_1h = None
    details = raw.get("output_tokens_details")
    thinking = (
        _count(details.get("thinking_tokens")) if isinstance(details, Mapping) else None
    )
    iterations = raw.get("iterations")
    unknown = isinstance(iterations, list) and any(
        not isinstance(item, Mapping) or item.get("type") != "message"
        for item in iterations
    )
    return _Usage(
        input_tokens=_count(raw.get("input_tokens")),
        output_tokens=_count(raw.get("output_tokens")),
        thinking_tokens=thinking,
        cache_write_5m=write_5m,
        cache_write_1h=write_1h,
        cache_read=_count(raw.get("cache_read_input_tokens")),
        speed=safe_label(raw.get("speed")),
        inference_geo=safe_label(raw.get("inference_geo")),
        unknown_iterations=unknown,
    )


def _tool_use(block: Mapping[str, Any]) -> _ToolUse:
    name = block.get("name")
    label = safe_label(name) or "(other)"
    inputs = block.get("input")
    inputs = inputs if isinstance(inputs, Mapping) else {}
    file_digest: str | None = None
    path_key = _EDIT_TOOLS.get(name) if isinstance(name, str) else None
    if path_key is not None and isinstance(inputs.get(path_key), str):
        file_digest = path_digest(inputs[path_key])
    command = inputs.get("command")
    is_test = (
        name in _TEST_TOOLS and isinstance(command, str) and is_test_command(command)
    )
    tool_id = block.get("id")
    return _ToolUse(
        tool_id if isinstance(tool_id, str) else None, label, file_digest, is_test
    )


def _str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _extract(obj: Mapping[str, Any]) -> _Line:
    """Reduce one JSON line to the allowlisted fields."""
    kind = obj.get("type")
    kind = kind if isinstance(kind, str) else ""
    message = obj.get("message")
    message = message if isinstance(message, Mapping) else {}
    content = message.get("content")
    blocks = (
        [b for b in content if isinstance(b, Mapping)]
        if isinstance(content, list)
        else []
    )
    usage = message.get("usage") if kind == "assistant" else None
    request_id = _str(obj.get("requestId"))
    message_id = _str(message.get("id"))
    call_key = (
        f"{_PREFIX}:{request_id}"
        if request_id
        else (f"{_PREFIX}:msg:{message_id}" if message_id else None)
    )
    duration = (
        obj.get("durationMs")
        if kind == "system" and obj.get("subtype") == "turn_duration"
        else None
    )
    return _Line(
        type=kind,
        uuid=_str(obj.get("uuid")),
        parent_uuid=_str(obj.get("parentUuid")),
        prompt_id=_str(obj.get("promptId")) if kind == "user" else None,
        ts=parse_iso(obj.get("timestamp")),
        cwd=_str(obj.get("cwd")),
        version=_str(obj.get("version")),
        call_key=call_key if kind == "assistant" else None,
        model=message.get("model") if isinstance(message.get("model"), str) else None,
        usage=_usage(usage) if isinstance(usage, Mapping) else None,
        is_api_error=obj.get("isApiErrorMessage") is True,
        tool_uses=tuple(
            _tool_use(b)
            for b in blocks
            if kind == "assistant" and b.get("type") == "tool_use"
        ),
        tool_results=tuple(
            (b["tool_use_id"], b.get("is_error") is True)
            for b in blocks
            if kind == "user"
            and b.get("type") == "tool_result"
            and isinstance(b.get("tool_use_id"), str)
        ),
        turn_duration_ms=_count(duration),
    )


@dataclass(slots=True)
class _CallCandidate:
    rank: str
    order: int
    line: _Line
    first_ts: datetime
    task_id: str
    run_id: str


@dataclass(slots=True)
class _Subagent:
    agent_id: str
    lines: list[_Line]
    meta: Mapping[str, Any]

    def meta_str(self, key: str) -> str | None:
        return _str(self.meta.get(key))


@dataclass(slots=True)
class _UnitState:
    session_id: str
    options: ReaderOptions
    diags: DiagnosticCollector
    tasks: dict[str, TaskDraft] = field(default_factory=dict)
    candidates: dict[str, list[_CallCandidate]] = field(default_factory=dict)
    spawn_owner: dict[str, tuple[str, str]] = field(
        default_factory=dict
    )  # tool_use id → (task, run)
    order: int = 0
    formats: set[str] = field(default_factory=set)

    def task(self, task_id: str) -> TaskDraft:
        return self.tasks.setdefault(task_id, TaskDraft(task_id=task_id))


class _SubagentLinker:
    """Resolves a subagent's spawn task, parent run and depth (ADR §3.5 rule 3).

    Task: the resolved task of the line holding ``tool_use.id == meta.toolUseId`` (main
    file or a sibling subagent), else the first ``promptId`` in the subagent file.
    Parent: ``meta.parentAgentId``, else the owner of ``toolUseId``, else the task's main run.
    """

    def __init__(self, agents: Mapping[str, _Subagent], state: _UnitState) -> None:
        self._agents = agents
        self._state = state
        self._sub_owner = {
            tool.tool_id: aid
            for aid, agent in agents.items()
            for line in agent.lines
            for tool in line.tool_uses
            if tool.tool_id is not None
        }
        self._tasks: dict[str, str] = {}

    def task_of(self, agent_id: str, visiting: frozenset[str] = frozenset()) -> str:
        if agent_id in self._tasks:
            return self._tasks[agent_id]
        agent = self._agents[agent_id]
        tool_use_id = agent.meta_str("toolUseId")
        owner = self._sub_owner.get(tool_use_id) if tool_use_id else None
        result: str | None = None
        if tool_use_id in self._state.spawn_owner:
            result = self._state.spawn_owner[tool_use_id][0]
        elif owner is not None and owner not in visiting | {agent_id}:
            result = self.task_of(owner, visiting | {agent_id})
        if result is None:
            first = next((ln.prompt_id for ln in agent.lines if ln.prompt_id), None)
            result = (
                f"{_PREFIX}:{first}" if first else _pre_task_id(self._state.session_id)
            )
        self._tasks[agent_id] = result
        return result

    def parent_of(self, agent_id: str) -> str | None:
        agent = self._agents[agent_id]
        parent_agent = agent.meta_str("parentAgentId")
        if parent_agent:
            return f"{_AGENT_PREFIX}{parent_agent}"
        tool_use_id = agent.meta_str("toolUseId")
        if tool_use_id in self._state.spawn_owner:
            return self._state.spawn_owner[tool_use_id][1]
        owner = self._sub_owner.get(tool_use_id) if tool_use_id else None
        if owner is not None and owner != agent_id:
            return f"{_AGENT_PREFIX}{owner}"
        task_id = self.task_of(agent_id)
        main_run = f"{task_id}:main"
        return main_run if main_run in self._state.task(task_id).runs else None

    def depth_of(self, agent_id: str, visiting: frozenset[str] = frozenset()) -> int:
        declared = _count(self._agents[agent_id].meta.get("spawnDepth"))
        if declared is not None and declared >= 1:
            return declared
        parent = self.parent_of(agent_id) or ""
        parent_id = (
            parent.removeprefix(_AGENT_PREFIX)
            if parent.startswith(_AGENT_PREFIX)
            else None
        )
        if parent_id is None or parent_id not in self._agents:
            return 1
        if parent_id in visiting | {agent_id}:
            return 1
        return self.depth_of(parent_id, visiting | {agent_id}) + 1


def _pre_task_id(session_id: str) -> str:
    """Synthetic task for lines before the first prompt of a session."""
    return f"{_PREFIX}:{session_id}:pre"


class ClaudeCodeReader:
    """``HostReader`` for Claude Code transcripts under ``root`` (``~/.claude``)."""

    host: Host = HOST

    def __init__(self, root: Path) -> None:
        self.root = root

    # ------------------------------------------------------------------ discovery (stat only)

    def _projects(self) -> Path:
        return self.root / "projects"

    def _unit(self, session_id: str, mains: Sequence[Path]) -> SessionUnit:
        files: list[FileFingerprint] = []
        for main in mains:
            fingerprint = fingerprint_file(self.root, main, "cc_main")
            if fingerprint is not None:
                files.append(fingerprint)
            sub_dir = main.parent / session_id / "subagents"
            if not sub_dir.is_dir():
                continue
            for path in sorted(sub_dir.iterdir()):
                if not path.name.startswith("agent-"):
                    continue
                kind = (
                    "cc_meta"
                    if path.name.endswith(".meta.json")
                    else "cc_sub"
                    if path.suffix == ".jsonl"
                    else None
                )
                if (
                    kind is not None
                    and (fingerprint := fingerprint_file(self.root, path, kind))
                    is not None
                ):
                    files.append(fingerprint)
        return SessionUnit(
            host=HOST, unit_id=session_id, root=self.root, files=tuple(files)
        )

    def discover(self) -> Iterator[SessionUnit]:
        projects = self._projects()
        if not projects.is_dir():
            return
        groups: dict[str, list[Path]] = {}
        for main in sorted(projects.glob("*/*.jsonl")):
            groups.setdefault(main.stem, []).append(main)
        for session_id in sorted(groups):
            yield self._unit(session_id, groups[session_id])

    def find_unit(self, session_or_conversation_id: str) -> SessionUnit | None:
        if not session_or_conversation_id or "/" in session_or_conversation_id:
            return None
        pattern = f"*/{glob.escape(session_or_conversation_id)}.jsonl"
        mains = (
            sorted(self._projects().glob(pattern)) if self._projects().is_dir() else []
        )
        return self._unit(session_or_conversation_id, mains) if mains else None

    def untracked(self) -> list[UntrackedRecord]:
        return []

    def earliest_available(self) -> date | None:
        earliest: datetime | None = None
        projects = self._projects()
        if not projects.is_dir():
            return None
        for main in projects.glob("*/*.jsonl"):
            first = self._first_timestamp(main)
            if first is not None and (earliest is None or first < earliest):
                earliest = first
        return earliest.date() if earliest is not None else None

    @staticmethod
    def _first_timestamp(path: Path) -> datetime | None:
        try:
            with path.open("rb") as handle:
                for _index, raw in zip(range(_EARLIEST_SCAN_LINES), handle):
                    if not raw.endswith(b"\n"):
                        return None
                    try:
                        obj = json.loads(raw)
                    except ValueError:
                        continue
                    if (
                        isinstance(obj, dict)
                        and (ts := parse_iso(obj.get("timestamp"))) is not None
                    ):
                        return ts
        except OSError as exc:
            _LOG.debug("cannot scan %s: %s", path.name, type(exc).__name__)
        return None

    # ------------------------------------------------------------------ parsing

    def read_unit(self, unit: SessionUnit, options: ReaderOptions) -> UnitBatch:
        diags = DiagnosticCollector()
        try:
            return self._read(unit, options, diags)
        except DATA_ERRORS as exc:
            kind = (
                DiagnosticKind.UNREADABLE
                if isinstance(exc, OSError)
                else DiagnosticKind.CORRUPT
            )
            _LOG.warning("claude-code unit unreadable: %s", type(exc).__name__)
            fresh = DiagnosticCollector()
            fresh.add(kind, "cc_main", type(exc).__name__)
            return self._empty(unit, fresh)

    def _empty(self, unit: SessionUnit, diags: DiagnosticCollector) -> UnitBatch:
        return UnitBatch(
            unit=unit,
            sessions=(),
            tasks=(),
            agent_runs=(),
            calls=(),
            tool_uses=(),
            diagnostics=diags.build(HOST, unit.unit_id),
            format_fingerprint=format_fingerprint([]),
        )

    def _load_lines(
        self, path: Path, file_kind: str, diags: DiagnosticCollector
    ) -> list[_Line]:
        objects, invalid = load_jsonl(path)
        diags.add(DiagnosticKind.CORRUPT, file_kind, "JSONDecodeError", invalid)
        return [_extract(obj) for obj in objects]

    def _read(
        self, unit: SessionUnit, options: ReaderOptions, diags: DiagnosticCollector
    ) -> UnitBatch:
        state = _UnitState(session_id=unit.unit_id, options=options, diags=diags)
        main_lines: list[_Line] = []
        for f in unit.files:
            if f.kind == "cc_main":
                main_lines.extend(
                    self._load_lines(self.root / f.relpath, "cc_main", diags)
                )
        self._read_main(main_lines, state)
        self._read_subagents(unit, state)
        calls = self._calls(state)
        tasks, runs, tools = assemble(HOST, unit.unit_id, state.tasks.values(), options)
        sessions = self._session(unit.unit_id, main_lines, tasks, options)
        return UnitBatch(
            unit=unit,
            sessions=sessions,
            tasks=tuple(tasks),
            agent_runs=tuple(runs),
            calls=tuple(calls),
            tool_uses=tuple(tools),
            diagnostics=diags.build(HOST, unit.unit_id),
            format_fingerprint=format_fingerprint(sorted(state.formats)),
        )

    # -- main thread

    @staticmethod
    def _resolver(lines: Sequence[_Line]) -> Callable[[_Line], str | None]:
        """Nearest ``user`` ancestor carrying a ``promptId`` along the ``parentUuid`` chain (memoized)."""
        by_uuid = {line.uuid: line for line in lines if line.uuid}
        memo: dict[str, str | None] = {}

        def resolve(line: _Line) -> str | None:
            chain: list[str] = []
            current: _Line | None = line
            found: str | None = None
            seen: set[str] = set()
            while current is not None:
                if current.type == "user" and current.prompt_id:
                    found = current.prompt_id
                    break
                if current.uuid is not None:
                    if current.uuid in memo:
                        found = memo[current.uuid]
                        break
                    if current.uuid in seen:
                        break
                    seen.add(current.uuid)
                    chain.append(current.uuid)
                current = (
                    by_uuid.get(current.parent_uuid) if current.parent_uuid else None
                )
            for uuid in chain:
                memo[uuid] = found
            return found

        return resolve

    def _read_main(self, lines: Sequence[_Line], state: _UnitState) -> None:
        resolve = self._resolver(lines)
        rank_ts = next((line.ts for line in lines if line.ts is not None), None)
        rank = (
            f"0:{iso_z(rank_ts)}:{state.session_id}"
            if rank_ts
            else f"0::{state.session_id}"
        )
        last_prompt: str | None = None
        tool_index: dict[str, tuple[RunDraft, _ToolUse]] = {}
        for line in lines:
            if line.type == "user" and line.prompt_id:
                last_prompt = line.prompt_id
            prompt = resolve(line) or last_prompt
            task_id = (
                f"{_PREFIX}:{prompt}" if prompt else _pre_task_id(state.session_id)
            )
            if line.type not in _TIMELINE_TYPES or line.ts is None:
                continue
            task = state.task(task_id)
            run_id = f"{task_id}:main"
            run = task.runs.get(run_id)
            if run is None:
                run = task.runs[run_id] = RunDraft(run_id, "main", None, 0)
            if line.turn_duration_ms is not None:
                task.reported_ms = line.turn_duration_ms
            self._apply_line(line, run, tool_index, state)
            for tool in line.tool_uses:
                if tool.tool_id is not None:
                    state.spawn_owner[tool.tool_id] = (task_id, run_id)
            self._candidate(line, rank, task_id, run_id, state)

    # -- shared per-line accounting

    @staticmethod
    def _apply_line(
        line: _Line,
        run: RunDraft,
        tool_index: dict[str, tuple[RunDraft, _ToolUse]],
        state: _UnitState,
    ) -> None:
        if line.ts is not None:
            run.events.append(line.ts)
        if line.version:
            state.formats.add(_source_format(line.version))
        if line.is_api_error:
            run.errors += 1
        for tool in line.tool_uses:
            run.record_tool(tool.label)
            if tool.file_digest is not None:
                run.files.add(tool.file_digest)
            if tool.is_test:
                run.test_runs += 1
            if tool.tool_id is not None:
                tool_index[tool.tool_id] = (run, tool)
        for tool_use_id, is_error in line.tool_results:
            owner = tool_index.get(tool_use_id)
            if owner is None or not is_error:
                continue
            owner_run, tool = owner
            owner_run.record_tool_error(tool.label)
            if tool.is_test:
                owner_run.test_failures += 1

    @staticmethod
    def _candidate(
        line: _Line, rank: str, task_id: str, run_id: str, state: _UnitState
    ) -> None:
        if (
            line.type != "assistant"
            or line.usage is None
            or line.model == _SYNTHETIC_MODEL
            or line.ts is None
        ):
            return
        if line.call_key is None:
            state.diags.add(
                DiagnosticKind.FORMAT_CHANGED, "cc_main", "MissingRequestId"
            )
            return
        state.order += 1
        state.candidates.setdefault(line.call_key, []).append(
            _CallCandidate(rank, state.order, line, line.ts, task_id, run_id)
        )

    # -- subagents

    def _read_subagents(self, unit: SessionUnit, state: _UnitState) -> None:
        metas: dict[str, Mapping[str, Any]] = {}
        subs: dict[str, list[_Line]] = {}
        for f in unit.files:
            name = f.relpath.rsplit("/", 1)[-1]
            if f.kind == "cc_meta":
                agent_id = name[len("agent-") : -len(".meta.json")]
                metas[agent_id] = self._load_meta(self.root / f.relpath, state.diags)
            elif f.kind == "cc_sub":
                agent_id = name[len("agent-") : -len(".jsonl")]
                try:
                    subs[agent_id] = self._load_lines(
                        self.root / f.relpath, "cc_sub", state.diags
                    )
                except DATA_ERRORS as exc:
                    state.diags.add(
                        DiagnosticKind.UNREADABLE, "cc_sub", type(exc).__name__
                    )
        agents = {
            aid: _Subagent(aid, lines, metas.get(aid, {}))
            for aid, lines in sorted(subs.items())
        }
        linker = _SubagentLinker(agents, state)
        for agent_id, agent in agents.items():
            self._read_subagent(
                agent,
                linker.task_of(agent_id),
                linker.parent_of(agent_id),
                linker.depth_of(agent_id),
                state,
            )

    def _load_meta(self, path: Path, diags: DiagnosticCollector) -> Mapping[str, Any]:
        try:
            raw = path.read_bytes()
            meta = json.loads(raw)
        except DATA_ERRORS as exc:
            diags.add(DiagnosticKind.CORRUPT, "cc_meta", type(exc).__name__)
            return {}
        if not isinstance(meta, dict):
            diags.add(DiagnosticKind.CORRUPT, "cc_meta", "NotAnObject")
            return {}
        return meta

    def _read_subagent(
        self,
        agent: _Subagent,
        task_id: str,
        parent: str | None,
        depth: int,
        state: _UnitState,
    ) -> None:
        run_id = f"{_AGENT_PREFIX}{agent.agent_id}"
        description = agent.meta_str("description")
        run = RunDraft(
            agent_run_id=run_id,
            agent_type=safe_label(agent.meta.get("agentType")) or _UNKNOWN_AGENT,
            parent_agent_run_id=parent,
            spawn_depth=depth,
            description_hash=(
                description_hash(state.options.description_salt, description)
                if description
                else None
            ),
            stopped=agent.meta.get("stoppedByUser") is True,
        )
        state.task(task_id).runs[run_id] = run
        rank_ts = next((line.ts for line in agent.lines if line.ts is not None), None)
        rank = (
            f"1:{iso_z(rank_ts)}:{state.session_id}"
            if rank_ts
            else f"1::{state.session_id}"
        )
        tool_index: dict[str, tuple[RunDraft, _ToolUse]] = {}
        for line in agent.lines:
            if line.type not in _TIMELINE_TYPES or line.ts is None:
                continue
            self._apply_line(line, run, tool_index, state)
            self._candidate(line, rank, task_id, run_id, state)

    # -- calls

    def _calls(self, state: _UnitState) -> list[CallRecord]:
        calls: list[CallRecord] = []
        for call_key, candidates in state.candidates.items():
            owner = min(candidates, key=lambda c: (c.rank, c.order))
            best = max(
                candidates,
                key=lambda c: (
                    c.line.usage.output_tokens
                    if c.line.usage and c.line.usage.output_tokens is not None
                    else -1,
                    -c.order,
                ),
            )
            first_ts = min(c.first_ts for c in candidates if c.rank == owner.rank)
            use = best.line.usage
            if use is None:
                continue
            if use.unknown_iterations:
                state.diags.add(
                    DiagnosticKind.UNKNOWN_USAGE_ITERATION,
                    "cc_sub" if owner.rank.startswith("1") else "cc_main",
                )
            calls.append(
                CallRecord(
                    call_id=call_key,
                    host=HOST,
                    session_id=state.session_id,
                    task_id=owner.task_id,
                    agent_run_id=owner.run_id,
                    ts=first_ts,
                    model=safe_label(best.line.model),
                    model_label=None,
                    input_tokens=use.input_tokens,
                    output_tokens=use.output_tokens,
                    thinking_tokens=use.thinking_tokens,
                    cache_write_5m_tokens=use.cache_write_5m,
                    cache_write_1h_tokens=use.cache_write_1h,
                    cache_read_tokens=use.cache_read,
                    latency_ms=None,
                    speed=use.speed,
                    inference_geo=use.inference_geo,
                    is_error=any(c.line.is_api_error for c in candidates),
                    source_format=_source_format(owner.line.version),
                    owner_rank=owner.rank,
                )
            )
        calls.sort(key=lambda c: (c.ts, c.call_id))
        return calls

    # -- session

    @staticmethod
    def _session(
        session_id: str,
        main_lines: Sequence[_Line],
        tasks: Sequence[Any],
        options: ReaderOptions,
    ) -> tuple[SessionRecord, ...]:
        if not tasks:
            return ()
        started = min(t.started_at for t in tasks)
        ended = max(t.ended_at for t in tasks)
        stale = (options.now - ended).total_seconds() > options.stale_after_s
        version = next(
            (line.version for line in reversed(main_lines) if line.version), None
        )
        return (
            SessionRecord(
                session_id=session_id,
                host=HOST,
                workspace_path=next(
                    (line.cwd for line in main_lines if line.cwd), None
                ),
                started_at=started,
                ended_at=ended,
                status="closed" if stale else "open",
                host_version=safe_label(version),
                owner_rank="0",
            ),
        )
