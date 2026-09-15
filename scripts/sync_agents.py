#!/usr/bin/env python3
"""Unified Agent and Plugin Synchronizer for Google Antigravity & Claude Code.

Everything is a Plugin:
1. Canonical agent definitions live directly inside plugins/<plugin>/agents/*.md.
2. Generates plugins/claude/<plugin>/ with pure Claude Code subagents, skills, hooks, and .claude-plugin/plugin.json.
3. Links plugins/antigravity/<plugin>/ to canonical plugins/<plugin>/ for symmetrical CLI installation.
4. Generates .claude-plugin/marketplace.json so Claude Code users can install via marketplace.

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

ORCHESTRATORS = {"senior-dev-orchestrator", "flutter-feature-orchestrator"}

CLAUDE_ORCHESTRATOR_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Agent"]
CLAUDE_WORKER_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]

PLUGIN_AGENTS_MAP = {
    "senior-dev": [
        "senior-dev-orchestrator.md",
        "product-analyst.md",
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
}


def parse_frontmatter(content: str) -> tuple[dict, str]:
    match = re.search(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError("Invalid YAML frontmatter")
    fm = yaml.safe_load(match.group(1))
    body = match.group(2)
    return fm, body


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
    dumped = yaml.dump(claude_fm, sort_keys=False, allow_unicode=True)
    return f"---\n{dumped}---\n{body}"


def sync_claude_plugins() -> None:
    PLUGINS_CLAUDE_DIR.mkdir(parents=True, exist_ok=True)

    for plugin_name, agent_files in PLUGIN_AGENTS_MAP.items():
        src_plugin = PLUGINS_DIR / plugin_name
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
        (claude_plugin_dir / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        # 2. agents/ (with pure Claude tools)
        agents_dir = dest_plugin / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        for afname in agent_files:
            src_af = src_plugin / "agents" / afname
            raw_content = src_af.read_text(encoding="utf-8")
            claude_text = format_claude_agent(raw_content, src_af.stem)
            (agents_dir / afname).write_text(claude_text, encoding="utf-8")

        # 3. skills/
        src_skills = src_plugin / "skills"
        if src_skills.is_dir():
            dest_skills = dest_plugin / "skills"
            if dest_skills.exists():
                shutil.rmtree(dest_skills)
            shutil.copytree(src_skills, dest_skills)

        # 4. hooks/ & hooks.json
        src_hooks_dir = src_plugin / "hooks"
        if src_hooks_dir.is_dir():
            dest_hooks_dir = dest_plugin / "hooks"
            if dest_hooks_dir.exists():
                shutil.rmtree(dest_hooks_dir)
            shutil.copytree(src_hooks_dir, dest_hooks_dir)

        src_hooks_json = src_plugin / "hooks.json"
        if src_hooks_json.is_file():
            shutil.copy2(src_hooks_json, dest_plugin / "hooks.json")

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

        # 6. README.md
        src_readme = src_plugin / "README.md"
        if src_readme.is_file():
            shutil.copy2(src_readme, dest_plugin / "README.md")

        print(f"✅ Generated Claude plugin: {dest_plugin}")


def sync_antigravity_plugin_links() -> None:
    PLUGINS_AGY_DIR.mkdir(parents=True, exist_ok=True)
    for plugin_name in PLUGIN_AGENTS_MAP:
        dest_link = PLUGINS_AGY_DIR / plugin_name
        target = Path("..") / plugin_name
        if dest_link.is_symlink() or dest_link.exists():
            dest_link.unlink(missing_ok=True)
        dest_link.symlink_to(target, target_is_directory=True)
    print(f"✅ Linked Antigravity plugins in {PLUGINS_AGY_DIR}")


def generate_marketplace_json() -> None:
    MARKETPLACE_JSON.parent.mkdir(parents=True, exist_ok=True)
    plugins_entry = []

    # 1. Claude-specialized plugins (with pure Claude agents)
    for plugin_name in sorted(PLUGIN_AGENTS_MAP.keys()):
        plugins_entry.append({
            "name": plugin_name,
            "source": f"./plugins/claude/{plugin_name}",
            "description": PLUGIN_DESCRIPTIONS.get(plugin_name, f"{plugin_name} plugin"),
        })

    # 2. Universal non-agent plugins (shared skills/hooks)
    for pdir in sorted(PLUGINS_DIR.iterdir()):
        if not pdir.is_dir() or pdir.name in ("claude", "antigravity", ".DS_Store"):
            continue
        if pdir.name in PLUGIN_AGENTS_MAP:
            continue
        plugins_entry.append({
            "name": pdir.name,
            "source": f"./plugins/{pdir.name}",
            "description": PLUGIN_DESCRIPTIONS.get(pdir.name, f"{pdir.name} developer skills plugin"),
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
    sync_antigravity_plugin_links()
    generate_marketplace_json()
    print("🎉 All plugin targets synchronized successfully!")


if __name__ == "__main__":
    main()
