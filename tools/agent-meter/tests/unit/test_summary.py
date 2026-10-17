"""Summary tests: session summary (SM-01/02), task rollups (US-06), formatting and labels (OQ-4)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from agent_meter.config import Config
from agent_meter.model import Host, TaskStatus
from agent_meter.paths import AppHome
from agent_meter.pricing import load_pricing
from agent_meter.project_resolver import ProjectsConfig
from agent_meter.store import Store
from agent_meter.summary import (
    AgentTypeRow,
    HostCost,
    PeriodTotals,
    SessionSummary,
    SummaryError,
    TaskRollup,
    fmt_duration,
    fmt_tokens,
    read_task_label,
    render_session_summary,
    render_task_rollup,
    session_summary,
    summary_from_snapshot,
    task_rollups,
)
from tests.fixtures.antigravity import USER_INPUT as AGY_USER_INPUT
from tests.fixtures.antigravity import AgyConversation, AgyStep, build_root
from tests.fixtures.canary import CANARY
from tests.fixtures.claude import ClaudeHome, ClaudeSession
from tests.fixtures.records import (
    make_agent_run,
    make_batch,
    make_call,
    make_project,
    make_session,
    make_task,
    make_unit,
    ts,
)

PID = "git:0123456789abcdef"
NOW = datetime(2026, 10, 16, 20, 0, tzinfo=UTC)


@pytest.fixture()
def store(tmp_path: Path) -> Iterator[Store]:
    home = AppHome.resolve(str(tmp_path / "h"))
    with Store.open(home, read_only=False, lock_timeout_s=1.0) as opened:
        opened.migrate()
        opened.load_reference_data(
            pricing=load_pricing(None), host_defaults={},
            projects=ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={}),
            project_refs=[make_project()], settings={"timezone": "America/Bogota"},
        )
        yield opened


def cross_host_store(store: Store) -> None:
    """Claude session today, Antigravity session today, plus one call last month and one yesterday."""
    claude = make_batch()
    agy_sid = "c-agy"
    agy_task = f"antigravity-cli:{agy_sid}:0"
    agy = make_batch(
        unit=make_unit(host=Host.ANTIGRAVITY_CLI, unit_id=agy_sid),
        sessions=(make_session(session_id=agy_sid, host=Host.ANTIGRAVITY_CLI, started_at=ts(3600), ended_at=ts(4000)),),
        tasks=(make_task(task_id=agy_task, session_id=agy_sid, host=Host.ANTIGRAVITY_CLI, started_at=ts(3600),
                         ended_at=ts(4000)),),
        agent_runs=(make_agent_run(agent_run_id=f"{agy_task}:main", task_id=agy_task, session_id=agy_sid,
                                   host=Host.ANTIGRAVITY_CLI),),
        calls=(
            make_call(call_id="a1", host=Host.ANTIGRAVITY_CLI, session_id=agy_sid, task_id=agy_task,
                      agent_run_id=f"{agy_task}:main", ts=ts(3700), model="gemini-3.8-flash"),
            make_call(call_id="a-old", host=Host.ANTIGRAVITY_CLI, session_id=agy_sid, task_id=agy_task,
                      agent_run_id=f"{agy_task}:main", ts=datetime(2026, 9, 30, 12, tzinfo=UTC),
                      model="gemini-3.8-flash"),
            make_call(call_id="a-yday", host=Host.ANTIGRAVITY_CLI, session_id=agy_sid, task_id=agy_task,
                      agent_run_id=f"{agy_task}:main", ts=datetime(2026, 10, 15, 12, tzinfo=UTC),
                      model="gemini-x-unknown"),
        ),
        tool_uses=(),
    )
    store.apply_batches([claude, agy])


def cost_of(store: Store, *call_ids: str) -> Decimal:
    marks = ", ".join("?" for _ in call_ids)
    value = store.query(f"SELECT SUM(cost_usd) AS s FROM v_calls WHERE call_id IN ({marks})", list(call_ids))[0]["s"]
    assert isinstance(value, Decimal)
    return value


# ----------------------------------------------------------------------------- formatting helpers


@pytest.mark.parametrize(
    ("ms", "text"),
    [(0, "0s"), (35_000, "35s"), (250_000, "4m 10s"), (782_000, "13m 02s"), (3_900_000, "1h 05m")],
)
def test_fmt_duration(ms: int, text: str) -> None:
    assert fmt_duration(ms) == text


@pytest.mark.parametrize(
    ("n", "text"), [(950, "950"), (1_500, "1.5K"), (85_000, "85K"), (1_210_000, "1.21M"), (9_800_000, "9.80M")]
)
def test_fmt_tokens(n: int, text: str) -> None:
    assert fmt_tokens(n) == text


def golden_session() -> SessionSummary:
    return SessionSummary(
        host=Host.ANTIGRAVITY_CLI, session_id="c-1", project_id=PID, project_name="project-x",
        started_at=NOW, ended_at=NOW, status="closed", wall_clock_ms=2_530_000, active_ms=1_085_000,
        tasks=7, calls=40, input_tokens=1_210_000, cache_read_tokens=9_800_000, cache_write_tokens=0,
        output_tokens=85_000, cache_hit_ratio=Decimal("0.89"), cost_usd=Decimal("1.37"), unpriced_calls=0,
        unpriced_models=(), estimated_calls=0, inferred_calls=0, task_p50_ms=35_000, task_p95_ms=250_000,
        today=PeriodTotals(
            cost_usd=Decimal("3.02"), unpriced_calls=0, unpriced_models=(),
            by_host=(HostCost(Host.CLAUDE_CODE, Decimal("1.65")), HostCost(Host.ANTIGRAVITY_CLI, Decimal("1.37"))),
        ),
        month=PeriodTotals(cost_usd=Decimal("41.80"), unpriced_calls=0, unpriced_models=(), by_host=()),
    )


def test_render_session_summary_golden() -> None:
    cfg = Config(timezone="UTC", display_currency="COP", usd_rate=Decimal("4100"))

    text = render_session_summary(golden_session(), cfg)

    assert text == (
        "[agent-meter] project-x · Antigravity CLI · session 42m 10s (active 18m 05s)\n"
        "  Tokens 1.21M in · 9.80M cache read · 85K out · cache hit 89%\n"
        "  Cost ≈ $1.37 · 7 tasks · P50 35s · P95 4m 10s\n"
        "  project-x today ≈ $3.02 (Claude Code $1.65 · Antigravity CLI $1.37) · month ≈ $41.80 (COP 171,380)"
    )


def test_render_partial_and_flagged_costs() -> None:
    summary = golden_session()
    flagged = SessionSummary(**{
        **{f: getattr(summary, f) for f in SessionSummary.__dataclass_fields__},
        "unpriced_calls": 312, "unpriced_models": ("gemini-x",), "estimated_calls": 1, "inferred_calls": 2,
    })

    text = render_session_summary(flagged, Config(timezone="UTC"))

    assert "Cost ≥ $1.37*† (312 calls unpriced: gemini-x)" in text
    assert "* estimated price · † model inferred" in text
    assert "COP" not in text


# ----------------------------------------------------------------------------- session summary


def test_sm01_session_summary_today_and_month_across_hosts(store: Store) -> None:
    cross_host_store(store)

    summary = session_summary(store, Host.CLAUDE_CODE, "s-0001", now=NOW)

    assert summary.project_name == "demo-repo"
    assert summary.tasks == 1 and summary.calls == 1
    assert summary.cost_usd == cost_of(store, "claude-code:req-0001")
    assert summary.today.cost_usd == cost_of(store, "claude-code:req-0001", "a1")
    assert {h.host: h.cost_usd for h in summary.today.by_host} == {
        Host.CLAUDE_CODE: cost_of(store, "claude-code:req-0001"),
        Host.ANTIGRAVITY_CLI: cost_of(store, "a1"),
    }
    assert summary.month.cost_usd == cost_of(store, "claude-code:req-0001", "a1")
    assert summary.month.unpriced_calls == 1
    assert summary.month.unpriced_models == ("gemini-x-unknown",)
    assert summary.today.unpriced_calls == 0


def test_sm02_today_follows_configured_timezone(store: Store) -> None:
    cross_host_store(store)
    just_after_midnight_utc = datetime(2026, 10, 17, 2, 0, tzinfo=UTC)  # still Oct 16 in Bogota

    summary = session_summary(store, Host.CLAUDE_CODE, "s-0001", now=just_after_midnight_utc)

    assert summary.today.cost_usd == cost_of(store, "claude-code:req-0001", "a1")


def test_unknown_session_raises(store: Store) -> None:
    with pytest.raises(SummaryError):
        session_summary(store, Host.CLAUDE_CODE, "nope", now=NOW)


# ----------------------------------------------------------------------------- task rollups


def fan_out(store: Store) -> None:
    main = make_agent_run()
    runs = [main] + [
        make_agent_run(agent_run_id=f"claude-code:agent:{n}", agent_type=t, spawn_depth=1, files_touched=f,
                       test_runs=tr, parent_agent_run_id=main.agent_run_id, active_ms=300_000)
        for n, t, f, tr in (("a1", "code-implementer", 4, 0), ("a2", "code-implementer", 3, 0), ("a3", "qa-tester", 0, 1))
    ]
    calls = [make_call(call_id=f"c{i}", agent_run_id=runs[i % 4].agent_run_id) for i in range(8)]
    tools = [
        _tool("claude-code:agent:a1", "Edit", 30), _tool("claude-code:agent:a2", "Edit", 11),
        _tool("claude-code:agent:a1", "Write", 12), _tool("claude-code:agent:a3", "Bash", 2),
    ]
    task = make_task(agent_runs=4, max_spawn_depth=1, active_ms=700_000, wall_clock_ms=782_000, retries=1,
                     retry_summary="qa-tester→code-implementer")
    later = make_task(task_id="claude-code:p-0002", seq_in_session=2, started_at=ts(900), ended_at=ts(950),
                      status=TaskStatus.IN_PROGRESS, wall_clock_ms=50_000, active_ms=50_000)
    store.apply_batches([make_batch(tasks=(task, later), agent_runs=tuple(runs), calls=tuple(calls),
                                    tool_uses=tuple(tools))])


def _tool(run: str, name: str, calls: int) -> object:
    from tests.fixtures.records import make_tool_use

    return make_tool_use(agent_run_id=run, tool_name=name, calls=calls)


def test_task_rollups_last_and_agent_rows(store: Store) -> None:
    fan_out(store)

    latest, first = task_rollups(store, last=2)
    only_session = task_rollups(store, session_id="s-0001")
    by_tag = task_rollups(store, tag="none")

    assert latest.task_id == "claude-code:p-0002" and latest.status == "in_progress"
    assert len(only_session) == 2
    assert by_tag == []
    assert first.cost_usd == cost_of(store, *[f"c{i}" for i in range(8)])
    assert first.parallelism == Decimal("1.97")
    assert [(a.agent_type, a.runs, a.calls) for a in first.agents] == [
        ("main", 1, 2), ("code-implementer", 2, 4), ("qa-tester", 1, 2),
    ]
    impl = first.agents[1]
    assert impl.tools == (("Edit", 41), ("Write", 12))
    assert impl.files_touched == 7


def test_render_task_rollup_without_and_with_label(store: Store) -> None:
    fan_out(store)
    rollup = task_rollups(store, last=2)[1]
    cfg = Config(timezone="UTC")

    plain = render_task_rollup(rollup, cfg)
    labelled = render_task_rollup(rollup, cfg, label="execute the plan")

    lines = plain.splitlines()
    assert lines[0] == "[agent-meter] demo-repo · Claude Code · task #1 · 13m 02s (active 11m 40s)"
    assert lines[1].startswith("  Cost ≈ $") and "4 agents (max depth 1) · parallelism 1.97x · 1 retry qa-tester→code-implementer" in lines[1]
    assert lines[2].split()[0] == "main"
    assert "code-implementer ×2" in lines[3] and "41 Edit · 12 Write · 7 files" in lines[3]
    assert lines[4].rstrip().endswith("tests ✓")
    assert 'task "execute the plan"' in labelled.splitlines()[0]


def test_render_in_progress_rollup(store: Store) -> None:
    fan_out(store)

    text = render_task_rollup(task_rollups(store, last=1)[0], Config(timezone="UTC"))

    assert text.splitlines()[0].endswith("· in progress")


def manual_rollup(**overrides: object) -> TaskRollup:
    base = dict(
        task_id="t", session_id="s", host=Host.CLAUDE_CODE, project_id=PID, project_name="p", seq_in_session=3,
        started_at=NOW, ended_at=NOW, status="done", wall_clock_ms=1000, active_ms=1000, cost_usd=None,
        unpriced_calls=2, unpriced_models=("m-x",), estimated_calls=0, inferred_calls=0, agent_runs=1,
        max_spawn_depth=0, parallelism=None, retries=0, retry_summary="", calls=2, tool_calls=0, files_touched=0,
        test_runs=1, test_failures=1, work_item_tag=None,
        agents=(AgentTypeRow("main", 1, 2, None, 2, (), 0, 1, 1),),
    )
    base.update(overrides)
    return TaskRollup(**base)  # type: ignore[arg-type]


def test_render_unpriced_rollup_shows_lower_bound() -> None:
    text = render_task_rollup(manual_rollup(), Config(timezone="UTC"))

    assert "Cost ≥ $0.00 (2 calls unpriced: m-x)" in text
    assert "tests ✗ 1/1" in text
    assert "task #3" in text


# ----------------------------------------------------------------------------- labels


def test_read_task_label_claude_truncates_and_sanitizes(tmp_path: Path) -> None:
    claude = ClaudeHome(tmp_path / ".claude")
    session = ClaudeSession("s-lab")
    session.prompt(0, "p1")
    claude.write(session)

    label = read_task_label({Host.CLAUDE_CODE: claude.root}, Host.CLAUDE_CODE, "s-lab", "claude-code:p1")

    assert label is not None
    assert label.startswith("please do the thing")
    assert len(label) <= 40
    assert read_task_label({Host.CLAUDE_CODE: claude.root}, Host.CLAUDE_CODE, "s-lab", "claude-code:zz") is None


def test_read_task_label_antigravity(tmp_path: Path) -> None:
    root = build_root(tmp_path / "antigravity-cli", [
        AgyConversation(conversation_id="c-l", trajectory_id="t-l", steps=[AgyStep(4, AGY_USER_INPUT, 10)]),
    ])

    label = read_task_label({Host.ANTIGRAVITY_CLI: root}, Host.ANTIGRAVITY_CLI, "c-l", "antigravity-cli:c-l:4")

    assert label == f"content {CANARY}"


def test_read_task_label_never_raises_on_missing_root(tmp_path: Path) -> None:
    assert read_task_label({}, Host.CLAUDE_CODE, "s", "claude-code:p") is None
    assert read_task_label({Host.CLAUDE_CODE: tmp_path / "missing"}, Host.CLAUDE_CODE, "../x", "claude-code:p") is None


# ----------------------------------------------------------------------------- snapshot fallback


def test_summary_from_snapshot_uses_session_text(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({
        "generated_at": NOW.isoformat(), "timezone": "UTC", "projects": {},
        "sessions": [{"host": "claude-code", "session_id": "s-1", "text": "[agent-meter] demo · Claude Code"}],
    }), encoding="utf-8")

    text = summary_from_snapshot(snapshot, Host.CLAUDE_CODE, "s-1", Config(timezone="UTC"))
    other = summary_from_snapshot(snapshot, Host.CLAUDE_CODE, "s-2", Config(timezone="UTC"))
    missing = summary_from_snapshot(tmp_path / "none.json", Host.CLAUDE_CODE, "s-2", Config(timezone="UTC"))

    assert text.startswith("[agent-meter] demo · Claude Code")
    assert text.endswith("(collecting… run 'agent-meter last' in a minute)")
    assert other.endswith("(collecting… run 'agent-meter last' in a minute)")
    assert missing.endswith("(collecting… run 'agent-meter last' in a minute)")
