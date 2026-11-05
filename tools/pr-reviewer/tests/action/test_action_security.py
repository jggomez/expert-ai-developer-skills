"""Security invariants of the composite action and the published workflows."""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parents[1]
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


def test_each_provider_only_receives_its_own_key_name():
    # Act
    script = step("review")["run"]

    # Assert
    assert 'export GEMINI_API_KEY="$API_KEY"' in script
    assert 'export ANTHROPIC_API_KEY="$API_KEY"' in script
    assert "GEMINI_API_KEY" not in step("review")["env"]


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


def test_the_subscription_token_reaches_only_the_official_action():
    # Act
    holders = [s.get("id") for s in STEPS if "oauth-token" in str(s.get("env", {})) or "oauth-token" in str(s.get("with", {}))]

    # Assert
    assert holders == ["claude_code"]


def test_claude_code_runs_after_the_raw_checkout_is_replaced_by_a_clean_copy():
    # Act
    prepare = step("prepare")

    # Assert
    assert "prepare-claude-code" in prepare["run"]
    assert [s.get("id") for s in STEPS].index("prepare") < [s.get("id") for s in STEPS].index("claude_code")


def test_only_one_provider_path_writes_the_report():
    # Act / Assert
    assert "!= 'claude-code'" in step("review")["if"]
    assert "== 'claude-code'" in step("collect")["if"]


def test_empty_inputs_fall_back_so_unset_repository_variables_are_harmless():
    # Arrange: `${{ vars.X }}` is empty when the variable does not exist, and the CLI owns the defaults.
    inputs = ACTION["inputs"]

    # Assert
    for name in set(inputs) - {"provider", "github-token"}:
        assert inputs[name].get("default", "") == "", name


@pytest.mark.parametrize("readme", ["README.md", "README.es.md", "docs/guide.md", "docs/guide.es.md"])
def test_every_input_is_documented(readme: str):
    # Arrange
    text = (ROOT / readme).read_text(encoding="utf-8")

    # Assert
    for name in ACTION["inputs"]:
        assert f"`{name}`" in text, name


def test_rubric_file_is_never_read_from_the_pull_request_checkout():
    # Arrange
    step = next(s for s in STEPS if s.get("id") == "review")

    # Assert: the base commit comes from the gate, not from a file in the PR.
    assert step["env"]["BASE_SHA"] == "${{ steps.context.outputs.base_sha }}"
    assert '--base "$BASE_SHA"' in step["run"]
