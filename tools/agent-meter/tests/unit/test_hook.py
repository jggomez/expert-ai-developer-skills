"""Hook fast path, hook worker and notifications (HK-01..04, I-4, US-01, notification policy)."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_meter import hook, notify
from agent_meter.config import Config, HostConfig, save_config
from agent_meter.locking import store_lock
from agent_meter.model import Host
from agent_meter.paths import AppHome
from tests.fixtures.antigravity import build_root
from tests.fixtures.canary import CANARY
from tests.fixtures.claude import ClaudeHome
from tests.fixtures.scenarios import (
    CLAUDE_SESSION_ID,
    agy_standard_conversations,
    claude_standard_session,
)

SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture()
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(hook, "_spawn_worker", lambda argv: calls.append(list(argv)))
    return calls


def run_hook(argv: list[str], stdin: bytes) -> tuple[int, str]:
    out = io.StringIO()
    code = hook.hook_main(argv, io.BytesIO(stdin), out)
    return code, out.getvalue()


CLAUDE_STOP = json.dumps({
    "session_id": "s-abc", "transcript_path": f"/Users/dev/.claude/projects/x/{CANARY}.jsonl", "cwd": f"/{CANARY}",
    "hook_event_name": "Stop", "stop_hook_active": False, "last_assistant_message": CANARY,
}).encode()
AGY_STOP = json.dumps({
    "conversationId": "c-root", "transcriptPath": "/Users/dev/.gemini/antigravity-ide/brain/c-root/x.jsonl",
    "workspacePaths": [f"/{CANARY}"], "terminationReason": "completed", "fullyIdle": True, "executionNum": 3,
    "prompt": CANARY,
}).encode()


# ----------------------------------------------------------------------------- HK-01 / HK-03


@pytest.mark.parametrize("stdin", [b"", b"not json", b"[1,2]", b"{\"session_id\": 5}", b"\xff\xfe", b"{" * 200_000])
@pytest.mark.parametrize(("host", "expected_stdout"), [("claude-code", ""), ("antigravity", "{}\n")])
def test_hk01_hk03_bad_stdin_exits_zero_with_exact_stdout(
    spawned: list[list[str]], stdin: bytes, host: str, expected_stdout: str
) -> None:
    code, out = run_hook(["--host", host, "--event", "task-end"], stdin)

    assert code == 0
    assert out == expected_stdout
    assert spawned == []


@pytest.mark.parametrize("argv", [[], ["--host"], ["--bogus", "x"], ["--timeout", "abc"], ["--event", "explode"]])
def test_hk01_bad_arguments_still_exit_zero(spawned: list[list[str]], argv: list[str]) -> None:
    code, out = run_hook(argv, CLAUDE_STOP)

    assert code == 0
    assert out == ""


def test_hk01_spawn_failure_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_argv: list[str]) -> None:
        raise OSError("no such executable")

    monkeypatch.setattr(hook, "_spawn_worker", fail)

    code, out = run_hook(["--host", "antigravity", "--event", "task-end"], AGY_STOP)

    assert (code, out) == (0, "{}\n")


def test_hk02_hard_timeout_is_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hook, "_spawn_worker", lambda _argv: time.sleep(5))
    started = time.monotonic()

    code, out = run_hook(["--host", "antigravity", "--event", "task-end", "--timeout", "0.3"], AGY_STOP)

    assert (code, out) == (0, "{}\n")
    assert time.monotonic() - started < 1.5


# ----------------------------------------------------------------------------- HK-04 payloads


def test_hk04_claude_payload_spawns_worker_with_allowlisted_args(spawned: list[list[str]]) -> None:
    code, out = run_hook(["--host", "claude-code", "--event", "session-end"], CLAUDE_STOP)

    assert (code, out) == (0, "")
    assert len(spawned) == 1
    argv = spawned[0]
    assert argv[argv.index("--host") + 1] == "claude-code"
    assert argv[argv.index("--event") + 1] == "session-end"
    assert argv[argv.index("--session-id") + 1] == "s-abc"
    assert not any(CANARY in a for a in argv)


def test_hk04_antigravity_payload_detects_host_from_transcript(spawned: list[list[str]]) -> None:
    run_hook(["--host", "antigravity", "--event", "task-end"], AGY_STOP)

    argv = spawned[0]
    assert argv[argv.index("--host") + 1] == "antigravity-ide"
    assert argv[argv.index("--session-id") + 1] == "c-root"
    assert argv[argv.index("--fully-idle") + 1] == "true"
    assert argv[argv.index("--termination-reason") + 1] == "completed"
    assert not any(CANARY in a for a in argv)


def test_parse_payload_allowlists_and_validates() -> None:
    raw = json.dumps({"conversationId": "../../etc", "fullyIdle": "yes", "terminationReason": "a b;c",
                      "transcriptPath": 7}).encode()

    payload = hook.parse_payload(raw, host_flag="antigravity", event="task-end")

    assert payload.session_id is None
    assert payload.fully_idle is None
    assert payload.termination_reason is None
    assert payload.transcript_path is None
    assert payload.host is None


def test_parse_payload_claude_session_end() -> None:
    payload = hook.parse_payload(
        json.dumps({"session_id": "s-1", "reason": "prompt_input_exit", "transcript_path": "/x/.claude/projects/a/s-1.jsonl"}).encode(),
        host_flag="claude-code", event="session-end",
    )

    assert payload.host is Host.CLAUDE_CODE
    assert payload.event == "session-end"
    assert payload.session_id == "s-1"
    assert payload.reason == "prompt_input_exit"


def test_i4_hook_path_never_imports_duckdb(tmp_path: Path) -> None:
    env = {**os.environ, "HOME": str(tmp_path), "AGENT_METER_HOME": str(tmp_path / "m"), "PYTHONPATH": str(SRC)}
    code = (
        "import io, sys; from agent_meter.cli import main; "
        "rc = main(['hook', '--host', 'antigravity', '--event', 'task-end']); "
        "print('|DUCKDB' if 'duckdb' in sys.modules else '|CLEAN', rc)"
    )

    done = subprocess.run([sys.executable, "-c", code], input=b"{}", capture_output=True, env=env, timeout=30, check=False)

    assert done.returncode == 0
    assert done.stdout.decode() == "{}\n|CLEAN 0\n"


# ----------------------------------------------------------------------------- worker


@pytest.fixture()
def worker_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[AppHome, list[tuple[str, str]]]]:
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    claude = ClaudeHome(tmp_path / "user" / ".claude")
    claude.write(claude_standard_session())
    agy = build_root(tmp_path / "user" / ".gemini" / "antigravity-cli", agy_standard_conversations())
    home = AppHome.resolve(str(tmp_path / "meter"))
    monkeypatch.setenv("AGENT_METER_HOME", str(home.root))
    hosts = {h: HostConfig(enabled=h in {Host.CLAUDE_CODE, Host.ANTIGRAVITY_CLI}) for h in Host}
    hosts[Host.CLAUDE_CODE] = HostConfig(root=claude.root)
    hosts[Host.ANTIGRAVITY_CLI] = HostConfig(root=agy)
    save_config(Config(timezone="UTC", hosts=hosts, notify_min_task_s=0), home)
    sent: list[tuple[str, str]] = []
    def fake_notify(title: str, body: str) -> bool:
        sent.append((title, body))
        return True

    monkeypatch.setattr(notify, "notify", fake_notify)
    yield home, sent


def test_worker_session_end_writes_summary_and_notifies_once(worker_env: tuple[AppHome, list[tuple[str, str]]]) -> None:
    home, sent = worker_env
    argv = ["--host", "claude-code", "--event", "session-end", "--session-id", CLAUDE_SESSION_ID]

    first = hook.worker_main(argv)
    second = hook.worker_main(argv)

    text = home.last_summary.read_text(encoding="utf-8")
    assert (first, second) == (0, 0)
    assert text.startswith("[agent-meter] demo-repo · Claude Code · session")
    assert CANARY not in text
    assert len(sent) == 1
    assert CANARY not in json.dumps(sent)


def test_worker_child_conversation_ingests_without_notifying(worker_env: tuple[AppHome, list[tuple[str, str]]]) -> None:
    home, sent = worker_env

    code = hook.worker_main(["--host", "antigravity-cli", "--event", "task-end", "--session-id", "c-child1",
                             "--fully-idle", "true"])

    assert code == 0
    assert sent == []
    assert "Antigravity CLI" in home.last_summary.read_text(encoding="utf-8")


def test_worker_not_fully_idle_does_not_notify(worker_env: tuple[AppHome, list[tuple[str, str]]]) -> None:
    _home, sent = worker_env

    hook.worker_main(["--host", "antigravity-cli", "--event", "task-end", "--session-id", "c-root",
                      "--fully-idle", "false"])

    assert sent == []


def test_worker_generic_antigravity_host_finds_unit(worker_env: tuple[AppHome, list[tuple[str, str]]]) -> None:
    home, _sent = worker_env

    hook.worker_main(["--host", "antigravity", "--event", "task-end", "--session-id", "c-root", "--fully-idle", "true"])

    assert "Antigravity CLI" in home.last_summary.read_text(encoding="utf-8")


def test_worker_policy_off_never_notifies(worker_env: tuple[AppHome, list[tuple[str, str]]]) -> None:
    home, sent = worker_env
    from agent_meter.config import load_config, set_key

    save_config(set_key(load_config(home), "notify", "off"), home)

    hook.worker_main(["--host", "claude-code", "--event", "session-end", "--session-id", CLAUDE_SESSION_ID])

    assert sent == []
    assert home.last_summary.exists()


def test_worker_locked_store_uses_snapshot_note(worker_env: tuple[AppHome, list[tuple[str, str]]],
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    home, _sent = worker_env
    monkeypatch.setattr(hook, "WORKER_LOCK_TIMEOUT_S", 0.1)

    with store_lock(home.lock, exclusive=True, timeout_s=1.0):
        code = hook.worker_main(["--host", "claude-code", "--event", "task-end", "--session-id", CLAUDE_SESSION_ID])

    assert code == 0
    assert "(collecting… run 'agent-meter last' in a minute)" in home.last_summary.read_text(encoding="utf-8")


def test_worker_unknown_session_is_quiet(worker_env: tuple[AppHome, list[tuple[str, str]]]) -> None:
    home, sent = worker_env

    code = hook.worker_main(["--host", "claude-code", "--event", "task-end", "--session-id", "nope"])

    assert code == 0
    assert sent == []
    assert not home.last_summary.exists()


def test_worker_bad_arguments_return_usage_error() -> None:
    assert hook.worker_main(["--host", "claude-code"]) == 2


# ----------------------------------------------------------------------------- notify


def test_notify_macos_passes_text_as_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def fake_run(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[bytes]:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("subprocess.run", fake_run)

    assert notify.notify('t "quoted"', "body\\with") is True
    assert seen[0][0] == "/usr/bin/osascript"
    assert seen[0][-2:] == ['t "quoted"', "body\\with"]


def test_notify_linux_uses_notify_send(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}" if name == "notify-send" else None)
    def fake_run(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[bytes]:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 1)

    monkeypatch.setattr("subprocess.run", fake_run)

    assert notify.notify("t", "b") is False
    assert seen == [["/usr/bin/notify-send", "--app-name=agent-meter", "t", "b"]]


def test_notify_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: object, **_kw: object) -> None:
        raise subprocess.TimeoutExpired("osascript", 5)

    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/osascript")
    monkeypatch.setattr("subprocess.run", boom)

    assert notify.notify("t", "b") is False
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert notify.notify("t", "b") is False
    monkeypatch.setattr("sys.platform", "win32")
    assert notify.notify("t", "b") is False


def test_notified_dedupe_survives_corrupt_state(worker_env: tuple[AppHome, list[tuple[str, str]]]) -> None:
    home, sent = worker_env
    home.ensure_dir(home.state_dir)
    home.notified.write_text("{corrupt", encoding="utf-8")

    hook.worker_main(["--host", "claude-code", "--event", "session-end", "--session-id", CLAUDE_SESSION_ID])

    assert len(sent) == 1
    assert isinstance(json.loads(home.notified.read_text(encoding="utf-8")), list)


def test_worker_uses_store_now(worker_env: tuple[AppHome, list[tuple[str, str]]]) -> None:
    home, _sent = worker_env

    hook.worker_main(["--host", "claude-code", "--event", "task-end", "--session-id", CLAUDE_SESSION_ID])

    from agent_meter.store import Store

    with Store.open(home, read_only=True, lock_timeout_s=1.0) as st:
        last = st.get_meta("last_collect_at")
    assert last is not None and datetime.fromisoformat(last) <= datetime.now(UTC)
