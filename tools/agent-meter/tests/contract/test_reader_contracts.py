"""Reader contract tests (L2): format fingerprints, RD-14 decoding contract, PV-01 and PV-03.

Each supported host format version has a fixture here; a new format without a fixture
yields a fingerprint outside ``KNOWN_FORMATS`` (doctor reports "format changed").
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from agent_meter.model import Host, UnitBatch
from agent_meter.readers import antigravity as agy
from agent_meter.readers import claude_code as cc
from agent_meter.readers.base import available_readers
from tests.fixtures.antigravity import build_root
from tests.fixtures.canary import CANARY
from tests.fixtures.claude import ClaudeHome
from tests.fixtures.records import make_options
from tests.fixtures.scenarios import agy_standard_conversations, claude_standard_session

pytestmark = pytest.mark.contract


@pytest.fixture()
def hosts(tmp_path: Path) -> dict[Host, Path]:
    claude = ClaudeHome(tmp_path / ".claude")
    claude.write(claude_standard_session())
    conversations = agy_standard_conversations()
    return {
        Host.CLAUDE_CODE: claude.root,
        Host.ANTIGRAVITY_CLI: build_root(
            tmp_path / ".gemini" / "antigravity-cli", conversations
        ),
        Host.ANTIGRAVITY_IDE: build_root(
            tmp_path / ".gemini" / "antigravity-ide", conversations[:1], summaries=False
        ),
    }


def all_batches(roots: dict[Host, Path]) -> Iterator[UnitBatch]:
    for reader in available_readers(roots):
        for unit in reader.discover():
            yield reader.read_unit(unit, make_options(description_salt=b"salt"))


def strings_in(value: object) -> Iterator[str]:
    """Every string reachable from a record (dataclass fields, tuples, enums, dates)."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        for f in dataclasses.fields(value):
            yield from strings_in(getattr(value, f.name))
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from strings_in(item)
    elif value is not None:
        yield str(value)


def test_canary_is_planted_in_fixture_files(hosts: dict[Host, Path]) -> None:
    planted = [
        p
        for root in hosts.values()
        for p in root.rglob("*")
        if p.is_file() and CANARY.encode() in p.read_bytes()
    ]

    assert any(p.suffix == ".jsonl" for p in planted)
    assert any(p.suffix == ".db" for p in planted)
    assert any(p.name.endswith(".meta.json") for p in planted)


def test_pv01_readers_never_surface_the_canary(hosts: dict[Host, Path]) -> None:
    batches = list(all_batches(hosts))
    untracked = [r for reader in available_readers(hosts) for r in reader.untracked()]

    leaked = [s for b in batches for s in strings_in(b) if CANARY in s]
    leaked += [s for s in strings_in(untracked) if CANARY in s]

    assert {b.unit.host for b in batches} == set(hosts)
    assert sum(len(b.calls) for b in batches) > 10
    assert leaked == []


def test_pv03_readers_do_not_modify_host_files(hosts: dict[Host, Path]) -> None:
    def snapshot() -> dict[Path, tuple[int, str]]:
        return {
            p: (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
            for root in hosts.values()
            for p in root.rglob("*")
            if p.is_file()
        }

    before = snapshot()
    list(all_batches(hosts))
    for reader in available_readers(hosts):
        reader.untracked()
        reader.earliest_available()

    assert snapshot() == before


def test_fixture_formats_are_known(hosts: dict[Host, Path]) -> None:
    for batch in all_batches(hosts):
        known = (
            cc.KNOWN_FORMATS
            if batch.unit.host is Host.CLAUDE_CODE
            else agy.KNOWN_FORMATS
        )
        assert batch.format_fingerprint in known, batch.unit.host


def own_trajectory(db: Path) -> str:
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as con:
        row = con.execute("SELECT trajectory_id FROM trajectory_meta").fetchone()
    return str(row[0])


def test_rd14_gen_metadata_tokens_equal_transcript_planner_tokens(
    hosts: dict[Host, Path],
) -> None:
    root = hosts[Host.ANTIGRAVITY_CLI]
    reader = agy.AntigravityReader(Host.ANTIGRAVITY_CLI, root)
    compared = 0
    for unit in reader.discover():
        owned = {
            c.call_id: c
            for c in reader.read_unit(unit, make_options()).calls
            if c.owner_rank == "0"
        }
        for cid in (unit.unit_id, *unit.member_ids):
            transcript = root / "brain" / cid / agy.TRANSCRIPT_REL
            db = root / "conversations" / f"{cid}.db"
            if not transcript.is_file() or not db.is_file():
                continue
            trajectory = own_trajectory(db)
            for raw in transcript.read_text(encoding="utf-8").splitlines():
                step = json.loads(raw)
                if step["type"] != "PLANNER_RESPONSE" or "input_tokens" not in step:
                    continue
                call = owned.get(
                    f"antigravity-cli:{trajectory}:{step['step_index'] - 1}"
                )  # step = last_step_index + 1
                if call is None:
                    continue
                compared += 1
                assert (
                    call.input_tokens,
                    call.cache_read_tokens,
                    call.output_tokens,
                ) == (
                    step["input_tokens"],
                    step["cache_read_tokens"],
                    step["output_tokens"],
                )

    assert compared >= 4


def test_contract_record_ids_follow_i9_formats(hosts: dict[Host, Path]) -> None:
    for batch in all_batches(hosts):
        host = batch.unit.host.value
        for call in batch.calls:
            assert call.call_id.startswith(f"{host}:")
        for run in batch.agent_runs:
            assert (
                run.agent_run_id == f"{run.task_id}:main"
                or run.agent_run_id.startswith(f"{host}:agent:")
            )
        for task in batch.tasks:
            assert task.task_id.startswith(f"{host}:")
        assert all(s.session_id == batch.unit.unit_id for s in batch.sessions)
