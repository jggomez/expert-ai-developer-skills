"""Record factories for tests (contracts.md §1: delivered first by Track 11A).

Every factory returns a valid, internally consistent record and accepts keyword
overrides for any field. Default ids chain together: session ``s-0001`` → task
``claude-code:p-0001`` → run ``claude-code:p-0001:main`` → call ``claude-code:req-0001``.
"""

from __future__ import annotations

import dataclasses
import hashlib
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from agent_meter.model import (
    AgentRunRecord,
    CallRecord,
    Diagnostic,
    DiagnosticKind,
    DurationSource,
    FileFingerprint,
    Host,
    ProjectRef,
    ReaderOptions,
    RunStatus,
    SessionRecord,
    SessionUnit,
    TaskRecord,
    TaskStatus,
    ToolUseRecord,
    UnitBatch,
    UntrackedReason,
    UntrackedRecord,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

__all__ = [
    "BASE_TS",
    "CALL_ID",
    "RUN_ID",
    "SESSION_ID",
    "TASK_ID",
    "make_agent_run",
    "make_batch",
    "make_call",
    "make_diagnostic",
    "make_file",
    "make_options",
    "make_project",
    "make_session",
    "make_task",
    "make_tool_use",
    "make_unit",
    "make_untracked",
    "ts",
]

BASE_TS = datetime(2026, 10, 16, 14, 0, 0, tzinfo=UTC)
SESSION_ID = "s-0001"
TASK_ID = "claude-code:p-0001"
RUN_ID = f"{TASK_ID}:main"
CALL_ID = "claude-code:req-0001"


def ts(seconds: float = 0.0) -> datetime:
    """Return ``BASE_TS + seconds`` (UTC, timezone-aware)."""
    return BASE_TS + timedelta(seconds=seconds)


_R = TypeVar("_R", bound="DataclassInstance")


def _build(cls: type[_R], defaults: dict[str, Any], overrides: dict[str, Any]) -> _R:
    known = {f.name for f in dataclasses.fields(cls)}
    unknown = set(overrides) - known
    if unknown:
        raise TypeError(f"{cls.__name__} has no field(s) {sorted(unknown)}")
    return cls(**{**defaults, **overrides})


def make_file(**overrides: Any) -> FileFingerprint:
    defaults = {
        "relpath": f"projects/-tmp-proj/{SESSION_ID}.jsonl",
        "kind": "cc_main",
        "size": 1024,
        "mtime_ns": 1_760_623_200_000_000_000,
        "inode": 4242,
    }
    return _build(FileFingerprint, defaults, overrides)


def make_unit(**overrides: Any) -> SessionUnit:
    defaults = {
        "host": Host.CLAUDE_CODE,
        "unit_id": SESSION_ID,
        "root": Path("/nonexistent/agent-meter-fixture-root"),
        "files": (make_file(),),
        "member_ids": (),
    }
    return _build(SessionUnit, defaults, overrides)


def make_project(**overrides: Any) -> ProjectRef:
    defaults = {
        "project_id": "git:0123456789abcdef",
        "kind": "remote",
        "display_name": "demo-repo",
        "remote_url": "github.com/example/demo-repo",
    }
    return _build(ProjectRef, defaults, overrides)


def make_session(**overrides: Any) -> SessionRecord:
    defaults = {
        "session_id": SESSION_ID,
        "host": Host.CLAUDE_CODE,
        "workspace_path": None,
        "started_at": ts(0),
        "ended_at": ts(600),
        "status": "closed",
        "host_version": "2.1.229",
        "owner_rank": "0",
        "project_id": "git:0123456789abcdef",
    }
    return _build(SessionRecord, defaults, overrides)


def make_task(**overrides: Any) -> TaskRecord:
    defaults = {
        "task_id": TASK_ID,
        "session_id": SESSION_ID,
        "host": Host.CLAUDE_CODE,
        "seq_in_session": 1,
        "started_at": ts(0),
        "ended_at": ts(600),
        "wall_clock_ms": 600_000,
        "active_ms": 480_000,
        "reported_ms": None,
        "duration_source": DurationSource.DERIVED,
        "status": TaskStatus.DONE,
        "agent_runs": 1,
        "max_spawn_depth": 0,
        "critical_path_ms": 480_000,
        "critical_path": "main",
        "retries": 0,
        "retry_summary": "",
        "owner_rank": "0",
        "project_id": "git:0123456789abcdef",
    }
    return _build(TaskRecord, defaults, overrides)


def make_agent_run(**overrides: Any) -> AgentRunRecord:
    defaults = {
        "agent_run_id": RUN_ID,
        "task_id": TASK_ID,
        "session_id": SESSION_ID,
        "host": Host.CLAUDE_CODE,
        "parent_agent_run_id": None,
        "agent_type": "main",
        "description_hash": None,
        "spawn_depth": 0,
        "started_at": ts(0),
        "ended_at": ts(600),
        "active_ms": 480_000,
        "status": RunStatus.DONE,
        "errors": 0,
        "files_touched": 0,
        "test_runs": 0,
        "test_failures": 0,
        "tools_untracked": False,
        "owner_rank": "0",
        "project_id": "git:0123456789abcdef",
    }
    return _build(AgentRunRecord, defaults, overrides)


def make_call(**overrides: Any) -> CallRecord:
    defaults = {
        "call_id": CALL_ID,
        "host": Host.CLAUDE_CODE,
        "session_id": SESSION_ID,
        "task_id": TASK_ID,
        "agent_run_id": RUN_ID,
        "ts": ts(5),
        "model": "claude-opus-5-5",
        "model_label": None,
        "input_tokens": 1_000,
        "output_tokens": 200,
        "thinking_tokens": None,
        "cache_write_5m_tokens": 300,
        "cache_write_1h_tokens": 0,
        "cache_read_tokens": 5_000,
        "latency_ms": None,
        "speed": None,
        "inference_geo": None,
        "is_error": False,
        "source_format": "cc-2.1",
        "owner_rank": f"0:2026-10-16T14:00:00.000Z:{SESSION_ID}",
        "project_id": "git:0123456789abcdef",
    }
    return _build(CallRecord, defaults, overrides)


def make_tool_use(**overrides: Any) -> ToolUseRecord:
    defaults = {"agent_run_id": RUN_ID, "tool_name": "Edit", "calls": 3, "errors": 0}
    return _build(ToolUseRecord, defaults, overrides)


def make_untracked(**overrides: Any) -> UntrackedRecord:
    defaults = {
        "conversation_id": "c-legacy-0001",
        "host": Host.ANTIGRAVITY_IDE,
        "reason": UntrackedReason.LEGACY_PB,
        "observed_from": date(2026, 5, 19),
        "observed_to": date(2026, 6, 2),
    }
    return _build(UntrackedRecord, defaults, overrides)


def make_diagnostic(**overrides: Any) -> Diagnostic:
    defaults = {
        "host": Host.CLAUDE_CODE,
        "kind": DiagnosticKind.FORMAT_CHANGED,
        "unit_hash": hashlib.sha256(SESSION_ID.encode()).hexdigest()[:12],
        "file_kind": "cc_main",
        "error_class": None,
        "count": 1,
    }
    return _build(Diagnostic, defaults, overrides)


def make_options(**overrides: Any) -> ReaderOptions:
    defaults = {"now": ts(3_600)}
    return _build(ReaderOptions, defaults, overrides)


def make_batch(**overrides: Any) -> UnitBatch:
    defaults = {
        "unit": make_unit(),
        "sessions": (make_session(),),
        "tasks": (make_task(),),
        "agent_runs": (make_agent_run(),),
        "calls": (make_call(),),
        "tool_uses": (make_tool_use(),),
        "diagnostics": (),
        "format_fingerprint": hashlib.sha256(b"cc:assistant,user").hexdigest(),
    }
    return _build(UnitBatch, defaults, overrides)
