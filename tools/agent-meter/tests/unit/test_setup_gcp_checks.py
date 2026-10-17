"""Tests for ``agent_meter.setup.gcp_checks`` (ADR §3.11 wizard checks; SU-05, SU-06, US-13)."""

from __future__ import annotations

import json
import socket
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest

from agent_meter.setup import gcp_checks
from agent_meter.setup.gcp_checks import (
    BUDGET_NOTE,
    REQUIRED_PERMISSIONS,
    Check,
    budget_alert_offer,
    run_checks,
)

PROJECT = "devhack-3f0c2"
TOKEN = "ya29.SECRET-TOKEN-VALUE"
EMAIL = "dev@example.com"


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    def refuse(*_args: object, **_kwargs: object) -> socket.socket:
        raise AssertionError("network access is not allowed in unit tests")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    yield


@dataclass
class FakeGcloud:
    installed: bool = True
    adc: str = "ok"  # ok | expired | missing
    project_exists: bool = True
    default_project: str = PROJECT
    billing: str = "True"  # True | False | error
    api_enabled: bool = True
    billing_account: str = "billingAccounts/0123AB-4567CD-89EF01"
    budgets: str = ""
    calls: list[list[str]] = field(default_factory=list)

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        if not self.installed:
            raise FileNotFoundError("gcloud")
        joined = " ".join(args)

        def done(
            code: int = 0, out: str = "", err: str = ""
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, code, out, err)

        if joined == "gcloud --version":
            return done(out="Google Cloud SDK 540.0.0\n")
        if joined.startswith("gcloud auth application-default print-access-token"):
            if self.adc == "expired":
                return done(
                    1,
                    err="ERROR: (gcloud.auth) Reauthentication failed. invalid_grant\n",
                )
            if self.adc == "missing":
                return done(
                    1, err="ERROR: Could not automatically determine credentials.\n"
                )
            return done(out=f"{TOKEN}\n")
        if joined.startswith(f"gcloud projects describe {PROJECT}"):
            return (
                done(out="123456789\n")
                if self.project_exists
                else done(1, err="NOT_FOUND\n")
            )
        if joined == "gcloud config get-value project":
            return done(out=f"{self.default_project}\n")
        if joined.startswith(f"gcloud billing projects describe {PROJECT}"):
            if "billingAccountName" in joined:
                return done(out=f"{self.billing_account}\n")
            if self.billing == "error":
                return done(1, err="PERMISSION_DENIED\n")
            return done(out=f"{self.billing}\n")
        if joined.startswith("gcloud services list --enabled"):
            return done(out="bigquery.googleapis.com\n" if self.api_enabled else "")
        if joined.startswith("gcloud billing budgets list"):
            return done(out=self.budgets)
        raise AssertionError(f"unexpected gcloud call: {joined}")


@dataclass
class FakeHttp:
    granted: tuple[str, ...] = REQUIRED_PERMISSIONS
    email: str | None = EMAIL
    offline: bool = False
    requests: list[tuple[str, dict[str, str], bytes]] = field(default_factory=list)

    def __call__(
        self, url: str, headers: dict[str, str], body: bytes
    ) -> tuple[int, bytes]:
        self.requests.append((url, headers, body))
        if self.offline:
            raise OSError("network unreachable")
        if url.endswith(":testIamPermissions"):
            return 200, json.dumps({"permissions": list(self.granted)}).encode()
        if "tokeninfo" in url:
            payload: dict[str, Any] = {"email": self.email} if self.email else {}
            return 200, json.dumps(payload).encode()
        raise AssertionError(f"unexpected url {url}")


def by_id(checks: list[Check]) -> dict[str, Check]:
    return {check.id: check for check in checks}


def test_all_prerequisites_met_returns_ok_in_fixed_order() -> None:
    # Arrange
    gcloud, http = FakeGcloud(), FakeHttp()

    # Act
    checks = run_checks(PROJECT, runner=gcloud, http=http)

    # Assert
    assert [c.id for c in checks] == [
        "gcloud",
        "adc",
        "project",
        "default-project",
        "billing",
        "api",
        "iam",
    ]
    assert {c.status for c in checks} == {"OK"}


