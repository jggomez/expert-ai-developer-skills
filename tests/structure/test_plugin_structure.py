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


def test_plugin_manifest_locations(workspace_root, plugin_dirs):
    """Verifies every plugin ships a manifest at BOTH locations, since the
    two hosts require different paths: Antigravity reads 'plugin.json' at
    the plugin root; Claude Code requires it at '.claude-plugin/plugin.json'
    specifically (a root-level plugin.json alone is not recognized) —
    verified against antigravity.google/docs/cli/plugins and
    code.claude.com/docs/en/plugins. Both must declare the same 'name'
    matching the plugin's directory name."""
    errors = []

    for plugin in plugin_dirs:
        plugin_path = os.path.join(workspace_root, "plugins", plugin)

        antigravity_manifest = os.path.join(plugin_path, "plugin.json")
        claude_manifest = os.path.join(plugin_path, ".claude-plugin", "plugin.json")

        if not os.path.isfile(antigravity_manifest):
            errors.append(f"{plugin}: missing plugin.json at the plugin root (required by Antigravity)")
        if not os.path.isfile(claude_manifest):
            errors.append(f"{plugin}: missing .claude-plugin/plugin.json (required by Claude Code)")
        if not os.path.isfile(antigravity_manifest) or not os.path.isfile(claude_manifest):
            continue

        with open(antigravity_manifest, "r", encoding="utf-8") as f:
            antigravity_data = json.load(f)
        with open(claude_manifest, "r", encoding="utf-8") as f:
            claude_data = json.load(f)

        if antigravity_data.get("name") != plugin:
            errors.append(f"{plugin}: plugin.json 'name' is '{antigravity_data.get('name')}', expected '{plugin}'")
        if claude_data.get("name") != plugin:
            errors.append(f"{plugin}: .claude-plugin/plugin.json 'name' is '{claude_data.get('name')}', expected '{plugin}'")

    assert not errors, "\n".join(errors)


def test_plugin_hooks_json_schema(workspace_root, plugin_dirs):
    """Verifies every plugin's hooks.json (when present) follows a valid
    schema for at least one host. A single hooks.json can serve both hosts
    at once since each reads a different top-level key: Claude Code reads
    'hooks' (event-name-keyed, no 'enabled' field); Antigravity reads any
    other top-level key as a named hook group (its own 'enabled' field and
    event names are valid there) — verified against
    antigravity.google/docs/hooks."""
    claude_code_events = {"SessionStart", "PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit", "Notification"}
    antigravity_events = {"PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"}
    errors = []

    for plugin in plugin_dirs:
        hooks_path = os.path.join(workspace_root, "plugins", plugin, "hooks.json")
        if not os.path.isfile(hooks_path):
            continue

        with open(hooks_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key, value in data.items():
            if key == "description":
                continue

            if key == "hooks":
                # Claude Code format: {"hooks": {EventName: [{"matcher"?, "hooks": [...]}]}}
                if not isinstance(value, dict):
                    errors.append(f"{plugin}: 'hooks' must map event names to hook definitions")
                    continue
                for event_name, groups in value.items():
                    if event_name not in claude_code_events:
                        errors.append(f"{plugin}: unknown Claude Code hook event '{event_name}' in hooks.json")
                        continue
                    for group in groups:
                        if "enabled" in group:
                            errors.append(
                                f"{plugin}: non-standard 'enabled' flag inside the 'hooks' (Claude Code) "
                                f"'{event_name}' group; Claude Code has no per-hook enabled field"
                            )
                        if "hooks" not in group:
                            errors.append(f"{plugin}: hook group for '{event_name}' is missing its 'hooks' array")
                continue

            # Any other top-level key is an Antigravity-style named hook
            # group: {"enabled": bool, EventName: [...]}.
            if not isinstance(value, dict):
                errors.append(f"{plugin}: hook group '{key}' must be an object")
                continue
            event_keys = [k for k in value.keys() if k != "enabled"]
            if not event_keys:
                errors.append(f"{plugin}: hook group '{key}' declares no events")
            for event_name in event_keys:
                if event_name not in antigravity_events:
                    errors.append(f"{plugin}: unknown Antigravity hook event '{event_name}' in group '{key}'")

    assert not errors, "\n".join(errors)


def test_plugin_mcp_json_schema(workspace_root, plugin_dirs):
    """Verifies each plugin's MCP config files. A plugin may ship both:
    '.mcp.json' (Claude Code — top-level 'mcpServers', each entry declaring
    a 'type' of stdio/http/sse) and/or 'mcp_config.json' (Antigravity —
    top-level 'mcpServers', each entry needing either 'command' (stdio) or
    'serverUrl' (remote)) — verified against antigravity.google/docs/mcp."""
    valid_claude_types = {"stdio", "http", "sse"}
    errors = []

    for plugin in plugin_dirs:
        plugin_path = os.path.join(workspace_root, "plugins", plugin)

        claude_mcp_path = os.path.join(plugin_path, ".mcp.json")
        if os.path.isfile(claude_mcp_path):
            with open(claude_mcp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "mcpServers" not in data:
                errors.append(f"{plugin}: .mcp.json must have a top-level 'mcpServers' key")
            else:
                for server_name, config in data["mcpServers"].items():
                    if config.get("type") not in valid_claude_types:
                        errors.append(
                            f"{plugin}: .mcp.json server '{server_name}' is missing a valid 'type' "
                            f"(one of {sorted(valid_claude_types)})"
                        )

        antigravity_mcp_path = os.path.join(plugin_path, "mcp_config.json")
        if os.path.isfile(antigravity_mcp_path):
            with open(antigravity_mcp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "mcpServers" not in data:
                errors.append(f"{plugin}: mcp_config.json must have a top-level 'mcpServers' key")
            else:
                for server_name, config in data["mcpServers"].items():
                    if "command" not in config and "serverUrl" not in config:
                        errors.append(
                            f"{plugin}: mcp_config.json server '{server_name}' needs either "
                            "'command' (stdio) or 'serverUrl' (remote)"
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


def test_root_agents_frontmatter(workspace_root):
    """Verifies every root-level agents/*.md (the Antigravity subagent
    definitions) has valid frontmatter with 'name' matching its filename
    and a 'description' — mirrors test_plugin_agents_frontmatter for the
    plugin-bundled agents."""
    agents_dir = os.path.join(workspace_root, "agents")
    errors = []

    for fname in os.listdir(agents_dir):
        if not fname.endswith(".md") or fname == "README.md":
            continue
        agent_name = fname[:-3]
        agent_path = os.path.join(agents_dir, fname)

        with open(agent_path, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            errors.append(f"agents/{fname}: missing or invalid YAML frontmatter")
            continue

        try:
            data = yaml.safe_load(match.group(1))
        except Exception as e:
            errors.append(f"agents/{fname}: invalid YAML frontmatter ({e})")
            continue

        if not data.get("description"):
            errors.append(f"agents/{fname}: 'description' field is missing or empty")
        if data.get("name") != agent_name:
            errors.append(
                f"agents/{fname}: frontmatter 'name' is '{data.get('name')}' "
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
