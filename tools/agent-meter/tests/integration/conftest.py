"""Integration (L3) fixtures: a temp HOME with fake Claude Code / Antigravity hosts, network blocked."""

from __future__ import annotations

import socket
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from agent_meter import cli
from agent_meter.paths import AppHome
from tests.fixtures.antigravity import build_root
from tests.fixtures.claude import ClaudeHome, ClaudeSession
from tests.fixtures.scenarios import agy_standard_conversations, claude_standard_session


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    def refuse(*_args: object, **_kwargs: object) -> socket.socket:
        raise RuntimeError("network access is not allowed in integration tests")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    yield


@dataclass
class World:
    user: Path
    meter: AppHome
    claude: ClaudeHome
    agy_root: Path

    def write_claude(self, session: ClaudeSession, *, tail: bytes = b"") -> Path:
        return self.claude.write(session, tail=tail)


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[World]:
    user = tmp_path / "user"
    monkeypatch.setenv("HOME", str(user))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.setenv("AGENT_METER_HOME", str(tmp_path / "meter"))
    claude = ClaudeHome(user / ".claude")
    claude.write(claude_standard_session())
    agy_root = build_root(user / ".gemini" / "antigravity-cli", agy_standard_conversations())
    meter = AppHome.resolve()
    for key, value in (("timezone", "UTC"), ("notify", "off")):
        assert cli.main(["config", "set", key, value]) == 0
    yield World(user=user, meter=meter, claude=claude, agy_root=agy_root)
