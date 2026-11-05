"""Helpers shared by the host readers: privacy filters, JSONL rules and record assembly."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import sqlite3
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePath
from typing import Any, Final

from agent_meter.model import (
    AgentRunRecord,
    Diagnostic,
    DiagnosticKind,
    DurationSource,
    FileFingerprint,
    Host,
    ReaderOptions,
    RunStatus,
    TaskRecord,
    TaskStatus,
    ToolUseRecord,
)
from agent_meter.readers._protowire import ProtoDecodeError
from agent_meter.timeline import (
    Interval,
    RunSpan,
    active_intervals,
    critical_path,
    retries,
    total_ms,
    union,
)

__all__ = [
    "DATA_ERRORS",
    "OTHER_LABEL",
    "DiagnosticCollector",
    "RunDraft",
    "TaskDraft",
    "assemble",
    "description_hash",
    "fingerprint_file",
    "is_test_command",
    "iso_z",
    "load_jsonl",
    "parse_iso",
    "read_complete_lines",
    "reports_test_failure",
    "safe_label",
    "shape_fingerprint",
    "unit_hash",
]

OTHER_LABEL: Final = "(other)"
_SAFE_LABEL: Final = re.compile(r"^[A-Za-z0-9_.:@/+ ()-]{1,80}$")
_ENV_ASSIGNMENT: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_TEST_PREFIXES: Final = (
    ("pytest",),
    ("python", "-m", "pytest"),
    ("python3", "-m", "pytest"),
    ("uv", "run", "pytest"),
    ("poetry", "run", "pytest"),
    ("tox",),
    ("nox",),
    ("npm", "test"),
    ("npm", "t"),
    ("pnpm", "test"),
    ("yarn", "test"),
    ("bun", "test"),
    ("jest",),
    ("vitest",),
    ("mocha",),
    ("npx", "jest"),
    ("npx", "vitest"),
    ("npx", "mocha"),
    ("npx", "playwright", "test"),
    ("playwright", "test"),
    ("flutter", "test"),
    ("dart", "test"),
    ("go", "test"),
    ("cargo", "test"),
    ("make", "test"),
    ("gradle", "test"),
    ("gradlew", "test"),
    ("mvn", "test"),
)
_SCRIPT_RUNNERS: Final = (("npm", "run"), ("pnpm", "run"), ("yarn", "run"), ("bun", "run"), ("yarn",))
_COMMAND_WRAPPERS: Final = frozenset({"command", "env", "exec", "nice", "sudo", "time"})
_SHELL_SEPARATORS: Final = frozenset(";&|()\n")
_FAILURE_TAIL_CHARS: Final = 16_384
_TEST_FAILURE: Final = re.compile(
    r"(?<!Found )\b[1-9]\d* (?:failed|failing|errors?)\b"  # "Found N errors" is ruff, mypy or tsc
    r"|Some tests failed"
    r"|test result: FAILED"
    r"|^--- FAIL:"
    r"|^FAIL\b",
    re.MULTILINE,
)

# Errors that mean "this input is unreadable or malformed" (never programming errors we hide:
# they are converted into a Diagnostic carrying only the exception class name, ADR §3.3).
DATA_ERRORS: Final = (
    OSError,
    sqlite3.Error,
    ValueError,  # includes json.JSONDecodeError, UnicodeDecodeError, ProtoDecodeError
    TypeError,
    KeyError,
    IndexError,
    AttributeError,
    OverflowError,
    RecursionError,
    ProtoDecodeError,
)


def safe_label(value: object) -> str | None:
    """Allowlisted free-text slot (ADR §3.13): valid → value, invalid → ``"(other)"``, empty → ``None``."""
    if not isinstance(value, str) or not value:
        return None
    return value if _SAFE_LABEL.fullmatch(value) else OTHER_LABEL


def unit_hash(unit_id: str) -> str:
    return hashlib.sha256(unit_id.encode("utf-8")).hexdigest()[:12]


def description_hash(salt: bytes, text: str) -> str:
    return hashlib.sha256(salt + text.encode("utf-8")).hexdigest()


def path_digest(path: str) -> str:
    """In-memory identity of a touched file path (only ever counted, never stored)."""
    return hashlib.sha256(path.encode("utf-8", "surrogatepass")).hexdigest()


def _shell_segments(command: str) -> list[list[str]]:
    """Tokens of each simple command in ``command``; unparseable input is one naive segment."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    segments: list[list[str]] = [[]]
    try:
        for token in lexer:
            if set(token) <= _SHELL_SEPARATORS:
                segments.append([])
            else:
                segments[-1].append(token)
    except ValueError:
        return [command.split()]
    return [segment for segment in segments if segment]


