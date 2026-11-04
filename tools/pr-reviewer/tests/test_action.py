"""Security invariants of the composite action and the published workflows."""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent.parent
ACTION = yaml.safe_load((ROOT / "action.yml").read_text())
STEPS = ACTION["runs"]["steps"]
SHA_PIN = re.compile(r"@[0-9a-f]{40}$")


def step(step_id: str) -> dict:
    return next(s for s in STEPS if s.get("id") == step_id)


def test_inputs_never_reach_a_shell_through_template_expansion():
    # Act
    offenders = [s.get("name") for s in STEPS if "${{" in s.get("run", "")]

    # Assert: `${{ }}` in `run` is script injection; values must go through `env`
    assert offenders == []


def test_third_party_actions_are_pinned_by_sha():
    # Act
    uses = [s["uses"] for s in STEPS if "uses" in s]

    # Assert
    assert uses
    assert all(SHA_PIN.search(u) for u in uses)


def test_ai_key_reaches_only_the_review_step():
    # Act
    holders = [s["id"] for s in STEPS if "inputs.api-key" in str(s.get("env", {}))]

    # Assert
    assert holders == ["review"]


def test_review_step_has_no_github_token():
    # Act
    review = step("review")

    # Assert
    assert "GITHUB_TOKEN" not in review.get("env", {})
    assert "github-token" not in str(review)
    assert "github.token" not in str(review)


def test_checkout_does_not_keep_credentials():
    # Act
    checkout = step("checkout")

    # Assert
    assert checkout["with"]["persist-credentials"] is False


def test_steps_after_the_gate_only_run_when_it_allows():
    # Act
    gated = STEPS[[s.get("id") for s in STEPS].index("context") + 1 :]

    # Assert
    assert gated
    assert all("should_run == 'true'" in s["if"] for s in gated)


def test_no_step_can_turn_the_job_red():
    # Act
    offenders = [s.get("name") for s in STEPS if s.get("continue-on-error") is not True]

    # Assert
    assert offenders == []


def test_uv_version_is_pinned():
    # Act
    setup = next(s for s in STEPS if "setup-uv" in s.get("uses", ""))

    # Assert
    assert re.fullmatch(r"\d+\.\d+\.\d+", setup["with"]["version"])


@pytest.mark.parametrize("path", [ROOT / "examples" / "pr-review.yml", REPO_ROOT / ".github" / "workflows" / "pr-review.yml"])
def test_concurrency_is_on_the_job_so_ignored_comments_cannot_cancel_a_review(path: Path):
    # Act
    workflow = yaml.safe_load(path.read_text())

    # Assert
    assert "concurrency" not in workflow
    assert workflow["jobs"]["review"]["concurrency"]["cancel-in-progress"] is True


@pytest.mark.parametrize("path", [ROOT / "examples" / "pr-review.yml", REPO_ROOT / ".github" / "workflows" / "pr-review.yml"])
def test_workflows_use_minimal_permissions_and_never_pull_request_target(path: Path):
    # Act
    text = path.read_text()
    workflow = yaml.safe_load(text)

    # Assert
    assert "pull_request_target" not in text
    permissions = workflow["jobs"]["review"]["permissions"]
    assert permissions == {"contents": "read", "pull-requests": "write"}
