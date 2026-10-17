"""QA-1 fixtures (Track 11, Phase 5): hermetic temp HOME + AGENT_METER_HOME, network blocked,
and a fake scheduler environment so no test can reach the real launchd / systemd / crontab.

Every test in this directory gets the ``qa`` marker. Tests that spawn real ``agent-meter``
subprocesses pass ``HOME`` / ``AGENT_METER_HOME`` explicitly and never run ``uninstall``
without ``--keep-scheduler`` (the subprocess would not see the fake scheduler).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agent_meter import cli
from agent_meter.paths import AppHome
from agent_meter.scheduler._base import SchedulerEnv
from tests.fixtures.antigravity import build_root
from tests.fixtures.claude import ClaudeHome, ClaudeSession
from tests.fixtures.scenarios import agy_standard_conversations, claude_standard_session

SRC = Path(__file__).resolve().parents[2] / "src"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/qa/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.qa)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "qa: QA-1 verification tests (Track 11 Phase 5)")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[object]]:
    """Any in-process socket connection attempt fails the test (L1-L3 are offline)."""
    attempts: list[object] = []

    def refuse(*args: object, **_kwargs: object) -> socket.socket:
        attempts.append(args)
        raise RuntimeError("network access is not allowed in QA tests")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    yield attempts


@dataclass
class FakeRunner:
    """Records scheduler commands; ``launchctl print`` reports 'not loaded', everything else succeeds."""

    calls: list[list[str]] = field(default_factory=list)

    def __call__(self, args: Sequence[str], *, input: str | None = None) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        self.calls.append(argv)
        if argv[:2] == ["launchctl", "print"]:
            return subprocess.CompletedProcess(argv, 113, "", "Could not find service")
        if argv[:2] == ["crontab", "-l"]:
            return subprocess.CompletedProcess(argv, 1, "", "no crontab for user")
        return subprocess.CompletedProcess(argv, 0, "", "")


@pytest.fixture(autouse=True)
def fake_scheduler(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeRunner:
    """Route every in-process scheduler call to a recorder bound to the temp HOME."""
    runner = FakeRunner()
    user_home = tmp_path / "user"

    def current(_cls: type[SchedulerEnv]) -> SchedulerEnv:
        return SchedulerEnv(platform="darwin", user_home=user_home, uid=os.getuid(), runner=runner,
                            which=lambda _name: None)

    monkeypatch.setattr(SchedulerEnv, "current", classmethod(current))
    return runner


@dataclass
class QAWorld:
    user: Path
    meter: AppHome
    claude: ClaudeHome
    agy_root: Path

    def write_claude(self, session: ClaudeSession, *, tail: bytes = b"") -> Path:
        return self.claude.write(session, tail=tail)

    def env(self) -> dict[str, str]:
        """Environment for real ``agent-meter`` subprocesses bound to this world."""
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CONFIG_DIR", "TZ")}
        env.update({
            "HOME": str(self.user),
            "AGENT_METER_HOME": str(self.meter.root),
            "PYTHONPATH": os.pathsep.join(p for p in (str(SRC), os.environ.get("PYTHONPATH", "")) if p),
        })
        return env


def agent_meter_argv() -> list[str]:
    """The installed console script when available (as hooks call it), else ``python -m agent_meter``."""
    exe = shutil.which("agent-meter")
    if exe and Path(exe).resolve().parent == Path(sys.executable).resolve().parent:
        return [exe]
    return [sys.executable, "-m", "agent_meter"]


def make_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, standard: bool = True) -> QAWorld:
    user = tmp_path / "user"
    user.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(user))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.setenv("AGENT_METER_HOME", str(tmp_path / "meter"))
    claude = ClaudeHome(user / ".claude")
    agy_parent = user / ".gemini" / "antigravity-cli"
    if standard:
        claude.write(claude_standard_session())
        agy_root = build_root(agy_parent, agy_standard_conversations())
    else:
        agy_root = agy_parent
    meter = AppHome.resolve()
    for key, value in (("timezone", "UTC"), ("notify", "off")):
        assert cli.main(["config", "set", key, value]) == 0
    return QAWorld(user=user, meter=meter, claude=claude, agy_root=agy_root)


@pytest.fixture()
def qa_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QAWorld:
    return make_world(tmp_path, monkeypatch)