def test_missing_gcloud_stops_with_install_guidance() -> None:
    # Arrange
    gcloud = FakeGcloud(installed=False)

    # Act
    checks = run_checks(PROJECT, runner=gcloud, http=FakeHttp())

    # Assert
    assert checks == [
        Check(
            id="gcloud",
            status="FAIL",
            message="gcloud CLI not found. Install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install",
            fix_command=None,
            autofix_safe=False,
        )
    ]


@pytest.mark.parametrize(
    ("adc", "phrase"),
    [("expired", "expired"), ("missing", "not configured")],
)
def test_bad_adc_fails_with_login_command_and_skips_iam(adc: str, phrase: str) -> None:
    # Arrange
    gcloud, http = FakeGcloud(adc=adc), FakeHttp()

    # Act
    checks = by_id(run_checks(PROJECT, runner=gcloud, http=http))

    # Assert
    assert checks["adc"].status == "FAIL"
    assert phrase in checks["adc"].message
    assert checks["adc"].fix_command == "gcloud auth application-default login"
    assert checks["adc"].autofix_safe is True
    assert checks["iam"].status == "WARN"
    assert "Application Default Credentials" in checks["iam"].message
    assert http.requests == []


def test_wrong_default_project_only_warns_and_explicit_project_is_always_used() -> None:
    # Arrange
    gcloud = FakeGcloud(default_project="overty-sphere")

    # Act
    checks = by_id(run_checks(PROJECT, runner=gcloud, http=FakeHttp()))

    # Assert
    check = checks["default-project"]
    assert check.status == "WARN"
    assert check.message == (
        "gcloud's default project is 'overty-sphere'; agent-meter ignores it and always uses "
        f"'{PROJECT}' explicitly"
    )
    assert check.fix_command is None
    for call in gcloud.calls:
        assert "overty-sphere" not in call
        if "--project" in call:
            assert call[call.index("--project") + 1] == PROJECT


def test_unknown_project_fails_and_skips_project_scoped_checks() -> None:
    # Arrange
    gcloud = FakeGcloud(project_exists=False)

    # Act
    checks = run_checks(PROJECT, runner=gcloud, http=FakeHttp())

    # Assert
    assert [c.id for c in checks] == ["gcloud", "adc", "project"]
    assert checks[-1].status == "FAIL"
    assert checks[-1].fix_command == 'gcloud projects list --format="value(projectId)"'
    assert checks[-1].autofix_safe is True


def test_billing_not_linked_fails_with_link_command_and_sandbox_alternative() -> None:
    # Arrange
    gcloud = FakeGcloud(billing="False")

    # Act
    check = by_id(run_checks(PROJECT, runner=gcloud, http=FakeHttp()))["billing"]

    # Assert
    assert check.status == "FAIL"
    assert check.fix_command == (
        f"gcloud billing projects link {PROJECT} --billing-account=BILLING_ACCOUNT_ID"
    )
    assert "gcloud billing accounts list" in check.message
    assert "--mode sandbox" in check.message
    assert check.autofix_safe is False


def test_billing_not_linked_is_fine_in_sandbox_mode() -> None:
    # Arrange
    gcloud = FakeGcloud(billing="False")

    # Act
    check = by_id(run_checks(PROJECT, runner=gcloud, http=FakeHttp(), mode="sandbox"))[
        "billing"
    ]

    # Assert
    assert check.status == "OK"
    assert "60 days" in check.message


def test_billing_status_unknown_warns() -> None:
    # Arrange
    gcloud = FakeGcloud(billing="error")

    # Act
    check = by_id(run_checks(PROJECT, runner=gcloud, http=FakeHttp()))["billing"]

    # Assert
    assert check.status == "WARN"
    assert "PERMISSION_DENIED" in check.message


def test_bigquery_api_disabled_fails_with_safe_enable_command() -> None:
    # Arrange
    gcloud = FakeGcloud(api_enabled=False)

    # Act
    check = by_id(run_checks(PROJECT, runner=gcloud, http=FakeHttp()))["api"]

    # Assert
    assert check.status == "FAIL"
    assert check.message == f"The BigQuery API is not enabled in project '{PROJECT}'"
    assert (
        check.fix_command
        == f"gcloud services enable bigquery.googleapis.com --project {PROJECT}"
    )
    assert check.autofix_safe is True


