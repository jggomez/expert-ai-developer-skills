"""CLI wiring tests (PRD §7, contracts §3.9): exit codes, --json, and cross-track calls via fakes."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from agent_meter import cli
from agent_meter.locking import store_lock
from agent_meter.paths import AppHome
from agent_meter.store import Store
from tests.fixtures.antigravity import build_root
from tests.fixtures.canary import CANARY
from tests.fixtures.claude import ClaudeHome
from tests.fixtures.scenarios import agy_standard_conversations, claude_standard_session


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AppHome]:
    user = tmp_path / "user"
    monkeypatch.setenv("HOME", str(user))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.setenv("AGENT_METER_HOME", str(tmp_path / "meter"))
    ClaudeHome(user / ".claude").write(claude_standard_session())
    build_root(user / ".gemini" / "antigravity-cli", agy_standard_conversations())
    meter = AppHome.resolve()
    assert cli.main(["config", "set", "timezone", "UTC"]) == 0
    assert cli.main(["config", "set", "notify", "off"]) == 0
    yield meter


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def collected(capsys: pytest.CaptureFixture[str]) -> None:
    code, _out, _err = run(capsys, "collect")
    assert code == 0


# ----------------------------------------------------------------------------- basics


def test_help_and_usage_errors(home: AppHome, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(capsys, "--help")[0] == 0
    assert run(capsys, "no-such-command")[0] == 2
    assert run(capsys)[0] == 2


def test_config_show_get_set(home: AppHome, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(capsys, "config", "set", "usd_rate", "4100")[0] == 0

    code, out, _ = run(capsys, "config", "get", "usd_rate")
    show_code, show, _ = run(capsys, "config", "show", "--json")
    bad = run(capsys, "config", "set", "notify", "loud")

    assert (code, out.strip()) == (0, "4100")
    assert show_code == 0 and json.loads(show)["timezone"] == "UTC"
    assert bad[0] == 2 and "notify" in bad[2]


def test_collect_then_idempotent(home: AppHome, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "collect")
    again, out2, _ = run(capsys, "collect")
    quiet = run(capsys, "--quiet", "collect", "--full")

    assert (code, again) == (0, 0)
    assert "units" in out and "skipped" in out2
    assert quiet == (0, "", "")


def test_collect_locked_exit_codes(home: AppHome, capsys: pytest.CaptureFixture[str],
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "INTERACTIVE_LOCK_S", 0.1)
    monkeypatch.setattr(cli, "SCHEDULED_LOCK_S", 0.1)
    with store_lock(home.lock, exclusive=True, timeout_s=1.0):
        interactive = run(capsys, "collect")
        scheduled = run(capsys, "collect", "--scheduled")

    assert interactive[0] == 4 and "busy" in interactive[2]
    assert scheduled[0] == 0


def test_last_and_tasks(home: AppHome, capsys: pytest.CaptureFixture[str]) -> None:
    empty = run(capsys, "last")
    collected(capsys)

    code, out, _ = run(capsys, "last")
    jcode, jout, _ = run(capsys, "last", "--json")
    tcode, tout, _ = run(capsys, "tasks", "--last", "2")
    tj = run(capsys, "tasks", "--last", "--json")

    assert empty[0] == 0 and "No sessions yet" in empty[1]
    assert code == 0 and out.startswith("[agent-meter]")
    assert jcode == 0 and "session_id" in json.loads(jout)
    assert tcode == 0 and tout.count("[agent-meter]") == 2
    assert len(json.loads(tj[1])) == 1
    for text in (out, jout, tout, tj[1]):
        assert CANARY not in text


def test_task_label_only_on_interactive_terminal(home: AppHome, capsys: pytest.CaptureFixture[str],
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    collected(capsys)

    plain = run(capsys, "tasks", "--project", "demo-repo", "--last", "5")[1]
    monkeypatch.setattr(cli, "_is_tty", lambda: True)
    tty = run(capsys, "tasks", "--project", "demo-repo", "--last", "5")[1]
    run(capsys, "config", "set", "show_task_labels", "false")
    opted_out = run(capsys, "tasks", "--project", "demo-repo", "--last", "5")[1]

    assert 'task "please do the thing' not in plain
    assert 'task "please do the thing' in tty
    assert 'task "' not in opted_out


def test_pricing_commands(home: AppHome, capsys: pytest.CaptureFixture[str]) -> None:
    collected(capsys)
    unpriced = run(capsys, "pricing", "unpriced", "--json")

    add = run(capsys, "pricing", "add", "gemini-x-new", "--input", "1", "--output", "2", "--cache-read", "0.1")
    dup = run(capsys, "pricing", "add", "gemini-x-new", "--input", "1", "--output", "2", "--cache-read", "0.1")
    replaced = run(capsys, "pricing", "set", "gemini-x-new", "--input", "1.5", "--output", "2", "--cache-read", "0.1")
    alias = run(capsys, "pricing", "alias", "gemini-x-alias", "gemini-x-new", "--estimated")
    listing = run(capsys, "pricing", "list", "--json")
    valid = run(capsys, "pricing", "validate")
    removed = run(capsys, "pricing", "remove", "--alias", "gemini-x-alias")
    bad_price = run(capsys, "pricing", "add", "m", "--input", "-1", "--output", "2", "--cache-read", "0.1")

    assert unpriced[0] == 0 and isinstance(json.loads(unpriced[1]), list)
    assert add[0] == 0 and dup[0] == 1 and replaced[0] == 0 and alias[0] == 0
    rows = json.loads(listing[1])
    assert any(r["model"] == "gemini-x-new" and r["input"] == "1.5" and r["source"] == "local" for r in rows)
    assert valid[0] == 0 and removed[0] == 0
    assert bad_price[0] == 2


def test_pricing_validate_reports_errors(home: AppHome, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    broken = tmp_path / "p.yaml"
    broken.write_text("version: 1\nmodels: {m: {windows: [{effective_from: 2026-01-01, tiers: [{min_prompt_tokens: 0, input: 1.0}]}]}}\n",
                      encoding="utf-8")

    code, out, err = run(capsys, "pricing", "validate", str(broken))

    assert code == 1
    assert "quoted decimal" in out + err


def test_projects_set_list_merge(home: AppHome, capsys: pytest.CaptureFixture[str]) -> None:
    collected(capsys)
    listing = json.loads(run(capsys, "projects", "list", "--json")[1])
    pid = next(p["project_id"] for p in listing if p["display_name"] == "demo-repo")

    set_code = run(capsys, "projects", "set", "demo-repo", "--name", "Project X", "--client", "Client Z",
                   "--billing", "hourly", "--rate", "80000", "--currency", "COP")[0]
    after = json.loads(run(capsys, "projects", "list", "--json")[1])
    merge = run(capsys, "projects", "merge", pid, "git:ffffffffffffffff")
    unknown = run(capsys, "projects", "set", "nope", "--name", "x")

    assert set_code == 0
    assert any(p["display_name"] == "Project X" and p["client"] == "Client Z" for p in after)
    assert merge[0] == 0
    assert "git:ffffffffffffffff" in home.projects.read_text(encoding="utf-8")
    assert unknown[0] == 2


def test_projects_list_hides_orphan_projects_left_by_relocation(
    home: AppHome, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange: a stale identity (e.g. a pre-move path id) with no sessions, calls or overrides.
    collected(capsys)
    with Store.open(home, read_only=False, lock_timeout_s=5) as store:
        store.execute(
            "INSERT INTO projects (project_id, kind, display_name) VALUES (?, 'path', 'old-dir')",
            ["path:0000000000000000"],
        )

    # Act
    listing = json.loads(run(capsys, "projects", "list", "--json")[1])

    # Assert
    ids = {p["project_id"] for p in listing}
    assert "path:0000000000000000" not in ids
    assert "(unassigned)" in ids and any(p["display_name"] == "demo-repo" for p in listing)


def test_hours_and_tags(home: AppHome, capsys: pytest.CaptureFixture[str]) -> None:
    collected(capsys)

    hs = run(capsys, "hours", "set", "demo-repo", "2026-10-14", "6.5")
    hl = json.loads(run(capsys, "hours", "list", "--json")[1])
    bad = run(capsys, "hours", "set", "demo-repo", "2026-13", "1")
    hu = run(capsys, "hours", "unset", "demo-repo", "2026-10-14")
    tag = run(capsys, "tag", "Track 11", "--project", "demo-repo", "--last", "2")
    tagged = json.loads(run(capsys, "tasks", "--tag", "Track 11", "--json")[1])
    live = run(capsys, "tag", "Next", "--project", "demo-repo")
    clear = run(capsys, "tag", "--clear", "--project", "demo-repo")
    neither = run(capsys, "tag", "--project", "demo-repo")

    assert hs[0] == 0 and hl[0]["hours"] == "6.50" and hl[0]["source"] == "manual"
    assert bad[0] == 2 and hu[0] == 0
    assert tag[0] == 0 and len(tagged) == 2
    assert live[0] == 0 and clear[0] == 0 and neither[0] == 2


def test_doctor_reports_and_fails(home: AppHome, capsys: pytest.CaptureFixture[str],
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    import agent_meter.scheduler as scheduler
    from agent_meter.setup import settings_merge

    monkeypatch.setattr(scheduler, "status", lambda **_kw: "not_loaded")
    monkeypatch.setattr(settings_merge, "registration_status", lambda _path, _target: "absent")
    collected(capsys)

    code, out, _ = run(capsys, "doctor")
    jcode, jout, _ = run(capsys, "doctor", "--json")
    home.pricing_local.write_text("version: 7\n", encoding="utf-8")
    failing = run(capsys, "doctor")

    assert code == 0
    # The Antigravity no-model call is now priced via the default model (gemini-3.8-flash).
    assert "claude-code" in out and "every call priced" in out
    assert jcode == 0 and {c["status"] for c in json.loads(jout)} <= {"OK", "WARN", "FAIL"}
    assert failing[0] == 3 and "FAIL" in failing[1]


def test_doctor_reports_a_corrupt_secret_and_collect_refuses(home: AppHome, capsys: pytest.CaptureFixture[str],
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    import agent_meter.scheduler as scheduler
    from agent_meter.setup import settings_merge

    monkeypatch.setattr(scheduler, "status", lambda **_kw: "not_loaded")
    monkeypatch.setattr(settings_merge, "registration_status", lambda _path, _target: "absent")
    collected(capsys)
    home.secret.write_bytes(b"truncated")

    # Act
    doctor_code, doctor_out, _ = run(capsys, "doctor")
    collect_code, collect_out, collect_err = run(capsys, "collect")

    # Assert
    assert doctor_code == 3
    assert "FAIL" in doctor_out and "secret corrupt; anonymized ids would change" in doctor_out
    assert collect_code == 1 and "secret corrupt" in collect_out + collect_err
    assert home.secret.read_bytes() == b"truncated"


def test_report_writes_file(home: AppHome, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    collected(capsys)
    out_file = tmp_path / "r.html"

    code, out, _ = run(capsys, "report", "--out", str(out_file), "--month", "2026-10")
    bad = run(capsys, "report", "--month", "2026-13")

    assert code == 0 and out_file.exists() and str(out_file) in out
    assert CANARY not in out_file.read_text(encoding="utf-8")
    assert bad[0] == 2


def test_sync_requires_cloud_and_calls_sink(home: AppHome, capsys: pytest.CaptureFixture[str],
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_meter.sinks import bigquery

    seen: dict[str, Any] = {}

    def fake_sync(_home: object, _cfg: object, _store: object, **kw: object) -> object:
        seen.update(kw)
        return bigquery.SyncResult(status="ok", loads=(), backlog={})

    monkeypatch.setattr(bigquery, "sync", fake_sync)
    disabled = run(capsys, "sync")
    run(capsys, "config", "set", "bigquery.enabled", "true")
    run(capsys, "config", "set", "bigquery.project", "devhack-3f0c2")

    code = run(capsys, "sync", "--full-reload")[0]

    assert disabled[0] == 1 and "setup --cloud" in disabled[2]
    assert code == 0 and seen["full_reload"] is True


def test_setup_wiring_and_usage_errors(home: AppHome, capsys: pytest.CaptureFixture[str],
                                       monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_meter.setup import wizard

    captured: dict[str, Any] = {}

    def fake_run(options: wizard.SetupOptions, deps: wizard.SetupDeps) -> wizard.SetupResult:
        captured["options"], captured["deps"] = options, deps
        return wizard.SetupResult(ok=True, changed=False, config=deps.config, actions=())

    monkeypatch.setattr(wizard, "run_setup", fake_run)

    code = run(capsys, "setup", "--local", "--yes", "--hosts", "claude-code", "--triggers", "scheduler", "--no-backfill")[0]
    bad = run(capsys, "setup", "--yes", "--triggers", "sometimes")
    no_tty = run(capsys, "setup")

    assert code == 0
    options = captured["options"]
    assert options.mode == "local" and options.assume_yes and options.backfill is False
    assert [h.value for h in options.hosts] == ["claude-code"]
    assert captured["deps"].executable.is_absolute()
    assert bad[0] == 2 and no_tty[0] == 2


def test_uninstall_and_purge(home: AppHome, capsys: pytest.CaptureFixture[str],
                             monkeypatch: pytest.MonkeyPatch) -> None:
    import agent_meter.scheduler as scheduler
    from agent_meter.setup import settings_merge

    monkeypatch.setattr(settings_merge, "uninstall", lambda _home: ["restored ~/.claude/settings.json"])
    monkeypatch.setattr(scheduler, "uninstall", lambda _home, **_kw: "launchd scheduler removed")
    collected(capsys)

    code, out, _ = run(capsys, "uninstall", "--keep-scheduler")
    purge = run(capsys, "uninstall", "--purge", "--yes")

    assert code == 0 and "restored" in out and "launchd" not in out
    assert purge[0] == 0 and not home.root.exists()


@pytest.fixture()
def no_host_changes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stub the host-side uninstall steps and record whether they ran."""
    import agent_meter.scheduler as scheduler
    from agent_meter.setup import settings_merge

    calls: list[str] = []

    def fake_settings_uninstall(_home: AppHome) -> list[str]:
        calls.append("settings")
        return []

    monkeypatch.setattr(settings_merge, "uninstall", fake_settings_uninstall)
    monkeypatch.setattr(scheduler, "uninstall", lambda _home, **_kw: "scheduler removed")
    return calls


