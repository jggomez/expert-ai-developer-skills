"""Track 41: every user request is re-triaged, and tests run only for what changed.

Seen on real runs: after the first request the orchestrator reused its first Invoke/SKIP triage
for every later request (product, design and architecture never reconsidered), test-matrix.md was
never extended, and the full suite ran once per implementer, again at fan-in, again in qa-tester and
again in compliance-verifier.
"""
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOSTS = ["antigravity", "claude"]
ORCHESTRATORS = [
    ("senior-dev", "senior-dev-orchestrator"),
    ("senior-dev-flutter", "flutter-feature-orchestrator"),
    ("python-backend", "python-backend-orchestrator"),
]
QA_TESTERS = ["senior-dev", "senior-dev-flutter", "python-backend"]
IMPLEMENTERS = [
    ("senior-dev", "code-implementer"),
    ("python-backend", "code-implementer"),
    ("senior-dev-flutter", "flutter-implementer"),
]
VERIFIERS = [
    ("senior-dev", "compliance-verifier"),
    ("python-backend", "compliance-verifier"),
    ("senior-dev-flutter", "flutter-reviewer"),
]
DISCOVERY = [
    ("senior-dev", "product-analyst"),
    ("senior-dev", "ui-ux-designer"),
    ("senior-dev", "architect-engineer"),
    ("python-backend", "product-analyst"),
    ("python-backend", "ui-ux-designer"),
    ("python-backend", "architect-engineer"),
    ("senior-dev-flutter", "product-analyst"),
    ("senior-dev-flutter", "ui-ux-designer"),
    ("senior-dev-flutter", "flutter-architect"),
]
CHANGE_RULES = [
    "## Every Request Is a Change",  # "###" in agents, "##" in skills
    "**One user message = one change**",
    "never copy the previous row",
    "## Changes",
]
QA_RULES = [
    "**Extend, never replace**",
    "**Skip what is already proven**",
    "**Affected tests first**",
    "**Full suite at most once per change**",
    "Last full run",
]


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _agent(host, plugin, agent):
    # Claude Code ships shared specialists only in senior-dev; other plugins depend on it.
    if host == "claude" and not os.path.exists(os.path.join(ROOT, "plugins", host, plugin, "agents", f"{agent}.md")):
        plugin = "senior-dev"
    return _read("plugins", host, plugin, "agents", f"{agent}.md")


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin,agent", ORCHESTRATORS)
def test_orchestrators_triage_every_request_again(host, plugin, agent):
    # Arrange
    body = _agent(host, plugin, agent)
    # Act
    missing = [rule for rule in CHANGE_RULES if rule not in body]
    # Assert
    assert not missing, f"{host}/{plugin}/{agent}.md is missing: {missing}"
    assert "Reusing a previous change's" in body, "red flag for a copied triage row is missing"


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin,agent", ORCHESTRATORS)
def test_orchestrators_leave_fan_in_tests_to_qa_tester(host, plugin, agent):
    # Arrange
    body = _agent(host, plugin, agent)
    # Act / Assert: the orchestrator no longer runs suites itself before qa-tester runs them again
    assert "At fan-in, run the affected suites once" not in body
    assert "At fan-in, `qa-tester` runs the affected tests once" in body


@pytest.mark.parametrize("skill", ["senior-dev-orchestrator", "flutter-senior-orchestration", "loop-engineering"])
def test_orchestration_skills_triage_every_request_again(skill):
    # Arrange
    body = _read("skills", skill, "SKILL.md")
    # Act
    missing = [rule for rule in CHANGE_RULES if rule not in body]
    # Assert
    assert not missing, f"skills/{skill} is missing: {missing}"


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin", QA_TESTERS)
def test_qa_testers_extend_the_matrix_and_test_only_what_changed(host, plugin):
    # Arrange
    body = _agent(host, plugin, "qa-tester")
    # Act
    missing = [rule for rule in QA_RULES if rule not in body]
    # Assert
    assert not missing, f"{host}/{plugin}/qa-tester.md is missing: {missing}"
    assert "Execute the full test suite (`exit code 0`)" not in body


@pytest.mark.parametrize("skill", ["qa-tester", "flutter-test-strategy"])
def test_test_skills_extend_the_matrix(skill):
    # Arrange
    body = _read("skills", skill, "SKILL.md")
    # Act / Assert
    for rule in ("**Extend, never replace**", "**Full suite at most once per change**"):
        assert rule in body, f"skills/{skill}: {rule}"


def test_matrix_template_records_the_change_and_last_full_run():
    # Arrange
    template = _read("skills", "qa-tester", "references", "test-matrix-template.md")
    # Act / Assert
    for field in ("**Change**", "**Affected run**", "**Last full run**", "C-01:"):
        assert field in template, field
    assert len(template.splitlines()) <= 50


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin,agent", IMPLEMENTERS)
def test_implementers_run_only_their_scoped_tests(host, plugin, agent):
    # Arrange
    body = _agent(host, plugin, agent)
    # Act / Assert
    assert "Full local unit test suite" not in body
    assert "never the full suite" in body
    assert "on the files you changed" in body


def test_code_implementer_skill_runs_only_scoped_tests():
    # Arrange
    body = _read("skills", "code-implementer", "SKILL.md")
    # Act / Assert
    assert "Execute the local unit test suite" not in body
    assert "leave the full suite to `qa-tester`" in body


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin,agent", VERIFIERS)
def test_verifiers_reuse_the_qa_tester_result(host, plugin, agent):
    # Arrange
    body = _agent(host, plugin, agent)
    # Act / Assert
    assert "Do not re-run the test suite" in body, f"{host}/{plugin}/{agent}.md"


def test_compliance_skill_reuses_the_qa_tester_result():
    # Arrange
    body = _read("skills", "compliance-verifier", "SKILL.md")
    # Act / Assert
    assert "Do not re-run the test suite" in body
    assert "Verify that 100% of tests pass" not in body


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin,agent", DISCOVERY)
def test_discovery_agents_append_the_change_delta(host, plugin, agent):
    # Arrange
    body = _agent(host, plugin, agent)
    # Act / Assert
    assert "**Change delta (later requests)**" in body, f"{host}/{plugin}/{agent}.md"


@pytest.mark.parametrize("skill", ["product-analyst", "ui-ux-designer", "senior-architect-engineering",
                                   "flutter-architecture-decisions"])
def test_discovery_skills_append_the_change_delta(skill):
    # Arrange
    body = _read("skills", skill, "SKILL.md")
    # Act / Assert
    assert "**Change delta (later requests)**" in body, f"skills/{skill}"
