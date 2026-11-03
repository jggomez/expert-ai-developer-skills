"""Behavioural tests for scripts/claude-hook-lib/gate-utils.js and the Claude Stop gates using it.

Each test builds a throw-away git repo, pipes a Claude Code hook payload into Node and
asserts exit code / stdout / stderr, so the real hook contract is exercised end to end.
"""
import glob
import json
import os
import shutil
import subprocess
import textwrap
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB = os.path.join(ROOT, "scripts", "claude-hook-lib", "gate-utils.js")
CLAUDE_PLUGINS = os.path.join(ROOT, "plugins", "claude")

pytestmark = pytest.mark.skipif(shutil.which("node") is None or shutil.which("git") is None,
                                reason="node and git are required")

# Minimal Stop gate driven by the shared library: runs $GATE_CMD as the verification.
HARNESS = textwrap.dedent("""
    const { execSync } = require('child_process');
    const g = require(process.env.GATE_LIB);
    const payload = g.readStdinJson();
    const gate = g.createStopGate({ gateId: 'harness', payload });
    if (gate.retryLimitReached()) g.exitAllow(g.retryLimitNotice('harness'));
    const skip = gate.begin();
    if (skip) { process.stdout.write('SKIP:' + skip); process.exit(0); }
    try {
      execSync(process.env.GATE_CMD, { cwd: gate.cwd, stdio: 'pipe' });
      gate.markPass();
      process.stdout.write('RAN:pass');
      process.exit(0);
    } catch (e) {
      g.exitBlock(gate.markFail('harness failed'));
    }
""")


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "app.py").write_text("x = 1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def _run_harness(repo, cmd, stop_hook_active=False):
    harness = repo / ".git" / "harness.js"
    harness.write_text(HARNESS)
    payload = {"cwd": str(repo), "hook_event_name": "Stop", "stop_hook_active": stop_hook_active}
    env = dict(os.environ, GATE_LIB=LIB, GATE_CMD=cmd)
    return subprocess.run(["node", str(harness)], input=json.dumps(payload), capture_output=True,
                          text=True, env=env, timeout=60)


def _run_parallel(harness, payload, env, count=2):
    """Starts `count` hooks and hands each its payload at once, as Claude Code does for
    parallel hooks (a sequential communicate() would feed the second one only after the
    first has finished)."""
    procs = [subprocess.Popen(["node", str(harness)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, env=env) for _ in range(count)]
    for proc in procs:
        proc.stdin.write(payload)
        proc.stdin.close()
    outs = [(proc.stdout.read(), proc.stderr.read()) for proc in procs]
    for proc in procs:
        proc.wait(timeout=60)
    return procs, outs


def _node_eval(expr):
    script = f"const g = require({json.dumps(LIB)}); process.stdout.write(JSON.stringify({expr}));"
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_clean_tree_skips_verification(repo):
    # Arrange: nothing changed since the last commit
    # Act
    result = _run_harness(repo, "exit 1")
    # Assert
    assert result.returncode == 0
    assert result.stdout == "SKIP:no code changes"


def test_docs_only_change_skips_verification(repo):
    # Arrange
    (repo / "NOTES.md").write_text("# notes\n")
    (repo / "docs").mkdir()
    (repo / "docs" / "spec.md").write_text("spec\n")
    # Act
    result = _run_harness(repo, "exit 1")
    # Assert
    assert result.returncode == 0
    assert result.stdout.startswith("SKIP:")


def test_code_change_with_failing_check_blocks(repo):
    # Arrange
    (repo / "app.py").write_text("x = 2\n")
    # Act
    result = _run_harness(repo, "exit 1")
    # Assert
    assert result.returncode == 2
    assert "harness failed" in result.stderr
    assert "block 1/3" in result.stderr


def test_retry_limit_lets_turn_end_with_notice(repo):
    # Arrange: one block on a fresh turn, then two more while Claude keeps fixing
    (repo / "app.py").write_text("x = 2\n")
    assert _run_harness(repo, "exit 1").returncode == 2
    assert _run_harness(repo, "exit 1", stop_hook_active=True).returncode == 2
    assert _run_harness(repo, "exit 1", stop_hook_active=True).returncode == 2
    # Act: fourth stop attempt in the same turn
    result = _run_harness(repo, "exit 1", stop_hook_active=True)
    # Assert
    assert result.returncode == 0
    assert "still failing after 3" in json.loads(result.stdout)["systemMessage"]


def test_new_turn_resets_retry_counter(repo):
    # Arrange: exhaust the retry budget
    (repo / "app.py").write_text("x = 2\n")
    for active in (False, True, True):
        _run_harness(repo, "exit 1", stop_hook_active=active)
    # Act: a new user turn (stop_hook_active false)
    result = _run_harness(repo, "exit 1")
    # Assert
    assert result.returncode == 2
    assert "block 1/3" in result.stderr


def test_green_state_is_cached_until_code_changes(repo):
    # Arrange
    (repo / "app.py").write_text("x = 2\n")
    first = _run_harness(repo, "true")
    # Act
    second = _run_harness(repo, "exit 1")
    (repo / "app.py").write_text("x = 3\n")
    third = _run_harness(repo, "exit 1")
    # Assert
    assert first.stdout == "RAN:pass"
    assert second.stdout == "SKIP:unchanged since last green run"
    assert third.returncode == 2


def test_parallel_gates_with_same_id_run_check_once(repo):
    # Arrange: the check appends to a counter file and takes a moment
    (repo / "app.py").write_text("x = 2\n")
    counter = repo / ".git" / "count"
    cmd = f"echo run >> {counter}; sleep 1"
    harness = repo / ".git" / "harness.js"
    harness.write_text(HARNESS)
    payload = json.dumps({"cwd": str(repo), "hook_event_name": "Stop", "stop_hook_active": False})
    env = dict(os.environ, GATE_LIB=LIB, GATE_CMD=cmd)
    # Act
    procs, outs = _run_parallel(harness, payload, env)
    # Assert
    assert all(p.returncode == 0 for p in procs), outs
    assert counter.read_text().count("run") == 1, outs
    stdouts = sorted(o[0] for o in outs)
    assert stdouts[0] == "RAN:pass", outs
    assert stdouts[1] in ("SKIP:verified by a parallel gate", "SKIP:unchanged since last green run"), outs


def test_parallel_gates_outside_git_still_run_check_once(tmp_path):
    # Arrange: no git repo, so there is no fingerprint; only the lock can de-duplicate
    workdir = tmp_path / "plain"
    workdir.mkdir()
    counter = tmp_path / "count"
    harness = tmp_path / "harness.js"
    harness.write_text(HARNESS)
    payload = json.dumps({"cwd": str(workdir), "hook_event_name": "Stop", "stop_hook_active": False})
    env = dict(os.environ, GATE_LIB=LIB, GATE_CMD=f"echo run >> {counter}; sleep 1", TMPDIR=str(tmp_path))
    # Act
    procs, outs = _run_parallel(harness, payload, env)
    # Assert
    assert all(p.returncode == 0 for p in procs), outs
    assert counter.read_text().count("run") == 1, outs


@pytest.mark.parametrize("tool_input,expected", [
    ({"old_string": "a", "new_string": "b"}, True),
    ({"old_string": "a\n" * 10, "new_string": "b"}, False),
    ({"old_string": "a", "new_string": "b", "replace_all": True}, False),
])
def test_is_small_edit(tool_input, expected):
    # Arrange / Act
    result = _node_eval(f"g.isSmallEdit('Edit', {json.dumps(tool_input)})")
    # Assert
    assert result is expected


def test_write_is_never_a_small_edit():
    assert _node_eval("g.isSmallEdit('Write', {content: 'x'})") is False


@pytest.mark.parametrize("agent_type,expected", [
    ("senior-dev-orchestrator", True),
    ("senior-dev:senior-dev-orchestrator", True),
    ("code-implementer", False),
    ("", False),
])
def test_is_agent(agent_type, expected):
    assert _node_eval(f"g.isAgent({{agent_type: {json.dumps(agent_type)}}}, ['senior-dev-orchestrator'])") is expected


def test_plugin_copies_match_canonical_library():
    # Arrange
    copies = glob.glob(os.path.join(CLAUDE_PLUGINS, "*", "hooks", "shared", "gate-utils.js"))
    # Act
    with open(LIB, encoding="utf-8") as f:
        canonical = f.read()
    drifted = [c for c in copies if open(c, encoding="utf-8").read() != canonical]
    # Assert
    assert len(copies) >= 6, f"expected the library in every gated Claude plugin, found {copies}"
    assert not drifted, f"run scripts/sync_agents.py; drifted copies: {drifted}"


def test_python_backend_stop_gate_skips_docs_only_turn(repo):
    # Arrange: a failing test suite exists, but this turn only touched docs
    (repo / "tests").mkdir()
    (repo / "tests" / "test_fail.py").write_text("def test_x():\n    assert False\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "add failing test")
    (repo / "README.md").write_text("docs only\n")
    hook = os.path.join(CLAUDE_PLUGINS, "python-backend", "hooks", "stop-gate.js")
    payload = {"cwd": str(repo), "hook_event_name": "Stop", "stop_hook_active": False}
    # Act
    result = subprocess.run(["node", hook], input=json.dumps(payload), capture_output=True, text=True, timeout=60)
    # Assert
    assert result.returncode == 0, result.stderr


def test_python_backend_stop_gate_blocks_failing_code_change(repo):
    # Arrange
    if shutil.which("pytest") is None:
        pytest.skip("pytest not on PATH")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text("from app import x\n\ndef test_x():\n    assert x == 1\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "tests")
    (repo / "app.py").write_text("x = 2\n")
    hook = os.path.join(CLAUDE_PLUGINS, "python-backend", "hooks", "stop-gate.js")
    payload = {"cwd": str(repo), "hook_event_name": "Stop", "stop_hook_active": False}
    # Act
    result = subprocess.run(["node", hook], input=json.dumps(payload), capture_output=True, text=True,
                            timeout=120, env=dict(os.environ, PYTHONPATH=str(repo)))
    # Assert
    assert result.returncode == 2
    assert "block 1/3" in result.stderr


def test_read_stdin_json_waits_for_a_late_payload():
    """Hook stdin may arrive after node starts; touching process.stdin made the pipe
    non-blocking, so readFileSync(0) threw EAGAIN and the payload was silently empty."""
    # Arrange
    script = (f"const g = require({json.dumps(LIB)});"
              "process.stdout.write(JSON.stringify(g.readStdinJson()));")
    proc = subprocess.Popen(["node", "-e", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    time.sleep(0.5)
    # Act
    out, _ = proc.communicate(json.dumps({"cwd": "/late"}), timeout=30)
    # Assert
    assert json.loads(out) == {"cwd": "/late"}