def _strip_wrappers(tokens: list[str]) -> list[str]:
    """Drop ``VAR=value`` prefixes and wrappers such as ``time`` or ``timeout 120``."""
    rest = list(tokens)
    while rest:
        if _ENV_ASSIGNMENT.match(rest[0]) or rest[0] in _COMMAND_WRAPPERS:
            rest.pop(0)
        elif rest[0] == "timeout" and len(rest) > 1:
            rest = rest[2:]
        else:
            break
    return rest


def _runs_tests(tokens: list[str]) -> bool:
    words = _strip_wrappers(tokens)
    if not words:
        return False
    words[0] = PurePath(words[0]).name
    for runner in _SCRIPT_RUNNERS:
        script = words[len(runner)] if len(words) > len(runner) else ""
        if tuple(words[: len(runner)]) == runner and (script == "test" or script.startswith("test:")):
            return True
    return any(tuple(words[: len(prefix)]) == prefix for prefix in _TEST_PREFIXES)


def is_test_command(command: str) -> bool:
    """True when any simple command of a shell line starts with a known test runner."""
    return any(_runs_tests(segment) for segment in _shell_segments(command))


def reports_test_failure(output: object) -> bool:
    """True when a test runner's summary reports failures, even if a pipe hid its exit code.

    The output is only inspected here. Nothing from it is kept, in line with the privacy rule.
    """
    if isinstance(output, list):
        return any(isinstance(b, Mapping) and reports_test_failure(b.get("text")) for b in output)
    return isinstance(output, str) and _TEST_FAILURE.search(output[-_FAILURE_TAIL_CHARS:]) is not None


def read_complete_lines(path: Path) -> list[bytes]:
    """Lines up to the last ``\\n``; a trailing partial line is never returned (ADR §3.3)."""
    with path.open("rb") as handle:
        data = handle.read()
    end = data.rfind(b"\n")
    if end < 0:
        return []
    return data[:end].split(b"\n")


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Parse complete JSONL lines into objects; returns ``(objects, invalid_line_count)``."""
    objects: list[dict[str, Any]] = []
    invalid = 0
    for raw in read_complete_lines(path):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except ValueError:
            invalid += 1
            continue
        if isinstance(value, dict):
            objects.append(value)
        else:
            invalid += 1
    return objects, invalid


def parse_iso(value: object) -> datetime | None:
    """ISO-8601 → aware UTC datetime; naive values are taken as UTC; invalid → ``None``."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def from_epoch(seconds: int, nanos: int = 0) -> datetime | None:
    try:
        return datetime.fromtimestamp(seconds, tz=UTC) + timedelta(
            microseconds=nanos // 1000
        )
    except (OverflowError, OSError, ValueError):
        return None


def iso_z(value: datetime) -> str:
    """Millisecond ISO-8601 in UTC with a ``Z`` suffix (used inside ``owner_rank``)."""
    utc = value.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def shape_fingerprint(tokens: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(sorted(set(tokens))).encode("utf-8")).hexdigest()


