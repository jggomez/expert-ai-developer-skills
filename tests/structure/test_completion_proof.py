"""Track 42: qa-tester proves a change is finished (tests, build, images), and the orchestrator
never reports a change as done without that proof."""
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOSTS = ["antigravity", "claude"]
ORCHESTRATORS = [
    ("senior-dev", "senior-dev-orchestrator"),
    ("senior-dev-flutter", "flutter-feature-orchestrator"),
    ("python-backend", "python-backend-orchestrator"),
]
PROOF_LINES = ["**Requirements**", "**Tests**", "**Build**", "**Static checks**", "**Images**", "**Verdict**"]


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _agent(host, plugin, agent):
    # Claude Code ships shared specialists only in senior-dev; other plugins depend on it.
    if host == "claude" and not os.path.exists(os.path.join(ROOT, "plugins", host, plugin, "agents", f"{agent}.md")):
        plugin = "senior-dev"
    return _read("plugins", host, plugin, "agents", f"{agent}.md")


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin", ["senior-dev", "senior-dev-flutter", "python-backend"])
def test_qa_tester_writes_a_completion_proof(host, plugin):
    # Arrange
    body = _agent(host, plugin, "qa-tester")
    # Act
    missing = [line for line in ["# Completion Proof"] + PROOF_LINES if line not in body]
    # Assert
    assert not missing, f"{host}/{plugin}/qa-tester.md is missing: {missing}"
    assert "check_evidence.py" in body and "`NOT DONE`" in body


def test_qa_skill_and_template_carry_the_completion_proof():
    # Arrange
    skill = _read("skills", "qa-tester", "SKILL.md")
    template = _read("skills", "qa-tester", "references", "test-matrix-template.md")
    # Act / Assert
    assert "Completion Proof" in skill
    assert "## 3. Completion Proof" in template
    for line in PROOF_LINES:
        assert line in template, line
    assert len(template.splitlines()) <= 50


def test_flutter_test_strategy_requires_a_build_proof():
    # Arrange / Act
    body = _read("skills", "flutter-test-strategy", "SKILL.md")
    # Assert
    assert "Completion Proof" in body and "flutter build" in body


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin,agent", ORCHESTRATORS)
def test_orchestrators_never_report_done_without_proof(host, plugin, agent):
    # Arrange
    body = _agent(host, plugin, agent)
    # Act / Assert
    assert "### Completion Proof Gate" in body
    assert "never tell the user a change is done" in body


@pytest.mark.parametrize("skill", ["senior-dev-orchestrator", "flutter-senior-orchestration"])
def test_orchestration_skills_carry_the_gate(skill):
    # Arrange / Act
    body = _read("skills", skill, "SKILL.md")
    # Assert
    assert "Completion Proof Gate" in body
