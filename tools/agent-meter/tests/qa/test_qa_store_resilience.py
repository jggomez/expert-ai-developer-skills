"""ST-03/04/05 with real processes and real files (unit tests cover them with in-process fakes).

* ST-03: a transcript that shrinks or is replaced (new inode) is re-read safely.
* ST-04: hook worker + scheduled collect + manual collect running concurrently; one writer at a
  time, worker gives up within its 3 s budget and falls back to the snapshot, no corruption.
* ST-05: the collector process is SIGKILLed inside the store transaction; the next run completes
  and the result equals a clean ingest.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from agent_meter import cli
from agent_meter.locking import store_lock
from agent_meter.store import Store
from tests.fixtures.claude import ClaudeSession, usage
from tests.fixtures.scenarios import CLAUDE_SESSION_ID, claude_standard_session
from tests.qa.conftest import QAWorld, agent_meter_argv, make_world

FACT_TABLES = ("sessions", "tasks", "agent_runs", "llm_calls", "tool_uses")


def _facts(world: QAWorld) -> dict[str, list[tuple[object, ...]]]:
    """Every fact row minus ingest bookkeeping, sorted: the comparable content of the store."""
    with Store.open(world.meter, read_only=True, lock_timeout_s=10.0) as st:
        out: dict[str, list[tuple[object, ...]]] = {}
        for table in FACT_TABLES:
            rows = st.query(f"SELECT * EXCLUDE (ingest_seq) FROM {table}")
            out[table] = sorted(tuple(sorted((k, str(v)) for k, v in r.items())) for r in rows)
        return out


def _pk_duplicates(world: QAWorld) -> int:
    keys = {"sessions": "session_id", "tasks": "task_id", "agent_runs": "agent_run_id", "llm_calls": "call_id"}
    with Store.open(world.meter, read_only=True, lock_timeout_s=10.0) as st:
        total = 0
        for table, key in keys.items():
            row = st.query(f"SELECT COUNT(*) - COUNT(DISTINCT {key}) AS d FROM {table}")[0]
            total += int(str(row["d"]))
        return total


def _share_secret(src: QAWorld, dst: QAWorld) -> None:
    """Same salt => same description hashes, so two homes are comparable row for row."""
    dst.meter.secret.parent.mkdir(parents=True, exist_ok=True)
    dst.meter.secret.write_bytes(src.meter.secret.read_bytes())
    dst.meter.secret.chmod(0o600)


def _collect(capsys: pytest.CaptureFixture[str], *extra: str) -> tuple[int, str]:
    capsys.readouterr()
    code = cli.main(["collect", *extra])
    out = capsys.readouterr()
    return code, out.out + out.err


# ----------------------------------------------------------------------------- ST-03


def test_st03_shrunk_transcript_is_reread_without_crash_or_duplicates(
    qa_world: QAWorld, capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange: a session with 3 prompts, collected
    session = ClaudeSession("s-shrink")
    for n in range(3):
        p = session.prompt(n * 100, f"shrink-p{n}")
        session.assistant(n * 100 + 5, f"shrink-r{n}", parent=p, use=usage(10 + n, 5, cache_read=0))
    path = qa_world.write_claude(session)
    assert _collect(capsys)[0] == 0

    # Act: the file shrinks to its first prompt only (truncate in place, same inode)
    first_prompt_lines = b"".join(path.read_bytes().splitlines(keepends=True)[:2])
    with path.open("r+b") as handle:
        handle.truncate(0)
        handle.write(first_prompt_lines)
    code, out = _collect(capsys)

    # Assert: run succeeded, the surviving call is intact, nothing duplicated (BR-15 keeps history)
    assert code == 0, out
    assert _pk_duplicates(qa_world) == 0
    with Store.open(qa_world.meter, read_only=True, lock_timeout_s=5.0) as st:
        kept = st.query("SELECT call_id, input_tokens FROM llm_calls WHERE session_id = 's-shrink' ORDER BY 1")
    assert {"call_id": "claude-code:shrink-r0", "input_tokens": 10} in kept


def test_st03_replaced_file_new_inode_is_reread_with_new_content(
    qa_world: QAWorld, capsys: pytest.CaptureFixture[str],
) -> None:
    session = ClaudeSession("s-replace")
    p = session.prompt(0, "rep-p0")
    session.assistant(5, "rep-r0", parent=p, use=usage(10, 5, cache_read=0))
    path = qa_world.write_claude(session)
    assert _collect(capsys)[0] == 0
    inode_before = path.stat().st_ino

    # Act: atomically replace the file with a corrected copy of identical size (new inode)
    replacement = ClaudeSession("s-replace")
    p2 = replacement.prompt(0, "rep-p0")
    replacement.assistant(5, "rep-r0", parent=p2, use=usage(20, 5, cache_read=0))
    data = replacement.encode()
    assert len(data) == path.stat().st_size
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.utime(tmp, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns))
    os.replace(tmp, path)
    assert path.stat().st_ino != inode_before
    code, out = _collect(capsys)

    assert code == 0, out
    with Store.open(qa_world.meter, read_only=True, lock_timeout_s=5.0) as st:
        rows = st.query("SELECT input_tokens FROM llm_calls WHERE call_id = 'claude-code:rep-r0'")
    assert rows == [{"input_tokens": 20}]
    assert _pk_duplicates(qa_world) == 0


# ----------------------------------------------------------------------------- ST-04


def test_st04_worker_skips_within_budget_when_store_is_locked_by_another_process(
    qa_world: QAWorld, capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange: a populated store + snapshot, then a foreign writer holds the lock
    assert _collect(capsys)[0] == 0
    qa_world.meter.last_summary.unlink(missing_ok=True)
    holder = subprocess.Popen(
        [sys.executable, "-c", textwrap.dedent(f"""
            import sys, time
            sys.path.insert(0, {str(Path(cli.__file__).parents[1])!r})
            from pathlib import Path
            from agent_meter.locking import store_lock
            with store_lock(Path({str(qa_world.meter.lock)!r}), exclusive=True, timeout_s=5):
                print("held", flush=True)
                time.sleep(20)
        """)],
        stdout=subprocess.PIPE, env=qa_world.env(),
    )
    try:
        assert holder.stdout is not None and holder.stdout.readline().strip() == b"held"

        # Act: the hook worker runs while the lock is held
        started = time.monotonic()
        done = subprocess.run(
            [*agent_meter_argv(), "hook-worker", "--host", "claude-code", "--event", "task-end",
             "--session-id", CLAUDE_SESSION_ID],
            capture_output=True, env=qa_world.env(), timeout=30, check=False,
        )
        elapsed = time.monotonic() - started
    finally:
        holder.kill()
        holder.wait()

    # Assert: exit 0, gave up within its 3 s lock budget (+ process start-up), wrote the snapshot note
    assert done.returncode == 0
    assert elapsed < 3.0 + 3.0, f"worker blocked {elapsed:.2f}s"
    text = qa_world.meter.last_summary.read_text(encoding="utf-8")
    assert "collecting" in text


def test_st04_concurrent_collectors_and_workers_leave_identical_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: two identical worlds; one ingested by a single collect (reference)
    ref = make_world(tmp_path / "ref", monkeypatch)
    assert subprocess.run([*agent_meter_argv(), "collect"], env=ref.env(), capture_output=True,
                          timeout=120, check=False).returncode == 0
    world = make_world(tmp_path / "race", monkeypatch)
    _share_secret(ref, world)

    # Act: 6 writers started at once against the same store (manual, scheduled, hook workers)
    argvs = [
        ["collect"], ["collect", "--full"], ["--quiet", "collect", "--scheduled"],
        ["hook-worker", "--host", "claude-code", "--event", "task-end", "--session-id", CLAUDE_SESSION_ID],
        ["hook-worker", "--host", "antigravity", "--event", "task-end", "--session-id", "c-root",
         "--fully-idle", "true"],
        ["collect"],
    ]
    procs = [subprocess.Popen([*agent_meter_argv(), *a], env=world.env(), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) for a in argvs]
    results = [(p.wait(timeout=180), p.stdout.read() if p.stdout else b"", p.stderr.read() if p.stderr else b"")
               for p in procs]
    for proc in procs:
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()

    # Assert: every process exited 0 and the store equals the single-writer reference
    assert [r[0] for r in results] == [0] * len(argvs), results
    assert _pk_duplicates(world) == 0
    # Workers send a task-end signal (may mark the last task done), so tasks/runs status can differ
    # legitimately; calls, sessions and tool counts must be identical to the single-writer run.
    race, single = _facts(world), _facts(ref)
    for table in ("llm_calls", "sessions", "tool_uses"):
        assert race[table] == single[table], table
    assert len(race["tasks"]) == len(single["tasks"]) and len(race["agent_runs"]) == len(single["agent_runs"])


# ----------------------------------------------------------------------------- ST-05


KILLER = textwrap.dedent("""
    import os, signal, sys
    sys.path.insert(0, sys.argv[1])
    from agent_meter.store import Store
    original = Store._merge_tool_uses

    def die(self, *args, **kwargs):
        os.kill(os.getpid(), signal.SIGKILL)   # the OS kills us mid-transaction

    Store._merge_tool_uses = die
    from agent_meter import cli
    sys.exit(cli.main(["collect"]))
