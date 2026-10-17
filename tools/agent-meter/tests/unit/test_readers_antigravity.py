"""Tests for ``readers.antigravity`` (ADR §3.4/§3.5; RD-06..09, RD-13..15)."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from agent_meter.model import (
    CallRecord,
    DiagnosticKind,
    Host,
    TaskStatus,
    UnitBatch,
    UntrackedReason,
)
from agent_meter.readers.antigravity import KNOWN_FORMATS, AntigravityReader
from tests.fixtures.antigravity import (
    GENERIC,
    PLANNER,
    USER_INPUT,
    AgyCall,
    AgyConversation,
    AgyStep,
    build_root,
    step_ts,
)
from tests.fixtures.canary import CANARY
from tests.fixtures.records import make_options
from tests.fixtures.scenarios import agy_child as child
from tests.fixtures.scenarios import agy_root_conversation as root_conversation
from tests.fixtures.scenarios import (
    agy_standard_conversations as standard_conversations,
)

CLI = Host.ANTIGRAVITY_CLI
SALT = b"pepper"


@pytest.fixture()
def cli_root(tmp_path: Path) -> Path:
    return build_root(tmp_path / "antigravity-cli", standard_conversations())


@pytest.fixture()
def cli(cli_root: Path) -> AntigravityReader:
    return AntigravityReader(CLI, cli_root)


@pytest.fixture()
def batch(cli: AntigravityReader) -> UnitBatch:
    unit = cli.find_unit("c-root")
    assert unit is not None
    return cli.read_unit(unit, make_options(now=step_ts(1100), description_salt=SALT))


def calls(batch: UnitBatch) -> dict[str, CallRecord]:
    return {c.call_id: c for c in batch.calls}


# --- discovery ----------------------------------------------------------------------------------------


def test_discover_groups_descendants_into_root_unit(cli: AntigravityReader) -> None:
    units = {u.unit_id: u for u in cli.discover()}

    assert sorted(units) == ["c-other", "c-root"]
    root = units["c-root"]
    assert root.host is CLI and root.member_ids == ("c-child1", "c-child2", "c-child3")
    kinds = {(f.kind, f.relpath) for f in root.files}
    assert ("agy_db", "conversations/c-root.db") in kinds
    assert (
        "agy_transcript",
        "brain/c-root/.system_generated/logs/transcript_full.jsonl",
    ) in kinds
    assert (
        "agy_subagents",
        "brain/c-root/.system_generated/subagents/uuid-c-child1.json",
    ) in kinds
    assert ("agy_db", "conversations/c-child3.db") in kinds
    assert not any(
        "chunks" in f.relpath or f.relpath.endswith("transcript.jsonl")
        for f in root.files
    )
    assert not any(f.relpath.endswith((".log", "summaries.db")) for f in root.files)


def test_find_unit_maps_child_to_root_unit(cli: AntigravityReader) -> None:
    found = cli.find_unit("c-child2")

    assert found is not None and found.unit_id == "c-root"
    assert cli.find_unit("unknown-id") is None


def test_wal_file_is_part_of_the_unit_and_its_rows_are_visible(tmp_path: Path) -> None:
    root = build_root(tmp_path / "antigravity-cli", [root_conversation()])
    db = root / "conversations" / "c-root.db"
    writer = sqlite3.connect(db)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        from tests.fixtures.antigravity import gen_blob

        data = gen_blob(AgyCall(9, input=42), "t-root")
        writer.execute("INSERT INTO gen_metadata VALUES (99, ?, ?)", (data, len(data)))
        writer.commit()
        reader = AntigravityReader(CLI, root)

        unit = reader.find_unit("c-root")
        assert unit is not None
        result = reader.read_unit(unit, make_options())
    finally:
        writer.close()

    assert any(f.kind == "agy_wal" for f in unit.files)
    assert calls(result)["antigravity-cli:t-root:9"].input_tokens == 42


# --- RD-14 contract + field mapping ----------------------------------------------------------------------


def test_gen_metadata_tokens_equal_transcript_tokens_on_step_plus_one(
    batch: UnitBatch,
) -> None:
    by_call = calls(batch)

    r2 = by_call["antigravity-cli:t-root:2"]

    assert (r2.input_tokens, r2.cache_read_tokens, r2.output_tokens) == (
        1_000,
        10_000,
        200,
    )
    assert r2.ts == step_ts(15)  # step 3 = last_step_index 2 + 1
    assert r2.thinking_tokens == 50 and (
        r2.cache_write_5m_tokens,
        r2.cache_write_1h_tokens,
    ) == (0, 0)
    assert r2.latency_ms == 2_500 and r2.source_format == "agy-gen-v1"
    assert r2.model == "gemini-3.8-flash" and r2.model_label is None


def test_model_label_and_empty_model(batch: UnitBatch) -> None:
    by_call = calls(batch)

    assert by_call["antigravity-cli:t-root:6"].model == "claude-sonnet-4-6"
    assert (
        by_call["antigravity-cli:t-root:6"].model_label
        == "Claude Sonnet 4.6 (Thinking)"
    )
    assert (
        by_call["antigravity-cli:t-root:10"].model is None
    )  # inferred later via default_model (RD-09)


def test_missing_usage_message_is_null_never_zero(batch: UnitBatch) -> None:
    r11 = calls(batch)["antigravity-cli:t-root:11"]

    assert (
        r11.input_tokens,
        r11.output_tokens,
        r11.cache_read_tokens,
        r11.thinking_tokens,
    ) == (None, None, None, None)
    assert (r11.cache_write_5m_tokens, r11.cache_write_1h_tokens) == (None, None)
    assert any(
        d.kind is DiagnosticKind.FORMAT_CHANGED and d.error_class == "MissingUsage"
        for d in batch.diagnostics
    )


# --- ownership / copies --------------------------------------------------------------------------------------


def test_owned_rows_rank_zero_and_prefix_copies_rank_holder(
    batch: UnitBatch, cli: AntigravityReader
) -> None:
    by_call = calls(batch)
    other_unit = cli.find_unit("c-other")
    assert other_unit is not None
    other = calls(cli.read_unit(other_unit, make_options()))

    assert by_call["antigravity-cli:t-root:2"].owner_rank == "0"
    assert by_call["antigravity-cli:t-old:0"].owner_rank == "1:c-root"
    assert (
        by_call["antigravity-cli:t-old:0"].task_id == "antigravity-cli:c-root:2"
    )  # prefix joins first task
    assert other["antigravity-cli:t-root:2"].owner_rank == "1:c-other"
    assert other["antigravity-cli:t-other:2"].owner_rank == "0"


# --- segmentation (RD-07) ---------------------------------------------------------------------------------------


def test_tasks_open_at_user_input_steps(batch: UnitBatch) -> None:
    tasks = {t.task_id: t for t in batch.tasks}

    assert list(tasks) == ["antigravity-cli:c-root:2", "antigravity-cli:c-root:10"]
    first, second = tasks.values()
    assert (
        first.seq_in_session,
        first.status,
        first.agent_runs,
        first.max_spawn_depth,
    ) == (1, TaskStatus.DONE, 3, 2)
    assert (second.seq_in_session, second.status, second.agent_runs) == (
        2,
        TaskStatus.IN_PROGRESS,
        2,
    )
    assert first.started_at == step_ts(0)
    assert second.ended_at == step_ts(1010)
    assert first.reported_ms is None and first.duration_source.value == "derived"


def test_children_map_to_parent_task_via_spawn_step_index(batch: UnitBatch) -> None:
    runs = {r.agent_run_id: r for r in batch.agent_runs}

    c1 = runs["antigravity-cli:agent:c-child1"]
    c2 = runs["antigravity-cli:agent:c-child2"]
    c3 = runs["antigravity-cli:agent:c-child3"]

    assert (c1.task_id, c1.parent_agent_run_id, c1.spawn_depth, c1.agent_type) == (
        "antigravity-cli:c-root:2",
        "antigravity-cli:c-root:2:main",
        1,
        "code-implementer",
    )
    assert (c2.task_id, c2.parent_agent_run_id, c2.spawn_depth, c2.agent_type) == (
        "antigravity-cli:c-root:2",
        "antigravity-cli:agent:c-child1",
        2,
        "qa-tester",
    )
    assert (c3.task_id, c3.parent_agent_run_id) == (
        "antigravity-cli:c-root:10",
        "antigravity-cli:c-root:10:main",
    )
    assert (
        c1.description_hash
        == hashlib.sha256(SALT + f"Role {CANARY}".encode()).hexdigest()
    )
    child_calls = [
        c for c in batch.calls if c.agent_run_id == "antigravity-cli:agent:c-child2"
    ]
    assert [c.task_id for c in child_calls] == ["antigravity-cli:c-root:2"]


# --- runs: tools, errors, files, tests (RD-08) -----------------------------------------------------------------


def test_tool_counts_errors_files_and_tests_from_transcript_only_once(
    batch: UnitBatch,
) -> None:
    runs = {r.agent_run_id: r for r in batch.agent_runs}
    tools = {
        (t.agent_run_id, t.tool_name): (t.calls, t.errors) for t in batch.tool_uses
    }
    main = runs["antigravity-cli:c-root:2:main"]

    assert tools[("antigravity-cli:c-root:2:main", "invoke_subagent")] == (1, 0)
    assert tools[("antigravity-cli:c-root:2:main", "write_to_file")] == (1, 0)
    assert tools[("antigravity-cli:c-root:2:main", "run_command")] == (1, 1)
    assert tools[("antigravity-cli:c-root:2:main", "view_file")] == (1, 0)
    assert (main.errors, main.files_touched, main.test_runs, main.test_failures) == (
        2,
        1,
        1,
        1,
    )
    assert tools[("antigravity-cli:agent:c-child1", "view_file")] == (1, 0)


def test_child_without_transcript_has_untracked_tools(batch: UnitBatch) -> None:
    runs = {r.agent_run_id: r for r in batch.agent_runs}

    assert runs["antigravity-cli:agent:c-child3"].tools_untracked is True
    assert not [
        t for t in batch.tool_uses if t.agent_run_id == "antigravity-cli:agent:c-child3"
    ]
    assert runs["antigravity-cli:c-root:2:main"].tools_untracked is False


def test_latency_extends_active_time(batch: UnitBatch) -> None:
    runs = {r.agent_run_id: r for r in batch.agent_runs}

    main_b = runs["antigravity-cli:c-root:10:main"]

    # events 1000, 1005, 1010 (gaps ≤ 120 s) → 10 s active; latency interval [1005, 1007.5] is inside.
    assert main_b.active_ms == 10_000 and main_b.started_at == step_ts(1000)


def test_session_record_uses_summary_workspace(batch: UnitBatch) -> None:
    (session,) = batch.sessions

    assert (
        session.session_id,
        session.host,
        session.host_version,
        session.owner_rank,
    ) == ("c-root", CLI, None, "0")
    assert session.workspace_path == "file:///Users/dev/work/demo-repo"
    assert (session.started_at, session.ended_at, session.status) == (
        step_ts(0),
        step_ts(1010),
        "open",
    )


# --- RD-06 transcript fallback, RD-13 IDE host ---------------------------------------------------------------


def test_transcript_fallback_reads_planner_tokens_only(tmp_path: Path) -> None:
    conv = AgyConversation(
        conversation_id="c-nodb",
        trajectory_id="t-nodb",
        db=False,
        steps=[
            AgyStep(0, USER_INPUT, 0),
            AgyStep(1, PLANNER, 5, tokens=(11, 22, 33)),
            AgyStep(2, GENERIC, 6, tokens=(99, 99, 99)),
            AgyStep(3, PLANNER, 7),
        ],
    )
    reader = AntigravityReader(CLI, build_root(tmp_path / "antigravity-cli", [conv]))
    unit = reader.find_unit("c-nodb")
    assert unit is not None

    result = reader.read_unit(unit, make_options())

    (call,) = result.calls
    assert call.call_id == "antigravity-cli:conv:c-nodb:1"
    assert (call.input_tokens, call.cache_read_tokens, call.output_tokens) == (
        11,
        22,
        33,
    )
    assert (
        call.model is None
        and call.source_format == "agy-transcript-v1"
        and call.owner_rank == "0"
    )
    assert call.ts == step_ts(5)
    assert result.format_fingerprint in KNOWN_FORMATS


def test_ide_host_uses_db_blob_workspace_and_host_prefix(tmp_path: Path) -> None:
    conv = AgyConversation(
        conversation_id="c-ide",
        trajectory_id="t-ide",
        transcript_tokens=False,
        workspace_uri="file:///Users/dev/work/ide%20proj",
        steps=[AgyStep(0, USER_INPUT, 0), AgyStep(1, PLANNER, 3)],
        calls=[AgyCall(0, model="gemini-3.6-flash")],
    )
    root = build_root(tmp_path / "antigravity-ide", [conv], summaries=False)
    reader = AntigravityReader(Host.ANTIGRAVITY_IDE, root)

    (unit,) = list(reader.discover())
    result = reader.read_unit(unit, make_options())

    (call,) = result.calls
    assert (
        call.call_id == "antigravity-ide:t-ide:0" and call.host is Host.ANTIGRAVITY_IDE
    )
    assert call.input_tokens == 1_000 and call.model == "gemini-3.6-flash"
    assert result.tasks[0].task_id == "antigravity-ide:c-ide:0"
    assert result.sessions[0].workspace_path == "file:///Users/dev/work/ide%20proj"
    assert result.format_fingerprint in KNOWN_FORMATS


def test_parent_falls_back_to_gen_metadata_parent_cascade_id(tmp_path: Path) -> None:
    kid = child(
        "c-kv",
        "c-root",
        "code-implementer",
        3,
        16,
        in_summaries=False,
        subagent_json=False,
    )
    kid.calls = [AgyCall(0, extra_kv={"parent_cascade_id": "c-root"})]
    reader = AntigravityReader(
        CLI, build_root(tmp_path / "antigravity-cli", [root_conversation(), kid])
    )

    units = {u.unit_id: u for u in reader.discover()}

    assert sorted(units) == ["c-root"] and units["c-root"].member_ids == ("c-kv",)


def test_call_timestamp_falls_back_to_call_start_then_previous_step(
    tmp_path: Path,
) -> None:
    conv = AgyConversation(
        conversation_id="c-ts",
        trajectory_id="t-ts",
        steps=[AgyStep(0, USER_INPUT, 0), AgyStep(1, PLANNER, 4)],
        calls=[AgyCall(5, start_at=60), AgyCall(7)],
    )
    reader = AntigravityReader(CLI, build_root(tmp_path / "antigravity-cli", [conv]))
    unit = reader.find_unit("c-ts")
    assert unit is not None

    by_call = calls(reader.read_unit(unit, make_options()))

    assert by_call["antigravity-cli:t-ts:5"].ts == step_ts(60)
    assert by_call["antigravity-cli:t-ts:7"].ts == step_ts(4)


# --- RD-15 / RD-11 robustness ------------------------------------------------------------------------------


def test_unknown_usage_layout_and_missing_keys_and_corrupt_rows(tmp_path: Path) -> None:
    conv = AgyConversation(
        conversation_id="c-drift",
        trajectory_id="t-drift",
        steps=[
            AgyStep(0, USER_INPUT, 0),
            AgyStep(1, PLANNER, 1),
            AgyStep(2, PLANNER, 2),
            AgyStep(3, PLANNER, 3),
        ],
        calls=[
            AgyCall(0, usage_fields=[22, 23, 25]),
            AgyCall(1, drop_keys=("trajectory_id",)),
            AgyCall(2, raw=b"\xff\xff\xff"),
        ],
    )
    reader = AntigravityReader(CLI, build_root(tmp_path / "antigravity-cli", [conv]))
    unit = reader.find_unit("c-drift")
    assert unit is not None

    result = reader.read_unit(unit, make_options())

    (call,) = result.calls
    assert call.call_id == "antigravity-cli:t-drift:0"
    assert (call.input_tokens, call.output_tokens, call.cache_read_tokens) == (
        None,
        None,
        None,
    )
    diag = {(d.kind, d.error_class): d.count for d in result.diagnostics}
    assert diag[(DiagnosticKind.FORMAT_CHANGED, "UnknownUsageLayout")] == 1
    assert diag[(DiagnosticKind.FORMAT_CHANGED, "MissingKey")] == 1
    assert diag[(DiagnosticKind.CORRUPT, "ProtoDecodeError")] == 1


def test_corrupt_database_falls_back_to_transcript_without_raising(
    tmp_path: Path,
) -> None:
    root = build_root(tmp_path / "antigravity-cli", [root_conversation()])
    (root / "conversations" / "c-root.db").write_bytes(os.urandom(4096))
    reader = AntigravityReader(CLI, root)
    unit = reader.find_unit("c-root")
    assert unit is not None

    result = reader.read_unit(unit, make_options())

    assert any(
        d.kind is DiagnosticKind.CORRUPT and d.file_kind == "agy_db"
        for d in result.diagnostics
    )
    assert "antigravity-cli:conv:c-root:3" in calls(result)


def test_changed_schema_is_format_changed(tmp_path: Path) -> None:
    root = build_root(tmp_path / "antigravity-cli", [root_conversation()])
    with sqlite3.connect(root / "conversations" / "c-root.db") as con:
        con.execute("ALTER TABLE gen_metadata RENAME TO gen_metadata_v2")
    reader = AntigravityReader(CLI, root)
    unit = reader.find_unit("c-root")
    assert unit is not None

    result = reader.read_unit(unit, make_options())

    assert any(
        d.kind is DiagnosticKind.FORMAT_CHANGED and d.file_kind == "agy_db"
        for d in result.diagnostics
    )
    assert result.format_fingerprint not in KNOWN_FORMATS
    assert all(c.input_tokens != 0 for c in result.calls)


def test_vanished_unit_never_raises(cli: AntigravityReader, cli_root: Path) -> None:
    unit = cli.find_unit("c-root")
    assert unit is not None
    for path in (cli_root / "conversations").glob("c-*"):
        path.unlink()
    for path in (cli_root / "brain").rglob("*.jsonl"):
        path.unlink()

    result = cli.read_unit(unit, make_options())

    assert result.calls == () and result.sessions == ()


# --- untracked / earliest / protocol ------------------------------------------------------------------------------


def test_legacy_pb_and_no_usage_transcripts_are_untracked(tmp_path: Path) -> None:
    pb_only = AgyConversation(
        "c-pb", "t-pb", db=False, transcript=False, legacy_pb=True
    )
    pb_with_db = AgyConversation(
        "c-pbdb", "t-pbdb", legacy_pb=True, steps=[AgyStep(0, USER_INPUT, 0)]
    )
    no_tokens = AgyConversation(
        "c-notok",
        "t-notok",
        db=False,
        transcript_tokens=False,
        steps=[AgyStep(0, USER_INPUT, 0), AgyStep(1, PLANNER, 86_400 * 2)],
    )
    root = build_root(
        tmp_path / "antigravity-ide", [pb_only, pb_with_db, no_tokens], summaries=False
    )
    pb_path = root / "conversations" / "c-pb.pb"
    stamp = (step_ts(0) - timedelta(days=150)).timestamp()
    os.utime(pb_path, (stamp, stamp))
    reader = AntigravityReader(Host.ANTIGRAVITY_IDE, root)

    untracked = {u.conversation_id: u for u in reader.untracked()}

    assert sorted(untracked) == ["c-notok", "c-pb"]
    assert (
        untracked["c-pb"].reason is UntrackedReason.LEGACY_PB
        and untracked["c-pb"].host is Host.ANTIGRAVITY_IDE
    )
    assert (
        untracked["c-pb"].observed_from
        == untracked["c-pb"].observed_to
        == date(2026, 5, 19)
    )
    assert untracked["c-notok"].reason is UntrackedReason.NO_USAGE_DATA
    assert (untracked["c-notok"].observed_from, untracked["c-notok"].observed_to) == (
        date(2026, 10, 16),
        date(2026, 10, 18),
    )
    assert "c-pb" not in {u.unit_id for u in reader.discover()}


def test_earliest_available(cli: AntigravityReader, tmp_path: Path) -> None:
    assert cli.earliest_available() == date(2026, 10, 16)
    assert AntigravityReader(CLI, tmp_path / "missing").earliest_available() is None


def test_known_format_and_determinism(cli: AntigravityReader, batch: UnitBatch) -> None:
    unit = cli.find_unit("c-root")
    assert unit is not None

    assert batch.format_fingerprint in KNOWN_FORMATS
    assert (
        cli.read_unit(unit, make_options(now=step_ts(1100), description_salt=SALT))
        == batch
    )


def test_rejects_non_antigravity_host(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        AntigravityReader(Host.CLAUDE_CODE, tmp_path)
