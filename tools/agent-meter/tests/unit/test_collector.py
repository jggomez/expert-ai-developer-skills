"""Collector tests over 11A's fake hosts: idempotency, skip-unchanged, locking, signals, robustness."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agent_meter.collector import collect, reader_roots
from agent_meter.config import Config, HostConfig
from agent_meter.locking import store_lock
from agent_meter.model import (
    Host,
    ReaderOptions,
    SessionUnit,
    UnitBatch,
    UntrackedRecord,
)
from agent_meter.paths import AppHome
from agent_meter.readers.base import HostReader, available_readers
from agent_meter.store import Store
from tests.fixtures.antigravity import build_root
from tests.fixtures.canary import CANARY
from tests.fixtures.claude import ClaudeHome
from tests.fixtures.records import make_unit
from tests.fixtures.scenarios import (
    CLAUDE_SESSION_ID,
    agy_standard_conversations,
    claude_standard_session,
)
from tests.privacy_helpers import CLEAR_TEXT_PATHS, assert_store_free_of

NOW = datetime(2026, 10, 16, 16, 0, tzinfo=UTC)


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[AppHome, dict[Host, Path]]]:
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    claude = ClaudeHome(tmp_path / "user" / ".claude")
    claude.write(claude_standard_session())
    roots = {
        Host.CLAUDE_CODE: claude.root,
        Host.ANTIGRAVITY_CLI: build_root(tmp_path / "user" / ".gemini" / "antigravity-cli", agy_standard_conversations()),
    }
    yield AppHome.resolve(str(tmp_path / "meter")), roots


def cfg_for(roots: dict[Host, Path]) -> Config:
    hosts = {h: HostConfig(enabled=h in roots, root=roots.get(h)) for h in Host}
    return Config(timezone="UTC", hosts=hosts)


def run(home: AppHome, roots: dict[Host, Path], **kwargs: object) -> object:
    return collect(home, cfg_for(roots), now=NOW, **kwargs)  # type: ignore[arg-type]


def counts(home: AppHome) -> dict[str, int]:
    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        return {
            t: int(st.query(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"])  # type: ignore[call-overload]
            for t in ("sessions", "tasks", "agent_runs", "llm_calls", "tool_uses")
        }


def test_collect_ingests_both_hosts_with_shared_project(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env

    result = collect(home, cfg_for(roots), now=NOW)

    assert result.status == "ok"
    assert result.stats is not None and result.stats.calls_changed > 0
    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        projects = st.query("SELECT DISTINCT host, project_id FROM sessions ORDER BY host")
    assert {p["host"] for p in projects} == {"claude-code", "antigravity-cli"}
    assert len({p["project_id"] for p in projects}) == 1  # PR-01: same repo from both hosts
    assert str(projects[0]["project_id"]).startswith("path:")


def test_st01_second_run_skips_unchanged_units(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env
    first = collect(home, cfg_for(roots), now=NOW)
    before = counts(home)

    second = collect(home, cfg_for(roots), now=NOW)
    full = collect(home, cfg_for(roots), now=NOW, full=True)

    assert first.units_skipped_unchanged == 0
    assert second.units_skipped_unchanged >= 2
    assert second.stats is not None and second.stats.units == 0
    assert full.stats is not None and full.stats.calls_changed == 0 and full.stats.units >= 2
    assert counts(home) == before


def test_st03_changed_unit_is_reread(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env
    collect(home, cfg_for(roots), now=NOW)
    session = claude_standard_session()
    p3 = session.prompt(3000, "p3")
    session.assistant(3005, "r-new", parent=p3)
    ClaudeHome(roots[Host.CLAUDE_CODE]).write(session)

    result = collect(home, cfg_for(roots), now=NOW)

    assert result.stats is not None and result.stats.calls_changed == 1
    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        assert st.query("SELECT COUNT(*) AS n FROM tasks WHERE task_id = 'claude-code:p3'") == [{"n": 1}]


def test_st04_locked_store_returns_locked(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env

    with store_lock(home.lock, exclusive=True, timeout_s=1.0):
        result = collect(home, cfg_for(roots), now=NOW, lock_timeout_s=0.1)

    assert result.status == "locked"
    assert result.stats is None


def test_only_ingests_a_single_unit(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env

    result = collect(home, cfg_for(roots), now=NOW, only=(Host.CLAUDE_CODE, CLAUDE_SESSION_ID))

    assert result.status == "ok"
    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        assert st.query("SELECT DISTINCT host FROM sessions") == [{"host": "claude-code"}]


def test_only_child_conversation_maps_to_root_unit(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env

    collect(home, cfg_for(roots), now=NOW, only=(Host.ANTIGRAVITY_CLI, "c-child2"))

    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        assert st.query("SELECT session_id FROM sessions") == [{"session_id": "c-root"}]


def test_session_end_signal_marks_last_task_done_and_survives_reingest(
    env: tuple[AppHome, dict[Host, Path]],
) -> None:
    home, roots = env
    soon = datetime(2026, 10, 16, 14, 40, tzinfo=UTC)  # last event of the fixture is < 30 min earlier
    collect(home, cfg_for(roots), now=soon)
    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        open_status = st.query("SELECT status FROM tasks WHERE task_id = 'claude-code:p2'")

    collect(home, cfg_for(roots), now=soon, only=(Host.CLAUDE_CODE, CLAUDE_SESSION_ID), signal="session-end")
    collect(home, cfg_for(roots), now=soon, full=True)

    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        task = st.query("SELECT status FROM tasks WHERE task_id = 'claude-code:p2'")
        session = st.query("SELECT status FROM sessions WHERE session_id = ?", [CLAUDE_SESSION_ID])
    assert open_status == [{"status": "in_progress"}]
    assert task == [{"status": "done"}]
    assert session == [{"status": "closed"}]


def test_since_skips_units_not_modified_after_date(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env
    future = (datetime.now(UTC) + timedelta(days=2)).date()

    result = collect(home, cfg_for(roots), now=NOW, since=future)

    assert result.stats is not None and result.stats.units == 0


def test_disabled_and_filtered_hosts_are_skipped(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env

    collect(home, cfg_for(roots), now=NOW, hosts=[Host.ANTIGRAVITY_CLI])

    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        assert st.query("SELECT DISTINCT host FROM sessions") == [{"host": "antigravity-cli"}]


def test_reader_roots_honour_config_overrides(tmp_path: Path) -> None:
    cfg = Config(timezone="UTC", hosts={
        **{h: HostConfig() for h in Host},
        Host.CLAUDE_CODE: HostConfig(root=tmp_path / "cc"),
        Host.ANTIGRAVITY_IDE: HostConfig(enabled=False),
    })

    roots = reader_roots(cfg)

    assert roots[Host.CLAUDE_CODE] == tmp_path / "cc"
    assert Host.ANTIGRAVITY_IDE not in roots


class _ExplodingReader:
    host = Host.CLAUDE_CODE
    root = Path("/nonexistent")

    def discover(self) -> Iterator[SessionUnit]:
        yield make_unit(unit_id="boom")

    def find_unit(self, session_or_conversation_id: str) -> SessionUnit | None:
        return None

    def read_unit(self, unit: SessionUnit, options: ReaderOptions) -> UnitBatch:
        raise KeyError("bug with a secret path /Users/dev/" + CANARY)

    def untracked(self) -> list[UntrackedRecord]:
        return []

    def earliest_available(self) -> None:
        return None


def test_unexpected_reader_error_becomes_diagnostic(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env
    readers: list[HostReader] = [_ExplodingReader(), *available_readers(roots)]

    result = collect(home, cfg_for(roots), now=NOW, readers=readers)

    assert result.status == "ok"
    assert any(d.error_class == "KeyError" for d in result.diagnostics)
    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        assert st.query("SELECT kind, error_class FROM diagnostics WHERE error_class = 'KeyError'") == [
            {"kind": "corrupt", "error_class": "KeyError"}
        ]
        assert st.query("SELECT COUNT(*) AS n FROM sessions")[0]["n"] == 3  # c-root, c-other, Claude


def test_br15_vanished_transcript_keeps_rows(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env
    collect(home, cfg_for(roots), now=NOW)
    before = counts(home)
    for path in roots[Host.CLAUDE_CODE].rglob("*.jsonl"):
        path.unlink()

    collect(home, cfg_for(roots), now=NOW, full=True)

    assert counts(home) == before


def test_pc07_invalid_local_pricing_keeps_previous_table(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env
    collect(home, cfg_for(roots), now=NOW)
    home.pricing_local.write_text("version: 1\nmodels: {broken: {windows: []}}\n", encoding="utf-8")

    result = collect(home, cfg_for(roots), now=NOW)

    assert result.status == "ok"
    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        assert st.query("SELECT COUNT(*) AS n FROM pricing")[0]["n"] > 0  # type: ignore[operator]
        assert st.get_meta("pricing_error") is not None


def test_pv01_canary_never_reaches_the_store_file(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env

    collect(home, cfg_for(roots), now=NOW)

    assert_store_free_of(home.db, CANARY, *CLEAR_TEXT_PATHS)  # layer 1: every stored value via SQL
    assert CANARY.encode() not in home.db.read_bytes()  # layer 2: raw bytes
    assert CANARY not in home.snapshot.read_text(encoding="utf-8")
    assert b"/Users/dev/work/demo-repo" not in home.db.read_bytes()


def test_invalid_projects_yaml_returns_error(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env
    home.projects.write_text("version: 2\n", encoding="utf-8")

    result = collect(home, cfg_for(roots), now=NOW)

    assert result.status == "error"
    assert result.message is not None and "projects.yaml" in result.message


def test_snapshot_and_meta_written(env: tuple[AppHome, dict[Host, Path]]) -> None:
    home, roots = env

    collect(home, replace(cfg_for(roots), timezone="America/Bogota"), now=NOW)

    assert home.snapshot.exists()
    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        assert st.get_meta("last_collect_at") == NOW.isoformat()
        assert st.query("SELECT value FROM settings WHERE key = 'timezone'") == [{"value": "America/Bogota"}]