def test_missing_iam_permissions_fail_with_role_bindings_for_adc_account() -> None:
    # Arrange
    http = FakeHttp(granted=("bigquery.jobs.create",))

    # Act
    check = by_id(run_checks(PROJECT, runner=FakeGcloud(), http=http))["iam"]

    # Assert
    assert check.status == "FAIL"
    assert "bigquery.datasets.create" in check.message
    assert "bigquery.jobs.create" not in check.message.split("missing", 1)[1]
    assert check.fix_command == (
        f"gcloud projects add-iam-policy-binding {PROJECT} --member=user:{EMAIL} "
        "--role=roles/bigquery.dataEditor && "
        f"gcloud projects add-iam-policy-binding {PROJECT} --member=user:{EMAIL} "
        "--role=roles/bigquery.jobUser"
    )
    assert check.autofix_safe is False
    url, headers, body = http.requests[0]
    assert (
        url
        == f"https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT}:testIamPermissions"
    )
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert json.loads(body) == {"permissions": list(REQUIRED_PERMISSIONS)}


def test_iam_check_offline_warns() -> None:
    # Arrange
    http = FakeHttp(offline=True)

    # Act
    check = by_id(run_checks(PROJECT, runner=FakeGcloud(), http=http))["iam"]

    # Assert
    assert check.status == "WARN"
    assert "could not verify" in check.message


def test_access_token_never_appears_in_results() -> None:
    # Arrange
    http = FakeHttp(granted=())

    # Act
    checks = run_checks(PROJECT, runner=FakeGcloud(), http=http)

    # Assert
    rendered = repr(checks)
    assert TOKEN not in rendered


def test_invalid_project_id_is_rejected() -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="project id"):
        run_checks("bad project; rm -rf /", runner=FakeGcloud(), http=FakeHttp())


def test_budget_offer_returns_exact_create_command_and_no_cap_warning() -> None:
    # Arrange
    gcloud = FakeGcloud()

    # Act
    check = budget_alert_offer(PROJECT, runner=gcloud)

    # Assert
    assert check.id == "budget"
    assert check.status == "WARN"
    assert check.fix_command == (
        "gcloud billing budgets create --billing-account=0123AB-4567CD-89EF01 "
        "--display-name=agent-meter --budget-amount=1USD "
        "--threshold-rule=percent=0.5 --threshold-rule=percent=1.0"
    )
    assert BUDGET_NOTE in check.message
    assert "does not cap" in BUDGET_NOTE
    assert check.autofix_safe is True


def test_budget_offer_is_ok_when_budget_exists() -> None:
    # Arrange
    gcloud = FakeGcloud(budgets="agent-meter\n")

    # Act
    check = budget_alert_offer(PROJECT, runner=gcloud)

    # Assert
    assert check.status == "OK"
    assert check.fix_command is None


def test_budget_offer_without_billing_account_explains() -> None:
    # Arrange
    gcloud = FakeGcloud(billing_account="")

    # Act
    check = budget_alert_offer(PROJECT, runner=gcloud)

    # Assert
    assert check.status == "WARN"
    assert check.fix_command is None
    assert "no billing account" in check.message


def test_default_runner_disables_prompts_and_sets_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    seen: dict[str, Any] = {}

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen["args"] = args
        seen.update(kwargs)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Act
    gcp_checks.default_runner(["gcloud", "--version"])

    # Assert
    assert seen["args"] == ["gcloud", "--version"]
    assert seen["timeout"] == 20
    assert seen["env"]["CLOUDSDK_CORE_DISABLE_PROMPTS"] == "1"
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert "shell" not in seen


def test_default_runner_turns_timeout_into_failed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    def slow(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(args, 20)

    monkeypatch.setattr(subprocess, "run", slow)

    # Act
    result = gcp_checks.default_runner(["gcloud", "projects", "list"])

    # Assert
    assert result.returncode == 124
    assert "timed out" in result.stderr


@pytest.mark.parametrize(
    ("status", "payload"),
    [(403, b'{"error": {"code": 403}}'), (200, b"[1, 2]"), (200, b"not json")],
)
def test_iam_check_with_unusable_response_warns(status: int, payload: bytes) -> None:
    # Arrange
    def http(url: str, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
        return status, payload

    # Act
    check = by_id(run_checks(PROJECT, runner=FakeGcloud(), http=http))["iam"]

    # Assert
    assert check.status == "WARN"
    assert "could not verify" in check.message
