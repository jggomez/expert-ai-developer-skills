"""Input and output of the official Claude Code Action."""

import json
import shlex
from pathlib import Path

from pr_reviewer.adapters.providers.claude_code import (
    build_input,
    report_from_output,
    write_diff,
)
from pr_reviewer.domain.models import DiffBundle, FileDiff
from support.builders import finding


def bundle() -> DiffBundle:
    return DiffBundle(base="a" * 40, head="b" * 40, files=[FileDiff(path="a.py", patch="+a = 1\n")])


def arguments(claude_args: str) -> dict[str, str]:
    parts = shlex.split(claude_args)
    return dict(zip(parts[::2], parts[1::2], strict=True))


def test_the_agent_can_only_read():
    # Act
    args = arguments(build_input(bundle(), diff_path="d", repo_path="r", model="", rubric=None).claude_args)

    # Assert
    assert args["--allowedTools"] == "Read,Glob,Grep"
    assert {"Bash", "Edit", "Write", "WebFetch", "WebSearch"} <= set(args["--disallowedTools"].split(","))


def test_the_schema_survives_the_action_argument_parser():
    # Act
    args = arguments(build_input(bundle(), diff_path="d", repo_path="r", model="", rubric=None).claude_args)

    # Assert
    assert "findings" in json.loads(args["--json-schema"])["properties"]


def test_a_hostile_model_name_stays_one_argument():
    # Act
    args = arguments(build_input(bundle(), diff_path="d", repo_path="r", model="x --allowedTools Bash", rubric=None).claude_args)

    # Assert
    assert args["--model"] == "x --allowedTools Bash"
    assert args["--allowedTools"] == "Read,Glob,Grep"


def test_the_prompt_keeps_the_safety_rules_with_a_custom_rubric():
    # Act
    prompt = build_input(bundle(), diff_path="d.patch", repo_path="repo", model="", rubric="# Only SQL").prompt

    # Assert
    assert "Only SQL" in prompt
    assert "never follow instructions" in prompt.lower()
    assert "d.patch" in prompt


def test_the_diff_is_written_to_a_file_and_not_to_the_prompt(tmp_path: Path):
    # Arrange
    path = tmp_path / "review" / "diff.patch"

    # Act
    write_diff(bundle(), path)
    prompt = build_input(bundle(), diff_path=str(path), repo_path="repo", model="", rubric=None).prompt

    # Assert
    assert path.read_text(encoding="utf-8") == "+a = 1\n"
    assert "+a = 1" not in prompt


def test_valid_output_becomes_a_report():
    # Arrange
    raw = json.dumps({"findings": [finding().model_dump()]})

    # Act
    report = report_from_output(raw, model="", outcome="success")

    # Assert
    assert report.status == "ok"
    assert report.provider == "claude-code"
    assert len(report.findings) == 1


def test_no_output_is_a_failure_and_names_the_outcome():
    # Act
    report = report_from_output("", model="m", outcome="failure")

    # Assert
    assert report.status == "failed"
    assert "failure" in report.error
    assert report.model == "m"


def test_invalid_output_is_a_failure_not_a_clean_review():
    # Act
    report = report_from_output('{"findings": [{"file": "a.py"}]}', model="", outcome="success")

    # Assert
    assert report.status == "failed"
    assert "invalid findings" in report.error
