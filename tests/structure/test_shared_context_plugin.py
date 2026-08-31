"""Structural checks specific to the shared-context plugin.

Complements the generic plugin-structure tests with assertions about this
plugin's own layout: dual-host hooks.json, the stdio MCP config pointing at the
bundled server, the host-neutral agent, and the Antigravity rules file that
substitutes for the missing SessionStart event.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest
import yaml

PLUGIN = os.path.abspath("plugins/shared-context")

EXPECTED_FILES = [
    ".claude-plugin/plugin.json",
    "plugin.json",
    "README.md",
    ".mcp.json",
    "mcp_config.json",
    "hooks.json",
    "hooks/session-start-context.js",
    "hooks/post-tool-autosave.js",
    "hooks/stop-flush.js",
    "rules/shared-context-rules.md",
    "mcp/mcp_server.py",
    "mcp/run-server.sh",
    "agents/context-keeper.md",
    "skills/context-capture/SKILL.md",
    "skills/context-restore/SKILL.md",
]


def _read(rel):
    with open(os.path.join(PLUGIN, rel), encoding="utf-8") as f:
        return f.read()


def _json(rel):
    return json.loads(_read(rel))


def test_expected_files_present():
    missing = [f for f in EXPECTED_FILES if not os.path.isfile(os.path.join(PLUGIN, f))]
    assert not missing, f"missing plugin files: {missing}"


def test_manifests_match_and_name_is_shared_context():
    assert _json(".claude-plugin/plugin.json").get("name") == "shared-context"
    assert _json("plugin.json").get("name") == "shared-context"


def test_hooks_json_serves_both_hosts():
    h = _json("hooks.json")

    cc = h["hooks"]
    assert {"SessionStart", "PostToolUse", "Stop"} <= set(cc)
    for event, groups in cc.items():
        for group in groups:
            assert "hooks" in group and "enabled" not in group
            for hook in group["hooks"]:
                assert "${CLAUDE_PLUGIN_ROOT}/hooks/" in hook["command"]

    agy = h["shared-context-relay"]
    assert agy.get("enabled") is True
    events = [k for k in agy if k != "enabled"]
    assert {"PreInvocation", "PostToolUse", "Stop"} <= set(events)
    assert "SessionStart" not in events  # Antigravity has no SessionStart event
    for event in events:
        for group in agy[event]:
            for hook in group["hooks"]:
                assert hook["command"].startswith("node ./hooks/")


def test_mcp_configs_point_at_the_launcher():
    cc = _json(".mcp.json")["mcpServers"]["shared-context"]
    assert cc["type"] == "stdio" and cc["command"] == "sh"
    assert cc["args"] == ["${CLAUDE_PLUGIN_ROOT}/mcp/run-server.sh"]

    agy = _json("mcp_config.json")["mcpServers"]["shared-context"]
    assert agy["command"] == "sh" and agy["args"] == ["./mcp/run-server.sh"]


def test_launcher_is_posix_sh_executable_and_pins_mcp_v1():
    path = os.path.join(PLUGIN, "mcp", "run-server.sh")
    assert os.access(path, os.X_OK), "run-server.sh is not executable"
    src = _read("mcp/run-server.sh")
    assert src.startswith("#!/bin/sh")
    assert "mcp<2" in src               # v1 FastMCP API is pinned
    assert "uv run" in src              # the easy path: no global install
    assert "mcp_server.py" in src
    if shutil.which("sh"):
        r = subprocess.run(["sh", "-n", path], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_context_keeper_agent_is_host_neutral():
    fm = yaml.safe_load(_read("agents/context-keeper.md").split("---", 2)[1])
    assert fm["name"] == "context-keeper"
    assert isinstance(fm["subagent"], bool) and isinstance(fm["mainAgent"], bool)
    assert "tools" not in fm
    assert fm["model"] == "inherit"
    assert fm["commandExecutionPolicy"] in ("off", "auto", "eager", "sandbox")
    assert set(fm["skills"]) == {"context-capture", "context-restore"}


def test_rules_file_enforces_ask_before_load():
    txt = _read("rules/shared-context-rules.md").lower()
    assert "ask the user" in txt
    assert "context_list.py" in txt
    assert "context/" in txt


def test_readme_bundled_skills_section_lists_both_skills():
    readme = _read("README.md")
    import re
    section = re.search(r"## \d+\. Bundled Skills.*?(?=\n## |\Z)", readme, re.DOTALL)
    assert section, "no 'Bundled Skills' section"
    names = set(re.findall(r"\*\*`([a-z0-9-]+)`\*\*", section.group(0)))
    assert {"context-capture", "context-restore"} <= names


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_hook_scripts_are_valid_javascript():
    for js in ("session-start-context.js", "post-tool-autosave.js", "stop-flush.js"):
        r = subprocess.run(
            ["node", "--check", os.path.join(PLUGIN, "hooks", js)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"{js}: {r.stderr}"


def test_mcp_server_module_exposes_every_tool_without_the_mcp_package():
    code = (
        "import importlib.util as u;"
        f"s=u.spec_from_file_location('m', {os.path.join(PLUGIN, 'mcp', 'mcp_server.py')!r});"
        "m=u.module_from_spec(s);s.loader.exec_module(m);"
        "names=['list','snapshot','read','write','pack','unpack','rollup','search'];"
        "print(all(callable(getattr(m,'tool_context_'+n,None)) for n in names))"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.stdout.strip() == "True", r.stderr
