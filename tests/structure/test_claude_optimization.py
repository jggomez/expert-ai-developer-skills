"""Structural guarantees for the Claude Code plugin optimisation (Track 31).

Covers: Antigravity leftovers, plugin dependencies instead of copies, preloaded-skill
resolution, Playwright MCP + E2E evidence gate wiring, and Stop-gate cost controls.
"""
import glob
import json
import os
import re
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLAUDE = os.path.join(ROOT, "plugins", "claude")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from claude_sync_config import (  # noqa: E402
    CLAUDE_PLUGIN_DEPENDENCIES,
    FORBIDDEN_CLAUDE_TOKENS,
    KEEP_LOCAL_SKILLS,
    PLAYWRIGHT_MCP_TOOLS,
    sanitize_claude_content,
)


def _frontmatter(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f.read().split("---", 2)[1])


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_no_antigravity_tokens_in_claude_docs_agents_and_configs():
    # Arrange
    files = [p for p in glob.glob(os.path.join(CLAUDE, "**", "*"), recursive=True)
             if os.path.isfile(p) and p.endswith((".md", ".json"))]
    # Act
    hits = [f"{os.path.relpath(p, ROOT)}: {tok}" for p in files for tok in FORBIDDEN_CLAUDE_TOKENS if tok in _read(p)]
    # Assert
    assert not hits, "\n".join(hits)


def test_sanitizer_translates_antigravity_syntax():
    # Arrange
    text = ("Gate via `ask_question` modal; Pass `invoke_subagent(Subagents=[...])` for fan-out; "
            "Mode A (`Workspace: 'inherit'`); Mode B (`Workspace: 'share'` / `'branch'`); `send_message`.")
    # Act
    out = sanitize_claude_content(text)
    # Assert
    assert "`AskUserQuestion`" in out
    assert "several `Agent` calls in one message" in out
    assert "(shared working tree)" in out
    assert '`isolation: "worktree"`' in out
    assert "`SendMessage`" in out
    assert not [tok for tok in FORBIDDEN_CLAUDE_TOKENS if tok in out]


def test_dependent_plugins_declare_dependencies_and_ship_no_copies():
    for plugin, deps in CLAUDE_PLUGIN_DEPENDENCIES.items():
        # Arrange
        manifest = json.loads(_read(os.path.join(CLAUDE, plugin, ".claude-plugin", "plugin.json")))
        own_agents = {os.path.basename(p) for p in glob.glob(os.path.join(CLAUDE, plugin, "agents", "*.md"))}
        own_skills = set(os.listdir(os.path.join(CLAUDE, plugin, "skills")))
        # Act / Assert
        assert manifest.get("dependencies") == deps, plugin
        for dep in deps:
            dep_agents = {os.path.basename(p) for p in glob.glob(os.path.join(CLAUDE, dep, "agents", "*.md"))}
            dep_skills = set(os.listdir(os.path.join(CLAUDE, dep, "skills")))
            assert not own_agents & dep_agents, f"{plugin} duplicates {dep} agents: {own_agents & dep_agents}"
            dup_skills = (own_skills & dep_skills) - KEEP_LOCAL_SKILLS
            assert not dup_skills, f"{plugin} duplicates {dep} skills: {dup_skills}"


def test_preloaded_skills_resolve_inside_the_agents_plugin():
    # Arrange
    errors = []
    for path in glob.glob(os.path.join(CLAUDE, "*", "agents", "*.md")):
        plugin = path.split(os.sep)[-3]
        # Act
        for skill in _frontmatter(path).get("skills") or []:
            if not os.path.isfile(os.path.join(CLAUDE, plugin, "skills", skill, "SKILL.md")):
                errors.append(f"{plugin}/{os.path.basename(path)} preloads missing skill '{skill}'")
    # Assert
    assert not errors, "\n".join(errors)


def test_orchestrators_run_as_main_thread_with_claude_dispatch_notes():
    for path in glob.glob(os.path.join(CLAUDE, "*", "agents", "*-orchestrator.md")):
        # Arrange
        fm, body = _frontmatter(path), _read(path)
        plugin, name = path.split(os.sep)[-3], os.path.basename(path)[:-3]
        # Act / Assert
        assert {"Agent", "AskUserQuestion", "Skill"} <= set(fm["tools"]), path
        assert f"claude --agent {plugin}:{name}" in body, path
        assert "subagent_type" in body and 'isolation: "worktree"' in body, path


