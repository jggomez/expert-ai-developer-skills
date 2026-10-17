"""Proves the SQL-level privacy dump catches what a raw ``.duckdb`` byte grep misses (M-1)."""

from __future__ import annotations

import secrets
from pathlib import Path

import duckdb
import pytest

from tests.fixtures.canary import CANARY
from tests.privacy_helpers import assert_store_free_of, store_values_containing

HIGH_CARDINALITY_ROWS = 20_000


def _compressed_canary_store(path: Path) -> None:
    """20,000 distinct canary-bearing strings: DuckDB compresses them (FSST) after CHECKPOINT."""
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE TABLE notes (id INTEGER, body VARCHAR)")
        con.execute(
            "INSERT INTO notes SELECT i, ? || '-' || i || '-' || md5(? || i) FROM range(?) AS r(i)",
            [CANARY, secrets.token_hex(8), HIGH_CARDINALITY_ROWS],
        )
        con.execute("CHECKPOINT")
    finally:
        con.close()


def test_sql_dump_catches_canary_hidden_from_raw_bytes(tmp_path: Path) -> None:
    # Arrange
    db = tmp_path / "synthetic.duckdb"
    _compressed_canary_store(db)

    # Act
    raw_bytes_contain_canary = CANARY.encode() in db.read_bytes()
    hits = store_values_containing(db, CANARY)

    # Assert
    assert raw_bytes_contain_canary is False  # the gap: a byte grep reports "clean"
    assert hits and hits[0][:2] == ("notes", "body")
    with pytest.raises(AssertionError, match=r"notes\.body"):
        assert_store_free_of(db, CANARY)


def test_sql_dump_checks_non_text_columns_and_passes_a_clean_store(tmp_path: Path) -> None:
    # Arrange
    db = tmp_path / "clean.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE facts (id INTEGER, tags VARCHAR[], amount DECIMAL(18, 2))")
    con.execute("INSERT INTO facts VALUES (1, ['alpha', 'beta'], 1.25)")
    con.close()

    # Act
    tag_hits = store_values_containing(db, "beta")

    # Assert
    assert [(table, column) for table, column, _value in tag_hits] == [("facts", "tags")]
    assert_store_free_of(db, CANARY, "/Users/dev/work/demo-repo")
