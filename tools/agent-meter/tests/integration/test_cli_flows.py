"""End-to-end CLI flows over fake hosts (L3): collect → hook → summary → report → uninstall.

Every flow runs in a temp HOME + AGENT_METER_HOME with the network blocked, and the privacy
canary planted in the fixtures must never appear in the store, snapshot, last-summary,
report, logs or any command output (PV-01).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from agent_meter import cli
from agent_meter.store import Store
from tests.fixtures.canary import CANARY
from tests.fixtures.claude import ClaudeSession, usage
from tests.fixtures.scenarios import CLAUDE_SESSION_ID, claude_standard_session
from tests.integration.conftest import World
from tests.privacy_helpers import CLEAR_TEXT_PATHS, assert_store_free_of

SRC = Path(__file__).resolve().parents[2] / "src"


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def all_meter_bytes(world: World) -> bytes:
    return b"".join(p.read_bytes() for p in world.meter.root.rglob("*") if p.is_file())


def daily_totals(world: World) -> list[dict[str, object]]:
    with Store.open(world.meter, read_only=True, lock_timeout_s=5.0) as st:
        return st.query("SELECT * FROM v_daily_project_cost ORDER BY ALL")


def transcript_digests(world: World) -> dict[str, tuple[str, int]]:
    roots = [world.claude.root, world.agy_root]
    return {
        str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
        for root in roots
        for p in root.rglob("*")
        if p.is_file()
    }


# ----------------------------------------------------------------------------- full flow + privacy


def test_full_local_flow_never_leaks_the_canary(world: World, capsys: pytest.CaptureFixture[str],
                                                monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import agent_meter.scheduler as scheduler
    from agent_meter.setup import settings_merge

    monkeypatch.setattr(scheduler, "status", lambda **_kw: "not_loaded")
    monkeypatch.setattr(settings_merge, "registration_status", lambda _p, _t: "absent")
    before = transcript_digests(world)
    report = tmp_path / "report.html"

    outputs = [
        run(capsys, "collect"),
        run(capsys, "hook-worker", "--host", "claude-code", "--event", "session-end", "--session-id", CLAUDE_SESSION_ID),
        run(capsys, "last"),
        run(capsys, "last", "--json"),
        run(capsys, "tasks", "--last", "5"),
        run(capsys, "tasks", "--json"),
        run(capsys, "projects", "list", "--json"),
        run(capsys, "pricing", "unpriced"),
        run(capsys, "doctor", "--json"),
        run(capsys, "report", "--out", str(report)),
        run(capsys, "verify", "--reconcile"),
    ]

    assert [code for code, _ in outputs] == [0] * len(outputs)
    for _code, text in outputs:
        assert CANARY not in text
        assert "/Users/dev/work/demo-repo" not in text
    assert world.meter.last_summary.exists()
    assert_store_free_of(world.meter.db, CANARY, *CLEAR_TEXT_PATHS)  # layer 1: every stored value via SQL
    assert CANARY.encode() not in all_meter_bytes(world)  # layer 2: raw bytes of every meter file
    assert CANARY not in report.read_text(encoding="utf-8")
    assert transcript_digests(world) == before  # PV-03: hosts are read-only


def test_us02_cross_host_project_totals(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    run(capsys, "collect")

    code, out = run(capsys, "last", "--json", "--project", "demo-repo")
    summary = json.loads(out)

    month = summary["month"]  # fixtures are dated 2026-10-16; month-to-date holds them on any later day
    hosts = {entry["host"] for entry in month["by_host"]}
    assert code == 0
    assert hosts == {"claude-code", "antigravity-cli"}
    by_host = [entry["cost_usd"] for entry in month["by_host"] if entry["cost_usd"] is not None]
    from decimal import Decimal

    assert Decimal(month["cost_usd"]) == sum((Decimal(v) for v in by_host), Decimal(0))


def test_us04_separate_and_unassigned_projects(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    other = ClaudeSession("s-other", cwd="/Users/dev/work/other-repo", slug="-Users-dev-work-other-repo")
    p = other.prompt(0, "po")
    other.assistant(5, "r-other", parent=p)
    scratch = ClaudeSession("s-home", cwd=str(world.user), slug="-home")
    q = scratch.prompt(0, "ph")
    scratch.assistant(5, "r-home", parent=q)
    world.write_claude(other)
    world.write_claude(scratch)

    run(capsys, "collect")
    names = {p["display_name"] for p in json.loads(run(capsys, "projects", "list", "--json")[1])}

    assert {"demo-repo", "other-repo", "(unassigned)"} <= names


# ----------------------------------------------------------------------------- idempotency & crash safety


def test_qa3_repeated_ingest_from_all_triggers_is_identical(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    run(capsys, "collect")
    first = daily_totals(world)

    for argv in (
        ("collect",),
        ("collect", "--full"),
        ("hook-worker", "--host", "claude-code", "--event", "task-end", "--session-id", CLAUDE_SESSION_ID),
        ("hook-worker", "--host", "antigravity", "--event", "task-end", "--session-id", "c-root", "--fully-idle", "true"),
        ("--quiet", "collect", "--scheduled"),
    ):
        assert run(capsys, *argv)[0] == 0

    assert daily_totals(world) == first


def test_us03_partial_line_then_completion_updates_in_place(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    session = claude_standard_session()
    p3 = session.prompt(1200, "p3")
    session.assistant(1205, "r-p3", parent=p3, use=usage(10, 5, cache_read=0))
    complete = session.encode()
    partial_tail = b'{"type": "assistant", "requestId": "r-partial", "message": {"usage": {"input_tok'
    world.write_claude(session, tail=partial_tail)

    run(capsys, "collect")
    with Store.open(world.meter, read_only=True, lock_timeout_s=5.0) as st:
        first = st.query("SELECT task_id, status FROM tasks WHERE task_id = 'claude-code:p3'")
        partial = st.query("SELECT COUNT(*) AS n FROM llm_calls WHERE call_id LIKE '%r-partial%'")
    p4 = session.prompt(1300, "p4")
    session.assistant(1305, "r-p4", parent=p4, use=usage(10, 5, cache_read=0))
    world.write_claude(session)
    run(capsys, "collect")

    with Store.open(world.meter, read_only=True, lock_timeout_s=5.0) as st:
        after = st.query("SELECT task_id, status FROM tasks WHERE task_id IN ('claude-code:p3', 'claude-code:p4') ORDER BY 1")
    assert complete  # the fixture really contained complete lines before the torn tail
    assert partial == [{"n": 0}]
    assert len(first) == 1
    assert after[0] == {"task_id": "claude-code:p3", "status": "done"}
    assert len(after) == 2


# ----------------------------------------------------------------------------- pricing edits are retroactive


def test_pc08_pricing_add_reprices_history_without_recollect(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    session = ClaudeSession("s-new-model")
    p = session.prompt(0, "pn")
    session.assistant(5, "r-new-model", parent=p, model="claude-brand-new-9", use=usage(1_000_000, 0, cache_read=0))
    world.write_claude(session)
    run(capsys, "collect")
    unpriced = json.loads(run(capsys, "pricing", "unpriced", "--json")[1])

    code, _ = run(capsys, "pricing", "add", "claude-brand-new-9", "--input", "3", "--output", "15", "--cache-read", "0.3")
    with Store.open(world.meter, read_only=True, lock_timeout_s=5.0) as st:
        cost = st.query("SELECT cost_usd FROM v_calls WHERE model = 'claude-brand-new-9'")

    assert any(row["model_effective"] == "claude-brand-new-9" for row in unpriced)
    assert code == 0
    assert str(cost[0]["cost_usd"]) == "3.000000000"


# ----------------------------------------------------------------------------- empty store, tags, uninstall


def test_us05_report_on_empty_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "nobody"))
    monkeypatch.setenv("AGENT_METER_HOME", str(tmp_path / "empty-meter"))
    out = tmp_path / "empty.html"

    code, _ = run(capsys, "report", "--out", str(out))
    last = run(capsys, "last")

    assert code == 0
    assert "No data yet" in out.read_text(encoding="utf-8")
    assert last[0] == 0 and "No sessions yet" in last[1]


def test_us07_tag_rolls_up_tasks_across_hosts(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    run(capsys, "collect")

    assert run(capsys, "tag", "Track 11", "--project", "demo-repo", "--last", "3")[0] == 0
    tagged = json.loads(run(capsys, "tasks", "--tag", "Track 11", "--json")[1])

    assert len(tagged) == 3
    assert {t["work_item_tag"] for t in tagged} == {"Track 11"}


def test_us11_uninstall_keeps_data_and_transcripts(world: World, capsys: pytest.CaptureFixture[str],
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    import agent_meter.scheduler as scheduler

    monkeypatch.setattr(scheduler, "uninstall", lambda _home, **_kw: "no scheduler installed (nothing to remove)")
    run(capsys, "collect")
    before = transcript_digests(world)

    code, out = run(capsys, "uninstall")

    assert code == 0 and "data kept" in out
    assert world.meter.db.exists()
    assert transcript_digests(world) == before


# ----------------------------------------------------------------------------- performance budgets


def test_pf02_no_change_incremental_collect_is_fast(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    run(capsys, "collect")

    started = time.monotonic()
    code, out = run(capsys, "collect")
    elapsed = time.monotonic() - started

    assert code == 0 and "Collected 0 units" in out
    assert elapsed < 2.0


def test_pf03_hook_subprocess_returns_fast_and_worker_writes_summary(world: World, tmp_path: Path) -> None:
    env = {
        **os.environ, "HOME": str(world.user), "AGENT_METER_HOME": str(world.meter.root),
        "PYTHONPATH": os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")]),
    }
    payload = json.dumps({"session_id": CLAUDE_SESSION_ID, "hook_event_name": "SessionEnd", "reason": "exit",
                          "last_assistant_message": CANARY}).encode()

    started = time.monotonic()
    done = subprocess.run(
        [sys.executable, "-m", "agent_meter", "hook", "--host", "claude-code", "--event", "session-end"],
        input=payload, capture_output=True, env=env, timeout=30, check=False,
    )
    blocking = time.monotonic() - started
    deadline = time.monotonic() + 20
    while not world.meter.last_summary.exists() and time.monotonic() < deadline:
        time.sleep(0.1)

    assert done.returncode == 0
    assert done.stdout == b""  # HK-03: nothing reaches the agent context
    assert blocking < 2.0
    text = world.meter.last_summary.read_text(encoding="utf-8")
    assert text.startswith("[agent-meter] demo-repo · Claude Code")
    assert CANARY not in text
