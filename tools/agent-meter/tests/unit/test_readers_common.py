"""Tests for shared reader helpers (privacy charset, partial lines, assembly)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agent_meter.model import DurationSource, Host, RunStatus, TaskStatus
from agent_meter.readers._common import (
    OTHER_LABEL,
    RunDraft,
    TaskDraft,
    assemble,
    description_hash,
    is_test_command,
    iso_z,
    load_jsonl,
    parse_iso,
    read_complete_lines,
    safe_label,
    unit_hash,
)
from tests.fixtures.records import make_options

T0 = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("code-implementer", "code-implementer"),
        ("Gemini 3.6 Flash (High)", "Gemini 3.6 Flash (High)"),
        ("mcp__server__tool", "mcp__server__tool"),
        ("claude-opus-5-5:fast", "claude-opus-5-5:fast"),
        ("rm -rf / && echo $SECRET", OTHER_LABEL),
        ("x" * 81, OTHER_LABEL),
        ("line\nbreak", OTHER_LABEL),
        ("", None),
        (None, None),
        (42, None),
    ],
)
def test_safe_label_enforces_charset(value: object, expected: str | None) -> None:
    assert safe_label(value) == expected


def test_unit_and_description_hashes() -> None:
    assert unit_hash("abc") == hashlib.sha256(b"abc").hexdigest()[:12]
    assert (
        description_hash(b"salt", "desc")
        == hashlib.sha256(b"salt" + b"desc").hexdigest()
    )


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("pytest -q tests", True),
        ("python -m pytest", True),
        ("PYTHONPATH=src uv run pytest -x", True),
        ("npm test", True),
        ("npx jest --ci", True),
        ("flutter test", True),
        ("dart test", True),
        ("go test ./...", True),
        ("cargo test", True),
        ("echo pytest", False),
        ("npm install", False),
        ("", False),
    ],
)
def test_is_test_command_matches_first_tokens_only(
    command: str, expected: bool
) -> None:
    assert is_test_command(command) is expected


def test_read_complete_lines_ignores_partial_trailing_line(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    path.write_bytes(b'{"a": 1}\n{"b": 2}\n{"c": 3')

    assert read_complete_lines(path) == [b'{"a": 1}', b'{"b": 2}']


def test_load_jsonl_counts_invalid_middle_lines_and_skips_non_objects(
    tmp_path: Path,
) -> None:
    path = tmp_path / "t.jsonl"
    path.write_bytes(b'{"a": 1}\nnot json\n[1, 2]\n\n{"b": 2}\n{"partial')

    objects, invalid = load_jsonl(path)

    assert objects == [{"a": 1}, {"b": 2}]
    assert invalid == 2


def test_parse_iso_and_iso_z() -> None:
    parsed = parse_iso("2026-10-16T14:00:00.123Z")

    assert parsed == datetime(2026, 10, 16, 14, 0, 0, 123000, tzinfo=UTC)
    assert parse_iso("2026-10-16T14:00:00") == datetime(2026, 10, 16, 14, tzinfo=UTC)
    assert parse_iso("garbage") is None and parse_iso(None) is None
    assert iso_z(parsed) == "2026-10-16T14:00:00.123Z"  # type: ignore[arg-type]


def make_run(
    run_id: str,
    agent_type: str,
    events: list[float],
    depth: int = 0,
    parent: str | None = None,
) -> RunDraft:
    run = RunDraft(
        agent_run_id=run_id,
        agent_type=agent_type,
        parent_agent_run_id=parent,
        spawn_depth=depth,
    )
    run.events.extend(at(s) for s in events)
    return run


def test_assemble_builds_tasks_runs_and_statuses() -> None:
    t1 = TaskDraft(task_id="claude-code:p1")
    main1 = make_run("claude-code:p1:main", "main", [0, 30, 60])
    sub = make_run(
        "claude-code:agent:a1",
        "qa-tester",
        [20, 50],
        depth=1,
        parent=main1.agent_run_id,
    )
    sub.tool_calls.update({"Bash": 2})
    sub.tool_errors.update({"Bash": 1})
    t1.runs.update({main1.agent_run_id: main1, sub.agent_run_id: sub})
    t2 = TaskDraft(task_id="claude-code:p2", reported_ms=5_000)
    main2 = make_run("claude-code:p2:main", "main", [1000, 1005])
    t2.runs[main2.agent_run_id] = main2
    options = make_options(now=at(1010))

    tasks, runs, tools = assemble(Host.CLAUDE_CODE, "s1", [t2, t1], options)

    assert [t.task_id for t in tasks] == ["claude-code:p1", "claude-code:p2"]
    first, second = tasks
    assert (
        first.seq_in_session,
        first.status,
        first.agent_runs,
        first.max_spawn_depth,
    ) == (1, TaskStatus.DONE, 2, 1)
    assert first.wall_clock_ms == 60_000 and first.active_ms == 60_000
    assert first.duration_source is DurationSource.DERIVED and first.reported_ms is None
    assert (
        second.status is TaskStatus.IN_PROGRESS
        and second.duration_source is DurationSource.REPORTED
    )
    by_id = {r.agent_run_id: r for r in runs}
    assert by_id["claude-code:agent:a1"].status is RunStatus.DONE
    assert by_id["claude-code:p2:main"].status is RunStatus.RUNNING
    assert all(r.owner_rank == "0" and r.session_id == "s1" for r in runs)
    assert [(t.tool_name, t.calls, t.errors) for t in tools] == [("Bash", 2, 1)]


def test_assemble_marks_last_task_stale_after_threshold() -> None:
    task = TaskDraft(task_id="t")
    run = make_run("t:main", "main", [0, 10])
    task.runs[run.agent_run_id] = run

    tasks, runs, _ = assemble(
        Host.CLAUDE_CODE, "s", [task], make_options(now=at(10 + 86_401))
    )

    assert (
        tasks[0].status is TaskStatus.CLOSED_STALE and runs[0].status is RunStatus.DONE
    )


def test_assemble_skips_runs_without_events() -> None:
    task = TaskDraft(task_id="t")
    task.runs["t:main"] = RunDraft(
        agent_run_id="t:main",
        agent_type="main",
        parent_agent_run_id=None,
        spawn_depth=0,
    )

    assert assemble(Host.CLAUDE_CODE, "s", [task], make_options()) == ([], [], [])
