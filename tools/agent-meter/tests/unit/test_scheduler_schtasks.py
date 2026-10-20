"""Unit tests for Windows Task Scheduler (``schtasks``) and Windows setup primitives."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath

import pytest

from agent_meter.scheduler import (
    SchedulerEnv,
    SchedulerError,
    detect_kind,
    install,
    schtasks,
    status,
    uninstall,
)
from agent_meter.setup import _files
from agent_meter.setup import settings_merge as sm

REPO_ROOT = Path(__file__).resolve().parents[4]
CLAUDE_WRAPPER = (
    REPO_ROOT / "plugins" / "claude" / "agent-metrics" / "hooks" / "agent-meter-hook.js"
)
AGY_WRAPPER = (
    REPO_ROOT
    / "plugins"
    / "antigravity"
    / "agent-metrics"
    / "hooks"
    / "agent-meter-hook.js"
)
NODE = shutil.which("node")


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
class FakeSchtasksSystem:
    """Emulates Windows ``schtasks.exe`` for unit testing without touching the host OS."""

    task_command: str | None = None
    fail_on: set[str] = field(default_factory=set)
    calls: list[list[str]] = field(default_factory=list)

    def __call__(
        self, args: Sequence[str], *, input: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        self.calls.append(argv)
        assert argv[0] == "schtasks", f"unexpected command: {argv}"
        verb = argv[1]
        if verb in self.fail_on:
            return subprocess.CompletedProcess(argv, 1, "", f"ERROR: {verb} failed")
        if verb == "/Query":
            if self.task_command is None:
                return subprocess.CompletedProcess(
                    argv,
                    1,
                    "",
                    "ERROR: The system cannot find the file specified.\n",
                )
            stdout = (
                f"Folder: \\\n"
                f"TaskName:      \\{schtasks.TASK_NAME}\n"
                f"Task To Run:   {self.task_command}\n"
            )
            return subprocess.CompletedProcess(argv, 0, stdout, "")
        if verb == "/Create":
            tr_index = argv.index("/TR")
            self.task_command = argv[tr_index + 1]
            return subprocess.CompletedProcess(
                argv,
                0,
                f'SUCCESS: The scheduled task "{schtasks.TASK_NAME}" has successfully been created.\n',
                "",
            )
        if verb == "/Delete":
            if self.task_command is None:
                return subprocess.CompletedProcess(argv, 1, "", "ERROR: not found")
            self.task_command = None
            return subprocess.CompletedProcess(
                argv,
                0,
                f'SUCCESS: The scheduled task "{schtasks.TASK_NAME}" was successfully deleted.\n',
                "",
            )
        raise AssertionError(f"unexpected schtasks verb: {argv}")


def make_win_env(
    tmp_path: Path,
    system: FakeSchtasksSystem,
    *,
    has_schtasks: bool = True,
) -> SchedulerEnv:
    user_home = tmp_path / "user"
    user_home.mkdir(exist_ok=True)
    return SchedulerEnv(
        platform="win32",
        user_home=user_home,
        uid=0,
        runner=system,
        which=lambda name: (
            "C:\\Windows\\System32\\schtasks.exe"
            if name == "schtasks" and has_schtasks
            else None
        ),
    )


@pytest.fixture
def home(tmp_path: Path) -> FakeHome:
    root = tmp_path / "agent-meter-home"
    root.mkdir()
    return FakeHome(root)


EXE = Path("/Users/alice/AppData/Local/bin/agent-meter.exe")


def test_detect_kind_on_win32_returns_schtasks_when_available(tmp_path: Path) -> None:
    # Arrange
    system = FakeSchtasksSystem()
    env_with = make_win_env(tmp_path, system, has_schtasks=True)
    env_without = make_win_env(tmp_path, system, has_schtasks=False)

    # Act / Assert
    assert detect_kind(env_with) == "schtasks"
    assert detect_kind(env_without) is None


def test_schtasks_install_and_idempotent_rerun(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSchtasksSystem()
    env = make_win_env(tmp_path, system)

    # Act — first install
    first_msg = install(home, EXE, env=env)

    # Assert — first install creates the task
    expected_tr = schtasks.render_command(home, EXE)
    assert "schtasks scheduler installed" in first_msg
    assert system.task_command == expected_tr
    assert [
        "schtasks",
        "/Create",
        "/F",
        "/SC",
        "MINUTE",
        "/MO",
        "15",
        "/TN",
        schtasks.TASK_NAME,
        "/TR",
        expected_tr,
    ] in system.calls
    assert status(env=env) == "loaded"

    # Act — second install with identical command
    system.calls.clear()
    second_msg = install(home, EXE, env=env)

    # Assert — idempotent no-op
    assert "no changes" in second_msg
    assert all(call[1] == "/Query" for call in system.calls)


def test_schtasks_is_loaded_and_uninstall(tmp_path: Path, home: FakeHome) -> None:
    # Arrange
    system = FakeSchtasksSystem()
    env = make_win_env(tmp_path, system)
    assert schtasks.is_loaded(env) is False

    install(home, EXE, env=env)
    assert schtasks.is_loaded(env) is True

    # Act
    removed_msg = uninstall(home, env=env)
    noop_msg = uninstall(home, env=env)

    # Assert
    assert "schtasks scheduler removed" in removed_msg
    assert schtasks.is_loaded(env) is False
    assert status(env=env) == "not_loaded"
    assert "no scheduler installed" in noop_msg


def test_schtasks_create_failure_raises_scheduler_error(
    tmp_path: Path, home: FakeHome
) -> None:
    # Arrange
    system = FakeSchtasksSystem(fail_on={"/Create"})
    env = make_win_env(tmp_path, system)

    # Act / Assert
    with pytest.raises(SchedulerError, match="schtasks /Create failed"):
        install(home, EXE, env=env)


def test_scheduler_env_current_when_getuid_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.delattr(os, "getuid", raising=False)

    # Act
    env = SchedulerEnv.current()

    # Assert
    assert env.uid == 0


def test_settings_merge_when_getuid_is_absent_and_windows_command_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    monkeypatch.delattr(os, "getuid", raising=False)
    monkeypatch.setattr(sm, "MANAGED_SETTINGS_PATHS", (tmp_path / "no-managed.json",))
    settings = tmp_path / "settings.json"
    settings.write_text('{"model": "opus"}\n', encoding="utf-8")
    win_exe = PureWindowsPath(r"C:\Program Files\Agent Meter\agent-meter.exe")

    # Act
    plan = sm.plan_claude(settings, "/opt/bin/agent-meter")
    monkeypatch.setattr(sm.os, "name", "nt")
    win_prefix = sm.command_prefix(win_exe)  # type: ignore[arg-type]
    monkeypatch.undo()

    # Assert
    assert plan.changed is True
    assert win_prefix == '"C:\\Program Files\\Agent Meter\\agent-meter.exe"'
    assert any(
        "ProgramData" in str(policy) for policy in sm.MANAGED_SETTINGS_PATHS
    )


def test_fsync_directory_on_windows_is_a_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    def forbid_open(*_args: object, **_kwargs: object) -> int:
        raise PermissionError("os.open on a directory is not permitted on Windows")

    monkeypatch.setattr(_files.os, "open", forbid_open)
    monkeypatch.setattr(_files.os, "name", "nt")

    # Act / Assert — should return immediately without calling os.open
    _files._fsync_directory(tmp_path)
    monkeypatch.undo()


@pytest.mark.skipif(NODE is None, reason="node not available")
@pytest.mark.skipif(os.name == "nt", reason="POSIX shell script stub used for .exe")
@pytest.mark.parametrize(
    ("wrapper", "host", "expected_stdout"),
    [
        (CLAUDE_WRAPPER, "claude-code", b""),
        (AGY_WRAPPER, "antigravity", b"{}\n"),
    ],
    ids=["claude", "antigravity"],
)
def test_hook_wrapper_locates_agent_meter_exe_on_path(
    wrapper: Path, host: str, expected_stdout: bytes, tmp_path: Path
) -> None:
    if not wrapper.is_file():
        pytest.skip("plugin wrapper outside standalone package copy")

    # Arrange
    bin_dir = tmp_path / "bin"
    record_dir = tmp_path / "record"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    record_dir.mkdir()
    home_dir.mkdir()

    exe_path = bin_dir / "agent-meter.exe"
    exe_path.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{record_dir}/argv"\n'
        f'/bin/cat > "{record_dir}/stdin"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    exe_path.chmod(
        exe_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )

    env = {
        "PATH": str(bin_dir),
        "HOME": str(home_dir),
    }
    payload = b'{"session_id": "win-test"}'

    # Act
    assert NODE is not None
    result = subprocess.run(
        [NODE, str(wrapper), "--host", host, "--event", "task-end"],
        input=payload,
        capture_output=True,
        env=env,
        timeout=15,
        check=False,
    )

    # Assert
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == expected_stdout
    assert (record_dir / "argv").read_text(encoding="utf-8").splitlines() == [
        "hook",
        "--host",
        host,
        "--event",
        "task-end",
    ]
    assert (record_dir / "stdin").read_bytes() == payload
