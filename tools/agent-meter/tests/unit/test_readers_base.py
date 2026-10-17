"""Tests for ``readers.base`` (contracts §3.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_meter.model import Host
from agent_meter.readers.antigravity import AntigravityReader
from agent_meter.readers.base import (
    HostReader,
    available_readers,
    default_roots,
    host_from_transcript_path,
)
from agent_meter.readers.claude_code import ClaudeCodeReader


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "/Users/me/.gemini/antigravity-cli/brain/c1/.system_generated/logs/transcript_full.jsonl",
            Host.ANTIGRAVITY_CLI,
        ),
        (
            "/Users/me/.gemini/antigravity-ide/brain/c1/.system_generated/logs/transcript_full.jsonl",
            Host.ANTIGRAVITY_IDE,
        ),
        (
            "/Users/me/.gemini/antigravity/brain/c1/.system_generated/logs/transcript_full.jsonl",
            Host.ANTIGRAVITY_APP,
        ),
        ("/Users/me/.claude/projects/-Users-me-repo/0b5e.jsonl", Host.CLAUDE_CODE),
        ("/custom/claude-config/projects/-Users-me-repo/0b5e.jsonl", Host.CLAUDE_CODE),
        ("/Users/me/.gemini/antigravity-browser-profile/x.jsonl", None),
        ("/tmp/random.txt", None),
        ("", None),
    ],
)
def test_host_from_transcript_path(path: str, expected: Host | None) -> None:
    assert host_from_transcript_path(path) is expected


def test_default_roots_respect_claude_config_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cc"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    roots = default_roots()

    assert roots == {
        Host.CLAUDE_CODE: tmp_path / "cc",
        Host.ANTIGRAVITY_CLI: tmp_path / "home" / ".gemini" / "antigravity-cli",
        Host.ANTIGRAVITY_IDE: tmp_path / "home" / ".gemini" / "antigravity-ide",
        Host.ANTIGRAVITY_APP: tmp_path / "home" / ".gemini" / "antigravity",
    }


def test_available_readers_only_for_existing_roots(tmp_path: Path) -> None:
    (tmp_path / "claude").mkdir()
    (tmp_path / "agy-ide").mkdir()
    roots = {
        Host.CLAUDE_CODE: tmp_path / "claude",
        Host.ANTIGRAVITY_CLI: tmp_path / "missing",
        Host.ANTIGRAVITY_IDE: tmp_path / "agy-ide",
    }

    readers = available_readers(roots)

    assert [(r.host, r.root) for r in readers] == [
        (Host.CLAUDE_CODE, tmp_path / "claude"),
        (Host.ANTIGRAVITY_IDE, tmp_path / "agy-ide"),
    ]
    assert isinstance(readers[0], ClaudeCodeReader) and isinstance(
        readers[1], AntigravityReader
    )
    assert all(isinstance(r, HostReader) for r in readers)


def test_available_readers_defaults_use_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    (tmp_path / ".gemini" / "antigravity").mkdir(parents=True)

    readers = available_readers()

    assert [(r.host, r.root) for r in readers] == [
        (Host.ANTIGRAVITY_APP, tmp_path / ".gemini" / "antigravity")
    ]
