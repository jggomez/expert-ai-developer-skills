"""Tests for ``agent_meter.setup.hosts`` and ``agent_meter.setup.prompter`` (wizard step 1, I/O)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from agent_meter.model import Host
from agent_meter.setup.hosts import (
    DetectedHost,
    antigravity_hooks_path,
    antigravity_plugin_installed,
    claude_plugin_installed,
    claude_settings_path,
    detect_hosts,
    parse_hosts,
)
from agent_meter.setup.prompter import AutoPrompter, ConsolePrompter, WizardAborted


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def test_detect_hosts_reports_all_four_roots_with_history_counts(
    tmp_path: Path,
) -> None:
    # Arrange
    touch(tmp_path / ".claude/projects/-Users-me-repo/s1.jsonl")
    touch(tmp_path / ".claude/projects/-Users-me-repo/s2.jsonl")
    touch(tmp_path / ".claude/projects/-Users-me-repo/s1/subagents/agent-a.jsonl")
    touch(tmp_path / ".gemini/antigravity-cli/conversations/c1.db")
    touch(tmp_path / ".gemini/antigravity-ide/conversations/i1.db")
    touch(tmp_path / ".gemini/antigravity-ide/conversations/i2.pb")

    # Act
    detected = detect_hosts(tmp_path, {})

    # Assert
    assert detected == [
        DetectedHost(Host.CLAUDE_CODE, tmp_path / ".claude", True, 2),
        DetectedHost(
            Host.ANTIGRAVITY_CLI, tmp_path / ".gemini/antigravity-cli", True, 1
        ),
        DetectedHost(
            Host.ANTIGRAVITY_IDE, tmp_path / ".gemini/antigravity-ide", True, 2
        ),
        DetectedHost(Host.ANTIGRAVITY_APP, tmp_path / ".gemini/antigravity", False, 0),
    ]


def test_claude_config_dir_overrides_root_and_settings_path(tmp_path: Path) -> None:
    # Arrange
    custom = tmp_path / "claude-config"
    touch(custom / "projects/p/s.jsonl")
    env = {"CLAUDE_CONFIG_DIR": str(custom)}

    # Act
    detected = detect_hosts(tmp_path, env)[0]

    # Assert
    assert detected == DetectedHost(Host.CLAUDE_CODE, custom, True, 1)
    assert claude_settings_path(tmp_path, env) == custom / "settings.json"
    assert claude_settings_path(tmp_path, {}) == tmp_path / ".claude/settings.json"


def test_antigravity_hooks_path_is_the_user_level_config_file_not_gemini_settings(
    tmp_path: Path,
) -> None:
    # Arrange / Act
    path = antigravity_hooks_path(tmp_path)

    # Assert
    assert path == tmp_path / ".gemini" / "config" / "hooks.json"
    assert path != tmp_path / ".gemini" / "settings.json"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ({"enabledPlugins": {"agent-metrics@skills-programming-ai": True}}, True),
        ({"enabledPlugins": {"agent-metrics@skills-programming-ai": False}}, False),
        ({"enabledPlugins": {"senior-dev@skills": True}}, False),
        ({"enabledPlugins": ["agent-metrics"]}, False),
        ({}, False),
    ],
)
def test_claude_plugin_installed(
    tmp_path: Path, content: object, expected: bool
) -> None:
    # Arrange
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(content))

    # Act / Assert
    assert claude_plugin_installed(settings) is expected


def test_claude_plugin_installed_tolerates_missing_or_broken_files(
    tmp_path: Path,
) -> None:
    # Arrange
    broken = tmp_path / "broken.json"
    broken.write_text("{")

    # Act / Assert
    assert claude_plugin_installed(tmp_path / "absent.json") is False
    assert claude_plugin_installed(broken) is False


def test_antigravity_plugin_installed(tmp_path: Path) -> None:
    # Arrange
    assert antigravity_plugin_installed(tmp_path) is False
    (tmp_path / ".gemini/config/plugins/agent-metrics").mkdir(parents=True)

    # Act / Assert
    assert antigravity_plugin_installed(tmp_path) is True


def test_parse_hosts_accepts_host_ids_and_rejects_unknown() -> None:
    # Arrange / Act / Assert
    assert parse_hosts("claude-code, antigravity-ide") == (
        Host.CLAUDE_CODE,
        Host.ANTIGRAVITY_IDE,
    )
    with pytest.raises(ValueError, match="unknown host 'cursor'"):
        parse_hosts("claude-code,cursor")
    with pytest.raises(ValueError, match="at least one host"):
        parse_hosts(" , ")


# --------------------------------------------------------------------------- prompter


def test_console_prompter_uses_defaults_on_blank_and_reprompts_on_invalid() -> None:
    # Arrange
    stdin = io.StringIO("\nn\nmaybe\ny\nfoo\ncloud\n\n")
    stdout = io.StringIO()
    prompter = ConsolePrompter(stdin, stdout)

    # Act
    first = prompter.confirm("Install hooks?", default=True)
    second = prompter.confirm("Store descriptions?", default=True)
    third = prompter.confirm("Again?", default=False)
    choice = prompter.choose("Mode", ["local", "cloud"], default="local")
    answer = prompter.ask("Project", default="devhack-3f0c2")

    # Assert
    assert (first, second, third, choice, answer) == (
        True,
        False,
        True,
        "cloud",
        "devhack-3f0c2",
    )
    output = stdout.getvalue()
    assert "Install hooks? [Y/n] " in output
    assert "please answer y or n" in output
    assert "choose one of: local, cloud" in output
    assert prompter.interactive is True


def test_console_prompter_raises_on_end_of_input() -> None:
    # Arrange
    prompter = ConsolePrompter(io.StringIO(""), io.StringIO())

    # Act / Assert
    with pytest.raises(WizardAborted):
        prompter.confirm("Continue?", default=True)


def test_auto_prompter_answers_every_question_with_its_default() -> None:
    # Arrange
    stdout = io.StringIO()
    prompter = AutoPrompter(stdout)

    # Act
    answers = (
        prompter.confirm("Anonymize?", default=False),
        prompter.confirm("Apply?", default=True),
        prompter.choose("Mode", ["local", "cloud"], default="local"),
        prompter.ask("Project", default="p"),
    )
    prompter.info("hello")

    # Assert
    assert answers == (False, True, "local", "p")
    assert prompter.interactive is False
    assert "hello\n" in stdout.getvalue()
    assert "Apply? yes (--yes)" in stdout.getvalue()
