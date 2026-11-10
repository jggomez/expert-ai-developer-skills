#!/usr/bin/env python3
"""Sync canonical skills from /skills into each plugin's bundled copy.

Every plugin ships a physical copy of the /skills subset it needs so it
stays self-contained when distributed on its own.

Synchronizes canonical /skills into BOTH:
  - plugins/antigravity/<plugin>/skills/
  - plugins/claude/<plugin>/skills/

When copying to plugins/claude/, tool sanitization is applied to ensure no
Antigravity tool names (run_command, write_to_file, replace_file_content,
invoke_subagent, manage_subagents) are introduced into plugins/claude/.

Usage: python3 scripts/sync_plugin_skills.py
"""
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_sync_config import (  # noqa: E402
    FORBIDDEN_CLAUDE_TOKENS,
    claude_excluded_skills,
    sanitize_claude_content,
)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SKILLS_DIR = WORKSPACE_ROOT / "skills"
ANTIGRAVITY_PLUGINS_DIR = WORKSPACE_ROOT / "plugins" / "antigravity"
CLAUDE_PLUGINS_DIR = WORKSPACE_ROOT / "plugins" / "claude"

# Must match each plugin's "Bundled Skills" list in its own README.md
PLUGIN_BUNDLED_SKILLS = {
    "python-backend": [
        "python-expert",
        "test-driven-development",
        "pull-request-expert",
        "code-smells-expert",
        "refactoring-code-expert",
        "security-audit",
        "performance-scalability",
        "database-migration-expert",
        "senior-architect-engineering",
        "design-spec-expert",
        "build-and-ci-gates",
        "context-capture",
        "context-restore",
        "loop-engineering",
    ],
    "senior-dev": [
        "senior-dev-orchestrator",
        "product-analyst",
        "ui-ux-designer",
        "senior-architect-engineering",
        "code-implementer",
        "code-smells-expert",
        "refactoring-code-expert",
        "qa-tester",
        "compliance-verifier",
        "code-critic",
        "adversarial-challenger",
        "blackbox-tester",
        "context-capture",
        "context-restore",
        "loop-engineering",
    ],
    "git-workflow": [
        "commit-expert",
        "pull-request-expert",
    ],
    "docs-and-quality": [
        "documentation-expert",
        "testing-expert",
        "guidelines-karpathy",
    ],
    "multi-agent-ops": [
        "loop-engineering",
        "repo-research",
    ],
    "senior-data-engineer": [
        "gcp-data-engineering",
        "cdc-scd-patterns",
        "context-capture",
        "context-restore",
    ],
    "sql-query-optimizer": [
        "bigquery-query-optimization",
        "sql-query-optimization",
        "context-capture",
        "context-restore",
    ],
    "shared-context": [
        "context-capture",
        "context-restore",
    ],
    "senior-dev-flutter": [
        "flutter-senior-orchestration",
        "flutter-architecture-decisions",
        "flutter-review-checklist",
        "flutter-test-strategy",
        "flutter-performance-profiling",
        "flutter-release-engineering",
        "flutter-upgrade-migration",
        "ui-ux-designer",
        "context-capture",
        "context-restore",
        "loop-engineering",
    ],
    "agent-metrics": ["agent-metrics"],
}

# Antigravity has no plugin dependencies: these plugins carry copies of the senior-dev
# specialists (scripts/sync_agents.py BUNDLED_AGENTS), so they also need the skills those
# agents preload. Claude Code uses plugin "dependencies" instead (claude_sync_config).
ANTIGRAVITY_EXTRA_SKILLS = {
    "python-backend": [
        "product-analyst",
        "ui-ux-designer",
        "code-implementer",
        "qa-tester",
        "compliance-verifier",
        "code-critic",
        "adversarial-challenger",
        "blackbox-tester",
    ],
    "senior-dev-flutter": [
        "product-analyst",
        "qa-tester",
        "compliance-verifier",
        "code-critic",
        "code-smells-expert",
        "refactoring-code-expert",
        "adversarial-challenger",
        "test-driven-development",
        "blackbox-tester",
    ],
}


def antigravity_skills(plugin: str) -> list[str]:
    base = PLUGIN_BUNDLED_SKILLS[plugin]
    return base + [s for s in ANTIGRAVITY_EXTRA_SKILLS.get(plugin, []) if s not in base]


def claude_skills(plugin: str) -> list[str]:
    excluded = claude_excluded_skills(plugin, PLUGIN_BUNDLED_SKILLS)
    return [s for s in PLUGIN_BUNDLED_SKILLS[plugin] if s not in excluded]


IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")

FORBIDDEN_CLAUDE_TOOLS = FORBIDDEN_CLAUDE_TOKENS




def sanitize_claude_skill_dir(target_dir: Path) -> None:
    """Walks the copied skill directory and replaces Antigravity tool names in text files."""
    for root, _, files in os.walk(target_dir):
        for fname in files:
            fpath = Path(root) / fname
            # Only process text-like files
            if fpath.suffix.lower() in {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".sql"}:
                try:
                    content = fpath.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue

                sanitized = sanitize_claude_content(content)
                if sanitized != content:
                    fpath.write_text(sanitized, encoding="utf-8")

                # Verify no forbidden Antigravity tools remain
                for forbidden in FORBIDDEN_CLAUDE_TOOLS:
                    if forbidden in sanitized:
                        print(
                            f"WARNING: Forbidden tool '{forbidden}' found in {fpath.relative_to(WORKSPACE_ROOT)}",
                            file=sys.stderr,
                        )


def sync_skill(plugin: str, name: str, ecosystem: str) -> bool:
    source = SOURCE_SKILLS_DIR / name

    if ecosystem == "antigravity":
        target = ANTIGRAVITY_PLUGINS_DIR / plugin / "skills" / name
    elif ecosystem == "claude":
        target = CLAUDE_PLUGINS_DIR / plugin / "skills" / name
    else:
        raise ValueError(f"Unknown ecosystem: {ecosystem}")

    if not source.is_dir():
        print(f"ERROR: {name} not found under {SOURCE_SKILLS_DIR}", file=sys.stderr)
        return False

    if target.is_dir():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=IGNORE)

    if ecosystem == "claude":
        sanitize_claude_skill_dir(target)

    return True


def main() -> None:
    failed = False
    for plugin in PLUGIN_BUNDLED_SKILLS:
        for ecosystem, names in (("antigravity", antigravity_skills(plugin)), ("claude", claude_skills(plugin))):
            for name in names:
                if sync_skill(plugin, name, ecosystem):
                    print(f"[{ecosystem}/{plugin}] synced {name}")
                else:
                    failed = True

        # Claude Code: drop skills a declared plugin dependency already ships.
        for name in sorted(claude_excluded_skills(plugin, PLUGIN_BUNDLED_SKILLS)):
            stale = CLAUDE_PLUGINS_DIR / plugin / "skills" / name
            if stale.is_dir():
                shutil.rmtree(stale)
                print(f"[claude/{plugin}] removed {name} (provided by a plugin dependency)")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
