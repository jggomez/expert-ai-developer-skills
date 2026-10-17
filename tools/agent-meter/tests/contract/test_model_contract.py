"""Contract tests for ``agent_meter.model`` (contracts.md §2) and the record factories."""

from __future__ import annotations

import dataclasses
import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from agent_meter import model
from agent_meter.model import (
    SCHEMA_VERSION,
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
from tests.fixtures import records

RECORD_CLASSES = (
    FileFingerprint,
    SessionUnit,
    ProjectRef,
    SessionRecord,
    TaskRecord,
    AgentRunRecord,
    CallRecord,
    ToolUseRecord,
    UntrackedRecord,
    Diagnostic,
    UnitBatch,
    ReaderOptions,
)


def test_schema_version_is_one() -> None:
    assert SCHEMA_VERSION == 1


def test_enum_values_match_contract() -> None:
    assert [h.value for h in Host] == [
        "claude-code",
        "antigravity-cli",
        "antigravity-ide",
        "antigravity-app",
    ]
    assert [s.value for s in TaskStatus] == ["in_progress", "done", "closed_stale"]
    assert [s.value for s in RunStatus] == ["running", "done", "error", "stopped"]
    assert [s.value for s in DurationSource] == ["reported", "derived"]
    assert [k.value for k in DiagnosticKind] == [
        "corrupt",
        "format_changed",
        "unreadable",
        "unknown_usage_iteration",
        "owner_missing",
    ]
    assert [r.value for r in UntrackedReason] == [
        "legacy_pb",
        "no_usage_data",
        "format_changed",
    ]
    assert Host.CLAUDE_CODE == "claude-code"


@pytest.mark.parametrize("cls", RECORD_CLASSES)
def test_records_are_frozen_slotted_dataclasses(cls: type) -> None:
    assert dataclasses.is_dataclass(cls)
    assert "__slots__" in cls.__dict__
    assert cls.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_field_order_matches_contract() -> None:
    names = [f.name for f in dataclasses.fields(CallRecord)]
    assert names == [
        "call_id",
        "host",
        "session_id",
        "task_id",
        "agent_run_id",
        "ts",
        "model",
        "model_label",
        "input_tokens",
        "output_tokens",
        "thinking_tokens",
        "cache_write_5m_tokens",
        "cache_write_1h_tokens",
        "cache_read_tokens",
        "latency_ms",
        "speed",
        "inference_geo",
        "is_error",
        "source_format",
        "owner_rank",
        "project_id",
    ]
    assert [f.name for f in dataclasses.fields(TaskRecord)][-2:] == [
        "owner_rank",
        "project_id",
    ]
    assert [f.name for f in dataclasses.fields(SessionRecord)] == [
        "session_id",
        "host",
        "workspace_path",
        "started_at",
        "ended_at",
        "status",
        "host_version",
        "owner_rank",
        "project_id",
    ]


def test_session_unit_fingerprint_is_sha256_over_sorted_files() -> None:
    a = FileFingerprint(
        relpath="b/x.jsonl", kind="cc_main", size=10, mtime_ns=5, inode=7
    )
    b = FileFingerprint(relpath="a/y.jsonl", kind="cc_sub", size=3, mtime_ns=2, inode=1)
    unit_ab = SessionUnit(
        host=Host.CLAUDE_CODE, unit_id="s1", root=Path("/r"), files=(a, b)
    )
    unit_ba = SessionUnit(
        host=Host.CLAUDE_CODE, unit_id="s1", root=Path("/r"), files=(b, a)
    )

    fp = unit_ab.fingerprint

    assert fp == unit_ba.fingerprint
    assert len(fp) == 64 and int(fp, 16) >= 0
    changed = SessionUnit(
        host=Host.CLAUDE_CODE,
        unit_id="s1",
        root=Path("/r"),
        files=(dataclasses.replace(a, size=11), b),
    )
    assert changed.fingerprint != fp


def test_reader_options_defaults() -> None:
    opts = ReaderOptions(now=datetime(2026, 10, 16, tzinfo=UTC))
    assert (opts.idle_threshold_s, opts.stale_after_s) == (120, 86_400)
    assert opts.store_agent_descriptions is False and opts.description_salt == b""


def test_record_factories_build_consistent_batch() -> None:
    batch = records.make_batch()

    assert isinstance(batch, UnitBatch)
    session = batch.sessions[0]
    task = batch.tasks[0]
    run = batch.agent_runs[0]
    call = batch.calls[0]
    assert task.session_id == session.session_id == call.session_id
    assert call.task_id == task.task_id and call.agent_run_id == run.agent_run_id
    assert batch.unit.unit_id == session.session_id
    assert isinstance(call.ts, datetime) and call.ts.tzinfo is not None


def test_factories_accept_overrides() -> None:
    call = records.make_call(model=None, input_tokens=None, host=Host.ANTIGRAVITY_CLI)
    untracked = records.make_untracked(observed_from=date(2026, 5, 1))
    diag = records.make_diagnostic(kind=DiagnosticKind.CORRUPT)

    assert call.model is None and call.input_tokens is None
    assert call.host is Host.ANTIGRAVITY_CLI
    assert untracked.observed_from == date(2026, 5, 1)
    assert diag.kind is DiagnosticKind.CORRUPT
    assert diag.unit_hash == hashlib.sha256(b"s-0001").hexdigest()[:12]


def test_model_public_names() -> None:
    assert set(model.__all__) >= {c.__name__ for c in RECORD_CLASSES}
