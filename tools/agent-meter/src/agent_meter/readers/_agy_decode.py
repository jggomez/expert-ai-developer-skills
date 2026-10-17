"""Antigravity decoding: conversation DB rows, ``gen_metadata`` protobuf and transcripts.

Pure, allowlist-driven functions used by ``readers.antigravity`` (ADR §3.4). Nothing here
returns text content: only ids, timestamps, counters, model labels, tool names, hashed
edit targets and a "test command" flag.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final
from urllib.parse import quote

from agent_meter.model import DiagnosticKind, Host
from agent_meter.readers._common import (
    DiagnosticCollector,
    from_epoch,
    is_test_command,
    load_jsonl,
    parse_iso,
    path_digest,
    safe_label,
)
from agent_meter.readers._protowire import (
    ProtoDecodeError,
    duration_ms,
    get_path,
    kv_map,
    parse,
)

__all__ = [
    "ERROR_MESSAGE",
    "GEN_FORMAT",
    "KNOWN_DB_SHAPE",
    "NON_RESULT_KINDS",
    "PLANNER",
    "TRANSCRIPT_FORMAT",
    "USER_INPUT",
    "DbContents",
    "GenCall",
    "Step",
    "Tool",
    "count",
    "fallback_calls",
    "owned_parent",
    "read_database",
    "read_transcript",
    "ro_connect",
    "step_ts",
    "workspace_from_summary",
]

USER_INPUT: Final = "USER_INPUT"
PLANNER: Final = "PLANNER_RESPONSE"
ERROR_MESSAGE: Final = "ERROR_MESSAGE"
NON_RESULT_KINDS: Final = frozenset(
    {USER_INPUT, PLANNER, ERROR_MESSAGE, "SYSTEM_MESSAGE", "CHECKPOINT"}
)
GEN_FORMAT: Final = "agy-gen-v1"
TRANSCRIPT_FORMAT: Final = "agy-transcript-v1"

_STEP_KINDS: Final = {14: USER_INPUT, 15: PLANNER, 17: ERROR_MESSAGE}
_EDIT_TOOLS: Final = frozenset(
    {"write_to_file", "replace_file_content", "multi_replace_file_content"}
)
_COMMAND_TOOLS: Final = frozenset({"run_command"})
_USAGE_FIELDS: Final = frozenset({2, 3, 5, 9, 10})  # 1.4.{2,3,5,9,10}
_REQUIRED_COLUMNS: Final = {
    "trajectory_meta": frozenset({"trajectory_id"}),
    "steps": frozenset({"idx", "step_type", "metadata"}),
    "gen_metadata": frozenset({"idx", "data"}),
}

# Table/column shape of the conversation DB as observed on 2026-10-16 (schema only).
KNOWN_DB_SHAPE: Final = (
    "table:battle_mode_infos(data,idx)",
    "table:executor_metadata(data,idx)",
    "table:gen_metadata(data,idx,size)",
    "table:parent_references(data,idx)",
    (
        "table:steps(error_details,has_subtrajectory,idx,metadata,permissions,"
        "render_info,status,step_format,step_payload,step_type,task_details)"
    ),
    "table:trajectory_meta(cascade_id,source,trajectory_id,trajectory_type)",
    "table:trajectory_metadata_blob(data,id)",
)

Usage = tuple[
    int | None, int | None, int | None, int | None
]  # input, output, thinking, cache read
_UNKNOWN_USAGE: Final[Usage] = (None, None, None, None)


@dataclass(frozen=True, slots=True)
class Tool:
    label: str
    file_digest: str | None
    is_test: bool


@dataclass(frozen=True, slots=True)
class Step:
    idx: int
    kind: str
    ts: datetime | None
    has_error: bool = False
    tools: tuple[Tool, ...] = ()
    tokens: tuple[int, int, int] | None = None  # transcript (input, cache_read, output)


@dataclass(frozen=True, slots=True)
class GenCall:
    call_id: str
    owner_rank: str
    step_idx: int
    ts: datetime
    model: str | None
    model_label: str | None
    input_tokens: int | None
    output_tokens: int | None
    thinking_tokens: int | None
    cache_read_tokens: int | None
    cache_write_tokens: int | None
    latency_ms: int | None
    is_error: bool
    source_format: str


@dataclass(frozen=True, slots=True)
class DbContents:
    steps: list[Step]
    calls: list[GenCall]
    workspace: str | None


@dataclass(frozen=True, slots=True)
class _DbRows:
    own_trajectory: str | None
    steps: list[tuple[Any, Any, Any]]
    gen: list[tuple[Any, Any]]
    blob: bytes | None


# ----------------------------------------------------------------------------- small helpers


def count(value: object) -> int | None:
    """Non-negative ``int`` (never ``bool``) or ``None``."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _first_bytes(values: Sequence[int | bytes]) -> bytes | None:
    return next((v for v in values if isinstance(v, bytes)), None)


