"""Track 43: screens must be wired to real sources. The architect (or the orchestrator) maps each
screen to its real source with a review checklist, qa-tester proves every row without mocks,
mobile Flutter runs on a device against the real backend, and reviewers answer the checklist."""
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOSTS = ["antigravity", "claude"]
ORCHESTRATORS = [
    ("senior-dev", "senior-dev-orchestrator"),
    ("senior-dev-flutter", "flutter-feature-orchestrator"),
    ("python-backend", "python-backend-orchestrator"),
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
@pytest.mark.parametrize("plugin,agent", [("senior-dev", "architect-engineer"), ("python-backend", "architect-engineer"),
                                          ("senior-dev-flutter", "flutter-architect")])
def test_architects_write_a_review_checklist_with_a_wiring_map(host, plugin, agent):
    body = _agent(host, plugin, agent)
    assert "### Review checklist" in body and "**Wiring map**" in body, f"{host}/{plugin}/{agent}"


@pytest.mark.parametrize("skill", ["senior-architect-engineering", "flutter-architecture-decisions"])
def test_architecture_skills_write_the_review_checklist(skill):
    assert "### Review checklist" in _read("skills", skill, "SKILL.md")


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin,agent", ORCHESTRATORS)
def test_orchestrators_require_a_wiring_map_and_real_mobile_runs(host, plugin, agent):
    body = _agent(host, plugin, agent)
    assert "**Wiring map**" in body
    assert "integration_test" in body and "real backend" in body


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin", ["senior-dev", "senior-dev-flutter", "python-backend"])
def test_qa_tester_proves_every_wiring_row_without_mocks(host, plugin):
    body = _agent(host, plugin, "qa-tester")
    assert "**Wiring**" in body and "no mocks" in body
    assert "flutter test integration_test" in body


def test_matrix_template_has_a_wiring_line():
    assert "**Wiring**" in _read("skills", "qa-tester", "references", "test-matrix-template.md")


def test_flutter_test_strategy_runs_mobile_against_the_real_backend():
    body = _read("skills", "flutter-test-strategy", "SKILL.md")
    assert "flutter test integration_test" in body and "real backend" in body


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin,agent", [("senior-dev", "critic"), ("senior-dev", "compliance-verifier"),
                                          ("python-backend", "compliance-verifier"),
                                          ("senior-dev-flutter", "flutter-reviewer")])
def test_reviewers_answer_the_review_checklist(host, plugin, agent):
    body = _agent(host, plugin, agent)
    assert "**Review checklist**" in body and "`OK`" in body, f"{host}/{plugin}/{agent}"


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin", ["senior-dev", "python-backend"])
def test_compliance_runs_the_fake_data_check_on_any_code_change(host, plugin):
    body = _agent(host, plugin, "compliance-verifier")
    assert "When UI changed, run" not in body
    assert "Whenever code changed, run" in body


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("plugin,agent", [("senior-dev", "code-implementer"), ("python-backend", "code-implementer"),
                                          ("senior-dev-flutter", "flutter-implementer")])
def test_implementers_wire_the_real_source(host, plugin, agent):
    assert "**Wire it for real**" in _agent(host, plugin, agent)