def test_purge_refuses_the_user_home_root(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                          monkeypatch: pytest.MonkeyPatch, no_host_changes: list[str]) -> None:
    # Arrange
    user = tmp_path / "user"
    user.mkdir()
    (user / "notes.txt").write_text("keep me", encoding="utf-8")
    monkeypatch.setenv("HOME", str(user))
    monkeypatch.setenv("AGENT_METER_HOME", str(user))

    # Act
    code, _out, err = run(capsys, "uninstall", "--purge", "--yes", "--keep-scheduler")

    # Assert
    assert code == 2
    assert "refusing to purge" in err and "home directory" in err
    assert (user / "notes.txt").read_text(encoding="utf-8") == "keep me"
    assert no_host_changes == []


def test_purge_refuses_unset_variable_style_path_equal_to_home(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
        no_host_changes: list[str]) -> None:
    # Arrange: AGENT_METER_HOME="$HOME/$UNSET" expands to "$HOME/"
    user = tmp_path / "user"
    user.mkdir()
    (user / "notes.txt").write_text("keep me", encoding="utf-8")
    monkeypatch.setenv("HOME", str(user))
    monkeypatch.setenv("AGENT_METER_HOME", f"{user}/")

    # Act
    code, _out, err = run(capsys, "uninstall", "--purge", "--yes", "--keep-scheduler")

    # Assert
    assert code == 2 and "home directory" in err
    assert (user / "notes.txt").exists()


