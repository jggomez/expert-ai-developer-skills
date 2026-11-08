"""Deterministic insight rules (Phase 2): each fires on seeded calls with hand-computed figures."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from agent_meter.insights import (
    Thresholds,
    build_insights,
    insights_document,
    render_insights,
)
from agent_meter.model import UnitBatch
from agent_meter.paths import AppHome
from agent_meter.pricing import load_pricing
from agent_meter.project_resolver import ProjectsConfig
from agent_meter.report import ReportOptions, build_report, report_insights
from agent_meter.store import Store
from tests.fixtures.records import (
    make_agent_run,
    make_batch,
    make_call,
    make_project,
    make_session,
    make_task,
    ts,
)

AS_OF = ts(0).date()
MODEL = "claude-sonnet-5-5"


@pytest.fixture()
def store(tmp_path: Path) -> Iterator[Store]:
    home = AppHome.resolve(str(tmp_path / "h"))
    with Store.open(home, read_only=False, lock_timeout_s=1.0) as opened:
        opened.migrate()
        opened.load_reference_data(
            pricing=load_pricing(None), host_defaults={},
            projects=ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={}),
            project_refs=[make_project()], settings={"timezone": "UTC"},
        )
        yield opened


def save(store: Store, batch: UnitBatch) -> None:
    store.apply_batches([batch])


def tokens(n: int) -> dict[str, int]:
    """``n`` input tokens and nothing else; at Sonnet 5.5's $2/MTok this costs n * 0.000002."""
    return {"input_tokens": n, "output_tokens": 0, "cache_read_tokens": 0,
            "cache_write_5m_tokens": 0, "cache_write_1h_tokens": 0, "model": MODEL}


def rule(store: Store, name: str, limits: Thresholds) -> list:
    return [i for i in build_insights(store, as_of=AS_OF, limits=limits).insights if i.rule == name]


def test_long_session_prices_the_tail_at_the_opening_average(store: Store) -> None:
    calls = [make_call(call_id=f"c{i}", ts=ts(i), **tokens(1_000_000 if i < 2 else 3_000_000)) for i in range(4)]
    save(store, make_batch(calls=tuple(calls)))

    (found,) = rule(store, "long_session", Thresholds(long_session_calls=4, session_baseline_calls=2))

    assert found.saving_usd == Decimal(8)  # two tail calls at $6 each against an opening average of $2
    assert found.evidence["sessions"] == 1


def test_stale_cache_compares_resumes_with_ordinary_calls(store: Store) -> None:
    moments = [0, 60, 4000]
    sizes = [1_000_000, 1_000_000, 5_000_000]
    calls = [make_call(call_id=f"c{i}", ts=ts(s), **tokens(n)) for i, (s, n) in enumerate(zip(moments, sizes))]
    save(store, make_batch(calls=tuple(calls)))

    (found,) = rule(store, "stale_cache", Thresholds(min_stale_resumes=1))

    assert found.evidence["resumes"] == 1
    assert found.saving_usd == Decimal(8)  # $10 resume against a $2 ordinary call


def test_repeated_implementers_ignores_parallel_runs(store: Store) -> None:
    runs = (
        make_agent_run(agent_run_id="r1", agent_type="code-implementer", started_at=ts(0), ended_at=ts(10)),
        make_agent_run(agent_run_id="r2", agent_type="code-implementer", started_at=ts(20), ended_at=ts(30)),
        make_agent_run(agent_run_id="r3", agent_type="code-implementer", started_at=ts(25), ended_at=ts(35)),
    )
    calls = tuple(
        make_call(call_id=f"c{r.agent_run_id}", agent_run_id=r.agent_run_id, **tokens(1_000_000)) for r in runs
    )
    save(store, make_batch(agent_runs=runs, calls=calls))

    (found,) = rule(store, "repeated_implementers", Thresholds(min_repeats_per_task=1))

    assert found.evidence == {"tasks": 1, "repeats": 1, "cost_usd": "2.000000000"}


def test_expensive_agent_uses_the_peer_median(store: Store) -> None:
    sizes = {"cheap-a": 1_000_000, "cheap-b": 1_000_000, "pricey": 3_000_000}
    runs = tuple(make_agent_run(agent_run_id=name, agent_type=name) for name in sizes)
    calls = tuple(make_call(call_id=name, agent_run_id=name, **tokens(n)) for name, n in sizes.items())
    save(store, make_batch(agent_runs=runs, calls=calls))

    (found,) = rule(store, "expensive_agent", Thresholds(min_agent_runs=1))

    assert found.evidence["agent_type"] == "pricey"
    assert found.saving_usd == Decimal(4)  # one run at $6 against a $2 peer median


