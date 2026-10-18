"""Guided BigQuery prerequisites for ``setup --cloud`` (ADR §3.11 wizard checks, US-13).

Every check returns a ``Check`` naming the exact problem and the exact fix command. The GCP
project is always passed explicitly; the gcloud default project is reported, never used.
``gcloud`` runs through an injectable ``runner`` (no shell, prompts disabled, 20 s timeout).
The IAM probe calls Resource Manager ``testIamPermissions`` with the ADC access token through
an injectable ``http`` callable. The token is held in memory only and never returned or logged.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Literal

__all__ = [
    "BUDGET_NOTE",
    "INSTALL_URL",
    "REQUIRED_PERMISSIONS",
    "Check",
    "HttpPost",
    "Runner",
    "budget_alert_offer",
    "default_http",
    "default_runner",
    "run_checks",
    "validate_project_id",
]

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]
HttpPost = Callable[[str, dict[str, str], bytes], tuple[int, bytes]]
Status = Literal["OK", "WARN", "FAIL"]

INSTALL_URL: Final = "https://cloud.google.com/sdk/docs/install"
# Only project-level permissions: Cloud Resource Manager `testIamPermissions` never returns
# dataset-scoped ones such as `bigquery.tables.create`/`updateData`, even for project owners.
# The account that creates the dataset becomes its owner, which covers table creation and loads.
REQUIRED_PERMISSIONS: Final = (
    "bigquery.datasets.create",
    "bigquery.jobs.create",
)
BUDGET_NOTE: Final = "A budget alert only emails you at 50% and 100% of $1; it does not cap or stop spending."
_TIMEOUT_S: Final = 20
_PROJECT_ID: Final = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_IAM_URL: Final = "https://cloudresourcemanager.googleapis.com/v1/projects/{project}:testIamPermissions"
_TOKENINFO_URL: Final = "https://oauth2.googleapis.com/tokeninfo"
_EXPIRED_MARKERS: Final = ("reauth", "invalid_grant", "expired", "invalid_rapt")


@dataclass(frozen=True, slots=True)
class Check:
    id: str
    status: Status
    message: str
    fix_command: str | None
    autofix_safe: bool


def default_runner(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ``gcloud`` without a shell, with prompts disabled and a 20 s timeout."""
    env = {**os.environ, "CLOUDSDK_CORE_DISABLE_PROMPTS": "1"}
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args, 124, "", f"{args[0]}: timed out after {_TIMEOUT_S}s"
        )


