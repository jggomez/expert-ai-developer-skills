"""Store tests: schema, idempotent upserts, ownership, views vs the pricing oracle.

Covers ST-01..06, TK-01/06/07 (store side), PC-06/PC-08 (view side), SM-02 and the
store-side privacy guarantees (PV-05: description hashes only, BR-15: never delete).
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import duckdb
import pytest

from agent_meter import store as store_module
from agent_meter.locking import LockTimeout, store_lock
from agent_meter.model import (
    DiagnosticKind,
    Host,
    TaskStatus,
    UnitBatch,
)
from agent_meter.paths import AppHome
from agent_meter.pricing import (
    PriceRow,
    PricingTable,
    cost_usd,
    load_pricing,
    resolve_price,
)
from agent_meter.project_resolver import ProjectOverride, ProjectsConfig
from agent_meter.readers._common import description_hash
from agent_meter.store import Store, StoreError
from tests.fixtures.canary import CANARY
from tests.fixtures.records import (
    make_agent_run,
    make_batch,
    make_call,
    make_diagnostic,
    make_project,
    make_session,
    make_task,
    make_tool_use,
    make_unit,
    make_untracked,
    ts,
)
from tests.privacy_helpers import CLEAR_TEXT_PATHS, assert_store_free_of

PID = "git:0123456789abcdef"
EMPTY_PROJECTS = ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={})


@pytest.fixture()
def home(tmp_path: Path) -> AppHome:
    return AppHome.resolve(str(tmp_path / "meter-home"))


@pytest.fixture()
def store(home: AppHome) -> Iterator[Store]:
    with Store.open(home, read_only=False, lock_timeout_s=1.0) as opened:
        opened.migrate()
        load_reference(opened)
        yield opened


def load_reference(
    store: Store,
    *,
    timezone: str = "UTC",
    pricing: PricingTable | None = None,
    projects: ProjectsConfig = EMPTY_PROJECTS,
    defaults: dict[Host, str | None] | None = None,
    extra_settings: dict[str, str] | None = None,
) -> None:
    store.load_reference_data(
        pricing=pricing if pricing is not None else load_pricing(None),
        host_defaults=defaults or {},
        projects=projects,
        project_refs=[make_project()],
        settings={"timezone": timezone, **(extra_settings or {})},
    )


def rows(store: Store, table: str) -> list[dict[str, object]]:
    return store.query(f"SELECT * FROM {table} ORDER BY ALL")


# ----------------------------------------------------------------------------- schema


def test_migrate_creates_schema_and_is_idempotent(store: Store) -> None:
    store.migrate()

    tables = {r["table_name"] for r in store.query("SELECT table_name FROM information_schema.tables")}
    assert {"sessions", "tasks", "agent_runs", "llm_calls", "tool_uses", "source_units", "pricing"} <= tables
    assert {"v_calls", "v_tasks", "v_client_month", "v_health"} <= tables
    assert store.get_meta("schema_version") == "1"
    columns = {r["column_name"] for r in store.query(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'llm_calls'")}
    assert not any("cost" in str(c) for c in columns)


def test_st06_forward_migration_preserves_data(home: AppHome, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: a v1 store with data
    with Store.open(home, read_only=False, lock_timeout_s=1.0) as st:
        st.migrate()
        st.apply_batches([make_batch()])
    monkeypatch.setattr(
        store_module, "MIGRATIONS", {2: ("ALTER TABLE llm_calls ADD COLUMN IF NOT EXISTS extra_v2 TEXT",)}
    )
    monkeypatch.setattr(store_module, "TARGET_SCHEMA_VERSION", 2)

    # Act
    with Store.open(home, read_only=False, lock_timeout_s=1.0) as st:
        st.migrate()
        calls = st.query("SELECT call_id, extra_v2 FROM llm_calls")
        version = st.get_meta("schema_version")

    # Assert
    assert calls == [{"call_id": "claude-code:req-0001", "extra_v2": None}]
    assert version == "2"


def test_newer_schema_is_refused(home: AppHome) -> None:
    with Store.open(home, read_only=False, lock_timeout_s=1.0) as st:
        st.migrate()
        st.set_meta("schema_version", "99")

    with Store.open(home, read_only=False, lock_timeout_s=1.0) as st, pytest.raises(StoreError, match="newer"):
        st.migrate()


def test_read_only_open_creates_missing_store(home: AppHome) -> None:
    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        assert st.query("SELECT COUNT(*) AS n FROM v_calls") == [{"n": 0}]
        with pytest.raises(duckdb.Error):
            st.set_meta("x", "y")


def test_st04_open_times_out_when_lock_held(home: AppHome) -> None:
    with store_lock(home.lock, exclusive=True, timeout_s=1.0), pytest.raises(LockTimeout):
        Store.open(home, read_only=False, lock_timeout_s=0.1)


# ----------------------------------------------------------------------------- idempotent upsert


def test_st01_same_batch_twice_is_idempotent(store: Store) -> None:
    batch = make_batch()

    first = store.apply_batches([batch])
    snapshot = {t: rows(store, t) for t in ("sessions", "tasks", "agent_runs", "llm_calls", "tool_uses")}
    second = store.apply_batches([batch])

    assert (first.calls_changed, first.tasks_changed, first.runs_changed, first.sessions_changed) == (1, 1, 1, 1)
    assert (second.calls_changed, second.tasks_changed, second.runs_changed, second.sessions_changed) == (0, 0, 0, 0)
    assert {t: rows(store, t) for t in snapshot} == snapshot


def test_changed_row_is_updated_with_new_ingest_seq(store: Store) -> None:
    store.apply_batches([make_batch()])
    before = store.query("SELECT ingest_seq, output_tokens FROM llm_calls")[0]

    stats = store.apply_batches([make_batch(calls=(make_call(output_tokens=999),))])
    after = store.query("SELECT ingest_seq, output_tokens FROM llm_calls")[0]

    assert stats.calls_changed == 1
    assert after["output_tokens"] == 999
    assert isinstance(after["ingest_seq"], int) and after["ingest_seq"] > before["ingest_seq"]  # type: ignore[operator]


def test_lower_owner_rank_wins_regardless_of_order(store: Store) -> None:
    owner = make_call(owner_rank="0:2026-10-16T14:00:00.000Z:s-0001", output_tokens=10)
    copy = make_call(owner_rank="1:2026-10-17T09:00:00.000Z:s-0002", output_tokens=99, session_id="s-0002")

    store.apply_batches([make_batch(calls=(copy,))])
    store.apply_batches([make_batch(calls=(owner,))])
    store.apply_batches([make_batch(calls=(copy,))])

    assert store.query("SELECT output_tokens, session_id FROM llm_calls") == [
        {"output_tokens": 10, "session_id": "s-0001"}
    ]


def test_duplicate_keys_inside_one_apply_keep_owner(store: Store) -> None:
    owner = make_call(owner_rank="0", output_tokens=10)
    copy = make_call(owner_rank="1:c-other", output_tokens=99)

    stats = store.apply_batches([make_batch(calls=(copy,)), make_batch(calls=(owner,))])

    assert stats.calls_changed == 1
    assert store.query("SELECT output_tokens FROM llm_calls") == [{"output_tokens": 10}]


def test_br15_empty_batch_never_deletes_rows(store: Store) -> None:
    store.apply_batches([make_batch()])
    empty = make_batch(
        sessions=(), tasks=(), agent_runs=(), calls=(), tool_uses=(),
        diagnostics=(make_diagnostic(kind=DiagnosticKind.UNREADABLE),),
    )

    store.apply_batches([empty])

    assert len(rows(store, "llm_calls")) == 1
    assert len(rows(store, "tool_uses")) == 1


def test_unit_fingerprint_recorded_except_for_unreadable_units(store: Store) -> None:
    unit = make_unit()
    unreadable = make_batch(
        unit=make_unit(unit_id="s-gone"), sessions=(), tasks=(), agent_runs=(), calls=(), tool_uses=(),
        diagnostics=(make_diagnostic(kind=DiagnosticKind.UNREADABLE),),
    )

    store.apply_batches([make_batch(unit=unit), unreadable])

    assert store.unit_fingerprint(Host.CLAUDE_CODE, "s-0001") == unit.fingerprint
    assert store.unit_fingerprint(Host.CLAUDE_CODE, "s-gone") is None
    assert store.query("SELECT kind, count FROM diagnostics") == [{"kind": "unreadable", "count": 1}]


def test_format_versions_flag_unknown_shapes(store: Store) -> None:
    store.apply_batches(
        [make_batch(format_fingerprint="known-fp"), make_batch(unit=make_unit(unit_id="s-2"), format_fingerprint="new-fp")],
        known_formats={Host.CLAUDE_CODE: frozenset({"known-fp"})},
    )

    assert store.query("SELECT fingerprint, known FROM format_versions ORDER BY fingerprint") == [
        {"fingerprint": "known-fp", "known": True},
        {"fingerprint": "new-fp", "known": False},
    ]
    assert store.query("SELECT host, units, unknown_formats FROM v_health") == [
        {"host": "claude-code", "units": 2, "unknown_formats": 1}
    ]


def test_st05_failure_mid_apply_rolls_back(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*_args: object, **_kwargs: object) -> int:
        raise RuntimeError("killed")

    monkeypatch.setattr(Store, "_merge_tool_uses", explode)

    with pytest.raises(RuntimeError):
        store.apply_batches([make_batch()])

    assert rows(store, "llm_calls") == []
    assert store.unit_fingerprint(Host.CLAUDE_CODE, "s-0001") is None


def test_tool_uses_replaced_wholesale_for_runs_in_batch(store: Store) -> None:
    store.apply_batches([make_batch(tool_uses=(make_tool_use(tool_name="Edit"), make_tool_use(tool_name="Bash")))])

    store.apply_batches([make_batch(tool_uses=(make_tool_use(tool_name="Edit", calls=7),))])

    assert store.query("SELECT tool_name, calls, project_id, host FROM tool_uses") == [
        {"tool_name": "Edit", "calls": 7, "project_id": PID, "host": "claude-code"}
    ]


def test_pv05_only_description_hash_is_stored(store: Store, home: AppHome) -> None:
    # Arrange
    description = f"{CANARY} review the billing module"
    hashed = description_hash(b"s" * 32, description)
    run = make_agent_run(agent_run_id="claude-code:agent:a1", agent_type="qa-tester", spawn_depth=1,
                         description_hash=hashed, parent_agent_run_id="claude-code:p-0001:main")

    # Act
    store.apply_batches([make_batch(agent_runs=(make_agent_run(), run))])
    store.execute("CHECKPOINT")

    # Assert
    columns = {r["column_name"] for r in store.query(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'agent_runs'")}
    assert "description" not in columns
    assert store.query("SELECT description_hash FROM agent_runs WHERE spawn_depth = 1") == [
        {"description_hash": hashed}
    ]
    assert_store_free_of(store, CANARY, description, *CLEAR_TEXT_PATHS)  # layer 1: every stored value via SQL
    assert CANARY.encode() not in home.db.read_bytes()  # layer 2: raw bytes


def test_missing_project_id_falls_back_to_unassigned(store: Store) -> None:
    store.apply_batches([make_batch(calls=(make_call(project_id=None),))])

    assert store.query("SELECT project_id FROM llm_calls") == [{"project_id": "(unassigned)"}]


# ----------------------------------------------------------------------------- cost view vs oracle


ORACLE_CASES = [
    make_call(call_id="c1", model="claude-opus-5-5"),
    make_call(call_id="c2", model="claude-haiku-4-5-20251001"),
    make_call(call_id="c3", model="gemini-3.8-flash-n", host=Host.ANTIGRAVITY_CLI),
    make_call(call_id="c4", model="claude-opus-5-5", speed="fast"),
    make_call(call_id="c5", model="gemini-x-unknown", host=Host.ANTIGRAVITY_CLI),
    make_call(call_id="c6", model=None, host=Host.ANTIGRAVITY_CLI),
    make_call(call_id="c7", model="gemini-3.1-pro-preview", input_tokens=250_000, host=Host.ANTIGRAVITY_CLI),
    make_call(call_id="c8", model="gemini-4-argon", ts=datetime(2026, 12, 1, 4, 0, tzinfo=UTC), host=Host.ANTIGRAVITY_CLI),
    make_call(call_id="c9", model="claude-opus-5-5", output_tokens=None),
    make_call(call_id="c10", model="claude-sonnet-5-5", input_tokens=123_457, output_tokens=7, cache_read_tokens=3),
]


@pytest.mark.parametrize("timezone", ["UTC", "America/Bogota"])
def test_v_calls_cost_equals_python_oracle(store: Store, timezone: str) -> None:
    # Arrange
    defaults: dict[Host, str | None] = {Host.ANTIGRAVITY_CLI: "gemini-3.8-flash"}
    load_reference(store, timezone=timezone, defaults=defaults)
    store.apply_batches([make_batch(calls=tuple(ORACLE_CASES))])
    table = load_pricing(None)
    from zoneinfo import ZoneInfo

    # Act
    view = {r["call_id"]: r for r in store.query("SELECT * FROM v_calls")}

    # Assert
    for call in ORACLE_CASES:
        local_day = call.ts.astimezone(ZoneInfo(timezone)).date()
        prompt = sum(t or 0 for t in (call.input_tokens, call.cache_read_tokens,
                                      call.cache_write_5m_tokens, call.cache_write_1h_tokens))
        res = resolve_price(table, call.model, local_day, prompt, speed=call.speed,
                            default_model=defaults.get(call.host))
        expected = cost_usd(res, input_tokens=call.input_tokens, output_tokens=call.output_tokens,
                            cache_write_5m_tokens=call.cache_write_5m_tokens,
                            cache_write_1h_tokens=call.cache_write_1h_tokens,
                            cache_read_tokens=call.cache_read_tokens)
        row = view[call.call_id]
        assert row["cost_usd"] == expected, call.call_id
        assert row["priced_model"] == res.priced_model, call.call_id
        assert row["estimated"] == res.estimated, call.call_id
        assert row["model_inferred"] == res.inferred, call.call_id
        assert row["unpriced"] == (expected is None), call.call_id
        assert row["local_date"] == local_day


def test_pc08_new_price_reprices_history_without_reingest(store: Store, home: AppHome) -> None:
    # Arrange
    store.apply_batches([make_batch(calls=(make_call(model="gemini-x-new"),))])
    assert store.query("SELECT cost_usd, unpriced FROM v_calls") == [{"cost_usd": None, "unpriced": True}]
    assert store.query("SELECT model_effective, calls FROM v_unpriced_models") == [
        {"model_effective": "gemini-x-new", "calls": 1}
    ]
    base = load_pricing(None)
    row = PriceRow(model="gemini-x-new", effective_from=date(2000, 1, 1), min_prompt_tokens=0,
                   input=Decimal("1"), output=Decimal("2"), cache_write_5m=None, cache_write_1h=None,
                   cache_read=Decimal("0.5"), source="local", source_url=None, fetched_at=None)

    # Act
    load_reference(store, pricing=PricingTable(rows=(*base.rows, row), aliases=base.aliases))

    # Assert: 1000*1 + 200*2 + 300*1 + 0*1 + 5000*0.5 = 4200 / 1e6
    assert store.query("SELECT cost_usd, unpriced FROM v_calls") == [
        {"cost_usd": Decimal("0.004200000"), "unpriced": False}
    ]
    assert store.query("SELECT COUNT(*) AS n FROM v_unpriced_models") == [{"n": 0}]


def test_none_pricing_keeps_previous_table(store: Store) -> None:
    before = store.query("SELECT COUNT(*) AS n FROM pricing")

    store.load_reference_data(pricing=None, host_defaults={}, projects=EMPTY_PROJECTS, project_refs=[],
                              settings={"timezone": "UTC"})

    assert store.query("SELECT COUNT(*) AS n FROM pricing") == before
    assert before[0]["n"] > 0  # type: ignore[operator]


def test_sm02_day_bucket_uses_configured_timezone(store: Store) -> None:
    late = make_call(call_id="late", ts=datetime(2026, 10, 17, 3, 30, tzinfo=UTC))
    store.apply_batches([make_batch(calls=(late,))])

    load_reference(store, timezone="UTC")
    utc_day = store.query("SELECT local_date FROM v_calls")[0]["local_date"]
    load_reference(store, timezone="America/Bogota")
    bogota_day = store.query("SELECT local_date, local_month FROM v_daily_project_cost")[0]

    assert utc_day == date(2026, 10, 17)
    assert bogota_day == {"local_date": date(2026, 10, 16), "local_month": "2026-10"}


# ----------------------------------------------------------------------------- task views


def fan_out_batch(status: TaskStatus = TaskStatus.DONE) -> UnitBatch:
    task = make_task(agent_runs=3, max_spawn_depth=1, active_ms=100_000, status=status)
    main = make_agent_run(active_ms=60_000, files_touched=1)
    impl1 = make_agent_run(agent_run_id="claude-code:agent:a1", agent_type="code-implementer", spawn_depth=1,
                           active_ms=80_000, files_touched=2, test_runs=1, parent_agent_run_id=main.agent_run_id)
    impl2 = make_agent_run(agent_run_id="claude-code:agent:a2", agent_type="code-implementer", spawn_depth=1,
                           active_ms=50_000, files_touched=3, test_runs=2, test_failures=1,
                           parent_agent_run_id=main.agent_run_id)
    calls = (
        make_call(call_id="m1"),
        make_call(call_id="i1", agent_run_id=impl1.agent_run_id, model="claude-sonnet-5-5"),
        make_call(call_id="i2", agent_run_id=impl2.agent_run_id, model="claude-sonnet-5-5"),
        make_call(call_id="u1", agent_run_id=impl2.agent_run_id, model="gemini-x-unknown"),
    )
    tools = (
        make_tool_use(agent_run_id=impl1.agent_run_id, tool_name="Edit", calls=4),
        make_tool_use(agent_run_id=impl2.agent_run_id, tool_name="Edit", calls=2),
        make_tool_use(agent_run_id=impl2.agent_run_id, tool_name="Write", calls=1),
    )
    return make_batch(tasks=(task,), agent_runs=(main, impl1, impl2), calls=calls, tool_uses=tools)


def test_tk01_task_cost_equals_sum_of_call_costs(store: Store) -> None:
    store.apply_batches([fan_out_batch()])

    task = store.query("SELECT cost_usd, calls, unpriced_calls FROM v_tasks")[0]
    call_sum = store.query("SELECT SUM(cost_usd) AS s FROM v_calls")[0]["s"]

    assert task["cost_usd"] == call_sum
    assert task["calls"] == 4
    assert task["unpriced_calls"] == 1


def test_tk07_tool_and_file_counts_and_parallelism(store: Store) -> None:
    store.apply_batches([fan_out_batch()])

    task = store.query("SELECT tool_calls, files_touched, test_runs, test_failures, parallelism FROM v_tasks")[0]
    per_type = store.query(
        "SELECT agent_type, runs, calls, tool_calls, files_touched FROM v_agent_type_cost ORDER BY agent_type")
    tools = store.query("SELECT tool_name, SUM(calls) AS n FROM v_tool_counts GROUP BY 1 ORDER BY 1")

    assert task == {"tool_calls": 7, "files_touched": 6, "test_runs": 3, "test_failures": 1,
                    "parallelism": Decimal("1.90")}
    assert per_type == [
        {"agent_type": "code-implementer", "runs": 2, "calls": 3, "tool_calls": 7, "files_touched": 5},
        {"agent_type": "main", "runs": 1, "calls": 1, "tool_calls": 0, "files_touched": 1},
    ]
    assert tools == [{"tool_name": "Edit", "n": 6}, {"tool_name": "Write", "n": 1}]


def test_tk06_in_progress_task_updated_not_duplicated(store: Store) -> None:
    store.apply_batches([fan_out_batch(TaskStatus.IN_PROGRESS)])

    store.apply_batches([fan_out_batch(TaskStatus.DONE)])

    assert store.query("SELECT task_id, status FROM v_tasks") == [
        {"task_id": "claude-code:p-0001", "status": "done"}
    ]


def test_session_and_latency_views(store: Store) -> None:
    second = make_task(task_id="claude-code:p-0002", seq_in_session=2, started_at=ts(700), ended_at=ts(760),
                       wall_clock_ms=60_000, active_ms=30_000, reported_ms=45_000)
    store.apply_batches([make_batch(tasks=(make_task(), second))])

    session = store.query("SELECT tasks, calls, wall_clock_ms, task_p50_ms, cache_hit_ratio FROM v_sessions")[0]
    latency = store.query("SELECT tasks, p50_ms FROM v_task_latency")[0]

    assert session["tasks"] == 2
    assert session["calls"] == 1
    assert session["wall_clock_ms"] == 600_000
    assert session["task_p50_ms"] == pytest.approx(322_500)
    assert session["cache_hit_ratio"] == Decimal("0.7937")
    assert latency == {"tasks": 2, "p50_ms": pytest.approx(322_500)}


# ----------------------------------------------------------------------------- tags, hours, clients


def test_tag_applies_to_new_tasks_until_cleared(store: Store) -> None:
    store.set_tag(PID, "Track 11", ts(-10))
    store.set_tag(PID, None, ts(650))
    later = make_task(task_id="claude-code:p-0002", seq_in_session=2, started_at=ts(700), ended_at=ts(760))
    store.apply_batches([make_batch(tasks=(make_task(), later))])

    tags = store.query("SELECT task_id, work_item_tag FROM v_tasks ORDER BY task_id")

    assert tags == [
        {"task_id": "claude-code:p-0001", "work_item_tag": "Track 11"},
        {"task_id": "claude-code:p-0002", "work_item_tag": None},
    ]


def test_tag_last_tags_most_recent_tasks(store: Store) -> None:
    tasks = tuple(
        make_task(task_id=f"claude-code:p-{i}", seq_in_session=i, started_at=ts(i * 100), ended_at=ts(i * 100 + 50))
        for i in range(1, 4)
    )
    store.apply_batches([make_batch(tasks=tasks)])

    tagged = store.tag_last(PID, "Fix", 2)

    assert tagged == ["claude-code:p-3", "claude-code:p-2"]
    assert store.query("SELECT COUNT(*) AS n FROM v_tasks WHERE work_item_tag = 'Fix'") == [{"n": 2}]


def test_manual_hours_override_derived(store: Store) -> None:
    other = make_task(task_id="claude-code:p-9", started_at=datetime(2026, 10, 14, 14, tzinfo=UTC),
                      ended_at=datetime(2026, 10, 14, 16, tzinfo=UTC))
    store.apply_batches([make_batch(tasks=(make_task(), other))])
    store.recompute_dev_hours("UTC", 1800)

    derived = store.query("SELECT local_date, hours, source FROM v_dev_hours ORDER BY local_date")
    store.set_manual_hours(PID, "2026-10-14", Decimal("6.5"))
    with_day = store.query("SELECT local_date, hours, source FROM v_dev_hours ORDER BY local_date")
    store.set_manual_hours(PID, "2026-10", Decimal("40"))
    with_month = store.query("SELECT local_date, hours, source FROM v_dev_hours ORDER BY local_date")
    removed = store.unset_manual_hours(PID, "2026-10")

    assert derived == [
        {"local_date": date(2026, 10, 14), "hours": Decimal("2.00"), "source": "derived"},
        {"local_date": date(2026, 10, 16), "hours": Decimal("0.17"), "source": "derived"},
    ]
    assert with_day[0] == {"local_date": date(2026, 10, 14), "hours": Decimal("6.50"), "source": "manual"}
    assert with_month == [{"local_date": date(2026, 10, 1), "hours": Decimal("40.00"), "source": "manual"}]
    assert removed is True
    assert store.unset_manual_hours(PID, "2026-10") is False


def _bigquery_style_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    """BigQuery ``ROUND(SAFE_DIVIDE(NUMERIC, NUMERIC), 4)``: 9-digit NUMERIC quotient, then 4 places."""
    quotient = (numerator / denominator).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_UP)
    return quotient.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def test_l2_client_month_money_is_exact_decimal_without_double(store: Store) -> None:
    # Arrange: 4100.6150 COP / 4100 = 1.00015 exactly; DuckDB DOUBLE arithmetic rounds it to 1.0001
    fixed_pid = "git:fixed000000000"
    projects = ProjectsConfig(
        projects={fixed_pid: ProjectOverride(client="Client Z", billing="fixed", fixed_price=Decimal("4100.6150"),
                                             currency="COP")},
        path_aliases={}, ignore=(), merges={},
    )
    store.apply_batches([
        make_batch(unit=make_unit(unit_id="s-f"), sessions=(make_session(session_id="s-f", project_id=fixed_pid),),
                   tasks=(), agent_runs=(), tool_uses=(),
                   calls=(make_call(call_id="f1", session_id="s-f", project_id=fixed_pid),)),
    ])
    load_reference(store, projects=projects, extra_settings={"display_currency": "COP", "usd_rate": "4100"})
    call_cost = store.query("SELECT cost_usd FROM v_calls WHERE call_id = 'f1'")[0]["cost_usd"]
    assert isinstance(call_cost, Decimal)

    # Act
    row = store.query(
        "SELECT billable_usd, ai_cost_ratio, typeof(billable_usd) AS billable_type, "
        "typeof(ai_cost_ratio) AS ratio_type FROM v_client_month WHERE project_id = ?", [fixed_pid])[0]
    definitions = {r["view_name"]: str(r["sql"]).upper() for r in store.query(
        "SELECT view_name, sql FROM duckdb_views() WHERE view_name IN ('v_client_month', 'v_agent_type_cost')")}

    # Assert
    assert row["billable_type"] == "DECIMAL(18,4)" and row["ratio_type"] == "DECIMAL(12,4)"
    assert row["billable_usd"] == Decimal("1.0002")
    assert row["ai_cost_ratio"] == _bigquery_style_ratio(call_cost, Decimal("1.0002"))
    assert set(definitions) == {"v_client_month", "v_agent_type_cost"}
    assert all("DOUBLE" not in sql for sql in definitions.values())


def test_l2_exact_money_division_rounds_half_away_from_zero(store: Store) -> None:
    # Arrange
    cases = [("4104.3050", "4100", "1.001050000"), ("-1", "3", "-0.333333333"), ("2", "3", "0.666666667"),
             ("1", "0", None)]

    store.execute("CREATE TEMP TABLE money_cases (n INTEGER, a DECIMAL(38, 9), b DECIMAL(18, 6))")
    for index, (a, b, _want) in enumerate(cases):
        store.execute("INSERT INTO money_cases VALUES (?, ?, ?)", [index, a, b])

    # Act
    results = store.query("SELECT am_money_div(a, b) AS q, typeof(am_money_div(a, b)) AS t FROM money_cases ORDER BY n")

    # Assert
    assert [r["q"] for r in results] == [None if want is None else Decimal(want) for _, _, want in cases]
    assert {r["t"] for r in results} == {"DECIMAL(38,9)"}


@pytest.mark.parametrize("period", ["2026-13", "2026-10-32", "last week", ""])
def test_manual_hours_rejects_bad_period(store: Store, period: str) -> None:
    with pytest.raises(StoreError):
        store.set_manual_hours(PID, period, Decimal("1"))


def test_pc06_client_month_hourly_fixed_and_no_client(store: Store) -> None:
    # Arrange
    fixed_pid, bare_pid = "git:fixed000000000", "path:bare000000000"
    projects = ProjectsConfig(
        projects={
            PID: ProjectOverride(display_name="Project X", client="Client Z", billing="hourly",
                                 rate=Decimal("80000"), currency="COP"),
            fixed_pid: ProjectOverride(client="Client Z", billing="fixed", fixed_price=Decimal("2500"),
                                       currency="USD"),
        },
        path_aliases={}, ignore=(), merges={},
    )
    store.apply_batches([
        make_batch(),
        make_batch(unit=make_unit(unit_id="s-f"), sessions=(make_session(session_id="s-f", project_id=fixed_pid),),
                   tasks=(), agent_runs=(), tool_uses=(),
                   calls=(make_call(call_id="f1", session_id="s-f", project_id=fixed_pid),)),
        make_batch(unit=make_unit(unit_id="s-b"), sessions=(make_session(session_id="s-b", project_id=bare_pid),),
                   tasks=(), agent_runs=(), tool_uses=(),
                   calls=(make_call(call_id="b1", session_id="s-b", project_id=bare_pid),)),
    ])
    load_reference(store, projects=projects, extra_settings={"display_currency": "COP", "usd_rate": "4000"})
    store.set_manual_hours(PID, "2026-10-16", Decimal("2"))
    call_cost = store.query("SELECT cost_usd FROM v_calls WHERE call_id = 'f1'")[0]["cost_usd"]
    assert isinstance(call_cost, Decimal)

    # Act
    months = {r["project_id"]: r for r in store.query("SELECT * FROM v_client_month")}

    # Assert
    hourly = months[PID]
    assert hourly["display_name"] == "Project X"
    assert hourly["billable_value"] == Decimal("160000.0000")
    assert hourly["billable_usd"] == Decimal("40.0000")
    assert abs(hourly["ai_cost_ratio"] - call_cost / Decimal(40)) <= Decimal("0.00005")  # type: ignore[operator]
    fixed = months[fixed_pid]
    assert fixed["billable_usd"] == Decimal("2500.0000")
    assert abs(fixed["ai_cost_ratio"] - call_cost / Decimal(2500)) <= Decimal("0.00005")  # type: ignore[operator]
    assert months[bare_pid]["ai_cost_ratio"] is None
    assert months[bare_pid]["client"] is None


# ----------------------------------------------------------------------------- reference data & projects


def test_project_refs_persist_and_never_lose_remote(store: Store) -> None:
    store.load_reference_data(
        pricing=None, host_defaults={}, projects=EMPTY_PROJECTS,
        project_refs=[make_project(remote_url=None, display_name="worktree-dir")], settings={"timezone": "UTC"},
    )
    store.load_reference_data(
        pricing=None, host_defaults={}, projects=EMPTY_PROJECTS, project_refs=[], settings={"timezone": "UTC"}
    )

    projects = store.query("SELECT project_id, display_name, remote_url FROM projects ORDER BY project_id")

    assert {"project_id": PID, "display_name": "demo-repo", "remote_url": "github.com/example/demo-repo"} in projects
    assert {"project_id": "(unassigned)", "display_name": "(unassigned)", "remote_url": None} in projects


def test_merge_projects_rekeys_rows_with_new_seq(store: Store) -> None:
    src = "path:aaaaaaaaaaaaaaaa"
    store.apply_batches([make_batch(calls=(make_call(project_id=src),), sessions=(make_session(project_id=src),))])
    store.set_manual_hours(src, "2026-10-16", Decimal("3"))
    seq_before = store.max_seq("llm_calls")

    moved = store.merge_projects(src, PID)

    call = store.query("SELECT project_id, ingest_seq FROM llm_calls")[0]
    assert moved == 2
    assert call["project_id"] == PID
    assert isinstance(call["ingest_seq"], int) and call["ingest_seq"] > seq_before
    assert store.query("SELECT project_id FROM dev_hours_manual") == [{"project_id": PID}]


def test_merges_in_projects_config_are_applied(store: Store) -> None:
    src = "path:bbbbbbbbbbbbbbbb"
    store.apply_batches([make_batch(calls=(make_call(project_id=src),))])

    load_reference(store, projects=ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={src: PID}))

    assert store.query("SELECT DISTINCT project_id FROM llm_calls") == [{"project_id": PID}]


def test_path_cache_round_trip(store: Store) -> None:
    cache = store.path_cache()

    cache.put("h" * 64, PID)
    cache.put("h" * 64, "git:ffffffffffffffff")

    assert cache.get("h" * 64) == "git:ffffffffffffffff"
    assert cache.get("missing") is None


# ----------------------------------------------------------------------------- misc API


def test_untracked_upsert_and_view(store: Store) -> None:
    store.record_untracked([make_untracked(), make_untracked(conversation_id="c-legacy-0002",
                                                             observed_from=date(2026, 5, 2))])
    store.record_untracked([make_untracked()])

    assert store.query("SELECT host, reason, conversations, observed_from FROM v_untracked") == [
        {"host": "antigravity-ide", "reason": "legacy_pb", "conversations": 2, "observed_from": date(2026, 5, 2)}
    ]


def test_rows_since_and_max_seq(store: Store) -> None:
    store.apply_batches([make_batch()])
    top = store.max_seq("llm_calls")

    fresh = list(store.rows_since("llm_calls", 0, ["call_id", "ingest_seq"]))
    none_left = list(store.rows_since("llm_calls", top, ["call_id"]))

    assert fresh == [{"call_id": "claude-code:req-0001", "ingest_seq": top}]
    assert none_left == []
    with pytest.raises(StoreError):
        list(store.rows_since("llm_calls; DROP TABLE x", 0, ["call_id"]))
    with pytest.raises(StoreError):
        list(store.rows_since("llm_calls", 0, ["call_id FROM meta --"]))


def test_meta_round_trip(store: Store) -> None:
    store.set_meta("bq_watermark:llm_calls", "12")
    store.set_meta("bq_watermark:llm_calls", "13")

    assert store.get_meta("bq_watermark:llm_calls") == "13"
    assert store.get_meta("absent") is None


def test_write_snapshot_contains_totals_and_sessions(store: Store, home: AppHome) -> None:
    store.apply_batches([make_batch()])

    store.write_snapshot(home.snapshot, tz="UTC", now=ts(3600))

    doc = json.loads(home.snapshot.read_text(encoding="utf-8"))
    project = doc["projects"][PID]
    assert doc["timezone"] == "UTC"
    assert project["display_name"] == "demo-repo"
    assert Decimal(project["today"]["total_usd"]) > 0
    assert project["today"]["by_host"].keys() == {"claude-code"}
    assert doc["sessions"][0]["session_id"] == "s-0001"
    assert "[agent-meter]" in doc["sessions"][0]["text"]


def test_dev_hours_recompute_rewrites_table(store: Store) -> None:
    store.apply_batches([make_batch()])
    store.recompute_dev_hours("UTC", 1800)
    store.apply_batches([make_batch(tasks=(make_task(ended_at=ts(3600), wall_clock_ms=3_600_000),))])

    store.recompute_dev_hours("UTC", 1800)

    assert store.query("SELECT hours FROM dev_hours_derived") == [{"hours": Decimal("1.00")}]


def test_query_returns_dicts_with_params(store: Store) -> None:
    store.apply_batches([make_batch()])

    result = store.query("SELECT call_id FROM llm_calls WHERE host = ?", ["claude-code"])

    assert result == [{"call_id": "claude-code:req-0001"}]


def test_session_rows_carry_no_workspace_path(store: Store) -> None:
    session = dataclasses.replace(make_session(), workspace_path="/Users/dev/secret-client")

    store.apply_batches([make_batch(sessions=(session,))])

    dump = json.dumps(rows(store, "sessions"), default=str)
    assert "secret-client" not in dump


def test_timestamps_round_trip_as_aware_utc(store: Store) -> None:
    store.apply_batches([make_batch()])

    value = store.query("SELECT ts FROM llm_calls")[0]["ts"]

    assert isinstance(value, datetime)
    assert value.utcoffset() == timedelta(0)
    assert value == ts(5)
