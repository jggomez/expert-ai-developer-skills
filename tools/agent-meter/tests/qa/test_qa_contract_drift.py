"""L2 end to end: "a new host version without a fixture fails loudly in doctor, not silently".

The unit suite proves the reader yields an unknown fingerprint and the store counts it; this
drives the real CLI (collect -> doctor) and asserts the user-visible WARN, plus RD-15's rule that
an unknown layout never becomes 0 tokens.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from agent_meter import cli
from agent_meter.store import Store
from tests.fixtures.antigravity import (
    PLANNER,
    USER_INPUT,
    AgyCall,
    AgyConversation,
    AgyStep,
    build_root,
)
from tests.fixtures.claude import ClaudeSession, usage
from tests.qa.conftest import QAWorld, make_world

pytestmark = pytest.mark.contract


def _doctor(capsys: pytest.CaptureFixture[str]) -> tuple[int, list[dict[str, str]]]:
    capsys.readouterr()
    code = cli.main(["doctor", "--json"])
    return code, json.loads(capsys.readouterr().out)


def _host_check(checks: list[dict[str, str]], host: str) -> dict[str, str]:
    return next(c for c in checks if c["check"] == host)


@pytest.fixture()
def empty_world(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> QAWorld:
    return make_world(tmp_path, monkeypatch, standard=False)  # type: ignore[arg-type]


def test_known_fixture_versions_report_ok(qa_world: QAWorld, capsys: pytest.CaptureFixture[str],
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_meter.setup import settings_merge

    monkeypatch.setattr(settings_merge, "registration_status", lambda _p, _t: "registered")
    assert cli.main(["collect"]) == 0

    _code, checks = _doctor(capsys)

    assert _host_check(checks, "claude-code")["status"] == "OK"
    assert "format changed" not in _host_check(checks, "claude-code")["message"]


def test_unknown_claude_version_makes_doctor_warn_format_changed(
    empty_world: QAWorld, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_meter.setup import settings_merge

    monkeypatch.setattr(settings_merge, "registration_status", lambda _p, _t: "registered")
    session = ClaudeSession("s-future", version="9.0.0")
    p = session.prompt(0, "fut-p")
    line = session.assistant(5, "fut-r", parent=p, use=usage(10, 5, cache_read=0))
    session.lines[-1]["brandNewTopLevelField"] = {"x": 1}
    assert line
    empty_world.write_claude(session)

    assert cli.main(["collect"]) == 0
    code, checks = _doctor(capsys)

    check = _host_check(checks, "claude-code")
    assert code in (0, 3)
    assert check["status"] in ("WARN", "FAIL")
    assert "format changed" in check["message"]
    with Store.open(empty_world.meter, read_only=True, lock_timeout_s=5.0) as st:
        # forward compatible: the call is still ingested with its real tokens
        assert st.query("SELECT input_tokens FROM llm_calls WHERE call_id = 'claude-code:fut-r'") == [
            {"input_tokens": 10}]


def test_changed_antigravity_layout_warns_and_never_writes_zero_tokens(
    empty_world: QAWorld, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_meter.setup import settings_merge

    monkeypatch.setattr(settings_merge, "registration_status", lambda _p, _t: "registered")
    conv = AgyConversation(
        conversation_id="c-drift", trajectory_id="t-drift",
        steps=[AgyStep(0, USER_INPUT, 0), AgyStep(1, PLANNER, 5, tokens=None)],
        calls=[AgyCall(0, usage_fields=(1, 7, 8))],  # renamed usage subfields: 2/3/5 gone
        transcript_tokens=False,
    )
    build_root(empty_world.agy_root, [conv])
    with sqlite3.connect(empty_world.agy_root / "conversations" / "c-drift.db") as con:
        con.execute("CREATE TABLE brand_new_table (x integer)")

    assert cli.main(["collect"]) == 0
    _code, checks = _doctor(capsys)

    check = _host_check(checks, "antigravity-cli")
    assert check["status"] in ("WARN", "FAIL")
    assert "format changed" in check["message"] or "skipped or corrupt" in check["message"]
    with Store.open(empty_world.meter, read_only=True, lock_timeout_s=5.0) as st:
        zeros = st.query("SELECT COUNT(*) AS n FROM llm_calls WHERE input_tokens = 0 OR output_tokens = 0")
        unknown = st.query("SELECT COUNT(*) AS n FROM llm_calls WHERE session_id = 'c-drift' AND input_tokens IS NULL")
        diag = st.query("SELECT COUNT(*) AS n FROM diagnostics WHERE host = 'antigravity-cli'")
    assert zeros == [{"n": 0}]
    # the call is either kept with unknown (NULL) tokens or reported as a diagnostic — never silent
    assert unknown[0]["n"] or diag[0]["n"], (unknown, diag)
