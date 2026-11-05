"""Render findings as GitHub Markdown.

All text here comes from the model or from the pull request author, so it is
treated as hostile: it may have been steered by text in the diff.
"""

from __future__ import annotations

import re

from pr_reviewer.application.ports import ReviewOutcome
from pr_reviewer.domain.findings import fingerprint
from pr_reviewer.domain.models import DiffBundle, Finding, ReviewReport
from pr_reviewer.domain.pricing import estimate_cost

SUMMARY_MARKER = "<!-- pr-reviewer:summary -->"
MAX_COMMENT_CHARS = 65_000  # GitHub rejects comment bodies over 65,536 characters.
MAX_TITLE_CHARS = 200
MAX_IMPACT_CHARS = 2_000
MAX_FIX_CHARS = 4_000
MAX_OMITTED_ROWS = 100
FINGERPRINT_PATTERN = re.compile(r"<!-- pr-reviewer:finding=([0-9a-f]{16}) -->")

_SECRETS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.DOTALL),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bxox[abeoprs]-[A-Za-z0-9-]{10,}"),
)
_MENTION = re.compile(r"(?<!\w)@(?=[A-Za-z0-9])")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_BADGE = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}


def redact_secrets(text: str) -> str:
    for pattern in _SECRETS:
        text = pattern.sub("[redacted]", text)
    return text


def sanitize(text: str) -> str:
    """Make model text safe to render: no secrets, pings, images, HTML or forged markers.

    Code spans get no exemption. Their limits are hard to match exactly as
    GitHub parses them, and a mismatch would let raw HTML through.
    """
    clean = redact_secrets(text).replace("<", "&lt;").replace("![", "!\\[")
    return _MENTION.sub("@\u200b", clean)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _one_line(text: str, limit: int = MAX_TITLE_CHARS) -> str:
    return _clip(" ".join(sanitize(text).split()), limit)


def _fence(code: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", code)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}\n{code.strip()}\n{fence}"


def format_inline_comment(finding: Finding) -> str:
    badge = _BADGE[finding.severity]
    body = [
        f"{badge} **{finding.severity.capitalize()} · {finding.category}**: {_one_line(finding.title)}",
        "",
        _clip(sanitize(finding.impact), MAX_IMPACT_CHARS),
    ]
    fix = _clip(redact_secrets(finding.proposed_fix).strip(), MAX_FIX_CHARS)
    if fix:
        body += ["", "**Proposed fix**", "", _fence(fix)]
    body += ["", f"<!-- pr-reviewer:finding={fingerprint(finding)} -->"]
    return "\n".join(body)


def _usage_line(report: ReviewReport) -> str:
    usage = report.usage
    total = usage.input_tokens + usage.output_tokens
    cost = estimate_cost(report.model, usage)
    price = f"~${cost:.3f}" if cost is not None else "cost unknown"
    return f"{report.model or report.provider} · {total:,} tokens · {price}"


def _path(path: str) -> str:
    """Render a path the pull request author chose as one inert table or list cell."""
    flat = _CONTROL.sub("?", path).replace("`", "'").replace("|", "\\|")
    return "`" + _clip(sanitize(flat), MAX_TITLE_CHARS) + "`"


def _findings_table(findings: list[Finding]) -> list[str]:
    rows = ["| Severity | Location | Problem |", "| --- | --- | --- |"]
    for finding in findings:
        title = _one_line(finding.title).replace("|", "\\|")
        rows.append(f"| {_BADGE[finding.severity]} {finding.severity} | {_path(f'{finding.file}:{finding.line}')} | {title} |")
    return rows


def _file_list(paths: list[str], reason: str) -> list[str]:
    rows = [f"- {_path(path)} ({reason})" for path in paths[:MAX_OMITTED_ROWS]]
    if len(paths) > len(rows):
        rows.append(f"- and {len(paths) - len(rows)} more")
    return ["", f"<details><summary>{len(paths)} file(s) failed</summary>", "", *rows, "", "</details>"]


def _omitted_section(bundle: DiffBundle) -> list[str]:
    if not bundle.omitted:
        return []
    rows = [f"- {_path(item.path)} ({item.reason})" for item in bundle.omitted[:MAX_OMITTED_ROWS]]
    hidden = len(bundle.omitted) - len(rows)
    if hidden:
        rows.append(f"- and {hidden} more")
    return [
        "",
        f"<details><summary>{len(bundle.omitted)} file(s) not reviewed</summary>",
        "",
        *rows,
        "",
        "</details>",
    ]


def format_summary(outcome: ReviewOutcome) -> str:
    report, bundle, selection = outcome.report, outcome.bundle, outcome.selection
    lines = [SUMMARY_MARKER, "## AI review", ""]

    if report.status == "partial":
        reason = _one_line(report.error) or "unknown error"
        lines += [f"⚠️ {len(report.unreviewed)} file(s) could not be reviewed: `{reason}`", ""]
    if report.status == "failed":
        lines.append(f"⚠️ The review could not finish: `{_one_line(report.error) or 'unknown error'}`")
    elif not bundle.files:
        lines.append("Nothing was reviewed: no file in this pull request could be included.")
    elif not selection.kept:
        lines.append("✅ No problems found in the reviewed code." if report.status == "ok" else "No problems found in the files that were reviewed.")
    else:
        lines += _findings_table(selection.kept)
        lines.append("")
        if outcome.inline_rejected:
            lines.append("GitHub rejected the inline comments, so the findings are listed only here.")
        elif outcome.inline_posted:
            lines.append(f"{outcome.inline_posted} new inline comment(s) posted.")
        if outcome.already_posted:
            lines.append(f"{outcome.already_posted} finding(s) already posted in an earlier run.")

    hidden = selection.outside_diff + selection.filtered + selection.over_limit
    if hidden:
        lines += [
            "",
            f"{hidden} finding(s) not shown: {selection.outside_diff} outside the diff, "
            f"{selection.filtered} below the thresholds, {selection.over_limit} over the limit.",
        ]
    lines += _file_list(report.unreviewed, "failed") if report.status == "partial" else []
    lines += _omitted_section(bundle)
    lines += ["", f"<sub>{_usage_line(report)} · commit {bundle.head[:7]} · comment `/review` to run again</sub>"]
    return _clip("\n".join(lines), MAX_COMMENT_CHARS)
