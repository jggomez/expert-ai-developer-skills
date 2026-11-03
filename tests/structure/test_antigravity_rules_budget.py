"""Antigravity rules hold constraints, not workflows, and stay cheap.

antigravity.google/docs/rules: `always_on` rules are injected in full into the system prompt on
every turn (shared 20k-token budget); `glob` rules load only when the agent touches matching
files; `model_decision` rules load only their description until the task matches. "Write a rule
for constraints and invariants" and a skill for multi-step workflows: the SDLC state machine
lives in the orchestrator agents and the loop-engineering skill, never in a rule.
"""
import glob
import os
import re

import pytest
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RULES = sorted(glob.glob(os.path.join(ROOT, "plugins", "antigravity", "*", "rules", "*.md")))

EXPECTED_TRIGGERS = {
    "senior-dev-rules.md": "always_on",
    "docs-and-quality-rules.md": "always_on",
    "gitflow-rules.md": "always_on",
    "flutter-rules.md": "glob",
    "python-backend-rules.md": "glob",
    "data-engineer-rules.md": "glob",
    "sql-optimization-rules.md": "model_decision",
    "multi-agent-ops-rules.md": "model_decision",
    "shared-context-rules.md": "model_decision",
    "git-hooks.md": "model_decision",
}
ALWAYS_ON_MAX_BYTES = 2600       # ~650 tokens per file
ALWAYS_ON_TOTAL_MAX_BYTES = 7000  # every always_on rule of every plugin together
WORKFLOW_MARKERS = ("[STATE 0", "STATE 0:", "| Tier 1", "6-State", "Invoke / SKIP")


def _parse(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    assert match, f"{path}: missing frontmatter"
    return yaml.safe_load(match.group(1)), text


@pytest.mark.parametrize("path", RULES, ids=lambda p: os.path.relpath(p, ROOT))
def test_rule_uses_the_cheapest_documented_trigger(path):
    # Arrange
    fm, text = _parse(path)
    name = os.path.basename(path)
    # Act / Assert
    assert fm.get("trigger") == EXPECTED_TRIGGERS[name], f"{name}: trigger {fm.get('trigger')}"
    assert fm.get("description"), f"{name}: description is required for model_decision and recommended for all"
    if fm["trigger"] == "glob":
        assert fm.get("globs"), f"{name}: a glob rule needs globs"
    if fm["trigger"] == "always_on":
        assert len(text.encode("utf-8")) <= ALWAYS_ON_MAX_BYTES, f"{name}: always_on rule is too large"


@pytest.mark.parametrize("path", RULES, ids=lambda p: os.path.relpath(p, ROOT))
def test_rules_do_not_restate_the_orchestrator_workflow(path):
    # Arrange
    _, text = _parse(path)
    # Act
    found = [m for m in WORKFLOW_MARKERS if m in text]
    # Assert
    assert not found, f"{os.path.basename(path)} restates the SDLC workflow: {found}"


def test_always_on_rules_fit_a_small_budget():
    # Arrange / Act
    total = sum(len(open(p, encoding="utf-8").read().encode("utf-8")) for p in RULES if _parse(p)[0]["trigger"] == "always_on")
    # Assert
    assert total <= ALWAYS_ON_TOTAL_MAX_BYTES, f"always_on rules total {total} bytes"
