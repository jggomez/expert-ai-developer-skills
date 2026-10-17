"""``agent-meter setup``: the re-runnable, consent-first setup wizard (PLAN steps 1-8, US-10/13).

Steps: detect hosts, choose mode, choose triggers (hooks with a JSON preview + consent, and/or
the scheduler), privacy defaults, backfill, projects, cloud prerequisites, summary + doctor.
Every side effect goes through ``SetupDeps`` so the flow is testable without a real home,
network or scheduler. ``setup --local --yes`` performs no network calls: the cloud
dependencies (``gcp_runner``, ``gcp_http``, ``provision_cloud``) are only used in cloud mode.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, get_args

from agent_meter import scheduler
from agent_meter.config import Config
from agent_meter.model import Host
from agent_meter.setup import gcp_checks
from agent_meter.setup._files import HomeLike
from agent_meter.setup.cloud import BigQueryMode, CloudPrerequisites, CloudReadiness
from agent_meter.setup.gcp_checks import HttpPost, Runner, validate_project_id
from agent_meter.setup.hosts import (
    ANTIGRAVITY_HOSTS,
    antigravity_hooks_path,
    antigravity_plugin_installed,
    claude_plugin_installed,
    claude_settings_path,
    detect_hosts,
)
from agent_meter.setup.prompter import Prompter
from agent_meter.setup.settings_merge import (
    MergePlan,
    PlanStale,
    SettingsRefused,
    apply,
    command_prefix,
    plan_antigravity,
    plan_claude,
    render_preview,
)

__all__ = [
    "Mode",
    "SetupDeps",
    "SetupOptions",
    "SetupResult",
    "SetupUsageError",
    "Trigger",
    "parse_triggers",
    "run_setup",
]

Mode = Literal["local", "cloud"]
Trigger = Literal["hooks", "scheduler"]

_TRIGGER_CHOICES: Final = ("hooks,scheduler", "hooks", "scheduler", "none")
_STEPS: Final = 8


class SetupUsageError(ValueError):
    """Invalid flag combination (CLI exit code 2)."""


def parse_triggers(text: str) -> frozenset[Trigger]:
    """``--triggers hooks,scheduler`` | ``hooks`` | ``scheduler`` | ``none``."""
    names = [part.strip() for part in text.split(",") if part.strip()]
    if "none" in names:
        if len(names) > 1:
            raise ValueError("'none' cannot be combined with other triggers")
        return frozenset()
    valid = get_args(Trigger)
    unknown = [name for name in names if name not in valid]
    if unknown or not names:
        raise ValueError(
            f"unknown trigger {unknown[0] if unknown else text!r}; use hooks, scheduler or none"
        )
    return frozenset(name for name in valid if name in names)


@dataclass(frozen=True, slots=True)
class SetupOptions:
    mode: Mode | None = None
    assume_yes: bool = False
    hosts: tuple[Host, ...] | None = None
    triggers: frozenset[Trigger] | None = None
    gcp_project: str | None = None
    bq_mode: BigQueryMode | None = None
    backfill: bool = True


def _install_scheduler(home: HomeLike, executable: Path) -> str:
    return scheduler.install(home, executable)


def _run_in_terminal(argv: list[str]) -> int:
    """Run an interactive fix (e.g. a browser login) attached to the user's terminal; no shell."""
    return subprocess.run(argv, check=False).returncode


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class SetupDeps:
    home: HomeLike
    config: Config
    save_config: Callable[[Config], None]
    executable: Path
    user_home: Path
    environ: Mapping[str, str]
    prompter: Prompter
    install_scheduler: Callable[[HomeLike, Path], str] = _install_scheduler
    gcp_runner: Runner = gcp_checks.default_runner
    gcp_http: HttpPost = gcp_checks.default_http
    run_interactive: Callable[[list[str]], int] = _run_in_terminal
    backfill: Callable[[], str] | None = None
    configure_projects: Callable[[Prompter], str] | None = None
    provision_cloud: Callable[[Config], str] | None = None
    doctor: Callable[[], str] | None = None
    now: Callable[[], datetime] = _utcnow


@dataclass(frozen=True, slots=True)
class SetupResult:
    ok: bool
    changed: bool
    config: Config
    actions: tuple[str, ...]


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


