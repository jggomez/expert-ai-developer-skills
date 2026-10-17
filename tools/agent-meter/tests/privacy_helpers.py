"""SQL-level privacy checks over a DuckDB store (PV-01 / PV-05, compliance finding M-1).

DuckDB compresses strings (FSST / dictionary), so grepping the raw ``.duckdb`` bytes can
report "clean" while clear text sits in a column. These helpers instead read every value
of every base table through SQL (``CAST(col AS VARCHAR)``), which decompresses them. Keep
the raw-byte grep as a second, cheap layer; it is not sufficient on its own.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

import duckdb

from agent_meter.store import Store

__all__ = ["CLEAR_TEXT_PATHS", "assert_store_free_of", "store_values_containing"]

CLEAR_TEXT_PATHS: Final = ("/Users/dev/work/demo-repo",)
"""Clear-text working-directory paths planted by the fixtures; they must never be stored."""

_HITS_PER_COLUMN: Final = 3

Rows = list[tuple[object, ...]]
QueryFn = Callable[[str, Sequence[object]], Rows]


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _scan(query: QueryFn, needles: Sequence[str]) -> list[tuple[str, str, str]]:
    columns = query(
        "SELECT c.table_schema, c.table_name, c.column_name "
        "FROM information_schema.columns AS c "
        "JOIN information_schema.tables AS t "
        "  ON t.table_catalog = c.table_catalog AND t.table_schema = c.table_schema "
        "  AND t.table_name = c.table_name "
        "WHERE t.table_type = 'BASE TABLE' AND c.table_catalog = current_database() "
        "ORDER BY c.table_schema, c.table_name, c.ordinal_position",
        (),
    )
    if not columns:
        raise AssertionError("privacy scan found no base-table columns; is this the right store?")
    hits: list[tuple[str, str, str]] = []
    for schema, table, column in columns:
        value = f"CAST({_quote(str(column))} AS VARCHAR)"
        source = f"{_quote(str(schema))}.{_quote(str(table))}"
        for needle in needles:
            rows = query(
                f"SELECT {value} FROM {source} WHERE contains({value}, ?) LIMIT {_HITS_PER_COLUMN}",
                (needle,),
            )
            hits.extend((str(table), str(column), str(row[0])) for row in rows)
    return hits


def store_values_containing(source: Path | Store, *needles: str) -> list[tuple[str, str, str]]:
    """Every ``(table, column, value)`` whose text form contains one of ``needles``.

    ``source`` is a ``.duckdb`` file (opened read-only) or an already open :class:`Store`
    (DuckDB refuses a second connection to a file the same process holds read-write).
    """
    if not needles:
        raise ValueError("store_values_containing needs at least one needle")
    if isinstance(source, Store):
        def store_query(sql: str, params: Sequence[object]) -> Rows:
            return [tuple(row.values()) for row in source.query(sql, params)]

        return _scan(store_query, needles)
    con = duckdb.connect(str(source), read_only=True)
    try:
        def file_query(sql: str, params: Sequence[object]) -> Rows:
            return con.execute(sql, list(params)).fetchall()

        return _scan(file_query, needles)
    finally:
        con.close()


def assert_store_free_of(source: Path | Store, *needles: str) -> None:
    """Fail listing ``table.column = value`` when any stored value contains a needle."""
    hits = store_values_containing(source, *needles)
    if hits:
        listed = "; ".join(f"{table}.{column} = {value[:80]!r}" for table, column, value in hits[:10])
        raise AssertionError(f"{len(hits)} stored value(s) contain forbidden text: {listed}")
