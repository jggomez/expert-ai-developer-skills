"""Tests for ``agent_meter.setup.cloud`` (wizard step 7 edge paths; SU-05, SU-06)."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field

from agent_meter.config import BigQueryConfig
from agent_meter.setup.cloud import CloudPrerequisites, CloudReadiness
from agent_meter.setup.gcp_checks import REQUIRED_PERMISSIONS

PROJECT = "devhack-3f0c2"


@dataclass
class SequencedPrompter:
    asks: list[str] = field(default_factory=list)
    confirms: dict[str, bool] = field(default_factory=dict)
    out: list[str] = field(default_factory=list)

    @property
    def interactive(self) -> bool:
        return True

    def info(self, text: str) -> None:
        self.out.append(text)

    def confirm(self, question: str, *, default: bool) -> bool:
        for key, value in self.confirms.items():
            if key in question:
                return value
        return default

    def choose(self, question: str, options: Sequence[str], *, default: str) -> str:
        return default

    def ask(self, question: str, *, default: str = "") -> str:
        return self.asks.pop(0)


@dataclass
class Gcloud:
    enable_fails: bool = False
    api_enabled: bool = True
    calls: list[list[str]] = field(default_factory=list)

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        joined = " ".join(args)
        outputs = {  # most specific keys first: billing describes also match "projects describe"
            "billingEnabled": "True\n",
            "billingAccountName": "billingAccounts/ABC\n",
            "gcloud --version": "Google Cloud SDK\n",
            "print-access-token": "tok\n",
            "projects describe": "42\n",
            "config get-value project": f"{PROJECT}\n",
            "budgets list": "",
            "services list": "bigquery.googleapis.com\n" if self.api_enabled else "",
        }
        if joined.startswith("gcloud services enable"):
            code = 1 if self.enable_fails else 0
            return subprocess.CompletedProcess(
                args, code, "", "PERMISSION_DENIED: no\n"
            )
        for key, out in outputs.items():
            if key in joined:
                return subprocess.CompletedProcess(args, 0, out, "")
        raise AssertionError(f"unexpected call {joined}")


def http(url: str, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
    return 200, json.dumps({"permissions": list(REQUIRED_PERMISSIONS)}).encode()


def no_terminal(argv: list[str]) -> int:
    raise AssertionError("no interactive command expected")


def test_invalid_project_answer_is_asked_again() -> None:
    # Arrange
    prompter = SequencedPrompter(
        asks=["Not Valid", PROJECT], confirms={"budget": False}
    )
    gcloud = Gcloud()

    # Act
    readiness = CloudPrerequisites(
        prompter, runner=gcloud, http=http, run_interactive=no_terminal
    ).run(project=None, mode=None, current=BigQueryConfig())

    # Assert
    assert readiness == CloudReadiness(True, PROJECT, "billing", False)
    assert any("not a valid GCP project id" in line for line in prompter.out)
    assert not any("budgets create" in " ".join(call) for call in gcloud.calls)


def test_failed_autofix_reports_stderr_and_leaves_cloud_not_ready() -> None:
    # Arrange
    prompter = SequencedPrompter()
    gcloud = Gcloud(enable_fails=True, api_enabled=False)

    # Act
    readiness = CloudPrerequisites(
        prompter, runner=gcloud, http=http, run_interactive=no_terminal
    ).run(project=PROJECT, mode="billing", current=BigQueryConfig())

    # Assert
    assert readiness.ready is False
    assert any("failed: PERMISSION_DENIED: no" in line for line in prompter.out)
    services_lists = [
        c for c in gcloud.calls if c[:3] == ["gcloud", "services", "list"]
    ]
    assert len(services_lists) == 1


def test_declined_autofix_is_not_run() -> None:
    # Arrange
    prompter = SequencedPrompter(confirms={"Run `gcloud services enable": False})
    gcloud = Gcloud(api_enabled=False)

    # Act
    readiness = CloudPrerequisites(
        prompter, runner=gcloud, http=http, run_interactive=no_terminal
    ).run(project=PROJECT, mode="billing", current=BigQueryConfig())

    # Assert
    assert readiness.ready is False
    assert not any(c[:3] == ["gcloud", "services", "enable"] for c in gcloud.calls)
