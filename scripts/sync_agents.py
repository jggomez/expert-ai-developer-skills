#!/usr/bin/env python3
"""Sync and mirror Antigravity agent definitions.

1. Mirrors canonical agents from /agents/*.md into /.agents/agents/*.md
   so Google Antigravity auto-discovers all 14 subagents in the workspace.
2. Synchronizes updates to/from plugin agent definitions where applicable.

Usage:
    python3 scripts/sync_agents.py
"""
import os
import shutil
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = WORKSPACE_ROOT / "agents"
DOT_AGENTS_DIR = WORKSPACE_ROOT / ".agents" / "agents"
PLUGINS_DIR = WORKSPACE_ROOT / "plugins"

# Map plugin agents to canonical root agents
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


def sync_agents(target_dirs: list[Path] | None = None) -> None:
    targets = [DOT_AGENTS_DIR]
    if target_dirs:
        targets.extend(target_dirs)

    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        count = 0
        for agent_file in AGENTS_DIR.glob("*.md"):
            if agent_file.name == "README.md":
                continue
            dest = target / agent_file.name
            shutil.copy2(agent_file, dest)
            count += 1
        print(f"✅ Successfully mirrored {count} agents to {target}")


if __name__ == "__main__":
    extra_dirs = [Path(arg).resolve() for arg in sys.argv[1:]] if len(sys.argv) > 1 else None
    sync_agents(extra_dirs)