def test_e2e_tester_has_playwright_mcp_and_evidence_contract():
    # Arrange
    path = os.path.join(CLAUDE, "senior-dev", "agents", "e2e-blackbox-tester.md")
    fm, body = _frontmatter(path), _read(path)
    mcp = json.loads(_read(os.path.join(CLAUDE, "senior-dev", ".mcp.json")))["mcpServers"]
    hooks = json.loads(_read(os.path.join(CLAUDE, "senior-dev", "hooks.json")))["hooks"]
    # Act
    subagent_stop = json.dumps(hooks.get("SubagentStop", []))
    # Assert
    assert set(PLAYWRIGHT_MCP_TOOLS) <= set(fm["tools"])
    assert "@playwright/mcp@latest" in mcp["playwright"]["args"]
    assert "e2e-evidence-gate.js" in subagent_stop
    assert "Verdict: PASSED|REJECTED|BLOCKED|SKIPPED" in body


def test_every_blocking_stop_hook_uses_the_shared_gate_library():
    # Arrange
    errors = []
    for hooks_json in glob.glob(os.path.join(CLAUDE, "*", "hooks.json")):
        plugin_dir = os.path.dirname(hooks_json)
        for group in json.loads(_read(hooks_json)).get("hooks", {}).get("Stop", []):
            for hook in group.get("hooks", []):
                match = re.search(r"hooks/([\w.-]+\.js)", hook.get("command", ""))
                if not match:
                    continue
                source = _read(os.path.join(plugin_dir, "hooks", match.group(1)))
                # Act: a Stop hook that can block (exit 2) must bound retries via gate-utils
                if "exit(2)" in source or "exitBlock" in source:
                    if "shared', 'gate-utils.js'" not in source:
                        errors.append(f"{os.path.basename(plugin_dir)}/{match.group(1)} blocks without gate-utils")
    # Assert
    assert not errors, "\n".join(errors)


def test_post_tool_autosave_is_scoped_to_mutating_tools():
    # Arrange
    hooks = json.loads(_read(os.path.join(CLAUDE, "shared-context", "hooks.json")))["hooks"]
    # Act
    matchers = {group.get("matcher") for group in hooks["PostToolUse"]}
    # Assert
    assert matchers == {"Write|Edit|Bash"}


def test_shared_hook_library_is_not_gitignored():
    """Hooks `require` hooks/shared/gate-utils.js; if git ignores it, installed plugins crash."""
    import subprocess

    # Arrange
    copies = glob.glob(os.path.join(CLAUDE, "*", "hooks", "shared", "gate-utils.js"))
    # Act
    ignored = [c for c in copies
               if subprocess.run(["git", "check-ignore", "-q", c], cwd=ROOT).returncode == 0]
    # Assert
    assert copies, "no shared hook library copies found"
    assert not ignored, f"gitignored hook library copies (installed plugins would crash): {ignored}"


def test_claude_plugins_track_commits_instead_of_a_frozen_version():
    """A fixed plugin version is the cache key: users would never receive new commits.
    Without `version`, Claude Code versions git-hosted plugins by commit SHA."""
    # Arrange
    marketplace = json.loads(_read(os.path.join(ROOT, ".claude-plugin", "marketplace.json")))
    manifests = glob.glob(os.path.join(CLAUDE, "*", ".claude-plugin", "plugin.json"))
    # Act
    pinned_manifests = [m for m in manifests if "version" in json.loads(_read(m))]
    pinned_entries = [p["name"] for p in marketplace["plugins"] if "version" in p]
    # Assert
    assert manifests
    assert not pinned_manifests, f"remove 'version' from: {pinned_manifests}"
    assert not pinned_entries, f"remove 'version' from marketplace entries: {pinned_entries}"


def test_every_claude_plugin_readme_has_a_marketplace_install_line():
    # Arrange
    marketplace = json.loads(_read(os.path.join(ROOT, ".claude-plugin", "marketplace.json")))
    # Act
    missing = [p["name"] for p in marketplace["plugins"]
               if f"claude plugin install {p['name']}@{marketplace['name']}"
               not in _read(os.path.join(ROOT, p["source"], "README.md"))]
    # Assert
    assert not missing, f"README without install line: {missing}"


def test_root_hooks_json_is_declared_in_the_manifest():
    """Claude Code only auto-loads hooks/hooks.json; a root hooks.json loads only via the
    manifest "hooks" field. Without it every hook of the plugin silently never runs."""
    # Arrange
    plugin_dirs = [d for d in glob.glob(os.path.join(CLAUDE, "*")) if os.path.isfile(os.path.join(d, "hooks.json"))]
    # Act
    undeclared = [os.path.basename(d) for d in plugin_dirs
                  if json.loads(_read(os.path.join(d, ".claude-plugin", "plugin.json"))).get("hooks") != "./hooks.json"]
    # Assert
    assert plugin_dirs
    assert not undeclared, f"hooks.json never loads in: {undeclared}"