def test_purge_refuses_a_dir_with_a_foreign_file_even_with_yes(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
        no_host_changes: list[str]) -> None:
    # Arrange
    fake_user = tmp_path / "fakeuser"
    (fake_user / "Documents").mkdir(parents=True)
    thesis = fake_user / "Documents" / "thesis.txt"
    thesis.write_text("chapter 1", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path / "real-user"))
    monkeypatch.setenv("AGENT_METER_HOME", str(fake_user))

    # Act
    code, _out, err = run(capsys, "uninstall", "--purge", "--yes", "--keep-scheduler")

    # Assert
    assert code == 2 and "Documents" in err
    assert thesis.read_text(encoding="utf-8") == "chapter 1"


def test_home_option_on_existing_foreign_dir_keeps_its_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    import os
    import stat

    documents = tmp_path / "Documents"
    documents.mkdir()
    os.chmod(documents, 0o755)
    monkeypatch.setenv("HOME", str(tmp_path / "user"))

    # Act
    code, _out, _err = run(capsys, "--home", str(documents), "config", "get", "timezone")

    # Assert
    assert code == 0
    assert stat.S_IMODE(os.stat(documents).st_mode) == 0o755


def test_verify_reconcile_detects_drift(home: AppHome, capsys: pytest.CaptureFixture[str]) -> None:
    collected(capsys)

    clean = run(capsys, "verify", "--reconcile", "--json")
    with Store.open(home, read_only=False, lock_timeout_s=1.0) as st:
        st.execute("UPDATE llm_calls SET output_tokens = output_tokens + 1 WHERE host = 'claude-code'")
    drift = run(capsys, "verify", "--reconcile")

    assert clean[0] == 0 and json.loads(clean[1]) == []
    assert drift[0] == 5 and "claude-code" in drift[1]


def test_hook_dispatch_always_zero(home: AppHome, monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"garbage")))
    monkeypatch.setattr("sys.stdout", out)

    code = cli.main(["--home", str(home.root), "hook", "--host", "antigravity", "--event", "task-end"])

    assert code == 0
    assert out.getvalue() == "{}\n"


def test_hook_worker_bad_args_is_usage(home: AppHome) -> None:
    assert cli.main(["hook-worker", "--host", "claude-code"]) == 2
