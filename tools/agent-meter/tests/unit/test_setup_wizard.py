"""Tests for ``agent_meter.setup.wizard`` (PLAN setup steps 1-8; SU-01, SU-02, SU-04, SU-06, BR-18)."""

from __future__ import annotations

import io
import json
import socket
import subprocess
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from agent_meter.config import BigQueryConfig, Config
from agent_meter.model import Host
from agent_meter.scheduler import SchedulerError
from agent_meter.setup import settings_merge
from agent_meter.setup._files import HomeLike
from agent_meter.setup.gcp_checks import REQUIRED_PERMISSIONS
from agent_meter.setup.prompter import AutoPrompter, Prompter
from agent_meter.setup.wizard import (
    SetupDeps,
    SetupOptions,
    SetupResult,
    SetupUsageError,
    parse_triggers,
    run_setup,
)

PROJECT = "devhack-3f0c2"
EXE = Path("/opt/tools/agent-meter")
RTK_SETTINGS = {
    "hooks": {
        "BeforeTool": [
            {
                "matcher": "run_shell_command",
                "hooks": [
                    {"type": "command", "command": "~/.gemini/hooks/rtk-hook-gemini.sh"}
                ],
            }
        ]
    }
}
CLAUDE_EXISTING = {
    "hooks": {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "guard.sh"}]}
        ]
    }
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[object]]:
    attempts: list[object] = []

    def refuse(*args: object, **_kwargs: object) -> socket.socket:
        attempts.append(args)
        raise AssertionError("network access attempted during setup")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    yield attempts


@pytest.fixture(autouse=True)
def no_managed_policy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        settings_merge, "MANAGED_SETTINGS_PATHS", (tmp_path / "none.json",)
    )


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
class FakeScheduler:
    installed: bool = False
    error: str | None = None
    calls: list[tuple[Path, Path]] = field(default_factory=list)

    def __call__(self, home: HomeLike, executable: Path) -> str:
        self.calls.append((home.root, executable))
        if self.error:
            raise SchedulerError(self.error)
        if self.installed:
            return "launchd scheduler already installed at x (no changes)"
        self.installed = True
        return "launchd scheduler installed at x"


@dataclass
class FakeGcloud:
    api_enabled: bool = True
    adc_ok: bool = True
    calls: list[list[str]] = field(default_factory=list)

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        joined = " ".join(args)

        def done(
            code: int = 0, out: str = "", err: str = ""
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, code, out, err)

        if joined == "gcloud --version":
            return done(out="Google Cloud SDK 540.0.0\n")
        if "print-access-token" in joined:
            return (
                done(out="tok\n")
                if self.adc_ok
                else done(1, err="Reauthentication failed\n")
            )
        if joined.startswith("gcloud projects describe"):
            return done(out="42\n")
        if joined == "gcloud config get-value project":
            return done(out="overty-sphere\n")
        if "billingEnabled" in joined:
            return done(out="True\n")
        if "billingAccountName" in joined:
            return done(out="billingAccounts/ABC-123\n")
        if joined.startswith("gcloud services list"):
            return done(out="bigquery.googleapis.com\n" if self.api_enabled else "")
        if joined.startswith("gcloud services enable"):
            self.api_enabled = True
            return done()
        if joined.startswith("gcloud billing budgets"):
            return done()
        raise AssertionError(f"unexpected gcloud call: {joined}")


