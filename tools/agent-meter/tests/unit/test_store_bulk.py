"""Large batches go through a bulk CSV load, which must store exactly what small batches store."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from agent_meter import store as store_module
from agent_meter.paths import AppHome
from agent_meter.store import Store
from tests.fixtures.records import make_batch, make_call

TRICKY_TEXT = ['plain', '', 'a,b', 'say "hi"', 'line\nbreak', 'cr\r\nlf', 'ñandú ✓', ' spaced ', 'NULL', "it's", '\\back']
COLUMNS = ["t TEXT", "n BIGINT", "flag BOOLEAN", "moment TIMESTAMPTZ", "price DECIMAL(12, 6)", "day DATE"]
NAMES = ("t", "n", "flag", "moment", "price", "day")


def rows() -> list[list[object]]:
    moment = datetime(2026, 11, 5, 12, 30, 15, 123456, tzinfo=UTC)
    bogota = timezone(timedelta(hours=-5))
    found: list[list[object]] = [
        [text, index, index % 2 == 0, moment + timedelta(microseconds=index), Decimal("1.250000"), moment.date()]
        for index, text in enumerate(TRICKY_TEXT)
    ]
    found.append([None, None, None, None, None, None])
    found.append(["other zone", 2**40, False, moment.astimezone(bogota), Decimal("0.000001"), None])
    return found


@pytest.fixture()
def store(tmp_path: Path) -> Iterator[Store]:
    with Store.open(AppHome.resolve(str(tmp_path / "h")), read_only=False, lock_timeout_s=1.0) as opened:
        opened.migrate()
        yield opened


def stored(store: Store, table: str) -> list[tuple[object, ...]]:
    return [tuple(row.values()) for row in store.query(f"SELECT * FROM {table} ORDER BY n NULLS LAST, t NULLS LAST")]


def test_bulk_load_stores_exactly_what_row_inserts_store(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    store.execute(f"CREATE TEMP TABLE by_row ({', '.join(COLUMNS)})")
    store.execute(f"CREATE TEMP TABLE by_bulk ({', '.join(COLUMNS)})")

    store._insert_rows("by_row", NAMES, rows())
    monkeypatch.setattr(store_module, "_BULK_ROWS", 1)
    store._insert_rows("by_bulk", NAMES, rows())

    assert stored(store, "by_bulk") == stored(store, "by_row")


def test_bulk_load_keeps_null_apart_from_empty_text(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    store.execute("CREATE TEMP TABLE texts (t TEXT)")
    monkeypatch.setattr(store_module, "_BULK_ROWS", 1)

    store._insert_rows("texts", ("t",), [[""], [None]])

    assert store.query("SELECT COUNT(*) AS n FROM texts WHERE t IS NULL")[0]["n"] == 1
    assert store.query("SELECT COUNT(*) AS n FROM texts WHERE t = ''")[0]["n"] == 1


def test_bulk_load_leaves_no_temporary_file(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    store.execute("CREATE TEMP TABLE texts (t TEXT)")
    monkeypatch.setattr(store_module, "_BULK_ROWS", 1)

    store._insert_rows("texts", ("t",), [["a"], ["b"]])

    assert not [p for p in store._home.state_dir.iterdir() if p.name.startswith("bulk-")]


def test_a_failed_bulk_load_also_cleans_up(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    store.execute("CREATE TEMP TABLE numbers (n BIGINT)")
    monkeypatch.setattr(store_module, "_BULK_ROWS", 1)

    with pytest.raises(Exception, match=r"(?i)convert|cast"):
        store._insert_rows("numbers", ("n",), [["not a number"], ["x"]])

    assert not [p for p in store._home.state_dir.iterdir() if p.name.startswith("bulk-")]


def many_calls() -> tuple[object, ...]:
    return tuple(make_call(call_id=f"claude-code:req-{i}", ts=datetime(2026, 11, 5, tzinfo=UTC) + timedelta(seconds=i),
                           model_label='lab"el,\n' if i % 2 else None) for i in range(30))


def test_rows_written_by_row_inserts_are_not_rewritten_by_a_bulk_load(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    batch = make_batch(calls=many_calls())
    first = store.apply_batches([batch])

    monkeypatch.setattr(store_module, "_BULK_ROWS", 1)
    second = store.apply_batches([batch])

    assert first.calls_changed == 30
    assert second.calls_changed == 0
