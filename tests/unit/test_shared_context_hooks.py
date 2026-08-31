"""Behavioral tests for the shared-context plugin's three Node hooks.

Each hook is run as a real subprocess with a sample stdin payload and the host
selected via environment variables (``CLAUDE_PLUGIN_ROOT`` present = Claude
Code; absent = Antigravity / generic). Skipped when ``node`` is unavailable.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")

HOOKS = os.path.abspath("plugins/shared-context/hooks")
SNAPSHOT = os.path.abspath("skills/context-capture/scripts/context_snapshot.py")
HOST_VARS = ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "CLAUDECODE", "ANTIGRAVITY", "AGY_PLUGIN_ROOT")


def run_hook(name, payload, env_extra=None, cwd=None):
    env = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["node", os.path.join(HOOKS, name)],
        input=json.dumps(payload), capture_output=True, text=True, env=env, cwd=cwd,
    )


def make_context(tmp_path, contextrc=None):
    ctx = tmp_path / "context"
    subprocess.run(
        [sys.executable, SNAPSHOT, "--context-dir", str(ctx), "--no-git",
         "--session", "s1", "--task", "prior work", "--agent", "gemini-pro"],
        check=True, capture_output=True,
    )
    if contextrc is not None:
        cfg = json.loads((ctx / ".contextrc.json").read_text())
        cfg.update(contextrc)
        (ctx / ".contextrc.json").write_text(json.dumps(cfg))
    return ctx


# --------------------------------------------------------------------------
# session-start-context.js
# --------------------------------------------------------------------------

def test_start_is_quiet_without_a_context_dir(tmp_path):
    r = run_hook("session-start-context.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert r.returncode == 0
    assert r.stdout.strip() == "{}"


def test_start_prompts_to_ask_the_user_on_claude_code(tmp_path):
    make_context(tmp_path)
    r = run_hook("session-start-context.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    ctx_text = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "1 prior session" in ctx_text
    assert "ASK the user" in ctx_text
    assert "context-restore" in ctx_text
    assert "without the user's explicit OK" in ctx_text


def test_start_emits_plain_text_for_antigravity(tmp_path):
    make_context(tmp_path)
    r = run_hook("session-start-context.js", {"workspacePaths": [str(tmp_path)]})
    assert r.stdout.strip().startswith("Shared AI context is available")
    assert not r.stdout.strip().startswith("{")


def test_start_is_debounced_on_the_second_call(tmp_path):
    make_context(tmp_path)
    first = run_hook("session-start-context.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert "additionalContext" in first.stdout
    second = run_hook("session-start-context.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert second.stdout.strip() == "{}"


# --------------------------------------------------------------------------
# post-tool-autosave.js
# --------------------------------------------------------------------------

def test_posttool_is_quiet_without_a_context_dir(tmp_path):
    r = run_hook("post-tool-autosave.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert r.returncode == 0 and r.stdout.strip() == "{}"


def test_posttool_nudges_a_checkpoint_at_the_threshold(tmp_path):
    make_context(tmp_path, {"autosave": {"everyNToolCalls": 1, "everyMinutes": 99999}})
    r = run_hook("post-tool-autosave.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    ctx_text = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "checkpoint due" in ctx_text and "context-capture" in ctx_text


def test_posttool_never_blocks_a_tool_call(tmp_path):
    make_context(tmp_path, {"autosave": {"everyNToolCalls": 1, "everyMinutes": 1}})
    out = json.loads(run_hook("post-tool-autosave.js", {"cwd": str(tmp_path)}).stdout)
    assert out.get("decision") == "allow"
    assert out.get("decision") not in ("deny", "block")


def test_posttool_below_threshold_stays_silent(tmp_path):
    make_context(tmp_path, {"autosave": {"everyNToolCalls": 999, "everyMinutes": 99999}})
    r = run_hook("post-tool-autosave.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert r.stdout.strip() == "{}"


# --------------------------------------------------------------------------
# stop-flush.js
# --------------------------------------------------------------------------

def test_stop_is_quiet_when_the_session_did_nothing(tmp_path):
    make_context(tmp_path)
    r = run_hook("stop-flush.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert r.stdout.strip() == "{}"


def test_stop_reminds_to_flush_after_activity_then_clears(tmp_path):
    make_context(tmp_path, {"autosave": {"everyNToolCalls": 999, "everyMinutes": 99999}})
    # one tool call recorded, below threshold -> no nudge but activity registered
    run_hook("post-tool-autosave.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})

    first = run_hook("stop-flush.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    reminder = json.loads(first.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "flush the shared context" in reminder
    assert "context_rollup.py" in reminder and "context_pack.py --auto" in reminder

    second = run_hook("stop-flush.js", {"cwd": str(tmp_path)}, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert second.stdout.strip() == "{}"


def test_stop_is_non_blocking_for_antigravity(tmp_path):
    make_context(tmp_path, {"autosave": {"everyNToolCalls": 999, "everyMinutes": 99999}})
    run_hook("post-tool-autosave.js", {"workspacePaths": [str(tmp_path)]})
    out = json.loads(run_hook("stop-flush.js", {"workspacePaths": [str(tmp_path)]}).stdout)
    assert out["decision"] == "allow"
