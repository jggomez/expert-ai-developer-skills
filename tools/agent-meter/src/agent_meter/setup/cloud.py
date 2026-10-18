"""Wizard step 7: guided BigQuery prerequisites (US-13, ADR §3.11).

Asks for the project and mode, runs ``gcp_checks``, offers to run each fix marked
``autofix_safe`` (browser logins only in an interactive terminal), re-checks once, and offers
the $1 budget alert in billing mode. The project is always the one chosen here, never the
gcloud default (SU-06).
"""

from __future__ import annotations

import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Literal

from agent_meter.config import BigQueryConfig
from agent_meter.setup.gcp_checks import (
    Check,
    HttpPost,
    Runner,
    budget_alert_offer,
    run_checks,
    validate_project_id,
)
from agent_meter.setup.prompter import Prompter

__all__ = ["SANDBOX_NOTE", "BigQueryMode", "CloudPrerequisites", "CloudReadiness"]

BigQueryMode = Literal["billing", "sandbox"]

SANDBOX_NOTE: Final = (
    "Sandbox mode: BigQuery deletes table data after 60 days, so the scheduler re-uploads "
    "everything weekly with `agent-meter sync --full-reload`."
)
_INTERACTIVE_FIXES: Final = frozenset({"adc"})
_PROJECT_QUESTION: Final = "GCP project id for BigQuery"


@dataclass(frozen=True, slots=True)
class CloudReadiness:
    ready: bool  # no FAIL check remains
    project: str
    mode: BigQueryMode
    budget_created: bool


def _failure_detail(result: subprocess.CompletedProcess[str]) -> str:
    return result.stderr.strip() or f"exit code {result.returncode}"


class CloudPrerequisites:
    def __init__(
        self,
        prompter: Prompter,
        *,
        runner: Runner,
        http: HttpPost,
        run_interactive: Callable[[list[str]], int],
    ) -> None:
        self._say = prompter
        self._runner = runner
        self._http = http
        self._run_interactive = run_interactive

    def run(
        self, *, project: str | None, mode: BigQueryMode | None, current: BigQueryConfig
    ) -> CloudReadiness:
        chosen_project = project or self._ask_project(current.project)
        chosen_mode = mode or self._ask_mode(current.mode)
        if chosen_mode == "sandbox":
            self._say.info(f"  {SANDBOX_NOTE}")
        checks = self._check_and_fix(chosen_project, chosen_mode)
        if any(check.status == "FAIL" for check in checks):
            return CloudReadiness(False, chosen_project, chosen_mode, False)
        budget = chosen_mode == "billing" and self._offer_budget(chosen_project)
        return CloudReadiness(True, chosen_project, chosen_mode, budget)

    # ------------------------------------------------------------------ questions

    def _ask_project(self, default: str) -> str:
        project = self._say.ask(_PROJECT_QUESTION, default=default)
        while True:
            try:
                return validate_project_id(project)
            except ValueError as exc:
                self._say.info(f"  {exc}")
                project = self._say.ask(_PROJECT_QUESTION)

    def _ask_mode(self, default: BigQueryMode) -> BigQueryMode:
        answer = self._say.choose(
            "BigQuery mode: billing (recommended, $1 budget alert offered) or sandbox "
            "(no billing, tables expire after 60 days)?",
            ["billing", "sandbox"],
            default=default,
        )
        return "sandbox" if answer == "sandbox" else "billing"

    # ------------------------------------------------------------------ checks and fixes

    def _show(self, check: Check) -> None:
        self._say.info(f"{check.status:<5} {check.id:<16} {check.message}")
        if check.fix_command and check.status != "OK":
            self._say.info(f"      fix: {check.fix_command}")

    def _run_checks(self, project: str, mode: BigQueryMode) -> list[Check]:
        checks = run_checks(project, runner=self._runner, http=self._http, mode=mode)
        for check in checks:
            self._show(check)
        return checks

    def _run_terminal_fix(self, command: str) -> bool:
        if not self._say.interactive:
            return False
        if not self._say.confirm(
            f"Run `{command}` now? (opens a browser)", default=True
        ):
            return False
        return self._run_interactive(shlex.split(command)) == 0

    def _run_captured_fix(self, command: str) -> bool:
        if not self._say.confirm(f"Run `{command}` now?", default=True):
            return False
        result = self._runner(shlex.split(command))
        if result.stdout.strip():
            self._say.info(result.stdout.rstrip())
        if result.returncode != 0:
            self._say.info(f"  `{command}` failed: {_failure_detail(result)}")
            return False
        return True

    def _run_fix(self, check: Check) -> bool:
        command = check.fix_command or ""
        if check.id in _INTERACTIVE_FIXES:
            return self._run_terminal_fix(command)
        return self._run_captured_fix(command)

    def _check_and_fix(self, project: str, mode: BigQueryMode) -> list[Check]:
        checks = self._run_checks(project, mode)
        fixable = [
            c for c in checks if c.status == "FAIL" and c.fix_command and c.autofix_safe
        ]
        # Every offered fix runs (no short-circuit) before a single re-check.
        if any([self._run_fix(check) for check in fixable]):
            self._say.info("Re-checking prerequisites...")
            checks = self._run_checks(project, mode)
        return checks

    def _offer_budget(self, project: str) -> bool:
        offer = budget_alert_offer(project, runner=self._runner)
        self._show(offer)
        if offer.fix_command is None:
            return False
        if not self._say.confirm("Create the $1 budget alert now?", default=True):
            return False
        # The Budget API is off by default in new projects; enabling it is free and idempotent.
        enable = self._runner(
            ["gcloud", "services", "enable", "billingbudgets.googleapis.com", "--project", project]
        )
        if enable.returncode != 0:
            self._say.info(f"  budget alert not created: {_failure_detail(enable)}")
            return False
        result = self._runner(shlex.split(offer.fix_command))
        if result.returncode != 0:
            self._say.info(f"  budget alert not created: {_failure_detail(result)}")
            return False
        return True