""")


def test_st05_sigkill_mid_transaction_then_next_run_equals_clean_ingest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = make_world(tmp_path / "ref", monkeypatch)
    assert subprocess.run([*agent_meter_argv(), "collect"], env=ref.env(), capture_output=True,
                          timeout=120, check=False).returncode == 0
    world = make_world(tmp_path / "killed", monkeypatch)
    _share_secret(ref, world)
    src = str(Path(cli.__file__).parents[1])

    killed = subprocess.run([sys.executable, "-c", KILLER, src], env=world.env(), capture_output=True,
                            timeout=120, check=False)
    assert killed.returncode == -signal.SIGKILL

    # The lock died with the process (flock); the store holds no partial facts
    with store_lock(world.meter.lock, exclusive=True, timeout_s=2.0):
        pass
    if world.meter.db.exists():
        with Store.open(world.meter, read_only=True, lock_timeout_s=5.0) as st:
            assert st.query("SELECT COUNT(*) AS n FROM llm_calls") == [{"n": 0}]

    recovered = subprocess.run([*agent_meter_argv(), "collect"], env=world.env(), capture_output=True,
                               timeout=120, check=False)
    assert recovered.returncode == 0, recovered.stderr
    assert _facts(world) == _facts(ref)


def test_st05_sigkill_during_second_run_keeps_first_run_data(
    qa_world: QAWorld, capsys: pytest.CaptureFixture[str],
) -> None:
    assert _collect(capsys)[0] == 0
    before = _facts(qa_world)
    session = claude_standard_session()
    p = session.prompt(4000, "late-p")
    session.assistant(4005, "late-r", parent=p, use=usage(7, 7, cache_read=0))
    qa_world.write_claude(session)

    killed = subprocess.run([sys.executable, "-c", KILLER, str(Path(cli.__file__).parents[1])],
                            env=qa_world.env(), capture_output=True, timeout=120, check=False)

    assert killed.returncode == -signal.SIGKILL
    assert _facts(qa_world) == before  # rolled back: the half-applied batch is invisible
    assert _collect(capsys)[0] == 0
    with Store.open(qa_world.meter, read_only=True, lock_timeout_s=5.0) as st:
        assert st.query("SELECT COUNT(*) AS n FROM llm_calls WHERE call_id = 'claude-code:late-r'") == [{"n": 1}]
