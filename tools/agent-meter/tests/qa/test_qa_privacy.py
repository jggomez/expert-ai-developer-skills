"""PV-01 / PV-03 / PV-04 sweep over EVERY CLI command (L7 privacy, synthetic data only).

The canary ``AGENT-METER-CANARY-7f3a`` is planted by the fixtures in prompts, assistant text,
thinking, tool inputs/outputs, file paths, git branch, slugs, subagent descriptions, Antigravity
step payloads, gen_metadata prompt fields and ``cli.log``. It must never appear in:
the store directory (DuckDB file, snapshot, config, backups, install manifest), outbox NDJSON,
the HTML report, ``last-summary.txt``, ``logs/``, or stdout/stderr of any command.
Hosts are read-only: transcripts' bytes and mtimes are unchanged (PV-03).
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from pathlib import Path

import pytest

from agent_meter import cli
from agent_meter.store import Store
from tests.fixtures.antigravity import build_root
from tests.fixtures.canary import CANARY
from tests.fixtures.claude import ClaudeHome
from tests.fixtures.scenarios import (
    CLAUDE_SESSION_ID,
    agy_standard_conversations,
    claude_standard_session,
)
from tests.qa.conftest import QAWorld, agent_meter_argv, make_world

pytestmark = pytest.mark.privacy

CANARY_B = CANARY.encode()


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _digests(*roots: Path) -> dict[str, tuple[str, int]]:
    return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for root in roots for p in root.rglob("*") if p.is_file()}


def _leaks(files: dict[str, bytes], needles: tuple[bytes, ...]) -> list[str]:
    return [f"{name}: {needle!r}" for name, data in files.items() for needle in needles if needle in data]


def _sweep(world: QAWorld, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture,
           monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[tuple[list[str], int, str]]:
    """Run every CLI command (and the real hook/worker subprocesses); return (argv, code, output)."""
    from agent_meter.setup import settings_merge
    from agent_meter.sinks import bigquery

    def offline(_project: str, _location: str) -> object:
        raise OSError("network unreachable")

    monkeypatch.setattr(bigquery, "google_gateway", offline)
    monkeypatch.setattr(settings_merge, "registration_status", lambda _p, _t: "registered")
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    pid_holder: dict[str, str] = {}

    def project_id() -> str:
        if "pid" not in pid_holder:
            with Store.open(world.meter, read_only=True, lock_timeout_s=5.0) as st:
                pid_holder["pid"] = str(st.query(
                    "SELECT project_id FROM projects WHERE display_name = 'demo-repo'")[0]["project_id"])
        return pid_holder["pid"]

    plan: list[list[str] | object] = [
        ["--version"], ["--help"], ["setup", "--local", "--yes"], ["collect"], ["collect", "--full"],
        ["collect", "--host", "claude-code"], ["collect", "--since", "2026-10-01"], ["--quiet", "collect", "--scheduled"],
        ["last"], ["last", "--json"], ["last", "--project", "demo-repo"],
        ["tasks"], ["tasks", "--json"], ["tasks", "--last", "5"], ["tasks", "--session", CLAUDE_SESSION_ID, "--json"],
        ["tasks", "--project", "demo-repo", "--since", "2026-10-01"],
        ["report", "--out", str(report_dir / "all.html")], ["report", "--month", "2026-10", "--out", str(report_dir / "m.html")],
        ["report", "--project", "demo-repo", "--from", "2026-10-01", "--to", "2026-10-31", "--out", str(report_dir / "p.html")],
        ["projects", "list"], ["projects", "list", "--json"],
        lambda: ["projects", "set", project_id(), "--name", "Demo", "--client", "Acme", "--billing", "hourly",
                 "--rate", "80", "--currency", "USD"],
        ["hours", "set", "Demo", "2026-10", "12.5"], ["hours", "list"], ["hours", "list", "--json"],
        ["hours", "unset", "Demo", "2026-10"],
        ["tag", "Track 11", "--project", "Demo", "--last", "2"], ["tasks", "--tag", "Track 11", "--json"],
        ["tag", "--clear", "--project", "Demo"],
        ["doctor"], ["doctor", "--json"],
        ["config", "show"], ["config", "show", "--json"], ["config", "get", "timezone"],
        ["pricing", "list"], ["pricing", "list", "--json"], ["pricing", "unpriced"], ["pricing", "unpriced", "--json"],
        ["pricing", "add", "qa-model-x", "--input", "1", "--output", "2", "--cache-read", "0.1"],
        ["pricing", "set", "qa-model-x", "--input", "1.5", "--output", "2", "--cache-read", "0.1"],
        ["pricing", "alias", "qa-alias-x", "qa-model-x", "--estimated"],
        ["pricing", "validate"], ["pricing", "remove", "--alias", "qa-alias-x"], ["pricing", "remove", "--model", "qa-model-x"],
        ["verify", "--reconcile", "--from", "2026-10-01", "--to", "2026-10-31"],
        ["verify", "--reconcile", "--json", "--from", "2026-10-01", "--to", "2026-10-31"],
        ["config", "set", "bigquery.project", "qa-test-project"], ["config", "set", "bigquery.enabled", "true"],
        ["sync", "--dry-run"], ["sync"], ["sync", "--full-reload"], ["--quiet", "collect", "--scheduled"],
        ["config", "set", "bigquery.enabled", "false"],
        ["hook-worker", "--host", "claude-code", "--event", "session-end", "--session-id", CLAUDE_SESSION_ID],
        ["hook-worker", "--host", "antigravity", "--event", "task-end", "--session-id", "c-root", "--fully-idle", "true"],
        ["projects", "merge", "Demo", "Demo"],
        ["uninstall"],
    ]
    results: list[tuple[list[str], int, str]] = []
    with caplog.at_level(logging.DEBUG):
        for item in plan:
            argv: list[str] = item() if callable(item) else item  # type: ignore[assignment]
            capsys.readouterr()
            code = cli.main(argv)
            out = capsys.readouterr()
            results.append((argv, code, out.out + out.err))
    results.append((["<log records>"], 0, "\n".join(r.getMessage() + str(r.args) for r in caplog.records)))

    # Real subprocesses: the hook fast path (both hosts), a worker with a broken config (writes
    # logs/hook.log), and a scheduled collect redirected to logs/scheduler.log as launchd does.
    payloads = [
        (["hook", "--host", "claude-code", "--event", "task-end"],
         {"session_id": CLAUDE_SESSION_ID, "last_assistant_message": CANARY, "prompt": CANARY, "cwd": f"/{CANARY}"}),
        (["hook", "--host", "antigravity", "--event", "task-end"],
         {"conversationId": "c-root", "fullyIdle": True, "prompt": CANARY, "workspacePaths": [f"/{CANARY}"],
          "transcriptPath": str(world.agy_root / "brain" / "c-root" / ".system_generated" / "logs" / "transcript_full.jsonl")}),
        (["hook", "--host", "claude-code", "--event", "task-end"], None),
    ]
    for argv, payload in payloads:
        raw = json.dumps(payload).encode() if payload is not None else CANARY_B + b"\x00{not json"
        done = subprocess.run([*agent_meter_argv(), *argv], input=raw, capture_output=True, env=world.env(),
                              timeout=30, check=False)
        results.append((argv, done.returncode, (done.stdout + done.stderr).decode("utf-8", "replace")))
    logs = world.meter.logs_dir
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / "scheduler.log").open("ab") as sink:
        # NB: the scheduler's own argv ("collect --scheduled --quiet") is DEF-QA1-01; use the parseable order
        done = subprocess.run([*agent_meter_argv(), "--quiet", "collect", "--scheduled"], stdout=sink,
                              stderr=sink, env=world.env(), timeout=120, check=False)
    results.append((["subprocess collect --scheduled"], done.returncode, ""))
    return results


def _assert_clean(world: QAWorld, results: list[tuple[list[str], int, str]], tmp_path: Path,
                  needles: tuple[bytes, ...]) -> None:
    leaks = [f"{argv}: {needle!r}" for argv, _c, text in results for needle in needles
             if needle.decode() in text]
    assert leaks == [], leaks
    meter_files = _tree_bytes(world.meter.root)
    assert any(name.startswith("outbox/") and name.endswith(".ndjson") for name in meter_files), \
        "sync left no outbox NDJSON to inspect"
    assert "last-summary.txt" in {Path(n).name for n in meter_files}
    assert _leaks(meter_files, needles) == []
    assert _leaks(_tree_bytes(tmp_path / "reports"), needles) == []


def test_pv01_every_command_store_outbox_report_logs_are_canary_free(
    qa_world: QAWorld, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    before = _digests(qa_world.claude.root, qa_world.agy_root)

    results = _sweep(qa_world, capsys, caplog, monkeypatch, tmp_path)

    codes = {" ".join(argv): code for argv, code, _ in results}
    # sync is offline by construction (exit 1, outbox kept); everything else succeeds
    # self-merge is a usage error by design; output is still swept for the canary
    assert {k: v for k, v in codes.items() if v != 0 and not k.startswith("sync")} == {"projects merge Demo Demo": 2}
    assert codes["sync"] == 1 and codes["sync --dry-run"] == 0
    _assert_clean(qa_world, results, tmp_path, (CANARY_B,))
    assert _digests(qa_world.claude.root, qa_world.agy_root) == before  # PV-03


def test_pv01_workspace_parent_directories_never_stored_or_printed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange: the canary is a parent directory of the workspace (and of the Claude slug dir);
    # the project's display name is the basename "demo-repo", but no clear-text path may persist.
    world = make_world(tmp_path, monkeypatch, standard=False)
    secret_dir = f"/Users/{CANARY}/work/demo-repo"
    session = claude_standard_session()
    for line in session.lines:
        if "cwd" in line:
            line["cwd"] = secret_dir
    for spec in session.subagents.values():
        for line in spec.writer.lines:
            if "cwd" in line:
                line["cwd"] = secret_dir
    session.slug = f"-Users-{CANARY}-work-demo-repo"
    ClaudeHome(world.claude.root).write(session)
    convs = agy_standard_conversations()
    for conv in convs:
        conv.workspace_uri = f"file://{secret_dir}"
    build_root(world.agy_root, convs)
    before = _digests(world.claude.root, world.agy_root)

    results = _sweep(world, capsys, caplog, monkeypatch, tmp_path)

    _assert_clean(world, results, tmp_path, (CANARY_B, secret_dir.encode()))
    assert _digests(world.claude.root, world.agy_root) == before
    with Store.open(world.meter, read_only=True, lock_timeout_s=5.0) as st:
        names = {r["display_name"] for r in st.query("SELECT display_name FROM projects")}
    assert "Demo" in names or "demo-repo" in names


def test_pv04_no_credentials_in_config_logs_or_outbox(
    qa_world: QAWorld, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    # Arrange: credentials present in the environment, as with ADC / API keys
    fake_token = "ya29.QA-FAKE-ACCESS-TOKEN-0000"
    for key in ("GOOGLE_OAUTH_ACCESS_TOKEN", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(key, fake_token)
    adc = qa_world.user / ".config" / "gcloud" / "application_default_credentials.json"
    adc.parent.mkdir(parents=True)
    adc.write_text(json.dumps({"refresh_token": fake_token, "client_secret": fake_token}), encoding="utf-8")

    results = _sweep(qa_world, capsys, caplog, monkeypatch, tmp_path)

    _assert_clean(qa_world, results, tmp_path, (fake_token.encode(),))
    salt = qa_world.meter.secret.read_bytes()
    outbox = {k: v for k, v in _tree_bytes(qa_world.meter.root).items() if k.startswith("outbox/")}
    assert _leaks(outbox, (salt, salt.hex().encode())) == []
