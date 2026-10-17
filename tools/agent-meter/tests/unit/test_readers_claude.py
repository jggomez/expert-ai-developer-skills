"""Tests for ``readers.claude_code`` (ADR §3.2/§3.5; RD-01..05, RD-10..12, TK-01/03)."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from agent_meter.model import (
    DiagnosticKind,
    DurationSource,
    Host,
    RunStatus,
    TaskStatus,
    UnitBatch,
)
from agent_meter.pricing import cost_usd, load_pricing, resolve_price
from agent_meter.readers.claude_code import KNOWN_FORMATS, ClaudeCodeReader
from tests.fixtures.claude import (
    CANARY,
    CWD,
    T0,
    ClaudeHome,
    ClaudeSession,
    tool_use,
    usage,
)
from tests.fixtures.records import make_options
from tests.fixtures.scenarios import CLAUDE_SESSION_ID as SID
from tests.fixtures.scenarios import claude_standard_session as build_standard

SALT = b"pepper"


def ts(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


@pytest.fixture()
def home(tmp_path: Path) -> ClaudeHome:
    return ClaudeHome(tmp_path / ".claude")


@pytest.fixture()
def standard(home: ClaudeHome) -> tuple[ClaudeCodeReader, UnitBatch]:
    home.write(build_standard())
    reader = ClaudeCodeReader(home.root)
    (unit,) = list(reader.discover())
    return reader, reader.read_unit(
        unit, make_options(now=ts(1600), description_salt=SALT)
    )


def calls_by_id(batch: UnitBatch) -> dict[str, object]:
    return {c.call_id: c for c in batch.calls}


# --- discovery ---------------------------------------------------------------------------------


def test_discover_groups_main_file_and_subagents_into_one_unit(
    home: ClaudeHome,
) -> None:
    home.write(build_standard())
    reader = ClaudeCodeReader(home.root)

    units = list(reader.discover())

    assert len(units) == 1
    unit = units[0]
    assert (
        unit.host is Host.CLAUDE_CODE and unit.unit_id == SID and unit.root == home.root
    )
    kinds = sorted((f.kind, f.relpath.rsplit("/", 1)[-1]) for f in unit.files)
    assert kinds == [
        ("cc_main", f"{SID}.jsonl"),
        ("cc_meta", "agent-a1.meta.json"),
        ("cc_meta", "agent-a2.meta.json"),
        ("cc_sub", "agent-a1.jsonl"),
        ("cc_sub", "agent-a2.jsonl"),
        ("cc_sub", "agent-a3.jsonl"),
    ]
    assert all(not f.relpath.startswith("/") for f in unit.files)


def test_fingerprint_changes_when_a_file_grows(home: ClaudeHome) -> None:
    session = build_standard()
    main = home.write(session)
    reader = ClaudeCodeReader(home.root)
    before = next(reader.discover()).fingerprint

    with main.open("ab") as handle:
        handle.write(b'{"type": "ai-title", "aiTitle": "x"}\n')

    assert next(reader.discover()).fingerprint != before


def test_find_unit_by_session_id(home: ClaudeHome) -> None:
    home.write(build_standard())
    reader = ClaudeCodeReader(home.root)

    found = reader.find_unit(SID)

    assert found is not None and found.unit_id == SID
    assert reader.find_unit("no-such-session") is None
    assert reader.find_unit("*") is None


def test_missing_root_discovers_nothing(tmp_path: Path) -> None:
    reader = ClaudeCodeReader(tmp_path / "absent")

    assert list(reader.discover()) == [] and reader.earliest_available() is None


# --- RD-01 dedup, RD-12 synthetic -------------------------------------------------------------------------


def test_duplicated_request_id_counts_once_with_max_output_and_first_ts(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard

    calls = calls_by_id(batch)
    r1 = calls["claude-code:r1"]

    assert sorted(calls) == sorted(
        f"claude-code:{r}"
        for r in ["r1", "r2", "r4", "r5", "ra1", "ra1b", "ra2", "ra3"]
    )
    assert r1.output_tokens == 30 and r1.input_tokens == 100  # type: ignore[attr-defined]
    assert r1.ts == ts(5)  # type: ignore[attr-defined]


def test_synthetic_model_lines_are_excluded(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard

    assert "claude-code:r3" not in calls_by_id(batch)
    assert all(c.model != "<synthetic>" for c in batch.calls)


def test_usage_field_mapping(standard: tuple[ClaudeCodeReader, UnitBatch]) -> None:
    _reader, batch = standard
    r1 = calls_by_id(batch)["claude-code:r1"]

    assert (
        r1.cache_write_5m_tokens,
        r1.cache_write_1h_tokens,
        r1.cache_read_tokens,
    ) == (300, 200, 1_000)  # type: ignore[attr-defined]
    assert (
        r1.model == "claude-opus-5-5"
        and r1.model_label is None
        and r1.latency_ms is None
    )  # type: ignore[attr-defined]
    assert r1.source_format == "cc-2.1" and r1.is_error is False  # type: ignore[attr-defined]
    assert calls_by_id(batch)["claude-code:r5"].is_error is True  # type: ignore[attr-defined]


def test_usage_variants_legacy_cache_thinking_speed_geo(home: ClaudeHome) -> None:
    s = ClaudeSession("s-usage")
    p = s.prompt(0, "pu")
    s.assistant(
        1,
        "u1",
        parent=p,
        use=usage(
            1, 2, cache_5m=7, legacy_cache_only=True, thinking=1, speed="fast", geo="us"
        ),
    )
    s.assistant(2, None, parent=p, message_id="msg-only", use=usage(1, 1))
    s.assistant(3, "u3", parent=p, model="bad model; rm -rf", use=usage(1, 1))
    home.write(s)
    reader = ClaudeCodeReader(home.root)

    batch = reader.read_unit(next(reader.discover()), make_options())

    calls = calls_by_id(batch)
    u1 = calls["claude-code:u1"]
    assert (u1.cache_write_5m_tokens, u1.cache_write_1h_tokens, u1.thinking_tokens) == (
        7,
        0,
        1,
    )  # type: ignore[attr-defined]
    assert (u1.speed, u1.inference_geo) == ("fast", "us")  # type: ignore[attr-defined]
    assert "claude-code:msg:msg-only" in calls
    assert calls["claude-code:u3"].model == "(other)"  # type: ignore[attr-defined]


def test_unknown_usage_iteration_type_raises_diagnostic(home: ClaudeHome) -> None:
    s = ClaudeSession("s-iter")
    p = s.prompt(0, "pi")
    s.assistant(
        1,
        "i1",
        parent=p,
        use=usage(
            iterations=[{"type": "message"}, {"type": "advisor", "input_tokens": 9}]
        ),
    )
    home.write(s)
    reader = ClaudeCodeReader(home.root)

    batch = reader.read_unit(next(reader.discover()), make_options())

    kinds = {d.kind: d.count for d in batch.diagnostics}
    assert kinds == {DiagnosticKind.UNKNOWN_USAGE_ITERATION: 1}
    assert len(batch.calls) == 1


def test_non_integer_usage_is_unknown_not_zero(home: ClaudeHome) -> None:
    s = ClaudeSession("s-bad-usage")
    p = s.prompt(0, "pb")
    bad = usage()
    bad["input_tokens"] = "lots"
    del bad["cache_read_input_tokens"]
    s.assistant(1, "b1", parent=p, use=bad)
    home.write(s)
    reader = ClaudeCodeReader(home.root)

    (call,) = reader.read_unit(next(reader.discover()), make_options()).calls

    assert (
        call.input_tokens is None
        and call.cache_read_tokens is None
        and call.output_tokens == 50
    )


# --- segmentation (RD-03/04/05) --------------------------------------------------------------------------


def test_tasks_and_reported_vs_derived_duration(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard

    tasks = {t.task_id: t for t in batch.tasks}

    assert list(tasks) == ["claude-code:p1", "claude-code:p2"]
    p1, p2 = tasks["claude-code:p1"], tasks["claude-code:p2"]
    assert (p1.seq_in_session, p1.status, p1.reported_ms, p1.duration_source) == (
        1,
        TaskStatus.DONE,
        90_000,
        DurationSource.REPORTED,
    )
    assert (p2.seq_in_session, p2.status, p2.reported_ms, p2.duration_source) == (
        2,
        TaskStatus.IN_PROGRESS,
        None,
        DurationSource.DERIVED,
    )
    assert p1.started_at == ts(0) and p1.ended_at == ts(1510)
    assert p1.wall_clock_ms == 1_510_000
    assert (p1.agent_runs, p1.max_spawn_depth) == (4, 2)
    assert all(
        t.owner_rank == "0" and t.session_id == SID and t.host is Host.CLAUDE_CODE
        for t in batch.tasks
    )


def test_main_thread_calls_follow_parent_chain_then_file_order(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard
    calls = calls_by_id(batch)

    assert calls["claude-code:r1"].task_id == "claude-code:p1"  # type: ignore[attr-defined]
    assert calls["claude-code:r2"].agent_run_id == "claude-code:p1:main"  # type: ignore[attr-defined]
    assert (
        calls["claude-code:r4"].task_id == "claude-code:p2"
    )  # broken chain → file order  # type: ignore[attr-defined]
    assert calls["claude-code:r5"].task_id == "claude-code:p2"  # type: ignore[attr-defined]


def test_subagent_linkage_via_meta_tool_use_id(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard
    runs = {r.agent_run_id: r for r in batch.agent_runs}

    a1 = runs["claude-code:agent:a1"]

    assert (a1.task_id, a1.agent_type, a1.spawn_depth) == (
        "claude-code:p1",
        "code-implementer",
        1,
    )
    assert a1.parent_agent_run_id == "claude-code:p1:main"
    assert (
        a1.description_hash
        == hashlib.sha256(SALT + f"Implement {CANARY} feature".encode()).hexdigest()
    )
    assert (
        runs["claude-code:p1:main"].agent_type == "main"
        and runs["claude-code:p1:main"].description_hash is None
    )


def test_nested_subagent_attaches_to_parent_run(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard
    runs = {r.agent_run_id: r for r in batch.agent_runs}

    a2 = runs["claude-code:agent:a2"]

    assert (a2.task_id, a2.parent_agent_run_id, a2.spawn_depth) == (
        "claude-code:p1",
        "claude-code:agent:a1",
        2,
    )


def test_background_subagent_calls_roll_up_to_spawn_task(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard
    calls = calls_by_id(batch)

    late = calls["claude-code:ra1b"]

    assert (
        late.task_id == "claude-code:p1" and late.agent_run_id == "claude-code:agent:a1"
    )  # type: ignore[attr-defined]


def test_subagent_without_meta_uses_first_prompt_id(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard
    runs = {r.agent_run_id: r for r in batch.agent_runs}

    a3 = runs["claude-code:agent:a3"]

    assert (a3.task_id, a3.agent_type, a3.parent_agent_run_id, a3.spawn_depth) == (
        "claude-code:p1",
        "(unknown)",
        "claude-code:p1:main",
        1,
    )
    assert a3.description_hash is None


def test_lines_before_first_prompt_form_pre_task(home: ClaudeHome) -> None:
    s = ClaudeSession("s-pre")
    first = s.assistant(0, "pre1", parent=None, use=usage(1, 1))
    s.prompt(10, "px", parent=first)
    home.write(s)
    reader = ClaudeCodeReader(home.root)

    batch = reader.read_unit(next(reader.discover()), make_options())

    assert calls_by_id(batch)["claude-code:pre1"].task_id == "claude-code:s-pre:pre"  # type: ignore[attr-defined]
    assert [t.task_id for t in batch.tasks] == [
        "claude-code:s-pre:pre",
        "claude-code:px",
    ]


# --- runs: time, tools, files, tests (TK-03, TK-07) ----------------------------------------------------------


def test_idle_gap_excluded_from_run_active_time(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard
    runs = {r.agent_run_id: r for r in batch.agent_runs}

    a1 = runs["claude-code:agent:a1"]

    assert (a1.started_at, a1.ended_at) == (ts(20), ts(1510))
    assert a1.active_ms == 16_000


def test_tool_counts_files_and_test_runs(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard
    runs = {r.agent_run_id: r for r in batch.agent_runs}
    tools = {
        (t.agent_run_id, t.tool_name): (t.calls, t.errors) for t in batch.tool_uses
    }

    main = runs["claude-code:p1:main"]

    assert tools[("claude-code:p1:main", "Edit")] == (2, 0)
    assert tools[("claude-code:p1:main", "Bash")] == (2, 1)
    assert tools[("claude-code:p1:main", "Write")] == (1, 0)
    assert tools[("claude-code:p1:main", "Agent")] == (1, 0)
    assert (main.files_touched, main.test_runs, main.test_failures, main.errors) == (
        2,
        1,
        1,
        1,
    )
    assert runs["claude-code:agent:a1"].files_touched == 1
    assert runs["claude-code:p2:main"].errors == 1  # API error line
    assert all(not r.tools_untracked for r in batch.agent_runs)


def test_session_record(standard: tuple[ClaudeCodeReader, UnitBatch]) -> None:
    _reader, batch = standard

    (session,) = batch.sessions

    assert (session.session_id, session.host, session.host_version) == (
        SID,
        Host.CLAUDE_CODE,
        "2.1.229",
    )
    assert session.workspace_path == CWD
    assert (session.started_at, session.ended_at, session.status) == (
        ts(0),
        ts(1510),
        "open",
    )
    assert session.owner_rank == "0" and session.project_id is None


def test_stale_session_closes_last_task(home: ClaudeHome) -> None:
    home.write(build_standard())
    reader = ClaudeCodeReader(home.root)

    batch = reader.read_unit(
        next(reader.discover()), make_options(now=ts(1510 + 86_401))
    )

    assert (
        batch.tasks[-1].status is TaskStatus.CLOSED_STALE
        and batch.sessions[0].status == "closed"
    )
    assert all(r.status is RunStatus.DONE for r in batch.agent_runs)


def test_stopped_subagent_status(home: ClaudeHome) -> None:
    s = ClaudeSession("s-stop")
    p = s.prompt(0, "ps")
    s.assistant(1, "x1", parent=p, tools=[tool_use("Agent", "tu-s")])
    sub = s.subagent("as", tool_use_id="tu-s", stopped=True)
    sub.assistant(2, "x2", parent=None)
    home.write(s)
    reader = ClaudeCodeReader(home.root)

    batch = reader.read_unit(next(reader.discover()), make_options())

    assert {r.agent_run_id: r.status for r in batch.agent_runs}[
        "claude-code:agent:as"
    ] is RunStatus.STOPPED


def test_task_cost_equals_sum_of_its_calls(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard
    table = load_pricing(None)

    def cost(call: object) -> Decimal | None:
        c = call  # CallRecord
        prompt = (
            c.input_tokens
            + c.cache_read_tokens
            + c.cache_write_5m_tokens
            + c.cache_write_1h_tokens
        )  # type: ignore[attr-defined]
        res = resolve_price(table, c.model, c.ts.date(), prompt)  # type: ignore[attr-defined]
        return cost_usd(
            res,
            input_tokens=c.input_tokens,
            output_tokens=c.output_tokens,  # type: ignore[attr-defined]
            cache_write_5m_tokens=c.cache_write_5m_tokens,
            cache_write_1h_tokens=c.cache_write_1h_tokens,  # type: ignore[attr-defined]
            cache_read_tokens=c.cache_read_tokens,
        )  # type: ignore[attr-defined]

    p1_costs = [cost(c) for c in batch.calls if c.task_id == "claude-code:p1"]

    assert None not in p1_costs
    expected = (
        Decimal(100) * 4
        + 30 * 20
        + 300 * 5
        + 200 * 8
        + Decimal(1000) * Decimal("0.20")  # r1 opus 5.5
        + Decimal(200) * 4
        + 20 * 20
        + Decimal(2000) * Decimal("0.20")  # r2 opus 5.5
        + Decimal(1000) * 2
        + 100 * 10
        + Decimal(5000) * Decimal("0.10")  # ra1 sonnet 5.5
        + Decimal(50) * 2
        + 5 * 10  # ra1b sonnet 5.5
        + Decimal(10) * 1
        + 1 * 5  # ra2 haiku 4.5 via alias
        + Decimal(10) * 4
        + 1 * 20  # ra3 opus 5.5
    ) / Decimal(1_000_000)
    assert sum(p1_costs, Decimal(0)) == expected  # type: ignore[arg-type]


# --- RD-02 partial line, RD-10 forward compat, RD-11 corruption ---------------------------------------------


def test_partial_trailing_line_is_not_ingested_until_complete(home: ClaudeHome) -> None:
    s = ClaudeSession("s-partial")
    p = s.prompt(0, "pp")
    s.assistant(1, "done-1", parent=p)
    partial = json.dumps(
        {
            "type": "assistant",
            "requestId": "late-1",
            "uuid": "z",
            "parentUuid": p,
            "timestamp": "2026-10-16T14:00:02.000Z",
            "message": {"id": "m", "model": "claude-opus-5-5", "usage": usage()},
        }
    ).encode()
    main = home.write(s, tail=partial[:-10])
    reader = ClaudeCodeReader(home.root)

    first = reader.read_unit(next(reader.discover()), make_options())
    main.write_bytes(main.read_bytes() + partial[-10:] + b"\n")
    second = reader.read_unit(next(reader.discover()), make_options())

    assert sorted(calls_by_id(first)) == ["claude-code:done-1"]
    assert first.diagnostics == ()
    assert sorted(calls_by_id(second)) == ["claude-code:done-1", "claude-code:late-1"]


def test_unknown_fields_and_line_types_are_ignored(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard

    assert batch.diagnostics == ()


def test_corrupt_middle_line_is_skipped_with_diagnostic(home: ClaudeHome) -> None:
    s = ClaudeSession("s-corrupt")
    p = s.prompt(0, "pc")
    s.assistant(1, "c1", parent=p)
    main = home.write(s)
    lines = main.read_bytes().split(b"\n")
    main.write_bytes(lines[0] + b"\n{not json at all\n" + b"\n".join(lines[1:]))
    reader = ClaudeCodeReader(home.root)

    batch = reader.read_unit(next(reader.discover()), make_options())

    assert [c.call_id for c in batch.calls] == ["claude-code:c1"]
    assert [(d.kind, d.file_kind, d.count) for d in batch.diagnostics] == [
        (DiagnosticKind.CORRUPT, "cc_main", 1)
    ]
    assert (
        batch.diagnostics[0].unit_hash == hashlib.sha256(b"s-corrupt").hexdigest()[:12]
    )


def test_corrupt_meta_and_unreadable_main_never_raise(home: ClaudeHome) -> None:
    session = build_standard()
    main = home.write(session)
    (main.parent / SID / "subagents" / "agent-a1.meta.json").write_text(
        "{broken", encoding="utf-8"
    )
    reader = ClaudeCodeReader(home.root)
    unit = next(reader.discover())

    with_bad_meta = reader.read_unit(unit, make_options())
    main.unlink()
    unreadable = reader.read_unit(unit, make_options())

    assert any(
        d.kind is DiagnosticKind.CORRUPT and d.file_kind == "cc_meta"
        for d in with_bad_meta.diagnostics
    )
    assert {r.agent_run_id: r.agent_type for r in with_bad_meta.agent_runs}[
        "claude-code:agent:a1"
    ] == "(unknown)"
    assert unreadable.calls == () and unreadable.sessions == ()
    assert [(d.kind, d.error_class) for d in unreadable.diagnostics] == [
        (DiagnosticKind.UNREADABLE, "FileNotFoundError")
    ]


def test_binary_garbage_file_never_raises(home: ClaudeHome) -> None:
    path = home.root / "projects" / "-x" / "s-garbage.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(os.urandom(2048) + b"\n")
    reader = ClaudeCodeReader(home.root)

    batch = reader.read_unit(next(reader.discover()), make_options())

    assert batch.calls == () and batch.diagnostics


# --- cross-file copies (resume / fork) ----------------------------------------------------------------------


def test_copied_request_keeps_original_attribution_rank(home: ClaudeHome) -> None:
    original = ClaudeSession("s-orig", slug="-proj")
    p = original.prompt(0, "po")
    original.assistant(5, "r-shared", parent=p, use=usage(10, 7))
    resumed = ClaudeSession("s-resumed", slug="-proj")
    q = resumed.prompt(3600, "pr")
    resumed.assistant(5, "r-shared", parent=q, use=usage(10, 7))
    home.write(original)
    home.write(resumed)
    reader = ClaudeCodeReader(home.root)
    units = {u.unit_id: u for u in reader.discover()}

    a = reader.read_unit(units["s-orig"], make_options()).calls[0]
    b = reader.read_unit(units["s-resumed"], make_options()).calls[0]

    assert a.call_id == b.call_id == "claude-code:r-shared"
    assert a.owner_rank == "0:2026-10-16T14:00:00.000Z:s-orig"
    assert b.owner_rank == "0:2026-10-16T15:00:00.000Z:s-resumed"
    assert a.owner_rank < b.owner_rank


def test_subagent_calls_rank_after_main_calls(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard
    calls = calls_by_id(batch)

    assert calls["claude-code:ra1"].owner_rank == f"1:2026-10-16T14:00:20.000Z:{SID}"  # type: ignore[attr-defined]
    assert calls["claude-code:r1"].owner_rank.startswith("0:")  # type: ignore[attr-defined]


# --- misc protocol methods -------------------------------------------------------------------------------------


def test_earliest_available_and_untracked(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    reader, _batch = standard

    assert reader.earliest_available() == date(2026, 10, 16)
    assert reader.untracked() == []
    assert reader.host is Host.CLAUDE_CODE


def test_format_fingerprint_is_known_for_fixture(
    standard: tuple[ClaudeCodeReader, UnitBatch],
) -> None:
    _reader, batch = standard

    assert batch.format_fingerprint in KNOWN_FORMATS


def test_unknown_version_yields_unknown_fingerprint(home: ClaudeHome) -> None:
    s = ClaudeSession("s-v9", version="9.0.1")
    s.assistant(0, "v1", parent=s.prompt(0, "pv"))
    home.write(s)
    reader = ClaudeCodeReader(home.root)

    batch = reader.read_unit(next(reader.discover()), make_options())

    assert batch.format_fingerprint not in KNOWN_FORMATS
    assert batch.calls[0].source_format == "cc-9.0"


def test_read_is_deterministic(home: ClaudeHome) -> None:
    home.write(build_standard())
    reader = ClaudeCodeReader(home.root)
    unit = next(reader.discover())
    options = make_options(now=datetime(2026, 10, 16, 15, tzinfo=UTC))

    assert reader.read_unit(unit, options) == reader.read_unit(unit, options)