def _first_int(values: Sequence[int | bytes]) -> int | None:
    return next((v for v in values if isinstance(v, int)), None)


def _text(value: bytes | None) -> str | None:
    if value is None:
        return None
    try:
        return value.decode("utf-8") or None
    except UnicodeDecodeError:
        return None


def ro_connect(path: Path) -> sqlite3.Connection:
    """Read-only SQLite connection (WAL content visible; ADR §3.3, invariant I-3)."""
    con = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True, timeout=2.0)
    con.execute("PRAGMA query_only=1")
    con.execute("PRAGMA busy_timeout=2000")
    return con


def step_ts(metadata: bytes) -> datetime | None:
    """``steps.metadata`` field ``1`` is a ``{1: seconds, 2: nanos}`` timestamp."""
    seconds = _first_int(get_path(metadata, "1.1"))
    if seconds is None:
        return None
    return from_epoch(seconds, _first_int(get_path(metadata, "1.2")) or 0)


def workspace_from_summary(raw: object) -> str | None:
    """``workspace_uris`` is a JSON list (usually) or a plain string."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if not text.startswith("["):
        return text
    try:
        values = json.loads(text)
    except ValueError:
        return None
    if not isinstance(values, list):
        return None
    return next((v for v in values if isinstance(v, str) and v), None)


# ----------------------------------------------------------------------------- transcripts


def _tool(entry: Mapping[str, Any]) -> Tool:
    name = entry.get("name")
    args = entry.get("args")
    args = args if isinstance(args, Mapping) else {}
    target = args.get("TargetFile")
    command = args.get("CommandLine")
    edited = target if name in _EDIT_TOOLS and isinstance(target, str) else None
    runs_tests = (
        name in _COMMAND_TOOLS and isinstance(command, str) and is_test_command(command)
    )
    return Tool(
        label=safe_label(name) or "(other)",
        file_digest=path_digest(edited) if edited is not None else None,
        is_test=runs_tests,
    )


def _planner_tokens(obj: Mapping[str, Any]) -> tuple[int, int, int] | None:
    tokens = (
        count(obj.get("input_tokens")),
        count(obj.get("cache_read_tokens")),
        count(obj.get("output_tokens")),
    )
    if tokens[0] is None or tokens[1] is None or tokens[2] is None:
        return None
    return tokens[0], tokens[1], tokens[2]


def _transcript_step(obj: Mapping[str, Any]) -> Step | None:
    idx = count(obj.get("step_index"))
    kind = obj.get("type")
    if idx is None or not isinstance(kind, str):
        return None
    calls = obj.get("tool_calls")
    error = obj.get("error")
    return Step(
        idx=idx,
        kind=kind,
        ts=parse_iso(obj.get("created_at")),
        has_error=obj.get("status") == "ERROR"
        or (isinstance(error, str) and bool(error)),
        tools=tuple(_tool(c) for c in calls if isinstance(c, Mapping))
        if isinstance(calls, list)
        else (),
        tokens=_planner_tokens(obj) if kind == PLANNER else None,
    )


def read_transcript(path: Path, diags: DiagnosticCollector) -> list[Step] | None:
    """Steps of ``transcript_full.jsonl`` ordered by index; ``None`` if the file is absent."""
    if not path.is_file():
        return None
    try:
        objects, invalid = load_jsonl(path)
    except OSError as exc:
        diags.add(DiagnosticKind.UNREADABLE, "agy_transcript", type(exc).__name__)
        return None
    diags.add(DiagnosticKind.CORRUPT, "agy_transcript", "JSONDecodeError", invalid)
    steps = {s.idx: s for obj in objects if (s := _transcript_step(obj)) is not None}
    return [steps[i] for i in sorted(steps)]


def fallback_calls(host: Host, cid: str, steps: Sequence[Step]) -> list[GenCall]:
    """Transcript usage for a conversation without a DB: ``PLANNER_RESPONSE`` steps only."""
    return [
        GenCall(
            call_id=f"{host.value}:conv:{cid}:{step.idx}",
            owner_rank="0",
            step_idx=step.idx,
            ts=step.ts,
            model=None,
            model_label=None,
            input_tokens=step.tokens[0],
            output_tokens=step.tokens[2],
            thinking_tokens=None,
            cache_read_tokens=step.tokens[1],
            cache_write_tokens=0,
            latency_ms=None,
            is_error=False,
            source_format=TRANSCRIPT_FORMAT,
        )
        for step in steps
        if step.kind == PLANNER and step.tokens is not None and step.ts is not None
    ]


# ----------------------------------------------------------------------------- databases


def _schema(con: sqlite3.Connection) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for (name,) in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ):
        info = con.execute(f"PRAGMA table_info({json.dumps(name)})")
        tables[name] = {row[1] for row in info}
    return tables


def _fetch_rows(con: sqlite3.Connection, tables: Mapping[str, set[str]]) -> _DbRows:
    own = con.execute("SELECT trajectory_id FROM trajectory_meta LIMIT 1").fetchone()
    steps = con.execute("SELECT idx, step_type, metadata FROM steps ORDER BY idx")
    gen = con.execute("SELECT idx, data FROM gen_metadata ORDER BY idx")
    blob = None
    if "trajectory_metadata_blob" in tables:
        blob = con.execute(
            "SELECT data FROM trajectory_metadata_blob ORDER BY id = 'main' DESC LIMIT 1"
        ).fetchone()
    return _DbRows(
        own_trajectory=own[0] if own and isinstance(own[0], str) else None,
        steps=steps.fetchall(),
        gen=gen.fetchall(),
        blob=blob[0] if blob and isinstance(blob[0], bytes) else None,
    )


def read_database(
    host: Host, cid: str, path: Path, diags: DiagnosticCollector, shape: set[str]
) -> DbContents | None:
    """Decode one ``conversations/<id>.db``; ``None`` when absent or of unknown schema.

    ``shape`` receives the table/column tokens used for the unit's format fingerprint.
    SQLite errors propagate to the caller, which turns them into diagnostics.
    """
    if not path.is_file():
        return None
    with closing(ro_connect(path)) as con:
        tables = _schema(con)
        shape.update(
            f"table:{t}({','.join(sorted(cols))})" for t, cols in tables.items()
        )
        if any(not req <= tables.get(t, set()) for t, req in _REQUIRED_COLUMNS.items()):
            diags.add(DiagnosticKind.FORMAT_CHANGED, "agy_db", "SchemaChanged")
            return None
        shape.add(f"fmt:{GEN_FORMAT}")
        rows = _fetch_rows(con, tables)
    if rows.own_trajectory is None:
        diags.add(DiagnosticKind.FORMAT_CHANGED, "agy_db", "MissingTrajectory")
    steps = [
        Step(
            idx=idx,
            kind=_STEP_KINDS.get(step_type, f"type:{step_type}"),
            ts=step_ts(metadata) if isinstance(metadata, bytes) else None,
        )
        for idx, step_type, metadata in rows.steps
        if isinstance(idx, int) and isinstance(step_type, int)
    ]
    decoder = _GenDecoder(host, cid, rows.own_trajectory, steps, diags)
    calls = [c for _idx, data in rows.gen if (c := decoder.decode(data)) is not None]
    workspace = _text(_first_bytes(get_path(rows.blob, "1.1"))) if rows.blob else None
    return DbContents(steps=steps, calls=calls, workspace=workspace)


def owned_parent(path: Path, scan_rows: int) -> str | None:
    """``parent_cascade_id`` from the first owned ``gen_metadata`` rows (parent fallback)."""
    with closing(ro_connect(path)) as con:
        own = con.execute(
            "SELECT trajectory_id FROM trajectory_meta LIMIT 1"
        ).fetchone()
        rows = con.execute(
            "SELECT data FROM gen_metadata ORDER BY idx LIMIT ?", (scan_rows,)
        ).fetchall()
    if own is None:
        return None
    for (data,) in rows:
        if not isinstance(data, bytes):
            continue
        kv = kv_map(data)
        if kv.get("trajectory_id") == own[0] and kv.get("parent_cascade_id"):
            return kv["parent_cascade_id"]
    return None


class _GenDecoder:
    """Decodes ``gen_metadata.data`` rows of one conversation into ``GenCall`` values."""

    def __init__(
        self,
        host: Host,
        cid: str,
        own_trajectory: str | None,
        steps: Sequence[Step],
        diags: DiagnosticCollector,
    ) -> None:
        self._host = host
        self._cid = cid
        self._own = own_trajectory
        self._diags = diags
        self._steps = sorted(steps, key=lambda s: s.idx)
        self._by_idx = {s.idx: s for s in steps}

    def decode(self, data: object) -> GenCall | None:
        if not isinstance(data, bytes):
            self._diags.add(DiagnosticKind.CORRUPT, "agy_db", "NotBytes")
            return None
        try:
            parse(data)
        except ProtoDecodeError:
            self._diags.add(DiagnosticKind.CORRUPT, "agy_db", "ProtoDecodeError")
            return None
        key = self._key(data)
        if key is None:
            self._diags.add(DiagnosticKind.FORMAT_CHANGED, "agy_db", "MissingKey")
            return None
        trajectory, last_step = key
        step_idx = last_step + 1  # the call belongs to the step after last_step_index
        ts = self._timestamp(data, step_idx)
        if ts is None:
            self._diags.add(DiagnosticKind.FORMAT_CHANGED, "agy_db", "MissingTimestamp")
            return None
        input_tokens, output_tokens, thinking, cache_read = self._usage(data)
        step = self._by_idx.get(step_idx)
        return GenCall(
            call_id=f"{self._host.value}:{trajectory}:{last_step}",
            owner_rank="0" if trajectory == self._own else f"1:{self._cid}",
            step_idx=step_idx,
            ts=ts,
            model=safe_label(_text(_first_bytes(get_path(data, "1.19")))),
            model_label=safe_label(_text(_first_bytes(get_path(data, "1.21")))),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking,
            cache_read_tokens=cache_read,
            cache_write_tokens=None if input_tokens is None else 0,
            latency_ms=duration_ms(data, "1.11"),
            is_error=step is not None and step.kind == ERROR_MESSAGE,
            source_format=GEN_FORMAT,
        )

    @staticmethod
    def _key(data: bytes) -> tuple[str, int] | None:
        kv = kv_map(data)
        trajectory = kv.get("trajectory_id")
        try:
            last_step = int(kv["last_step_index"])
        except (KeyError, ValueError):
            return None
        return (trajectory, last_step) if trajectory else None

    def _usage(self, data: bytes) -> Usage:
        """``1.4``: absent → unknown (never 0); present → absent subfields are proto3 zeros."""
        message = _first_bytes(get_path(data, "1.4"))
        if message is None:
            self._diags.add(DiagnosticKind.FORMAT_CHANGED, "agy_db", "MissingUsage")
            return _UNKNOWN_USAGE
        try:
            fields = {
                f: v for f, w, v in parse(message) if w == 0 and isinstance(v, int)
            }
        except ProtoDecodeError:
            self._diags.add(DiagnosticKind.CORRUPT, "agy_db", "ProtoDecodeError")
            return _UNKNOWN_USAGE
        if not fields.keys() & _USAGE_FIELDS:
            self._diags.add(
                DiagnosticKind.FORMAT_CHANGED, "agy_db", "UnknownUsageLayout"
            )
            return _UNKNOWN_USAGE
        return fields.get(2, 0), fields.get(3, 0), fields.get(9, 0), fields.get(5, 0)

    def _timestamp(self, data: bytes, step_idx: int) -> datetime | None:
        """Step ``ts`` → call start ``1.9.4`` → latest earlier step with a timestamp."""
        step = self._by_idx.get(step_idx)
        if step is not None and step.ts is not None:
            return step.ts
        seconds = _first_int(get_path(data, "1.9.4.1"))
        if seconds is not None:
            return from_epoch(seconds, _first_int(get_path(data, "1.9.4.2")) or 0)
        earlier = [s.ts for s in self._steps if s.idx <= step_idx and s.ts is not None]
        return earlier[-1] if earlier else None
