import filecmp
import json
import os
import re

import pytest
import yaml


def _discover_plugins(workspace_root):
    plugins_dir = os.path.join(workspace_root, "plugins", "antigravity")
    return sorted(
        name for name in os.listdir(plugins_dir)
        if os.path.isdir(os.path.join(plugins_dir, name)) and not name.startswith(".")
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
        plugin_path = os.path.join(workspace_root, "plugins", "antigravity", plugin)

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
        hooks_path = os.path.join(workspace_root, "plugins", "antigravity", plugin, "hooks.json")
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
        plugin_path = os.path.join(workspace_root, "plugins", "antigravity", plugin)

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
    valid frontmatter with 'name' matching its filename, a 'description', and
    the explicit 'subagent'/'mainAgent' booleans Antigravity CLI requires to
    register the agent at all (it does not fall back to their documented
    defaults). The frontmatter is kept host-neutral so the same file loads in
    both Claude Code and Antigravity: no 'tools' key (its values are
    host-specific), and 'model' is only ever 'inherit' (the sole value both
    hosts accept)."""
    errors = []

    for plugin in plugin_dirs:
        agents_dir = os.path.join(workspace_root, "plugins", "antigravity", plugin, "agents")
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
            for key in ("subagent", "mainAgent"):
                if not isinstance(data.get(key), bool):
                    errors.append(
                        f"{plugin}/agents/{fname}: '{key}' must be an explicit boolean "
                        "(Antigravity CLI does not register the agent without it)"
                    )
            tools = data.get("tools")
            if not isinstance(tools, list) or not tools:
                errors.append(f"{plugin}/agents/{fname}: must declare explicit 'tools' list so Antigravity equips write and execution capabilities")
            else:
                for required_tool in ("run_command", "view_file", "write_to_file", "replace_file_content"):
                    if required_tool not in tools:
                        errors.append(f"{plugin}/agents/{fname}: 'tools' list missing required capability '{required_tool}'")
                if agent_name in ("senior-dev-orchestrator", "flutter-feature-orchestrator"):
                    for orch_tool in ("invoke_subagent", "manage_subagents", "send_message"):
                        if orch_tool not in tools:
                            errors.append(f"{plugin}/agents/{fname}: orchestrator 'tools' missing '{orch_tool}'")
            if data.get("model") not in (None, "inherit"):
                errors.append(
                    f"{plugin}/agents/{fname}: 'model' is '{data.get('model')}' — use "
                    "'inherit' (the only value both Claude Code and Antigravity accept)"
                )
            cep = data.get("commandExecutionPolicy")
            if cep == "sandbox":
                errors.append(
                    f"{plugin}/agents/{fname}: 'commandExecutionPolicy' cannot be 'sandbox' "
                    "(no container sandbox is assumed; use 'auto' or 'off')"
                )
            elif cep is not None and cep not in ("off", "auto", "eager"):
                errors.append(
                    f"{plugin}/agents/{fname}: 'commandExecutionPolicy' is {cep!r} — must be "
                    'one of off/auto/eager as a string (quote "off", or YAML parses '
                    "it as the boolean false)"
                )
            if cep != "auto":
                errors.append(f"{plugin}/agents/{fname}: agent must have commandExecutionPolicy: 'auto', got {cep!r}")

    assert not errors, "\n".join(errors)





def test_plugin_skills_match_root_skills(workspace_root, plugin_dirs):
    """Verifies skills bundled inside any plugins/<name>/skills stay in sync
    with the canonical copy in /skills, since each plugin ships a physical
    duplicate rather than a reference."""
    root_skills = os.path.join(workspace_root, "skills")
    errors = []

    for plugin in plugin_dirs:
        plugin_skills = os.path.join(workspace_root, "plugins", "antigravity", plugin, "skills")
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
        plugin_skills = os.path.join(workspace_root, "plugins", "antigravity", plugin, "skills")
        if not os.path.isdir(plugin_skills):
            continue

        readme_path = os.path.join(workspace_root, "plugins", "antigravity", plugin, "README.md")
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


def test_all_agents_have_canonical_sections(workspace_root, plugin_dirs):
    """Verifies all agent definition files in plugins/<name>/agents/
    strictly contain the 7 canonical architecture sections:
    1. # Role & Objective
    2. # When to Use & Routing Triggers
    3. # Operating Guidelines & Workflow
    4. # Tooling & Environment Protocol
    5. # Inputs, Outputs & Hand-off Protocol
    6. # Quality Standards & Anti-Patterns (Red Flags)
    7. # Verification & Completion Checklist"""
    required_sections = [
        "# Role & Objective",
        "# When to Use & Routing Triggers",
        "# Operating Guidelines & Workflow",
        "# Tooling & Environment Protocol",
        "# Inputs, Outputs & Hand-off Protocol",
        "# Quality Standards & Anti-Patterns (Red Flags)",
        "# Verification & Completion Checklist",
    ]
    errors = []

    # Check plugin agents (Antigravity canonical plugins)
    for plugin in plugin_dirs:
        plugin_agents_dir = os.path.join(workspace_root, "plugins", "antigravity", plugin, "agents")
        if not os.path.isdir(plugin_agents_dir):
            continue
        for fname in os.listdir(plugin_agents_dir):
            if not fname.endswith(".md"):
                continue
            agent_path = os.path.join(plugin_agents_dir, fname)
            with open(agent_path, "r", encoding="utf-8") as f:
                content = f.read()
            for section in required_sections:
                if section not in content:
                    errors.append(f"plugins/{plugin}/agents/{fname}: missing required section '{section}'")

    assert not errors, "\n".join(errors)


def test_plugin_rules_validity(workspace_root, plugin_dirs):
    """Verifies that plugins with rules directories (senior-dev, senior-dev-flutter,
    senior-data-engineer, python-backend, shared-context) contain valid markdown rules
    with non-empty content and valid frontmatter when present."""
    expected_rule_plugins = {
        "senior-dev": "senior-dev-rules.md",
        "senior-dev-flutter": "flutter-rules.md",
        "senior-data-engineer": "data-engineer-rules.md",
        "python-backend": "python-backend-rules.md",
        "shared-context": "shared-context-rules.md",
    }
    errors = []

    for plugin, rule_file in expected_rule_plugins.items():
        rule_path = os.path.join(workspace_root, "plugins", "antigravity", plugin, "rules", rule_file)
        if not os.path.isfile(rule_path):
            errors.append(f"plugins/{plugin}/rules/{rule_file}: rule file does not exist")
            continue

        with open(rule_path, "r", encoding="utf-8") as f:
            content = f.read()

        if len(content.strip()) < 50:
            errors.append(f"plugins/{plugin}/rules/{rule_file}: rule file is suspiciously short or empty")

        match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if match:
            try:
                data = yaml.safe_load(match.group(1))
                if not isinstance(data, dict):
                    errors.append(f"plugins/{plugin}/rules/{rule_file}: frontmatter must be a YAML mapping")
            except Exception as e:
                errors.append(f"plugins/{plugin}/rules/{rule_file}: invalid YAML frontmatter ({e})")

    assert not errors, "\n".join(errors)


def test_command_workflows_exist_and_mirrored(workspace_root):
    """Verifies all 9 core command workflows exist in workflows/ and are mirrored
    to .agents/workflows/ so Antigravity registers them as slash commands."""
    core_commands = {
        "spec-workflow.md": "/spec",
        "plan-workflow.md": "/plan",
        "build-workflow.md": "/build",
        "test-workflow.md": "/test",
        "constraints-workflow.md": "/constraints",
        "review-workflow.md": "/review",
        "perf-workflow.md": "/perf",
        "code-simplify-workflow.md": "/code-simplify",
        "ship-workflow.md": "/ship",
    }
    errors = []

    for wf_file, cmd in core_commands.items():
        root_wf = os.path.join(workspace_root, "workflows", wf_file)
        agent_wf = os.path.join(workspace_root, ".agents", "workflows", wf_file)

        if not os.path.isfile(root_wf):
            errors.append(f"workflows/{wf_file}: missing core workflow file")
            continue
        if not os.path.isfile(agent_wf):
            errors.append(f".agents/workflows/{wf_file}: missing mirrored workflow file in .agents/workflows")
            continue

        with open(root_wf, "r", encoding="utf-8") as f:
            content = f.read()

        if cmd not in content:
            errors.append(f"workflows/{wf_file}: does not mention command '{cmd}'")

    assert not errors, "\n".join(errors)


def test_agents_execution_policy_and_tools(workspace_root, plugin_dirs):
    """Verifies that no agent definition in plugins/*/agents/
    has commandExecutionPolicy: 'off' (which revokes run_command and paralyzes Antigravity),
    and verifies that no agent has a restrictive 'tools:' whitelist that omits write_to_file
    or run_command."""
    search_dirs = []
    for p in plugin_dirs:
        plugin_agents = os.path.join(workspace_root, "plugins", "antigravity", p, "agents")
        if os.path.isdir(plugin_agents):
            search_dirs.append(plugin_agents)

    errors = []
    for s_dir in search_dirs:
        if not os.path.isdir(s_dir):
            continue
        for fname in os.listdir(s_dir):
            if not fname.endswith(".md") or fname == "README.md":
                continue
            path = os.path.join(s_dir, fname)
            rel_path = os.path.relpath(path, workspace_root)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if not match:
                errors.append(f"{rel_path}: missing YAML frontmatter")
                continue

            try:
                fm = yaml.safe_load(match.group(1))
            except Exception as e:
                errors.append(f"{rel_path}: YAML parsing error: {e}")
                continue

            policy = fm.get("commandExecutionPolicy")
            if policy == "off":
                errors.append(f"{rel_path}: commandExecutionPolicy cannot be 'off' (must be 'auto')")

            tools = fm.get("tools")
            if tools is not None:
                # If tools is defined, it must not omit critical writing and command tools
                if "write_to_file" not in tools or "run_command" not in tools:
                    errors.append(
                        f"{rel_path}: restrictive 'tools' list detected missing write_to_file or run_command"
                    )

    assert not errors, "\n".join(errors)


def test_claude_plugins_manifest_and_tools(workspace_root):
    """Verifies all Claude Code specialized plugins in plugins/claude/
    declare valid .claude-plugin/plugin.json manifests and pure Claude Code tools
    (Bash, Read, Write, Edit, Glob, Grep, Agent) with zero Antigravity tool leakage."""
    claude_plugins_dir = os.path.join(workspace_root, "plugins", "claude")
    assert os.path.isdir(claude_plugins_dir), "plugins/claude directory does not exist"

    valid_claude_tools = {"Bash", "Read", "Write", "Edit", "Glob", "Grep", "Agent", "WebSearch", "WebFetch"}
    antigravity_only_tools = {"run_command", "view_file", "write_to_file", "replace_file_content"}
    errors = []

    for plugin_name in os.listdir(claude_plugins_dir):
        plugin_path = os.path.join(claude_plugins_dir, plugin_name)
        if not os.path.isdir(plugin_path) or plugin_name == ".DS_Store":
            continue

        manifest_path = os.path.join(plugin_path, ".claude-plugin", "plugin.json")
        if not os.path.isfile(manifest_path):
            errors.append(f"plugins/claude/{plugin_name}: missing .claude-plugin/plugin.json")
            continue

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("name") != plugin_name:
            errors.append(f"plugins/claude/{plugin_name}: manifest name '{data.get('name')}' != '{plugin_name}'")

        agents_dir = os.path.join(plugin_path, "agents")
        if os.path.isdir(agents_dir):
            for fname in os.listdir(agents_dir):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(agents_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
                if not match:
                    errors.append(f"plugins/claude/{plugin_name}/agents/{fname}: missing YAML frontmatter")
                    continue
                fm = yaml.safe_load(match.group(1))
                tools = fm.get("tools", [])
                for t in tools:
                    if t not in valid_claude_tools:
                        errors.append(f"plugins/claude/{plugin_name}/agents/{fname}: non-Claude tool '{t}'")
                    if t in antigravity_only_tools:
                        errors.append(f"plugins/claude/{plugin_name}/agents/{fname}: leaked Antigravity tool '{t}'")
                for key in ("subagent", "mainAgent", "commandExecutionPolicy"):
                    if key in fm:
                        errors.append(f"plugins/claude/{plugin_name}/agents/{fname}: leaked Antigravity key '{key}'")

    assert not errors, "\n".join(errors)





def test_claude_marketplace_manifest(workspace_root):
    """Verifies .claude-plugin/marketplace.json exists, is valid JSON,
    and all declared plugin sources exist on disk."""
    market_path = os.path.join(workspace_root, ".claude-plugin", "marketplace.json")
    assert os.path.isfile(market_path), ".claude-plugin/marketplace.json does not exist"

    with open(market_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("name") == "expert-ai-developer-skills"
    assert "plugins" in data and len(data["plugins"]) >= 5

    errors = []
    for p in data["plugins"]:
        source = p.get("source")
        if not source:
            errors.append(f"Plugin '{p.get('name')}' missing 'source'")
            continue
        full_path = os.path.normpath(os.path.join(workspace_root, source))
        if not os.path.isdir(full_path):
            errors.append(f"Plugin '{p.get('name')}' source path does not exist: {source}")

    assert not errors, "\n".join(errors)