def test_red_test_loop_counts_runs_with_many_failures(store: Store) -> None:
    runs = (
        make_agent_run(agent_run_id="loop", agent_type="code-implementer", test_runs=9, test_failures=6),
        make_agent_run(agent_run_id="ok", agent_type="code-implementer", test_runs=4, test_failures=2),
    )
    calls = tuple(make_call(call_id=r.agent_run_id, agent_run_id=r.agent_run_id, **tokens(1_000_000)) for r in runs)
    save(store, make_batch(agent_runs=runs, calls=calls))

    (found,) = rule(store, "red_test_loop", Thresholds(red_loop_failures=5, min_red_loops=1))

    assert found.evidence == {"runs": 1, "min_failures": 5, "failures": 6, "cost_usd": "2.000000000",
                              "top_agent": "code-implementer"}
    assert found.saving_usd is None


def test_red_test_loop_stays_quiet_below_the_minimum(store: Store) -> None:
    run = make_agent_run(agent_run_id="loop", agent_type="code-implementer", test_runs=9, test_failures=6)
    save(store, make_batch(agent_runs=(run,), calls=(make_call(call_id="c", agent_run_id="loop", **tokens(10)),)))

    assert rule(store, "red_test_loop", Thresholds(red_loop_failures=5, min_red_loops=2)) == []


def test_untested_implementers_needs_changed_files_and_no_test(store: Store) -> None:
    runs = (
        make_agent_run(agent_run_id="blind", agent_type="flutter-implementer", files_touched=4, test_runs=0),
        make_agent_run(agent_run_id="read-only", agent_type="code-implementer", files_touched=0, test_runs=0),
        make_agent_run(agent_run_id="tested", agent_type="code-implementer", files_touched=3, test_runs=2),
        make_agent_run(agent_run_id="reviewer", agent_type="critic", files_touched=2, test_runs=0),
    )
    calls = tuple(make_call(call_id=r.agent_run_id, agent_run_id=r.agent_run_id, **tokens(1_000_000)) for r in runs)
    save(store, make_batch(agent_runs=runs, calls=calls))

    (found,) = rule(store, "untested_implementers", Thresholds(min_untested_runs=1))

    assert found.evidence == {"runs": 1, "implementer_runs": 3, "cost_usd": "2.000000000"}
    assert found.saving_usd is None


def test_outlier_tasks_reports_no_saving(store: Store) -> None:
    tasks = tuple(make_task(task_id=f"t{i}", seq_in_session=i) for i in range(10))
    calls = tuple(
        make_call(call_id=f"c{i}", task_id=f"t{i}", **tokens(9_000_000 if i == 0 else 100_000)) for i in range(10)
    )
    save(store, make_batch(tasks=tasks, calls=calls))

    (found,) = rule(store, "outlier_tasks", Thresholds())

    assert found.saving_usd is None
    assert found.evidence["top_tasks"] == 1
    assert found.evidence["costliest"][0]["task_id"] == "t0"


def test_model_what_if_reprices_the_same_tokens(store: Store) -> None:
    call = make_call(**{**tokens(1_000_000), "model": "claude-opus-5-5"})
    save(store, make_batch(calls=(call,)))

    (found,) = rule(store, "model_what_if", Thresholds())

    assert found.saving_usd == Decimal(2)  # $4 at Opus 5.5 against $2 at Sonnet 5.5
    assert "price only" in found.action


def test_calls_outside_the_window_do_not_count(store: Store) -> None:
    old = make_call(ts=ts(0) - timedelta(days=40), **tokens(1_000_000))
    save(store, make_batch(calls=(old,)))

    report = build_insights(store, as_of=AS_OF, limits=Thresholds(long_session_calls=1))

    assert report.insights == ()
    assert "No rule fired" in render_insights(report)


def test_same_data_and_date_give_identical_output(store: Store) -> None:
    calls = tuple(make_call(call_id=f"c{i}", ts=ts(i), **tokens(1_000_000)) for i in range(4))
    save(store, make_batch(sessions=(make_session(),), calls=calls))
    limits = Thresholds(long_session_calls=2, session_baseline_calls=1)

    first = json.dumps(insights_document(build_insights(store, as_of=AS_OF, limits=limits)), sort_keys=True)
    second = json.dumps(insights_document(build_insights(store, as_of=AS_OF, limits=limits)), sort_keys=True)

    assert first == second
    assert json.loads(first)["note"].startswith("Savings are estimates")


def test_report_opens_with_the_where_to_cut_section(store: Store) -> None:
    calls = tuple(make_call(call_id=f"c{i}", ts=ts(i), **tokens(1_000_000)) for i in range(4))
    save(store, make_batch(calls=calls))
    options = ReportOptions(date_from=AS_OF, date_to=AS_OF)
    insights = report_insights(store, options)
    assert insights is not None
    limited = build_insights(store, as_of=AS_OF, limits=Thresholds(long_session_calls=2, session_baseline_calls=1))

    html = build_report(store, options, insights=limited)

    assert (insights.date_from, insights.date_to) == (AS_OF, AS_OF)
    assert html.index('id="where-to-cut"') < html.index('id="overview"')
    assert "Estimated saving" in html


def test_report_omits_the_section_for_a_client_filter(store: Store) -> None:
    assert report_insights(store, ReportOptions(client="acme")) is None
