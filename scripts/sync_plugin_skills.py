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
        "context-capture",
        "context-restore",
        "loop-engineering",
    ],
    "agent-metrics": ["agent-metrics"],
}

IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")

FORBIDDEN_CLAUDE_TOOLS = [
    "run_command",
    "write_to_file",
    "replace_file_content",
    "invoke_subagent",
    "manage_subagents",
]


def sanitize_claude_content(text: str) -> str:
    """Sanitizes Antigravity tool references into Claude Code native equivalents."""
    # 1. invoke_subagent invocations
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
    text = re.sub(
        r'invoke_subagent\(([^)]+)\)',
        r'Agent(\1)',
        text,
    )

    # 2. Bare tool name replacements
    text = re.sub(r'\binvoke_subagent\b', 'Agent', text)
    text = re.sub(r'\bmanage_subagents\b', 'Agent', text)
    text = re.sub(r'\bsend_message\b', 'Agent', text)
    text = re.sub(r'\bwrite_to_file\b', 'Write', text)
    text = re.sub(r'\breplace_file_content\b', 'Edit', text)
    text = re.sub(r'\bview_file\b', 'Read', text)
    text = re.sub(r'\brun_command\b', 'Bash', text)

    return text


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
    for plugin, skills in PLUGIN_BUNDLED_SKILLS.items():
        for name in skills:
            # Sync to Antigravity
            if sync_skill(plugin, name, "antigravity"):
                print(f"[antigravity/{plugin}] synced {name}")
            else:
                failed = True

            # Sync to Claude Code
            if sync_skill(plugin, name, "claude"):
                print(f"[claude/{plugin}] synced {name}")
            else:
                failed = True

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
