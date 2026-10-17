"""Canonical records shared by every agent-meter module (contracts.md §2).

All records are immutable, slotted dataclasses. Timestamps are timezone-aware UTC,
token counts are ``int`` with ``None`` meaning *unknown* (never coerced to 0).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal

__all__ = [
    "SCHEMA_VERSION",
    "AgentRunRecord",
    "CallRecord",
    "Diagnostic",
    "DiagnosticKind",
    "DurationSource",
    "FileFingerprint",
    "Host",
    "ProjectRef",
    "ReaderOptions",
    "RunStatus",
    "SessionRecord",
    "SessionUnit",
    "TaskRecord",
    "TaskStatus",
    "ToolUseRecord",
    "UnitBatch",
    "UntrackedReason",
    "UntrackedRecord",
]

SCHEMA_VERSION: Final = 1


class Host(StrEnum):
    CLAUDE_CODE = "claude-code"
    ANTIGRAVITY_CLI = "antigravity-cli"
    ANTIGRAVITY_IDE = "antigravity-ide"
    ANTIGRAVITY_APP = "antigravity-app"


class TaskStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CLOSED_STALE = "closed_stale"


class RunStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    STOPPED = "stopped"


class DurationSource(StrEnum):
    REPORTED = "reported"
    DERIVED = "derived"


class DiagnosticKind(StrEnum):
    CORRUPT = "corrupt"
    FORMAT_CHANGED = "format_changed"
    UNREADABLE = "unreadable"
    UNKNOWN_USAGE_ITERATION = "unknown_usage_iteration"
    OWNER_MISSING = "owner_missing"


class UntrackedReason(StrEnum):
    LEGACY_PB = "legacy_pb"
    NO_USAGE_DATA = "no_usage_data"
    FORMAT_CHANGED = "format_changed"


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    relpath: str  # relative to the host root; never persisted
    kind: str  # "cc_main" | "cc_sub" | "cc_meta" | "agy_db" | "agy_wal" | "agy_transcript" | "agy_subagents"
    size: int
    mtime_ns: int
    inode: int


@dataclass(frozen=True, slots=True)
class SessionUnit:
    host: Host
    unit_id: (
        str  # == root session_id (Claude sessionId / Antigravity root conversation_id)
    )
    root: Path  # host root directory (in memory only)
    files: tuple[FileFingerprint, ...]
    member_ids: tuple[str, ...] = ()  # Antigravity: child conversation ids in this unit

    @property
    def fingerprint(self) -> str:
        """SHA-256 hex over the sorted ``(relpath, size, mtime_ns, inode)`` tuples."""
        digest = hashlib.sha256()
        for relpath, size, mtime_ns, inode in sorted(
            (f.relpath, f.size, f.mtime_ns, f.inode) for f in self.files
        ):
            digest.update(f"{relpath}\0{size}\0{mtime_ns}\0{inode}\n".encode())
        return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ProjectRef:
    project_id: str  # "git:<16 hex>" | "path:<16 hex>" | "(unassigned)"
    kind: Literal["remote", "path", "unassigned"]
    display_name: str
    remote_url: str | None  # normalized, credential-free, e.g. "github.com/owner/repo"


@dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: str
    host: Host
    workspace_path: (
        str | None
    )  # TRANSIENT: consumed by collector -> project_id; never stored
    started_at: datetime
    ended_at: datetime
    status: Literal["open", "closed"]
    host_version: str | None  # e.g. Claude "2.1.229"; Antigravity None
    owner_rank: str
    project_id: str | None = None  # filled by collector


@dataclass(frozen=True, slots=True)
class TaskRecord:
    task_id: str
    session_id: str
    host: Host
    seq_in_session: int
    started_at: datetime
    ended_at: datetime
    wall_clock_ms: int
    active_ms: int
    reported_ms: int | None
    duration_source: DurationSource
    status: TaskStatus
    agent_runs: int
    max_spawn_depth: int
    critical_path_ms: int
    critical_path: str  # "main→code-implementer→qa-tester"
    retries: int
    retry_summary: str  # "" | "qa-tester→code-implementer"
    owner_rank: str
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class AgentRunRecord:
    agent_run_id: str
    task_id: str
    session_id: str
    host: Host
    parent_agent_run_id: str | None
    agent_type: str  # "main" for depth 0; validated charset (ADR §3.13)
    description_hash: str | None  # sha256(salt+description) hex; None for main
    spawn_depth: int
    started_at: datetime
    ended_at: datetime
    active_ms: int
    status: RunStatus
    errors: int
    files_touched: int
    test_runs: int
    test_failures: int
    tools_untracked: bool
    owner_rank: str
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class CallRecord:
    call_id: str
    host: Host
    session_id: str
    task_id: str
    agent_run_id: str
    ts: datetime
    model: str | None
    model_label: str | None
    input_tokens: int | None
    output_tokens: int | None
    thinking_tokens: int | None
    cache_write_5m_tokens: int | None
    cache_write_1h_tokens: int | None
    cache_read_tokens: int | None
    latency_ms: int | None
    speed: str | None
    inference_geo: str | None
    is_error: bool
    source_format: str  # e.g. "cc-2.1" | "agy-gen-v1" | "agy-transcript-v1"
    owner_rank: str
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolUseRecord:
    agent_run_id: str
    tool_name: str
    calls: int
    errors: int


@dataclass(frozen=True, slots=True)
class UntrackedRecord:
    conversation_id: str
    host: Host
    reason: UntrackedReason
    observed_from: date
    observed_to: date


@dataclass(frozen=True, slots=True)
class Diagnostic:
    host: Host
    kind: DiagnosticKind
    unit_hash: str  # sha256(unit_id)[:12] — never the raw id or a path
    file_kind: str
    error_class: str | None
    count: int = 1


@dataclass(frozen=True, slots=True)
class UnitBatch:
    unit: SessionUnit
    sessions: tuple[SessionRecord, ...]
    tasks: tuple[TaskRecord, ...]
    agent_runs: tuple[AgentRunRecord, ...]
    calls: tuple[CallRecord, ...]
    tool_uses: tuple[ToolUseRecord, ...]
    diagnostics: tuple[Diagnostic, ...]
    format_fingerprint: (
        str  # sha256 of the observed shape (table/column set, 1.20 keys, line types)
    )


@dataclass(frozen=True, slots=True)
class ReaderOptions:
    now: datetime
    idle_threshold_s: int = 120
    stale_after_s: int = 86_400
    store_agent_descriptions: bool = False
    description_salt: bytes = b""  # from ~/.agent-meter/secret
