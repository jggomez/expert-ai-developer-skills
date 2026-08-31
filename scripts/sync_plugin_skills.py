#!/usr/bin/env python3
"""Sync canonical skills from /skills into each plugin's bundled copy.

Every plugin ships a physical copy of the /skills subset it needs so it
stays self-contained when distributed on its own. Run this after editing any
bundled skill so both copies stay identical (enforced by
tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills).

Usage: python3 scripts/sync_plugin_skills.py
"""
import shutil
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SKILLS_DIR = WORKSPACE_ROOT / "skills"
PLUGINS_DIR = WORKSPACE_ROOT / "plugins"

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
    ],
    "senior-dev": [
        "senior-dev-orchestrator",
        "product-analyst",
        "senior-architect-engineering",
        "code-implementer",
        "code-smells-expert",
        "refactoring-code-expert",
        "qa-tester",
        "compliance-verifier",
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
    ],
    "sql-query-optimizer": [
        "bigquery-query-optimization",
        "sql-query-optimization",
    ],
    "shared-context": [
        "context-capture",
        "context-restore",
    ],
}

IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")


def sync_skill(plugin: str, name: str) -> bool:
    source = SOURCE_SKILLS_DIR / name
    target = PLUGINS_DIR / plugin / "skills" / name

    if not source.is_dir():
        print(f"ERROR: {name} not found under {SOURCE_SKILLS_DIR}", file=sys.stderr)
        return False

    if target.is_dir():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=IGNORE)
    return True


def main() -> None:
    failed = False
    for plugin, skills in PLUGIN_BUNDLED_SKILLS.items():
        for name in skills:
            if sync_skill(plugin, name):
                print(f"[{plugin}] synced {name}")
            else:
                failed = True

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