def fingerprint_file(root: Path, path: Path, kind: str) -> FileFingerprint | None:
    """Stat one file into a ``FileFingerprint``; ``None`` if it vanished meanwhile."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return FileFingerprint(
        relpath=path.relative_to(root).as_posix(),
        kind=kind,
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        inode=stat.st_ino,
    )


class DiagnosticCollector:
    """Aggregates diagnostics by ``(kind, file_kind, error_class)``."""

    def __init__(self) -> None:
        self._counts: Counter[tuple[DiagnosticKind, str, str | None]] = Counter()

    def add(
        self,
        kind: DiagnosticKind,
        file_kind: str,
        error_class: str | None = None,
        count: int = 1,
    ) -> None:
        if count > 0:
            self._counts[(kind, file_kind, error_class)] += count

    def build(self, host: Host, unit_id: str) -> tuple[Diagnostic, ...]:
        hashed = unit_hash(unit_id)
        return tuple(
            Diagnostic(
                host=host,
                kind=kind,
                unit_hash=hashed,
                file_kind=file_kind,
                error_class=error_class,
                count=n,
            )
            for (kind, file_kind, error_class), n in sorted(
                self._counts.items(), key=lambda item: str(item[0])
            )
        )


@dataclass(slots=True)
class RunDraft:
    """Mutable accumulator for one agent run while a unit is parsed."""

    agent_run_id: str
    agent_type: str
    parent_agent_run_id: str | None
    spawn_depth: int
    description_hash: str | None = None
    events: list[datetime] = field(default_factory=list)
    extra: list[Interval] = field(default_factory=list)
    errors: int = 0
    files: set[str] = field(default_factory=set)
    test_runs: int = 0
    test_failures: int = 0
    tools_untracked: bool = False
    stopped: bool = False
    tool_calls: Counter[str] = field(default_factory=Counter)
    tool_errors: Counter[str] = field(default_factory=Counter)

    def record_tool(self, name: str | None) -> str:
        label = name or OTHER_LABEL
        self.tool_calls[label] += 1
        return label

    def record_tool_error(self, label: str) -> None:
        self.tool_errors[label] += 1
        self.errors += 1

    def bounds(self) -> tuple[datetime, datetime] | None:
        instants = [
            *self.events,
            *(s for s, _e in self.extra),
            *(e for _s, e in self.extra),
        ]
        if not instants:
            return None
        return min(instants), max(instants)


@dataclass(slots=True)
class TaskDraft:
    task_id: str
    reported_ms: int | None = None
    runs: dict[str, RunDraft] = field(default_factory=dict)


def _ms(delta: timedelta) -> int:
    return delta // timedelta(milliseconds=1)


@dataclass(slots=True)
class _BuiltRun:
    draft: RunDraft
    started_at: datetime
    ended_at: datetime
    intervals: list[Interval]

    @property
    def active_ms(self) -> int:
        return total_ms(self.intervals)


@dataclass(frozen=True, slots=True)
class _Scope:
    host: Host
    session_id: str
    task_id: str


def _build_runs(draft: TaskDraft, idle_threshold_s: int) -> list[_BuiltRun]:
    built: list[_BuiltRun] = []
    for run in draft.runs.values():
        bounds = run.bounds()
        if bounds is not None:
            intervals = active_intervals(run.events, idle_threshold_s, run.extra)
            built.append(_BuiltRun(run, bounds[0], bounds[1], intervals))
    return built


def _task_status(is_last: bool, ended: datetime, options: ReaderOptions) -> TaskStatus:
    """BR-14: a later task closes this one; otherwise stale after ``stale_after_s``."""
    if not is_last:
        return TaskStatus.DONE
    if options.now - ended > timedelta(seconds=options.stale_after_s):
        return TaskStatus.CLOSED_STALE
    return TaskStatus.IN_PROGRESS


def _task_record(
    scope: _Scope,
    draft: TaskDraft,
    seq: int,
    status: TaskStatus,
    runs: Sequence[_BuiltRun],
) -> TaskRecord:
    started = min(r.started_at for r in runs)
    ended = max(r.ended_at for r in runs)
    spans = [
        RunSpan(
            r.draft.agent_run_id,
            r.draft.agent_type,
            r.started_at,
            r.ended_at,
            r.active_ms,
        )
        for r in runs
    ]
    path_ms, path = critical_path(spans)
    retry_count, retry_summary = retries(spans)
    reported = draft.reported_ms is not None
    return TaskRecord(
        task_id=scope.task_id,
        session_id=scope.session_id,
        host=scope.host,
        seq_in_session=seq,
        started_at=started,
        ended_at=ended,
        wall_clock_ms=_ms(ended - started),
        active_ms=total_ms(union(i for r in runs for i in r.intervals)),
        reported_ms=draft.reported_ms,
        duration_source=DurationSource.REPORTED if reported else DurationSource.DERIVED,
        status=status,
        agent_runs=len(runs),
        max_spawn_depth=max(r.draft.spawn_depth for r in runs),
        critical_path_ms=path_ms,
        critical_path="→".join(path),
        retries=retry_count,
        retry_summary=retry_summary,
        owner_rank="0",
    )


def _run_record(
    scope: _Scope, built: _BuiltRun, task_status: TaskStatus
) -> AgentRunRecord:
    run = built.draft
    if run.stopped:
        status = RunStatus.STOPPED
    elif task_status is TaskStatus.IN_PROGRESS:
        status = RunStatus.RUNNING
    else:
        status = RunStatus.DONE
    return AgentRunRecord(
        agent_run_id=run.agent_run_id,
        task_id=scope.task_id,
        session_id=scope.session_id,
        host=scope.host,
        parent_agent_run_id=run.parent_agent_run_id,
        agent_type=run.agent_type,
        description_hash=run.description_hash,
        spawn_depth=run.spawn_depth,
        started_at=built.started_at,
        ended_at=built.ended_at,
        active_ms=built.active_ms,
        status=status,
        errors=run.errors,
        files_touched=len(run.files),
        test_runs=run.test_runs,
        test_failures=run.test_failures,
        tools_untracked=run.tools_untracked,
        owner_rank="0",
    )


def _tool_records(run: RunDraft) -> list[ToolUseRecord]:
    return [
        ToolUseRecord(run.agent_run_id, name, calls, run.tool_errors.get(name, 0))
        for name, calls in sorted(run.tool_calls.items())
    ]


def assemble(
    host: Host, session_id: str, drafts: Iterable[TaskDraft], options: ReaderOptions
) -> tuple[list[TaskRecord], list[AgentRunRecord], list[ToolUseRecord]]:
    """Turn task/run drafts into records: timing, statuses, critical path, retries, tools.

    Runs without any event are dropped; tasks are ordered by start time (``seq_in_session``).
    """
    built = [
        (d, runs) for d in drafts if (runs := _build_runs(d, options.idle_threshold_s))
    ]
    built.sort(key=lambda item: (min(r.started_at for r in item[1]), item[0].task_id))
    tasks: list[TaskRecord] = []
    run_records: list[AgentRunRecord] = []
    tool_records: list[ToolUseRecord] = []
    for seq, (draft, runs) in enumerate(built, start=1):
        scope = _Scope(host, session_id, draft.task_id)
        ended = max(r.ended_at for r in runs)
        status = _task_status(seq == len(built), ended, options)
        tasks.append(_task_record(scope, draft, seq, status, runs))
        ordered = sorted(
            runs,
            key=lambda r: (r.draft.spawn_depth, r.started_at, r.draft.agent_run_id),
        )
        for built_run in ordered:
            run_records.append(_run_record(scope, built_run, status))
            tool_records.extend(_tool_records(built_run.draft))
    return tasks, run_records, tool_records
