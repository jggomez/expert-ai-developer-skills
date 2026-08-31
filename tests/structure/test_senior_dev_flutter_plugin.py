"""Structural checks specific to the senior-dev-flutter plugin.

Complements the generic plugin-structure tests: the boundary is explicit
(README states the official packs are a required companion), the 5 agents are
host-neutral, the 2 hooks serve both hosts, and the MCP config points at
`dart mcp-server`.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest
import yaml

PLUGIN = os.path.abspath("plugins/senior-dev-flutter")

EXPECTED_FILES = [
    ".claude-plugin/plugin.json",
    "plugin.json",
    "README.md",
    ".mcp.json",
    "mcp_config.json",
    "hooks.json",
    "hooks/flutter-pre-tool-gate.js",
    "hooks/flutter-stop-gate.js",
]
AGENTS = [
    "flutter-feature-orchestrator",
    "flutter-architect",
    "flutter-implementer",
    "flutter-reviewer",
    "flutter-release-engineer",
]
SKILLS = [
    "flutter-senior-orchestration",
    "flutter-architecture-decisions",
    "flutter-review-checklist",
    "flutter-test-strategy",
    "flutter-performance-profiling",
    "flutter-release-engineering",
    "flutter-upgrade-migration",
]


def _read(rel):
    with open(os.path.join(PLUGIN, rel), encoding="utf-8") as f:
        return f.read()


def _json(rel):
    return json.loads(_read(rel))


def test_expected_files_and_dirs_present():
    missing = [f for f in EXPECTED_FILES if not os.path.isfile(os.path.join(PLUGIN, f))]
    for a in AGENTS:
        if not os.path.isfile(os.path.join(PLUGIN, "agents", f"{a}.md")):
            missing.append(f"agents/{a}.md")
    for s in SKILLS:
        if not os.path.isfile(os.path.join(PLUGIN, "skills", s, "SKILL.md")):
            missing.append(f"skills/{s}/SKILL.md")
    assert not missing, f"missing: {missing}"


def test_manifests_match():
    assert _json(".claude-plugin/plugin.json").get("name") == "senior-dev-flutter"
    assert _json("plugin.json").get("name") == "senior-dev-flutter"


def test_mcp_points_at_dart_mcp_server():
    cc = _json(".mcp.json")["mcpServers"]["dart"]
    assert cc["type"] == "stdio" and cc["command"] == "dart" and cc["args"] == ["mcp-server"]
    agy = _json("mcp_config.json")["mcpServers"]["dart"]
    assert agy["command"] == "dart" and agy["args"] == ["mcp-server"]


def test_hooks_json_serves_both_hosts():
    h = _json("hooks.json")
    cc = h["hooks"]
    assert {"PreToolUse", "Stop"} <= set(cc)
    for event, groups in cc.items():
        for g in groups:
            assert "hooks" in g and "enabled" not in g
            for hook in g["hooks"]:
                assert "${CLAUDE_PLUGIN_ROOT}/hooks/" in hook["command"]
    agy = h["senior-dev-flutter-gates"]
    assert agy.get("enabled") is True
    events = [k for k in agy if k != "enabled"]
    assert {"PreToolUse", "Stop"} <= set(events)
    for event in events:
        for g in agy[event]:
            for hook in g["hooks"]:
                assert hook["command"].startswith("node ./hooks/")


def test_all_five_agents_are_host_neutral():
    for name in AGENTS:
        fm = yaml.safe_load(_read(f"agents/{name}.md").split("---", 2)[1])
        assert fm["name"] == name, name
        assert isinstance(fm["subagent"], bool) and isinstance(fm["mainAgent"], bool), name
        assert "tools" not in fm, f"{name} must not declare a tools key"
        assert fm["model"] == "inherit", name
        assert fm["commandExecutionPolicy"] in ("off", "auto", "eager", "sandbox"), name
        assert isinstance(fm.get("skills"), list) and fm["skills"], name
    orch = yaml.safe_load(_read("agents/flutter-feature-orchestrator.md").split("---", 2)[1])
    assert orch["mainAgent"] is True
    assert orch["commandExecutionPolicy"] == "off"


def test_readme_declares_official_packs_as_required_companion():
    readme = _read("README.md")
    assert "npx skills add flutter/agent-plugins" in readme
    assert "npx skills add dart-lang/skills" in readme
    assert "dart mcp-server" in readme
    # the boundary must be stated
    assert re.search(r"do(es)? not (repeat|duplicate|touch)", readme, re.I)
    section = re.search(r"## \d+\. Bundled Skills.*?(?=\n## |\Z)", readme, re.DOTALL)
    assert section
    names = set(re.findall(r"\*\*`([a-z0-9-]+)`\*\*", section.group(0)))
    assert set(SKILLS) <= names


def test_agent_skill_refs_are_bundled():
    bundled = set(os.listdir(os.path.join(PLUGIN, "skills")))
    for name in AGENTS:
        fm = yaml.safe_load(_read(f"agents/{name}.md").split("---", 2)[1])
        for s in fm["skills"]:
            assert s in bundled, f"{name} refs unbundled skill {s}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_hook_scripts_are_valid_javascript():
    for js in ("flutter-pre-tool-gate.js", "flutter-stop-gate.js"):
        r = subprocess.run(["node", "--check", os.path.join(PLUGIN, "hooks", js)],
                           capture_output=True, text=True)
        assert r.returncode == 0, f"{js}: {r.stderr}"


def test_audit_script_is_stdlib_only():
    src = _read(os.path.join(
        "skills", "flutter-review-checklist", "scripts", "flutter_project_audit.py"))
    for banned in ("import yaml", "import requests", "import numpy", "from yaml"):
        assert banned not in src, f"audit script uses non-stdlib: {banned}"