def default_http(url: str, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
    """HTTPS POST returning ``(status, body)``; connection errors raise ``OSError``."""
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
            return int(response.status), bytes(response.read())
    except urllib.error.HTTPError as exc:
        return int(exc.code), bytes(exc.read())


def validate_project_id(project: str) -> str:
    if not _PROJECT_ID.fullmatch(project):
        raise ValueError(
            f"{project!r} is not a valid GCP project id (6-30 chars: a-z, 0-9, -)"
        )
    return project


def _first_line(text: str) -> str:
    stripped = text.strip()
    return stripped.splitlines()[0] if stripped else "no output"


class _Gcloud:
    """Runs gcloud through the injected runner; a missing binary becomes exit code 127."""

    def __init__(self, runner: Runner) -> None:
        self._runner = runner

    def __call__(self, *args: str) -> subprocess.CompletedProcess[str]:
        argv = ["gcloud", *args]
        try:
            return self._runner(argv)
        except FileNotFoundError:
            return subprocess.CompletedProcess(
                argv, 127, "", "gcloud: command not found"
            )


def _ok(check_id: str, message: str) -> Check:
    return Check(check_id, "OK", message, None, False)


def _check_gcloud(gcloud: _Gcloud) -> Check:
    result = gcloud("--version")
    if result.returncode != 0:
        return Check(
            "gcloud",
            "FAIL",
            f"gcloud CLI not found. Install the Google Cloud SDK: {INSTALL_URL}",
            None,
            False,
        )
    return _ok("gcloud", f"gcloud installed ({_first_line(result.stdout)})")


def _check_adc(gcloud: _Gcloud) -> tuple[Check, str | None]:
    result = gcloud("auth", "application-default", "print-access-token")
    token = result.stdout.strip()
    if result.returncode == 0 and token:
        return _ok("adc", "Application Default Credentials are valid"), token
    stderr = result.stderr.lower()
    state = (
        "expired"
        if any(marker in stderr for marker in _EXPIRED_MARKERS)
        else "not configured"
    )
    return (
        Check(
            "adc",
            "FAIL",
            f"Application Default Credentials are {state}; agent-meter uploads with ADC",
            "gcloud auth application-default login",
            True,
        ),
        None,
    )


def _check_project(gcloud: _Gcloud, project: str) -> Check:
    result = gcloud("projects", "describe", project, "--format=value(projectNumber)")
    if result.returncode != 0 or not result.stdout.strip():
        return Check(
            "project",
            "FAIL",
            f"Project '{project}' was not found or is not accessible with your gcloud account "
            f"({_first_line(result.stderr)}); pick one of your projects or create one with "
            f"`gcloud projects create {project}`",
            'gcloud projects list --format="value(projectId)"',
            True,
        )
    return _ok("project", f"Project '{project}' found (number {result.stdout.strip()})")


def _check_default_project(gcloud: _Gcloud, project: str) -> Check:
    current = gcloud("config", "get-value", "project").stdout.strip()
    if current == project:
        return _ok("default-project", f"gcloud's default project is '{project}'")
    shown = current or "(unset)"
    return Check(
        "default-project",
        "WARN",
        f"gcloud's default project is '{shown}'; agent-meter ignores it and always uses "
        f"'{project}' explicitly",
        None,
        False,
    )


def _check_billing(
    gcloud: _Gcloud, project: str, mode: Literal["billing", "sandbox"]
) -> Check:
    result = gcloud(
        "billing", "projects", "describe", project, "--format=value(billingEnabled)"
    )
    if result.returncode != 0:
        return Check(
            "billing",
            "WARN",
            f"Could not read the billing status of '{project}' ({_first_line(result.stderr)})",
            None,
            False,
        )
    if result.stdout.strip().lower() == "true":
        return _ok("billing", f"Billing is linked to '{project}'")
    if mode == "sandbox":
        return _ok(
            "billing",
            "No billing account: sandbox mode stores tables for 60 days, so agent-meter "
            "reloads them weekly with `sync --full-reload`",
        )
    return Check(
        "billing",
        "FAIL",
        f"Billing is not linked to '{project}'. Find your account id with "
        "`gcloud billing accounts list`, or run setup with `--mode sandbox` "
        "(no billing, tables expire after 60 days)",
        f"gcloud billing projects link {project} --billing-account=BILLING_ACCOUNT_ID",
        False,
    )


def _check_api(gcloud: _Gcloud, project: str) -> Check:
    result = gcloud(
        "services",
        "list",
        "--enabled",
        "--project",
        project,
        "--filter=config.name=bigquery.googleapis.com",
        "--format=value(config.name)",
    )
    if result.returncode == 0 and "bigquery.googleapis.com" in result.stdout:
        return _ok("api", f"The BigQuery API is enabled in '{project}'")
    return Check(
        "api",
        "FAIL",
        f"The BigQuery API is not enabled in project '{project}'",
        f"gcloud services enable bigquery.googleapis.com --project {project}",
        True,
    )


def _json_object(payload: bytes) -> dict[str, object]:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("unexpected response shape")
    return data


def _adc_email(http: HttpPost, token: str) -> str | None:
    body = urllib.parse.urlencode({"access_token": token}).encode()
    status, payload = http(
        _TOKENINFO_URL, {"Content-Type": "application/x-www-form-urlencoded"}, body
    )
    if status != 200:
        return None
    email = _json_object(payload).get("email")
    return email if isinstance(email, str) and email else None


def _iam_fix(project: str, email: str | None) -> str:
    member = f"user:{email or 'YOUR_ADC_EMAIL'}"
    return " && ".join(
        f"gcloud projects add-iam-policy-binding {project} --member={member} --role={role}"
        for role in ("roles/bigquery.dataEditor", "roles/bigquery.jobUser")
    )


def _missing_permissions(http: HttpPost, project: str, token: str) -> list[str]:
    """Resource Manager ``testIamPermissions``; raises ``OSError``/``ValueError`` when unusable."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = json.dumps({"permissions": list(REQUIRED_PERMISSIONS)}).encode()
    status, payload = http(_IAM_URL.format(project=project), headers, body)
    if status != 200:
        raise ValueError(f"HTTP {status}")
    permissions = _json_object(payload).get("permissions", [])
    granted = set(permissions) if isinstance(permissions, list) else set()
    return [perm for perm in REQUIRED_PERMISSIONS if perm not in granted]


def _check_iam(http: HttpPost, project: str, token: str | None) -> Check:
    if token is None:
        return Check(
            "iam",
            "WARN",
            "IAM permissions not checked: they need valid Application Default Credentials",
            None,
            False,
        )
    try:
        missing = _missing_permissions(http, project, token)
        email = _adc_email(http, token) if missing else None
    except (OSError, ValueError) as exc:
        return Check(
            "iam",
            "WARN",
            f"could not verify IAM permissions on '{project}' ({exc}); you need "
            "roles/bigquery.dataEditor and roles/bigquery.jobUser",
            None,
            False,
        )
    if not missing:
        return _ok("iam", "Your ADC account can create datasets, tables and load jobs")
    return Check(
        "iam",
        "FAIL",
        f"Your ADC account ({email or 'unknown'}) is missing {', '.join(missing)}; "
        "a project owner must grant roles/bigquery.dataEditor and roles/bigquery.jobUser",
        _iam_fix(project, email),
        False,
    )


def run_checks(
    project: str,
    *,
    runner: Runner = default_runner,
    http: HttpPost = default_http,
    mode: Literal["billing", "sandbox"] = "billing",
) -> list[Check]:
    """All cloud prerequisites in order; stops early when later checks cannot run."""
    validate_project_id(project)
    gcloud = _Gcloud(runner)
    first = _check_gcloud(gcloud)
    if first.status == "FAIL":
        return [first]
    adc, token = _check_adc(gcloud)
    checks = [first, adc, _check_project(gcloud, project)]
    if checks[-1].status == "FAIL":
        return checks
    checks.append(_check_default_project(gcloud, project))
    checks.append(_check_billing(gcloud, project, mode))
    checks.append(_check_api(gcloud, project))
    checks.append(_check_iam(http, project, token))
    return checks


def _billing_account(gcloud: _Gcloud, project: str) -> str | None:
    result = gcloud(
        "billing", "projects", "describe", project, "--format=value(billingAccountName)"
    )
    account = result.stdout.strip().removeprefix("billingAccounts/")
    return account if result.returncode == 0 and account else None


def _budget_exists(gcloud: _Gcloud, account: str, project: str) -> bool:
    budgets = gcloud(
        "billing",
        "budgets",
        "list",
        f"--billing-account={account}",
        f"--billing-project={project}",
        "--format=value(displayName)",
    )
    return budgets.returncode == 0 and "agent-meter" in budgets.stdout.split()


def budget_alert_offer(project: str, *, runner: Runner = default_runner) -> Check:
    """Offer a $1 budget alert on the project's billing account (alerts never cap spend)."""
    validate_project_id(project)
    gcloud = _Gcloud(runner)
    account = _billing_account(gcloud, project)
    if account is None:
        return Check(
            "budget",
            "WARN",
            f"'{project}' has no billing account linked, so no budget alert can be created. "
            + BUDGET_NOTE,
            None,
            False,
        )
    if _budget_exists(gcloud, account, project):
        return _ok(
            "budget", f"Budget alert 'agent-meter' already exists. {BUDGET_NOTE}"
        )
    return Check(
        "budget",
        "WARN",
        f"No agent-meter budget alert on billing account {account}. {BUDGET_NOTE}",
        # --billing-project: bill the Budget API call to the chosen project, never to
        # gcloud's default project (which may belong to another account or organization).
        f"gcloud billing budgets create --billing-account={account} --display-name=agent-meter "
        "--budget-amount=1USD --threshold-rule=percent=0.5 --threshold-rule=percent=1.0 "
        f"--billing-project={project}",
        True,
    )
