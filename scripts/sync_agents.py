#!/usr/bin/env python3
"""Unified Agent and Plugin Synchronizer for Google Antigravity & Claude Code.

Everything is a Plugin:
1. Canonical agent definitions live directly inside plugins/antigravity/<plugin>/agents/*.md.
2. Generates/updates plugins/claude/<plugin>/ with pure Claude Code subagents, skills, hooks, and .claude-plugin/plugin.json
   while sanitizing Antigravity tool names into native Claude Code tools and preserving Claude-specific hooks.json and README.md.
3. Generates .claude-plugin/marketplace.json so Claude Code users can install via marketplace.

Usage:
    python3 scripts/sync_agents.py
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path
import yaml

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = WORKSPACE_ROOT / "plugins"
PLUGINS_CLAUDE_DIR = PLUGINS_DIR / "claude"
PLUGINS_AGY_DIR = PLUGINS_DIR / "antigravity"
MARKETPLACE_JSON = WORKSPACE_ROOT / ".claude-plugin" / "marketplace.json"

ORCHESTRATORS = {"senior-dev-orchestrator", "flutter-feature-orchestrator", "python-backend-orchestrator"}

CLAUDE_ORCHESTRATOR_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Agent"]
CLAUDE_WORKER_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]

PLUGIN_AGENTS_MAP = {
    "senior-dev": [
        "senior-dev-orchestrator.md",
        "product-analyst.md",
        "ui-ux-designer.md",
        "architect-engineer.md",
        "code-implementer.md",
        "qa-tester.md",
        "compliance-verifier.md",
    ],
    "senior-dev-flutter": [
        "flutter-feature-orchestrator.md",
        "flutter-architect.md",
        "flutter-implementer.md",
        "flutter-reviewer.md",
        "flutter-release-engineer.md",
    ],
    "python-backend": [
        "python-backend-orchestrator.md",
    ],
    "senior-data-engineer": [
        "senior-data-engineer.md",
    ],
    "shared-context": [
        "context-keeper.md",
    ],
    "sql-query-optimizer": [
        "sql-query-optimizer.md",
    ],
}

PLUGIN_DESCRIPTIONS = {
    "senior-dev": "Senior Developer Orchestrator and specialized subagents for SDLC execution using TDD, clean code, and automated verification.",
    "senior-dev-flutter": "Senior Flutter orchestrator, architecture decisions, profiling, and release engineering.",
    "senior-data-engineer": "Google Cloud data engineering subagent with BigQuery, Datastream, Dataform, and Pub/Sub MCP access.",
    "shared-context": "Cross-agent working memory: captures and restores architecture decisions across AI sessions.",
    "sql-query-optimizer": "Diagnoses and rewrites slow BigQuery and relational SQL queries using real execution plans.",
    "python-backend": "Production Python backend engineering skills: FastAPI, TDD, migrations, CI/CD, and performance.",
    "git-workflow": "Gitflow workflow branch safety and conventional pull request verification.",
    "docs-and-quality": "Documentation standards, test-driven development, and Karpathy guidelines.",
    "multi-agent-ops": "Self-correcting loop engineering and automated codebase research.",
    "agent-metrics": "Optional: token, cost and latency metrics per project, task and subagent via the standalone agent-meter CLI.",
}


def parse_frontmatter(content: str) -> tuple[dict, str]:
    match = re.search(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError("Invalid YAML frontmatter")
    fm = yaml.safe_load(match.group(1))
    body = match.group(2)
    return fm, body


def sanitize_claude_body(text: str) -> str:
    """Sanitizes Antigravity tool and policy references in markdown bodies into Claude Code equivalents."""
    text = re.sub(
        r'invoke_subagent\(name="([^"]+)",\s*prompt="([^"]+)"\)',
        r'Agent(agent="\1", prompt="\2")',
        text,
    )
    text = re.sub(
        r'invoke_subagent\(name="([^"]+)"\)',
        r'Agent(agent="\1")',
        text,
    )
    text = re.sub(r"commandExecutionPolicy:\s*['\"]?auto['\"]?", "permissionMode: default", text)
    text = re.sub(r"\bcommandExecutionPolicy\b", "permissionMode", text)
    text = re.sub(r"\binvoke_subagent\b", "Agent", text)
    text = re.sub(r"\bmanage_subagents\b", "Agent", text)
    text = re.sub(r"\bsend_message\b", "Agent", text)
    text = re.sub(r"\bwrite_to_file\b", "Write", text)
    text = re.sub(r"\breplace_file_content\b", "Edit", text)
    text = re.sub(r"\bview_file\b", "Read", text)
    text = re.sub(r"\brun_command\b", "Bash", text)
    text = re.sub(r"\blist_dir\b", "Glob", text)
    text = re.sub(r"\bgrep_search\b", "Grep", text)
    text = re.sub(r"\bfind_by_name\b", "Glob", text)
    text = re.sub(
        r"In \*\*Google Antigravity\*\*:\s*Use `Write` and `Edit`",
        "In **Claude Code**: Use `Write` and `Edit`",
        text,
    )
    return text


def format_claude_agent(content: str, name: str) -> str:
    fm, body = parse_frontmatter(content)
    is_orch = name in ORCHESTRATORS
    tools = CLAUDE_ORCHESTRATOR_TOOLS if is_orch else CLAUDE_WORKER_TOOLS

    claude_fm = {
        "name": name,
        "description": fm.get("description", ""),
        "model": "inherit",
        "permissionMode": "default",
        "tools": tools,
    }
    if fm.get("skills"):
        claude_fm["skills"] = fm["skills"]

    sanitized_body = sanitize_claude_body(body)
    dumped = yaml.dump(claude_fm, sort_keys=False, allow_unicode=True)
    return f"---\n{dumped}---\n{sanitized_body}"


def sanitize_claude_skill_dir(target_dir: Path) -> None:
    """Sanitizes Antigravity tool names in copied Claude skill files."""
    for root, _, files in os.walk(target_dir):
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix.lower() in {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".sql"}:
                try:
                    content = fpath.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                sanitized = sanitize_claude_body(content)
                if sanitized != content:
                    fpath.write_text(sanitized, encoding="utf-8")


def _extra_manifest_keys(manifest_path: Path, generated: dict) -> dict:
    """Keys a hand-maintained Claude manifest adds on top of the generated ones (e.g. "hooks")."""
    if not manifest_path.is_file():
        return {}
    try:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {manifest_path}: {exc}") from exc
    if not isinstance(existing, dict):
        raise ValueError(f"{manifest_path} must contain a JSON object")
    return {key: value for key, value in existing.items() if key not in generated}


def sync_claude_plugins() -> None:
    PLUGINS_CLAUDE_DIR.mkdir(parents=True, exist_ok=True)

    for plugin_name in PLUGIN_DESCRIPTIONS.keys():
        src_plugin = PLUGINS_AGY_DIR / plugin_name
        dest_plugin = PLUGINS_CLAUDE_DIR / plugin_name
        dest_plugin.mkdir(parents=True, exist_ok=True)

        # 1. .claude-plugin/plugin.json
        claude_plugin_dir = dest_plugin / ".claude-plugin"
        claude_plugin_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "name": plugin_name,
            "version": "1.0.0",
            "description": PLUGIN_DESCRIPTIONS.get(plugin_name, f"{plugin_name} plugin for Claude Code"),
            "author": {
                "name": "jggomez"
            }
        }
        manifest.update(_extra_manifest_keys(claude_plugin_dir / "plugin.json", manifest))
        (claude_plugin_dir / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        # 2. agents/ (with pure Claude tools and sanitized body if plugin has agents)
        if plugin_name in PLUGIN_AGENTS_MAP:
            agent_files = PLUGIN_AGENTS_MAP[plugin_name]
            agents_dir = dest_plugin / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)
            for afname in agent_files:
                src_af = src_plugin / "agents" / afname
                raw_content = src_af.read_text(encoding="utf-8")
                claude_text = format_claude_agent(raw_content, src_af.stem)
                (agents_dir / afname).write_text(claude_text, encoding="utf-8")

        # 3. skills/ (copied and sanitized for Claude Code)
        src_skills = src_plugin / "skills"
        if src_skills.is_dir():
            dest_skills = dest_plugin / "skills"
            if dest_skills.exists():
                shutil.rmtree(dest_skills)
            shutil.copytree(src_skills, dest_skills)
            sanitize_claude_skill_dir(dest_skills)

        # 4. hooks/ & hooks.json (do NOT overwrite existing Claude-native hooks or hooks.json)
        src_hooks_dir = src_plugin / "hooks"
        if src_hooks_dir.is_dir():
            dest_hooks_dir = dest_plugin / "hooks"
            dest_hooks_dir.mkdir(parents=True, exist_ok=True)
            for hook_file in src_hooks_dir.iterdir():
                dest_hook_file = dest_hooks_dir / hook_file.name
                if hook_file.is_file() and not dest_hook_file.exists():
                    shutil.copy2(hook_file, dest_hook_file)

        src_hooks_json = src_plugin / "hooks.json"
        dest_hooks_json = dest_plugin / "hooks.json"
        if src_hooks_json.is_file() and not dest_hooks_json.exists():
            shutil.copy2(src_hooks_json, dest_hooks_json)

        # 5. .mcp.json & mcp/
        src_mcp_json = src_plugin / ".mcp.json"
        if src_mcp_json.is_file():
            shutil.copy2(src_mcp_json, dest_plugin / ".mcp.json")

        src_mcp_dir = src_plugin / "mcp"
        if src_mcp_dir.is_dir():
            dest_mcp_dir = dest_plugin / "mcp"
            if dest_mcp_dir.exists():
                shutil.rmtree(dest_mcp_dir)
            shutil.copytree(src_mcp_dir, dest_mcp_dir)

        # 6. README.md (do NOT overwrite existing Claude-specific README.md)
        src_readme = src_plugin / "README.md"
        dest_readme = dest_plugin / "README.md"
        if src_readme.is_file() and not dest_readme.exists():
            shutil.copy2(src_readme, dest_readme)

        print(f"✅ Generated Claude plugin: {dest_plugin}")


def generate_marketplace_json() -> None:
    MARKETPLACE_JSON.parent.mkdir(parents=True, exist_ok=True)
    plugins_entry = []

    for plugin_name in sorted(PLUGIN_DESCRIPTIONS.keys()):
        plugins_entry.append({
            "name": plugin_name,
            "source": f"./plugins/claude/{plugin_name}",
            "description": PLUGIN_DESCRIPTIONS.get(plugin_name, f"{plugin_name} plugin"),
        })

    marketplace_data = {
        "$schema": "https://json.schemastore.org/claude-code-marketplace.json",
        "name": "expert-ai-developer-skills",
        "version": "1.0.0",
        "description": "Production-grade skills, subagents, and plugins for Claude Code and Google Antigravity.",
        "owner": {
            "name": "jggomez"
        },
        "plugins": plugins_entry
    }

    MARKETPLACE_JSON.write_text(json.dumps(marketplace_data, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Generated Claude Code marketplace catalog: {MARKETPLACE_JSON}")


def main() -> None:
    print("🚀 Synchronizing plugins (Everything is a Plugin)...")
    sync_claude_plugins()
    generate_marketplace_json()
    print("🎉 All plugin targets synchronized successfully!")


if __name__ == "__main__":
    main()
