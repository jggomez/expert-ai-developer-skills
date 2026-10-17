"""Tests for ``agent_meter.scheduler`` (ADR §3.10 "Scheduler"; PF-05, SU-01, US-11)."""

from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agent_meter.scheduler import (
    SchedulerEnv,
    SchedulerError,
    SchedulerUnsupported,
    detect_kind,
    install,
    status,
    uninstall,
)

UID = 501
LABEL = "dev.agentmeter.collect"


@dataclass(frozen=True)
class FakeHome:
    root: Path

    @property
    def backups_dir(self) -> Path:
        return self.root / "backups"

    @property
    def install_manifest(self) -> Path:
        return self.root / "install.json"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"


@dataclass
class FakeSystem:
    """Emulates launchctl, systemctl --user and crontab well enough for idempotency checks."""

    launchd_loaded: bool = False
    systemd_available: bool = True
    timer_active: bool = False
    crontab: str | None = None
    fail: set[str] = field(default_factory=set)
    calls: list[list[str]] = field(default_factory=list)

    def __call__(
        self, args: Sequence[str], *, input: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        self.calls.append(argv)
        key = " ".join(argv[:3])
        if key in self.fail or argv[0] + " " + argv[1] in self.fail:
            return subprocess.CompletedProcess(argv, 5, "", f"boom: {key}")
        if argv[0] == "launchctl":
            return self._launchctl(argv)
        if argv[0] == "systemctl":
            return self._systemctl(argv)
        if argv[0] == "crontab":
            return self._crontab(argv, input)
        raise AssertionError(f"unexpected command {argv}")

    def _launchctl(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        verb = argv[1]
        if verb == "print":
            return subprocess.CompletedProcess(
                argv, 0 if self.launchd_loaded else 113, "", ""
            )
        if verb == "bootstrap":
            self.launchd_loaded = True
        elif verb == "bootout":
            self.launchd_loaded = False
        return subprocess.CompletedProcess(argv, 0, "", "")

    def _systemctl(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        verb = argv[2]
        if verb == "show-environment":
            return subprocess.CompletedProcess(
                argv, 0 if self.systemd_available else 1, "", ""
            )
        if verb == "is-active":
            return subprocess.CompletedProcess(
                argv, 0 if self.timer_active else 3, "", ""
            )
        if verb == "enable":
            self.timer_active = True
        elif verb == "disable":
            self.timer_active = False
        return subprocess.CompletedProcess(argv, 0, "", "")

    def _crontab(
        self, argv: list[str], text: str | None
    ) -> subprocess.CompletedProcess[str]:
        if argv[1] == "-l":
            if self.crontab is None:
                return subprocess.CompletedProcess(
                    argv, 1, "", "crontab: no crontab for me\n"
                )
            return subprocess.CompletedProcess(argv, 0, self.crontab, "")
        assert argv[1] == "-"
        self.crontab = text
        return subprocess.CompletedProcess(argv, 0, "", "")


def make_env(
    tmp_path: Path,
    system: FakeSystem,
    *,
    platform: str = "darwin",
    tools: tuple[str, ...] = ("launchctl", "systemctl", "crontab"),
) -> SchedulerEnv:
    user_home = tmp_path / "user"
    user_home.mkdir(exist_ok=True)
    return SchedulerEnv(
        platform=platform,
        user_home=user_home,
        uid=UID,
        runner=system,
        which=lambda name: f"/usr/bin/{name}" if name in tools else None,
    )


@pytest.fixture
def home(tmp_path: Path) -> FakeHome:
    root = tmp_path / "agent-meter-home"
    root.mkdir()
    return FakeHome(root)


EXE = Path("/opt/tools/agent-meter")


def manifest(home: FakeHome) -> dict[str, object]:
    loaded: dict[str, object] = json.loads(home.install_manifest.read_text())
    return loaded


# --------------------------------------------------------------------------- detection


@pytest.mark.parametrize(
    ("platform", "systemd", "tools", "expected"),
    [
        ("darwin", True, ("launchctl",), "launchd"),
        ("linux", True, ("systemctl", "crontab"), "systemd"),
        ("linux", False, ("systemctl", "crontab"), "cron"),
        ("linux", True, ("crontab",), "cron"),
        ("linux", False, (), None),
        ("win32", True, ("crontab",), None),
    ],
)
def test_detect_kind_prefers_native_scheduler_then_cron(
    tmp_path: Path,
    platform: str,
    systemd: bool,
    tools: tuple[str, ...],
    expected: str | None,
) -> None:
    # Arrange
    env = make_env(
        tmp_path, FakeSystem(systemd_available=systemd), platform=platform, tools=tools
    )

    # Act / Assert
    assert detect_kind(env) == expected


# --------------------------------------------------------------------------- launchd


def test_launchd_install_writes_plist_and_bootstraps(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem()
    env = make_env(tmp_path, system)

    # Act
    message = install(home, EXE, env=env)

    # Assert
    plist_path = env.user_home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    plist = plistlib.loads(plist_path.read_bytes())
    assert plist == {
        "Label": LABEL,
        "ProgramArguments": [str(EXE), "collect", "--scheduled", "--quiet"],
        "EnvironmentVariables": {"AGENT_METER_HOME": str(home.root)},
        "StartInterval": 900,
        "RunAtLoad": True,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "Nice": 10,
        "StandardOutPath": str(home.logs_dir / "scheduler.log"),
        "StandardErrorPath": str(home.logs_dir / "scheduler.log"),
    }
    assert ["launchctl", "bootstrap", f"gui/{UID}", str(plist_path)] in system.calls
    assert system.launchd_loaded is True
    assert home.logs_dir.is_dir()
    assert "installed" in message
    assert manifest(home)["scheduler"] == {"kind": "launchd", "path": str(plist_path)}


def test_launchd_install_twice_reports_no_changes(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem()
    env = make_env(tmp_path, system)
    install(home, EXE, env=env)
    system.calls.clear()

    # Act
    message = install(home, EXE, env=env)

    # Assert
    assert "no changes" in message
    assert all(call[1] == "print" for call in system.calls)


def test_launchd_reinstall_with_new_executable_reloads_agent(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem()
    env = make_env(tmp_path, system)
    install(home, EXE, env=env)
    system.calls.clear()

    # Act
    install(home, Path("/new/bin/agent-meter"), env=env)

    # Assert
    verbs = [call[1] for call in system.calls]
    assert verbs == ["print", "bootout", "bootstrap"]
    assert system.calls[1] == ["launchctl", "bootout", f"gui/{UID}/{LABEL}"]


def test_launchd_bootstrap_failure_raises_with_stderr(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem(fail={"launchctl bootstrap gui/501"})
    env = make_env(tmp_path, system)

    # Act
    with pytest.raises(SchedulerError) as excinfo:
        install(home, EXE, env=env)

    # Assert
    assert "boom" in str(excinfo.value)
    assert not home.install_manifest.exists()


def test_launchd_uninstall_boots_out_removes_plist_and_manifest_record(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem()
    env = make_env(tmp_path, system)
    install(home, EXE, env=env)
    plist_path = env.user_home / "Library" / "LaunchAgents" / f"{LABEL}.plist"

    # Act
    message = uninstall(home, env=env)

    # Assert
    assert not plist_path.exists()
    assert system.launchd_loaded is False
    assert "removed" in message
    assert not home.install_manifest.exists()


def test_uninstall_keeps_settings_records_in_manifest(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem()
    env = make_env(tmp_path, system)
    home.install_manifest.write_text(
        json.dumps({"version": 1, "files": [{"path": "/x"}]})
    )
    install(home, EXE, env=env)

    # Act
    uninstall(home, env=env)

    # Assert
    assert manifest(home) == {"version": 1, "files": [{"path": "/x"}]}


def test_uninstall_when_nothing_installed_is_a_no_op(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem()
    env = make_env(tmp_path, system)

    # Act
    message = uninstall(home, env=env)

    # Assert
    assert "no scheduler" in message
    assert [call[1] for call in system.calls] == ["print"]


def test_status_reports_loaded_not_loaded_unsupported(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem()
    env = make_env(tmp_path, system)

    # Act / Assert
    assert status(env=env) == "not_loaded"
    install(home, EXE, env=env)
    assert status(env=env) == "loaded"
    assert status(env=make_env(tmp_path, system, platform="win32")) == "unsupported"


# --------------------------------------------------------------------------- systemd


def test_systemd_install_writes_units_and_enables_timer(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem()
    env = make_env(tmp_path, system, platform="linux")
    exe = Path("/home/me/My Tools/agent-meter")

    # Act
    message = install(home, exe, env=env)

    # Assert
    unit_dir = env.user_home / ".config" / "systemd" / "user"
    service = (unit_dir / "agent-meter-collect.service").read_text()
    timer = (unit_dir / "agent-meter-collect.timer").read_text()
    assert (
        'ExecStart="/home/me/My Tools/agent-meter" collect --scheduled --quiet'
        in service
    )
    assert f'Environment="AGENT_METER_HOME={home.root}"' in service
    assert "Type=oneshot" in service
    for line in (
        "OnBootSec=2min",
        "OnCalendar=*:0/15",
        "Persistent=true",
        "WantedBy=timers.target",
    ):
        assert line in timer.splitlines()
    # Persistent= only catches up missed runs for OnCalendar timers, not monotonic ones.
    assert "OnUnitActiveSec" not in timer
    assert ["systemctl", "--user", "daemon-reload"] in system.calls
    assert [
        "systemctl",
        "--user",
        "enable",
        "--now",
        "agent-meter-collect.timer",
    ] in system.calls
    assert "installed" in message
    assert manifest(home)["scheduler"] == {
        "kind": "systemd",
        "path": str(unit_dir / "agent-meter-collect.timer"),
    }


def test_systemd_install_is_idempotent_and_uninstall_cleans_up(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem()
    env = make_env(tmp_path, system, platform="linux")
    install(home, EXE, env=env)
    system.calls.clear()

    # Act
    second = install(home, EXE, env=env)
    removed = uninstall(home, env=env)

    # Assert
    unit_dir = env.user_home / ".config" / "systemd" / "user"
    assert "no changes" in second
    assert "removed" in removed
    assert [
        "systemctl",
        "--user",
        "disable",
        "--now",
        "agent-meter-collect.timer",
    ] in system.calls
    assert not any(unit_dir.iterdir())
    assert system.timer_active is False


def test_systemd_unit_escapes_percent_signs(tmp_path: Path, home: FakeHome) -> None:
    # Arrange
    env = make_env(tmp_path, FakeSystem(), platform="linux")

    # Act
    install(home, Path("/opt/100%/agent-meter"), env=env)

    # Assert
    service = (
        env.user_home / ".config/systemd/user/agent-meter-collect.service"
    ).read_text()
    assert 'ExecStart="/opt/100%%/agent-meter"' in service


# --------------------------------------------------------------------------- cron


def test_cron_fallback_appends_marked_line_and_keeps_user_lines(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSystem(systemd_available=False, crontab="0 3 * * * backup.sh\n")
    env = make_env(tmp_path, system, platform="linux")

    # Act
    message = install(home, EXE, env=env)

    # Assert
    assert system.crontab == (
        "0 3 * * * backup.sh\n"
        f"*/15 * * * * AGENT_METER_HOME={home.root} {EXE} collect --scheduled --quiet # agent-meter\n"
    )
    assert "installed" in message
    assert status(env=env) == "loaded"
    assert manifest(home)["scheduler"] == {"kind": "cron", "path": "crontab"}


def test_cron_install_twice_and_uninstall(tmp_path: Path, home: FakeHome) -> None:
    # Arrange
    system = FakeSystem(systemd_available=False)
    env = make_env(tmp_path, system, platform="linux")
    install(home, Path("/opt/50% off/agent-meter"), env=env)
    first = system.crontab

    # Act
    second = install(home, Path("/opt/50% off/agent-meter"), env=env)
    removed = uninstall(home, env=env)

    # Assert
    assert first is not None
    assert "'/opt/50\\% off/agent-meter'" in first
    assert "no changes" in second
    assert "removed" in removed
    assert system.crontab == ""
    assert status(env=env) == "not_loaded"


def test_cron_read_failure_raises(tmp_path: Path, home: FakeHome) -> None:
    # Arrange
    system = FakeSystem(systemd_available=False, fail={"crontab -l"})
    env = make_env(tmp_path, system, platform="linux")

    # Act / Assert
    with pytest.raises(SchedulerError):
        install(home, EXE, env=env)


# --------------------------------------------------------------------------- guards


def test_install_rejects_relative_executable(tmp_path: Path, home: FakeHome) -> None:
    # Arrange
    env = make_env(tmp_path, FakeSystem())

    # Act / Assert
    with pytest.raises(ValueError, match="absolute"):
        install(home, Path("agent-meter"), env=env)


def test_install_on_unsupported_platform_raises(tmp_path: Path, home: FakeHome) -> None:
    # Arrange
    env = make_env(tmp_path, FakeSystem(), platform="win32")

    # Act / Assert
    with pytest.raises(SchedulerUnsupported, match="agent-meter collect"):
        install(home, EXE, env=env)


def test_current_env_uses_real_platform_and_home() -> None:
    # Arrange / Act
    env = SchedulerEnv.current()

    # Assert
    assert env.user_home == Path.home()
    assert env.platform == sys.platform
