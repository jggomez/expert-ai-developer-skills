"""Behavioural tests for scripts/hook-lib/gate-utils.js under the Google Antigravity hook contract.

Antigravity (antigravity.google/docs/hooks) differs from Claude Code:
- hooks always exit 0 and answer with JSON on stdout (non-zero exits are ignored, fail-open);
- a Stop hook keeps the agent working with {"decision": "continue", "reason": ...};
- there is no `stop_hook_active` flag: a turn is identified by conversationId + lastUserInput;
- the workspace comes from `workspacePaths`, and Stop carries `terminationReason`.
"""
import json
import os
import shutil
import subprocess
import textwrap

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB = os.path.join(ROOT, "scripts", "hook-lib", "gate-utils.js")
AGY_PLUGINS = os.path.join(ROOT, "plugins", "antigravity")

pytestmark = pytest.mark.skipif(shutil.which("node") is None or shutil.which("git") is None,
                                reason="node and git are required")

HARNESS = textwrap.dedent("""
    const { execSync } = require('child_process');
    const g = require(process.env.GATE_LIB);
    const payload = g.readStdinJson();
    if (!g.isFinalStop(payload)) g.exitAllow();
    const gate = g.createStopGate({ gateId: 'harness', payload });
    if (gate.retryLimitReached()) g.exitAllow(g.retryLimitNotice('harness'));
    if (gate.begin()) g.exitAllow();
    try {
      execSync(process.env.GATE_CMD, { cwd: gate.cwd, stdio: 'pipe' });
      gate.markPass();
      g.exitAllow();
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


def _stop(repo, cmd, user_input="fix the bug", reason="model_stop", workspace=None, counter=None, idle=True):
    harness = repo / ".git" / "harness.js"
    harness.write_text(HARNESS)
    payload = {
        "conversationId": "conv-1",
        "workspacePaths": [str(workspace or repo)],
        "transcriptPath": str(repo / ".git" / "transcript.jsonl"),
        "artifactDirectoryPath": str(repo / ".git" / "artifacts"),
        "modelName": "flash",
        "executionNum": 1,
        "terminationReason": reason,
        "fullyIdle": idle,
        "lastUserInput": user_input,
    }
    if counter:
        cmd = f"echo run >> {counter}; {cmd}"
    env = dict(os.environ, GATE_LIB=LIB, GATE_CMD=cmd)
    result = subprocess.run(["node", str(harness)], input=json.dumps(payload), capture_output=True,
                            text=True, env=env, timeout=60)
    return result, json.loads(result.stdout or "{}")


def test_failing_check_keeps_the_agent_working_with_continue(repo):
    # Arrange
    (repo / "app.py").write_text("x = 2\n")
    # Act
    result, out = _stop(repo, "exit 1")
    # Assert: Antigravity ignores exit codes, so the block must be JSON on stdout with exit 0
    assert result.returncode == 0
    assert out["decision"] == "continue"
    assert "harness failed" in out["reason"] and "block 1/3" in out["reason"]


def test_retry_limit_ends_the_turn_after_three_blocks(repo):
    # Arrange
    (repo / "app.py").write_text("x = 2\n")
    # Act
    decisions = [_stop(repo, "exit 1")[1]["decision"] for _ in range(4)]
    # Assert
    assert decisions == ["continue", "continue", "continue", "allow"]


def test_a_new_user_message_resets_the_retry_counter(repo):
    # Arrange
    (repo / "app.py").write_text("x = 2\n")
    for _ in range(3):
        _stop(repo, "exit 1", user_input="first request")
    # Act
    _, out = _stop(repo, "exit 1", user_input="second request")
    # Assert
    assert out["decision"] == "continue" and "block 1/3" in out["reason"]


def test_green_state_is_cached_until_code_changes(repo):
    # Arrange
    (repo / "app.py").write_text("x = 2\n")
    counter = repo / ".git" / "count"
    # Act
    first = _stop(repo, "true", counter=counter)[1]
    second = _stop(repo, "true", counter=counter)[1]
    # Assert
    assert first["decision"] == "allow" and second["decision"] == "allow"
    assert counter.read_text().count("run") == 1


def test_only_a_model_stop_runs_verification(repo):
    # Arrange
    (repo / "app.py").write_text("x = 2\n")
    counter = repo / ".git" / "count"
    # Act
    _, out = _stop(repo, "exit 1", reason="max_steps_exceeded", counter=counter)
    # Assert
    assert out["decision"] == "allow"
    assert not counter.exists()


def test_stop_waits_while_subagents_or_background_tasks_still_run(repo):
    # Arrange: fullyIdle=false means background work (e.g. parallel implementers) is still running,
    # so the tree may hold half-finished edits from other workers
    (repo / "app.py").write_text("x = 2\n")
    counter = repo / ".git" / "count"
    # Act
    _, out = _stop(repo, "exit 1", idle=False, counter=counter)
    # Assert
    assert out["decision"] == "allow"
    assert not counter.exists()


def test_workspace_subfolder_resolves_to_the_git_root(repo):
    # Arrange: Antigravity may report a subfolder of the repository as the workspace
    (repo / "pkg").mkdir()
    (repo / "app.py").write_text("x = 2\n")
    counter = repo / ".git" / "count"
    # Act
    _, out = _stop(repo, "test -f app.py", workspace=repo / "pkg", counter=counter)
    # Assert: the check ran from the repository root, where app.py lives
    assert out["decision"] == "allow"
    assert counter.read_text().count("run") == 1


def _node_eval(expr):
    script = f"const g = require({json.dumps(LIB)}); process.stdout.write(JSON.stringify({expr}));"
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize("tool,args,expected", [
    ("replace_file_content", {"TargetFile": "/a.py", "TargetContent": "x = 1", "ReplacementContent": "x = 2"}, True),
    ("replace_file_content", {"TargetFile": "/a.py", "TargetContent": "a\n" * 12, "ReplacementContent": "b"}, False),
    ("replace_file_content", {"TargetFile": "/a.py", "TargetContent": "x", "ReplacementContent": "y", "AllowMultiple": True}, False),
    ("multi_replace_file_content", {"TargetFile": "/a.py", "ReplacementChunks": [
        {"TargetContent": "a", "ReplacementContent": "b"}, {"TargetContent": "c", "ReplacementContent": "d"}]}, True),
    ("multi_replace_file_content", {"TargetFile": "/a.py", "ReplacementChunks": [
        {"TargetContent": "a\n" * 6, "ReplacementContent": "b"},
        {"TargetContent": "c\n" * 6, "ReplacementContent": "d"}]}, False),
    ("write_to_file", {"TargetFile": "/a.py", "CodeContent": "x = 1"}, False),
])
def test_is_small_edit_understands_antigravity_edit_tools(tool, args, expected):
    # Arrange / Act
    result = _node_eval(f"g.isSmallEdit({json.dumps(tool)}, {json.dumps(args)})")
    # Assert
    assert result is expected


def test_antigravity_plugin_copies_match_canonical_library():
    # Arrange
    gated = ["senior-dev", "python-backend", "senior-dev-flutter", "senior-data-engineer",
             "docs-and-quality", "git-workflow"]
    with open(LIB, encoding="utf-8") as f:
        canonical = f.read()
    # Act
    missing_or_drifted = []
    for plugin in gated:
        copy = os.path.join(AGY_PLUGINS, plugin, "hooks", "shared", "gate-utils.js")
        if not os.path.isfile(copy) or open(copy, encoding="utf-8").read() != canonical:
            missing_or_drifted.append(plugin)
    # Assert
    assert not missing_or_drifted, f"run scripts/sync_agents.py: {missing_or_drifted}"


def _run_plugin_hook(script_rel, payload):
    script = os.path.join(AGY_PLUGINS, script_rel)
    result = subprocess.run(["node", script], input=json.dumps(payload), capture_output=True,
                            text=True, timeout=120, cwd=os.path.dirname(os.path.dirname(script)))
    return result, json.loads(result.stdout or "{}")


def _agy_stop(repo, reason="model_stop"):
    return {"conversationId": "conv-9", "workspacePaths": [str(repo)], "terminationReason": reason,
            "fullyIdle": True, "lastUserInput": "add a feature"}


@pytest.mark.skipif(shutil.which("pytest") is None, reason="pytest CLI not on PATH")
def test_python_backend_stop_gate_keeps_antigravity_working_on_red_tests(repo):
    # Arrange: a failing test suite in the user's project (hooks run from the plugin root)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text("def test_x():\n    assert False\n")
    # Act
    result, out = _run_plugin_hook("python-backend/hooks/stop-gate.js", _agy_stop(repo))
    # Assert
    assert result.returncode == 0
    assert out["decision"] == "continue" and "PYTHON QUALITY GATE FAILURE" in out["reason"]


def test_universal_gate_ignores_non_final_stops(repo):
    # Arrange
    (repo / "tests").mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n")
    (repo / "tests" / "test_app.py").write_text("def test_x():\n    assert False\n")
    # Act
    result, out = _run_plugin_hook("senior-dev/hooks/universal-quality-gate.js", _agy_stop(repo, "error"))
    # Assert
    assert result.returncode == 0 and out == {"decision": "allow"}


def _agy_pre_tool(repo, tool, args):
    return {"conversationId": "conv-7", "workspacePaths": [str(repo)],
            "toolCall": {"name": tool, "args": args}}


@pytest.mark.parametrize("tool,args,decision", [
    ("replace_file_content", {"TargetContent": "x = 1", "ReplacementContent": "x = 2"}, "allow"),
    ("multi_replace_file_content", {"ReplacementChunks": [{"TargetContent": "x = 1", "ReplacementContent": "x = 2"}]},
     "allow"),
    ("replace_file_content", {"TargetContent": "x = 1\n" * 12, "ReplacementContent": "x = 2"}, "deny"),
    ("write_to_file", {"CodeContent": "x = 1\n"}, "deny"),
])
def test_plan_first_gate_exempts_small_antigravity_edits(repo, tool, args, decision):
    # Arrange: a feature branch without PLAN.md (protected branches are denied for another reason)
    _git(repo, "checkout", "-qb", "feat/x")
    payload = _agy_pre_tool(repo, tool, dict(args, TargetFile=str(repo / "app.py")))
    # Act
    result, out = _run_plugin_hook("python-backend/hooks/pre-tool-gate.js", payload)
    # Assert
    assert result.returncode == 0
    assert out["decision"] == decision
    if decision == "deny":
        assert "PLAN FIRST" in out["reason"]