def fake_http(url: str, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
    return 200, json.dumps({"permissions": list(REQUIRED_PERMISSIONS)}).encode()


class ScriptedPrompter:
    def __init__(self, answers: dict[str, object]) -> None:
        self.answers = answers
        self.out: list[str] = []
        self.asked: list[str] = []

    @property
    def interactive(self) -> bool:
        return True

    def info(self, text: str) -> None:
        self.out.append(text)

    def _answer(self, question: str, default: object) -> object:
        self.asked.append(question)
        for key, value in self.answers.items():
            if key in question:
                return value
        return default

    def confirm(self, question: str, *, default: bool) -> bool:
        return bool(self._answer(question, default))

    def choose(self, question: str, options: Sequence[str], *, default: str) -> str:
        answer = str(self._answer(question, default))
        assert answer in options
        return answer

    def ask(self, question: str, *, default: str = "") -> str:
        return str(self._answer(question, default))


@dataclass
class World:
    user_home: Path
    home: FakeHome
    scheduler: FakeScheduler
    gcloud: FakeGcloud
    saved: list[Config]
    backfills: list[str]
    provisioned: list[Config]
    interactive_runs: list[list[str]]
    stdout: io.StringIO

    def deps(
        self, prompter: Prompter | None = None, config: Config | None = None
    ) -> SetupDeps:
        def save(cfg: Config) -> None:
            self.saved.append(cfg)

        def backfill() -> str:
            self.backfills.append("run")
            return "backfill: 12 sessions ingested"

        def provision(cfg: Config) -> str:
            self.provisioned.append(cfg)
            return f"dataset {cfg.bigquery.project}.{cfg.bigquery.dataset} ready"

        def run_interactive(argv: list[str]) -> int:
            self.interactive_runs.append(argv)
            return 0

        return SetupDeps(
            home=self.home,
            config=config or (self.saved[-1] if self.saved else Config(timezone="UTC")),
            save_config=save,
            executable=EXE,
            user_home=self.user_home,
            environ={},
            prompter=prompter or AutoPrompter(self.stdout),
            install_scheduler=self.scheduler,
            gcp_runner=self.gcloud,
            gcp_http=fake_http,
            run_interactive=run_interactive,
            backfill=backfill,
            provision_cloud=provision,
            doctor=lambda: "doctor: all OK",
        )

    @property
    def claude_settings(self) -> Path:
        return self.user_home / ".claude" / "settings.json"

    @property
    def agy_hooks(self) -> Path:
        return self.user_home / ".gemini" / "config" / "hooks.json"

    @property
    def gemini_settings(self) -> Path:
        return self.user_home / ".gemini" / "settings.json"


@pytest.fixture
def world(tmp_path: Path) -> World:
    user_home = tmp_path / "user"
    (user_home / ".claude" / "projects" / "-repo").mkdir(parents=True)
    (user_home / ".claude" / "projects" / "-repo" / "s1.jsonl").write_bytes(b"")
    (user_home / ".gemini" / "antigravity-cli" / "conversations").mkdir(parents=True)
    (user_home / ".gemini" / "antigravity-cli" / "conversations" / "c1.db").write_bytes(
        b""
    )
    (user_home / ".gemini" / "settings.json").write_text(
        json.dumps(RTK_SETTINGS, indent=2)
    )
    (user_home / ".claude" / "settings.json").write_text(
        json.dumps(CLAUDE_EXISTING, indent=2)
    )
    root = tmp_path / "agent-meter-home"
    root.mkdir()
    return World(
        user_home=user_home,
        home=FakeHome(root),
        scheduler=FakeScheduler(),
        gcloud=FakeGcloud(),
        saved=[],
        backfills=[],
        provisioned=[],
        interactive_runs=[],
        stdout=io.StringIO(),
    )


def commands(path: Path) -> list[str]:
    found: list[str] = []

    def walk(obj: object) -> None:
        if isinstance(obj, dict):
            if isinstance(obj.get("command"), str):
                found.append(obj["command"])
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(json.loads(path.read_text()))
    return found


LOCAL_YES = SetupOptions(mode="local", assume_yes=True)


# --------------------------------------------------------------------------- local, non-interactive


def test_local_yes_registers_hooks_scheduler_and_backfills_without_network(
    world: World, no_network: list[object]
) -> None:
    # Arrange
    gemini_before = world.gemini_settings.read_bytes()

    # Act
    result = run_setup(LOCAL_YES, world.deps())

    # Assert
    assert isinstance(result, SetupResult)
    assert result.ok is True
    assert result.changed is True
    assert commands(world.claude_settings) == [
        "guard.sh",
        f"{EXE} hook --host claude-code --event session-end",
        f"{EXE} hook --host claude-code --event task-end",
    ]
    assert commands(world.agy_hooks) == [
        f"{EXE} hook --host antigravity --event task-end"
    ]
    assert world.gemini_settings.read_bytes() == gemini_before
    assert world.scheduler.calls == [(world.home.root, EXE)]
    assert world.backfills == ["run"]
    assert world.gcloud.calls == []
    assert no_network == []
    assert not any(
        name == "google" or name.startswith("google.") for name in sys.modules
    )
    output = world.stdout.getvalue()
    assert "claude-code" in output and "1 session" in output
    assert (
        '"command": "/opt/tools/agent-meter hook --host claude-code --event task-end"'
        in output
    )
    assert "doctor: all OK" in output


def test_second_run_reports_no_changes(world: World) -> None:
    # Arrange
    run_setup(LOCAL_YES, world.deps())
    backups = sorted(world.home.backups_dir.iterdir())
    claude_after_first = world.claude_settings.read_bytes()
    world.stdout.seek(0)
    world.stdout.truncate()

    # Act
    result = run_setup(LOCAL_YES, world.deps())

    # Assert
    assert result.ok is True
    assert result.changed is False
    assert sorted(world.home.backups_dir.iterdir()) == backups
    assert world.claude_settings.read_bytes() == claude_after_first
    assert "Setup complete: no changes" in world.stdout.getvalue()


def test_hosts_flag_limits_hook_registration_and_disables_other_hosts(
    world: World,
) -> None:
    # Arrange
    options = SetupOptions(mode="local", assume_yes=True, hosts=(Host.CLAUDE_CODE,))

    # Act
    result = run_setup(options, world.deps())

    # Assert
    assert not world.agy_hooks.exists()
    assert result.config.host(Host.CLAUDE_CODE).enabled is True
    assert result.config.host(Host.ANTIGRAVITY_CLI).enabled is False
    assert world.saved[-1] == result.config


@pytest.mark.parametrize(
    ("triggers", "hooks", "scheduled"),
    [("none", False, False), ("scheduler", False, True), ("hooks", True, False)],
)
def test_triggers_flag(
    world: World, triggers: str, hooks: bool, scheduled: bool
) -> None:
    # Arrange
    claude_before = world.claude_settings.read_bytes()
    options = SetupOptions(
        mode="local", assume_yes=True, triggers=parse_triggers(triggers)
    )

    # Act
    run_setup(options, world.deps())

    # Assert
    assert (world.claude_settings.read_bytes() != claude_before) is hooks
    assert world.agy_hooks.exists() is hooks
    assert bool(world.scheduler.calls) is scheduled


def test_no_backfill_flag_skips_import(world: World) -> None:
    # Arrange / Act
    run_setup(SetupOptions(mode="local", assume_yes=True, backfill=False), world.deps())

    # Assert
    assert world.backfills == []


def test_invalid_settings_are_refused_and_scheduler_is_offered_instead(
    world: World,
) -> None:
    # Arrange
    world.claude_settings.write_bytes(b"{ not json")
    options = SetupOptions(
        mode="local", assume_yes=True, triggers=parse_triggers("hooks")
    )

    # Act
    result = run_setup(options, world.deps())

    # Assert
    assert result.ok is True
    assert world.claude_settings.read_bytes() == b"{ not json"
    assert world.scheduler.calls == [(world.home.root, EXE)]
    output = world.stdout.getvalue()
    assert "refusing to edit" in output
    assert "scheduler" in output


def test_plugin_overlap_skips_user_level_claude_hooks(world: World) -> None:
    # Arrange
    world.claude_settings.write_text(
        json.dumps({"enabledPlugins": {"agent-metrics@skills-programming-ai": True}})
    )
    before = world.claude_settings.read_bytes()

    # Act
    run_setup(LOCAL_YES, world.deps())

    # Assert
    assert world.claude_settings.read_bytes() == before
    assert "agent-metrics plugin" in world.stdout.getvalue()


def test_scheduler_failure_is_reported_and_marks_result_not_ok(world: World) -> None:
    # Arrange
    world.scheduler.error = "launchctl bootstrap failed: boom"

    # Act
    result = run_setup(LOCAL_YES, world.deps())

    # Assert
    assert result.ok is False
    assert "launchctl bootstrap failed: boom" in world.stdout.getvalue()


# --------------------------------------------------------------------------- interactive


def test_interactive_user_can_decline_each_settings_change(world: World) -> None:
    # Arrange
    claude_before = world.claude_settings.read_bytes()
    prompter = ScriptedPrompter(
        {
            "Mode": "local",
            "Triggers": "hooks,scheduler",
            f"Apply this change to {world.claude_settings.resolve()}": False,
            "Review projects": False,
        }
    )

    # Act
    result = run_setup(SetupOptions(), world.deps(prompter=prompter))

    # Assert
    assert world.claude_settings.read_bytes() == claude_before
    assert world.agy_hooks.exists()
    assert any("declined" in action for action in result.actions)


def test_wizard_never_asks_about_storing_subagent_descriptions(world: World) -> None:
    # Arrange: M-2 — the key is reserved for v2; descriptions are always salted hashes in v1
    prompter = ScriptedPrompter({"Mode": "local", "Review projects": False, "description": True})

    # Act
    result = run_setup(SetupOptions(), world.deps(prompter=prompter))

    # Assert
    assert prompter.asked, "the interactive wizard should have asked its other questions"
    assert not any("description" in question.lower() for question in prompter.asked)
    assert result.config.store_agent_descriptions is False


def test_interactive_projects_step_runs_when_accepted(world: World) -> None:
    # Arrange
    reviewed: list[Prompter] = []
    prompter = ScriptedPrompter({"Review projects": True})

    def configure(p: Prompter) -> str:
        reviewed.append(p)
        return "projects: 3 configured"

    deps = replace(world.deps(prompter=prompter), configure_projects=configure)

    # Act
    run_setup(SetupOptions(mode="local"), deps)

    # Assert
    assert reviewed == [prompter]
    assert "projects: 3 configured" in prompter.out


# --------------------------------------------------------------------------- cloud


def test_cloud_yes_uses_explicit_project_offers_budget_and_provisions(
    world: World,
) -> None:
    # Arrange
    options = SetupOptions(
        mode="cloud", assume_yes=True, gcp_project=PROJECT, bq_mode="billing"
    )

    # Act
    result = run_setup(options, world.deps())

    # Assert
    assert result.ok is True
    assert result.config.bigquery == BigQueryConfig(
        enabled=True, project=PROJECT, mode="billing"
    )
    assert world.provisioned == [result.config]
    assert world.saved[-1] == result.config
    for call in world.gcloud.calls:
        assert "overty-sphere" not in call
    assert [
        "gcloud",
        "billing",
        "budgets",
        "create",
        "--billing-account=ABC-123",
        "--display-name=agent-meter",
        "--budget-amount=1USD",
        "--threshold-rule=percent=0.5",
        "--threshold-rule=percent=1.0",
    ] in world.gcloud.calls
    output = world.stdout.getvalue()
    assert "does not cap" in output
    assert f"always uses '{PROJECT}' explicitly" in output


def test_cloud_runs_safe_autofix_then_rechecks(world: World) -> None:
    # Arrange
    world.gcloud.api_enabled = False
    options = SetupOptions(
        mode="cloud", assume_yes=True, gcp_project=PROJECT, bq_mode="billing"
    )

    # Act
    result = run_setup(options, world.deps())

    # Assert
    assert [
        "gcloud",
        "services",
        "enable",
        "bigquery.googleapis.com",
        "--project",
        PROJECT,
    ] in (world.gcloud.calls)
    assert result.ok is True
    assert result.config.bigquery.enabled is True


def test_cloud_with_expired_adc_non_interactive_prints_fix_and_keeps_cloud_disabled(
    world: World,
) -> None:
    # Arrange
    world.gcloud.adc_ok = False
    options = SetupOptions(
        mode="cloud", assume_yes=True, gcp_project=PROJECT, bq_mode="billing"
    )

    # Act
    result = run_setup(options, world.deps())

    # Assert
    assert result.ok is False
    assert result.config.bigquery.enabled is False
    assert world.provisioned == []
    assert world.interactive_runs == []
    output = world.stdout.getvalue()
    assert "FAIL  adc" in output
    assert "gcloud auth application-default login" in output
    assert "Local metrics keep working" in output


def test_cloud_interactive_runs_adc_login_in_the_terminal(world: World) -> None:
    # Arrange
    world.gcloud.adc_ok = False
    prompter = ScriptedPrompter(
        {"Mode": "cloud", "GCP project": PROJECT, "Run `gcloud auth": True}
    )

    def fixed_after_login(argv: list[str]) -> int:
        world.interactive_runs.append(argv)
        world.gcloud.adc_ok = True
        return 0

    deps = replace(world.deps(prompter=prompter), run_interactive=fixed_after_login)

    # Act
    result = run_setup(SetupOptions(), deps)

    # Assert
    assert world.interactive_runs == [
        ["gcloud", "auth", "application-default", "login"]
    ]
    assert result.ok is True
    assert result.config.bigquery.project == PROJECT


def test_cloud_sandbox_mode_explains_expiry_and_skips_budget(world: World) -> None:
    # Arrange
    options = SetupOptions(
        mode="cloud", assume_yes=True, gcp_project=PROJECT, bq_mode="sandbox"
    )

    # Act
    result = run_setup(options, world.deps())

    # Assert
    assert result.config.bigquery.mode == "sandbox"
    assert "60 days" in world.stdout.getvalue()
    assert not any("budgets" in call for call in world.gcloud.calls)


def test_cloud_yes_without_project_is_a_usage_error(world: World) -> None:
    # Arrange / Act / Assert
    with pytest.raises(SetupUsageError, match="--gcp-project"):
        run_setup(SetupOptions(mode="cloud", assume_yes=True), world.deps())


def test_cloud_with_invalid_project_is_a_usage_error(world: World) -> None:
    # Arrange / Act / Assert
    with pytest.raises(SetupUsageError, match="project id"):
        run_setup(
            SetupOptions(mode="cloud", assume_yes=True, gcp_project="Bad Project"),
            world.deps(),
        )


# --------------------------------------------------------------------------- parsing


def test_parse_triggers() -> None:
    # Arrange / Act / Assert
    assert parse_triggers("hooks,scheduler") == frozenset({"hooks", "scheduler"})
    assert parse_triggers("none") == frozenset()
    with pytest.raises(ValueError, match="unknown trigger"):
        parse_triggers("hooks,cron")
    with pytest.raises(ValueError, match="'none' cannot be combined"):
        parse_triggers("none,hooks")