class _Wizard:
    def __init__(self, options: SetupOptions, deps: SetupDeps) -> None:
        self.options = options
        self.deps = deps
        self.say = deps.prompter
        self.cfg = deps.config
        self.actions: list[str] = []
        self.changed = False
        self.ok = True

    # ------------------------------------------------------------------ flow

    def run(self) -> SetupResult:
        self._validate()
        selected = self._detect()
        mode = self._mode()
        triggers = self._triggers()
        if "hooks" in triggers:
            triggers = self._register_hooks(selected, triggers)
        if "scheduler" in triggers:
            self._install_scheduler()
        self._privacy(mode)
        self._backfill()
        self._projects()
        if mode == "cloud":
            self._cloud()
        self._summary()
        return SetupResult(self.ok, self.changed, self.cfg, tuple(self.actions))

    def _step(self, number: int, title: str) -> None:
        self.say.info(f"\n[{number}/{_STEPS}] {title}")

    def _record(self, action: str, *, changed: bool) -> None:
        self.actions.append(action)
        self.changed |= changed

    def _fail(self, action: str) -> None:
        self.say.info(f"  {action}")
        self.actions.append(action)
        self.ok = False

    def _validate(self) -> None:
        opts = self.options
        if opts.mode == "cloud" and opts.assume_yes and not opts.gcp_project:
            raise SetupUsageError("--cloud --yes needs --gcp-project <project id>")
        if opts.gcp_project is not None:
            try:
                validate_project_id(opts.gcp_project)
            except ValueError as exc:
                raise SetupUsageError(str(exc)) from exc

    # ------------------------------------------------------------------ steps 1-3

    def _detect(self) -> tuple[Host, ...]:
        self._step(1, "Detect hosts")
        detected = detect_hosts(self.deps.user_home, self.deps.environ)
        for found in detected:
            word = "session" if found.host is Host.CLAUDE_CODE else "conversation"
            history = f" · {_plural(found.units, word)}" if found.present else ""
            state = "found" if found.present else "not found"
            self.say.info(f"  {found.host.value:<16} {state:<9} {found.root}{history}")
        if self.options.hosts is not None:
            return self.options.hosts
        selected = tuple(found.host for found in detected if found.present)
        if not selected:
            self.say.info(
                "  no supported host found; install Claude Code or Antigravity, then re-run setup"
            )
        return selected

    def _mode(self) -> Mode:
        self._step(2, "Mode")
        if self.options.mode is not None:
            self.say.info(f"  {self.options.mode}")
            return self.options.mode
        default: Mode = "cloud" if self.cfg.bigquery.enabled else "local"
        answer = self.say.choose(
            "Mode: local only, or local + BigQuery cloud?",
            ["local", "cloud"],
            default=default,
        )
        return "cloud" if answer == "cloud" else "local"

    def _triggers(self) -> frozenset[Trigger]:
        self._step(3, "Triggers")
        if self.options.triggers is not None:
            return self.options.triggers
        answer = self.say.choose(
            "Triggers: host hooks (summary after each task/session) and/or the 15-min scheduler?",
            list(_TRIGGER_CHOICES),
            default=_TRIGGER_CHOICES[0],
        )
        return parse_triggers(answer)

    def _hook_targets(
        self, selected: tuple[Host, ...]
    ) -> list[tuple[str, Path, Callable[[Path, str], MergePlan], bool]]:
        user_home, environ = self.deps.user_home, self.deps.environ
        targets: list[tuple[str, Path, Callable[[Path, str], MergePlan], bool]] = []
        if Host.CLAUDE_CODE in selected:
            path = claude_settings_path(user_home, environ)
            targets.append(
                ("claude-code", path, plan_claude, claude_plugin_installed(path))
            )
        if ANTIGRAVITY_HOSTS.intersection(selected):
            targets.append(
                (
                    "antigravity",
                    antigravity_hooks_path(user_home),
                    plan_antigravity,
                    antigravity_plugin_installed(user_home),
                )
            )
        return targets

    def _register_hooks(
        self, selected: tuple[Host, ...], triggers: frozenset[Trigger]
    ) -> frozenset[Trigger]:
        prefix = command_prefix(self.deps.executable)
        refused = False
        for label, path, planner, plugin in self._hook_targets(selected):
            if plugin:
                self.say.info(
                    f"  {label}: the agent-metrics plugin is installed and registers the hooks; "
                    "skipping user-level hooks"
                )
                continue
            try:
                plan = planner(path, prefix)
            except SettingsRefused as exc:
                self.say.info(f"  {exc}")
                self._record(
                    f"{label} hooks: not registered ({exc.reason})", changed=False
                )
                refused = True
                continue
            self._apply_plan(label, plan)
        offer_scheduler = refused and "scheduler" not in triggers
        if offer_scheduler and self.say.confirm(
            "Install the scheduler instead so these hosts are still collected every 15 min?",
            default=True,
        ):
            return triggers | {"scheduler"}
        return triggers

    def _apply_plan(self, label: str, plan: MergePlan) -> None:
        self.say.info(render_preview(plan, self.deps.home))
        if not plan.changed:
            self._record(f"{label} hooks: no changes", changed=False)
            return
        if not self.say.confirm(f"Apply this change to {plan.file}?", default=True):
            self._record(
                f"{label} hooks: declined; {plan.file} left untouched", changed=False
            )
            return
        try:
            apply(plan, self.deps.home, now=self.deps.now())
        except PlanStale as exc:
            self._fail(f"{label} hooks: {exc}")
            return
        self._record(f"{label} hooks registered in {plan.file}", changed=True)

    def _install_scheduler(self) -> None:
        try:
            message = self.deps.install_scheduler(self.deps.home, self.deps.executable)
        except scheduler.SchedulerError as exc:
            self._fail(f"scheduler not installed: {exc}")
            return
        self.say.info(f"  {message}")
        self._record(message, changed=not message.endswith(scheduler.NO_CHANGES))

    # ------------------------------------------------------------------ steps 4-6

    def _save(self, cfg: Config, action: str) -> None:
        if cfg == self.cfg:
            return
        self.deps.save_config(cfg)
        self.cfg = cfg
        self._record(action, changed=True)

    def _privacy(self, mode: Mode) -> None:
        self._step(4, "Privacy")
        cfg = self.cfg
        if self.options.hosts is not None:
            chosen = set(self.options.hosts)
            hosts = {
                host: replace(cfg.host(host), enabled=host in chosen) for host in Host
            }
            cfg = replace(cfg, hosts=hosts)
        # Subagent descriptions are always stored as salted hashes in v1; the
        # store_agent_descriptions key is reserved for v2, so there is nothing to ask.
        if mode == "cloud":
            anonymize = self.say.confirm(
                "Anonymize project names before uploading to BigQuery?",
                default=cfg.bigquery.anonymize_projects,
            )
            cfg = replace(
                cfg, bigquery=replace(cfg.bigquery, anonymize_projects=anonymize)
            )
        self._save(cfg, "saved host and privacy settings to config.toml")

    def _backfill(self) -> None:
        self._step(5, "Backfill")
        if not self.options.backfill:
            self.say.info(
                "  skipped (--no-backfill); run `agent-meter collect` any time"
            )
            return
        if self.deps.backfill is None:
            return
        if self.say.confirm("Import existing history now?", default=True):
            self.say.info(f"  {self.deps.backfill()}")

    def _projects(self) -> None:
        self._step(6, "Projects and clients")
        configure = self.deps.configure_projects
        if (
            configure is not None
            and self.say.interactive
            and self.say.confirm("Review projects and clients now?", default=False)
        ):
            self.say.info(configure(self.say))
            return
        self.say.info(
            "  edit display names, clients and rates any time with `agent-meter projects`"
        )

    # ------------------------------------------------------------------ step 7 (cloud)

    def _cloud(self) -> None:
        self._step(7, "Cloud prerequisites (BigQuery)")
        readiness = CloudPrerequisites(
            self.say,
            runner=self.deps.gcp_runner,
            http=self.deps.gcp_http,
            run_interactive=self.deps.run_interactive,
        ).run(
            project=self.options.gcp_project,
            mode=self.options.bq_mode,
            current=self.cfg.bigquery,
        )
        if readiness.budget_created:
            self._record(
                f"created the $1 budget alert for {readiness.project} (alerts do not cap spend)",
                changed=True,
            )
        if not readiness.ready:
            self._fail(
                "Cloud setup incomplete: fix the FAIL items above and run `agent-meter setup "
                "--cloud` again. Local metrics keep working."
            )
            return
        self._enable_bigquery(readiness)

    def _enable_bigquery(self, readiness: CloudReadiness) -> None:
        """Provision the dataset first; the sink is enabled in config only after it succeeds."""
        bigquery = replace(
            self.cfg.bigquery,
            enabled=True,
            project=readiness.project,
            mode=readiness.mode,
        )
        candidate = replace(self.cfg, bigquery=bigquery)
        if self.deps.provision_cloud is not None:
            self.say.info(f"  {self.deps.provision_cloud(candidate)}")
        self._save(
            candidate,
            f"enabled the BigQuery sink for {readiness.project} ({readiness.mode} mode)",
        )

    # ------------------------------------------------------------------ step 8

    def _summary(self) -> None:
        self._step(8, "Summary")
        for action in self.actions:
            self.say.info(f"  - {action}")
        outcome = "changes applied" if self.changed else "no changes"
        problems = "" if self.ok else " (with problems, see above)"
        self.say.info(f"Setup complete: {outcome}{problems}")
        if self.deps.doctor is not None:
            self.say.info(self.deps.doctor())


def run_setup(options: SetupOptions, deps: SetupDeps) -> SetupResult:
    """Run the wizard; raises ``SetupUsageError`` for bad flags and ``WizardAborted`` on Ctrl-D."""
    return _Wizard(options, deps).run()
