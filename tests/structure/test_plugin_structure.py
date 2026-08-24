import filecmp
import json
import os
import re

import pytest
import yaml


def _discover_plugins(workspace_root):
    plugins_dir = os.path.join(workspace_root, "plugins")
    return sorted(
        name for name in os.listdir(plugins_dir)
        if os.path.isdir(os.path.join(plugins_dir, name))
    )


@pytest.fixture
def plugin_dirs(workspace_root):
    return _discover_plugins(workspace_root)


def test_plugin_hooks_json_schema(workspace_root, plugin_dirs):
    """Verifies every plugin's hooks.json (when present) follows the plugin
    hooks schema: a top-level 'hooks' object keyed by event name, with no
    legacy custom groupings."""
    known_events = {"SessionStart", "PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit", "Notification"}
    errors = []

    for plugin in plugin_dirs:
        hooks_path = os.path.join(workspace_root, "plugins", plugin, "hooks.json")
        if not os.path.isfile(hooks_path):
            continue

        with open(hooks_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "hooks" not in data:
            errors.append(f"{plugin}: hooks.json must have a top-level 'hooks' key")
            continue
        if not isinstance(data["hooks"], dict):
            errors.append(f"{plugin}: 'hooks' must map event names to hook definitions")
            continue

        for event_name, groups in data["hooks"].items():
            if event_name not in known_events:
                errors.append(f"{plugin}: unknown hook event '{event_name}' in hooks.json")
                continue
            for group in groups:
                if "enabled" in group:
                    errors.append(
                        f"{plugin}: non-standard 'enabled' flag found on a '{event_name}' hook group; "
                        "Claude Code has no per-hook enabled field (use disableAllHooks to disable everything)"
                    )
                if "hooks" not in group:
                    errors.append(f"{plugin}: hook group for '{event_name}' is missing its 'hooks' array")

    assert not errors, "\n".join(errors)


def test_plugin_mcp_json_schema(workspace_root, plugin_dirs):
    """Verifies every plugin's .mcp.json (when present) uses the real Claude
    Code filename/shape: top-level 'mcpServers', each entry declaring a
    'type' (stdio/http/sse)."""
    valid_types = {"stdio", "http", "sse"}
    errors = []

    for plugin in plugin_dirs:
        plugin_path = os.path.join(workspace_root, "plugins", plugin)
        legacy_path = os.path.join(plugin_path, "mcp_config.json")
        if os.path.isfile(legacy_path):
            errors.append(f"{plugin}: uses legacy filename 'mcp_config.json' instead of '.mcp.json'")

        mcp_path = os.path.join(plugin_path, ".mcp.json")
        if not os.path.isfile(mcp_path):
            continue

        with open(mcp_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "mcpServers" not in data:
            errors.append(f"{plugin}: .mcp.json must have a top-level 'mcpServers' key")
            continue

        for server_name, config in data["mcpServers"].items():
            if config.get("type") not in valid_types:
                errors.append(
                    f"{plugin}: MCP server '{server_name}' is missing a valid 'type' "
                    f"(one of {sorted(valid_types)})"
                )

    assert not errors, "\n".join(errors)


def test_plugin_agents_frontmatter(workspace_root, plugin_dirs):
    """Verifies every plugin-bundled subagent .md file (when present) has
    valid frontmatter with 'name' matching its filename and a 'description'."""
    errors = []

    for plugin in plugin_dirs:
        agents_dir = os.path.join(workspace_root, "plugins", plugin, "agents")
        if not os.path.isdir(agents_dir):
            continue

        for fname in os.listdir(agents_dir):
            if not fname.endswith(".md"):
                continue
            agent_name = fname[:-3]
            agent_path = os.path.join(agents_dir, fname)

            with open(agent_path, "r", encoding="utf-8") as f:
                content = f.read()

            match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if not match:
                errors.append(f"{plugin}/agents/{fname}: missing or invalid YAML frontmatter")
                continue

            try:
                data = yaml.safe_load(match.group(1))
            except Exception as e:
                errors.append(f"{plugin}/agents/{fname}: invalid YAML frontmatter ({e})")
                continue

            if not data.get("description"):
                errors.append(f"{plugin}/agents/{fname}: 'description' field is missing or empty")
            if data.get("name") != agent_name:
                errors.append(
                    f"{plugin}/agents/{fname}: frontmatter 'name' is '{data.get('name')}' "
                    f"but the file is '{fname}' (they must match)"
                )

    assert not errors, "\n".join(errors)


def test_plugin_skills_match_root_skills(workspace_root, plugin_dirs):
    """Verifies skills bundled inside any plugins/<name>/skills stay in sync
    with the canonical copy in /skills, since each plugin ships a physical
    duplicate rather than a reference."""
    root_skills = os.path.join(workspace_root, "skills")
    errors = []

    for plugin in plugin_dirs:
        plugin_skills = os.path.join(workspace_root, "plugins", plugin, "skills")
        if not os.path.isdir(plugin_skills):
            continue

        for skill_name in os.listdir(plugin_skills):
            plugin_skill_dir = os.path.join(plugin_skills, skill_name)
            root_skill_dir = os.path.join(root_skills, skill_name)

            if not os.path.isdir(plugin_skill_dir):
                continue
            if not os.path.exists(root_skill_dir):
                errors.append(f"{plugin}/{skill_name}: bundled in the plugin but missing from /skills")
                continue

            comparison = filecmp.dircmp(root_skill_dir, plugin_skill_dir)
            diffs = _collect_dircmp_diffs(comparison)
            if diffs:
                errors.append(f"{plugin}/{skill_name}: out of sync with /skills -> {diffs}")

    assert not errors, "\n".join(errors)


def _collect_dircmp_diffs(comparison):
    diffs = []
    diffs.extend(comparison.diff_files)
    diffs.extend(f"missing in plugin: {f}" for f in comparison.left_only if f != ".DS_Store")
    diffs.extend(f"missing in root: {f}" for f in comparison.right_only if f != ".DS_Store")
    for subdir, sub_comparison in comparison.subdirs.items():
        diffs.extend(_collect_dircmp_diffs(sub_comparison))
    return diffs


def test_plugin_readme_bundled_skills_exist(workspace_root, plugin_dirs):
    """Verifies every skill referenced in each plugin README's bundled-skills
    list actually exists in that plugin's skills/ dir (catches dangling
    references like a removed or renamed skill)."""
    errors = []

    for plugin in plugin_dirs:
        plugin_skills = os.path.join(workspace_root, "plugins", plugin, "skills")
        if not os.path.isdir(plugin_skills):
            continue

        readme_path = os.path.join(workspace_root, "plugins", plugin, "README.md")
        if not os.path.isfile(readme_path):
            continue

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        section_match = re.search(r"## \d+\. Bundled Skills.*?(?=\n## |\Z)", content, re.DOTALL)
        if not section_match:
            errors.append(f"{plugin}: could not find a 'Bundled Skills' section in the README")
            continue

        referenced = re.findall(r"\*\*`([a-z0-9-]+)`\*\*", section_match.group(0))
        if not referenced:
            errors.append(f"{plugin}: no skills parsed from the 'Bundled Skills' section")
            continue

        for name in referenced:
            if not os.path.isdir(os.path.join(plugin_skills, name)):
                errors.append(f"{plugin}: README references skill '{name}' not bundled in the plugin")

    assert not errors, "\n".join(errors)
