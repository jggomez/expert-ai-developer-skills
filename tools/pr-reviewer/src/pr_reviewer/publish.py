"""Turn a review report into pull request comments.

Nothing here runs pull request code, and all model output is treated as
untrusted: it may have been steered by text in the diff.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from pr_reviewer.github import GitHubClient, GitHubError
from pr_reviewer.models import (
    SEVERITY_RANK,
    DiffBundle,
    Finding,
    ReviewReport,
    Severity,
)
from pr_reviewer.pricing import estimate_cost

SUMMARY_MARKER = "<!-- pr-reviewer:summary -->"
MAX_COMMENT_CHARS = 65_000  # GitHub rejects comment bodies over 65,536 characters.
MAX_TITLE_CHARS = 200
MAX_IMPACT_CHARS = 2_000
MAX_FIX_CHARS = 4_000
MAX_OMITTED_ROWS = 100
_FINGERPRINT = re.compile(r"<!-- pr-reviewer:finding=([0-9a-f]{16}) -->")
_UNPROCESSABLE = 422
_NOT_OURS = (403, 404)

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


@dataclass(frozen=True)
class PublishOptions:
    max_findings: int = 10
    min_severity: Severity = "low"


@dataclass(frozen=True)
class Selection:
    kept: list[Finding]
    outside_diff: int = 0
    filtered: int = 0
    over_limit: int = 0


@dataclass(frozen=True)
class PublishResult:
    inline_posted: int
    already_posted: int


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


def fingerprint(finding: Finding) -> str:
    """Identify a finding across runs. Excludes the line, which moves between commits."""
    title = " ".join(finding.title.lower().split())
    return hashlib.sha256(f"{finding.file}|{finding.category}|{title}".encode()).hexdigest()[:16]


def select_findings(findings: list[Finding], bundle: DiffBundle, options: PublishOptions) -> Selection:
    """Keep findings that point at the diff, pass the filters and fit the limit."""
    lines = {file.path: set(file.commentable_lines) for file in bundle.files}
    in_diff = [f for f in findings if f.line in lines.get(f.file, set())]
    threshold = SEVERITY_RANK[options.min_severity]
    relevant = [f for f in in_diff if SEVERITY_RANK[f.severity] <= threshold and f.confidence != "low"]
    ordered = sorted(relevant, key=lambda f: SEVERITY_RANK[f.severity])
    return Selection(
        kept=ordered[: options.max_findings],
        outside_diff=len(findings) - len(in_diff),
        filtered=len(in_diff) - len(relevant),
        over_limit=max(len(ordered) - options.max_findings, 0),
    )


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


def format_summary(
    report: ReviewReport,
    bundle: DiffBundle,
    selection: Selection,
    *,
    inline_posted: int,
    already_posted: int,
    inline_rejected: bool,
) -> str:
    lines = [SUMMARY_MARKER, "## AI review: efficiency, optimality and cost", ""]

    if report.status == "failed":
        lines.append(f"⚠️ The review could not finish: `{_one_line(report.error) or 'unknown error'}`")
    elif not bundle.files:
        lines.append("Nothing was reviewed: no file in this pull request could be included.")
    elif not selection.kept:
        lines.append("✅ No efficiency, optimality or cost problems found in the reviewed code.")
    else:
        lines += _findings_table(selection.kept)
        lines.append("")
        if inline_rejected:
            lines.append("GitHub rejected the inline comments, so the findings are listed only here.")
        elif inline_posted:
            lines.append(f"{inline_posted} new inline comment(s) posted.")
        if already_posted:
            lines.append(f"{already_posted} finding(s) already posted in an earlier run.")

    hidden = selection.outside_diff + selection.filtered + selection.over_limit
    if hidden:
        lines += [
            "",
            f"{hidden} finding(s) not shown: {selection.outside_diff} outside the diff, "
            f"{selection.filtered} below the thresholds, {selection.over_limit} over the limit.",
        ]
    lines += _omitted_section(bundle)
    lines += ["", f"<sub>{_usage_line(report)} · commit {bundle.head[:7]} · comment `/review` to run again</sub>"]
    return _clip("\n".join(lines), MAX_COMMENT_CHARS)


def _is_bot(comment: dict[str, Any]) -> bool:
    return (comment.get("user") or {}).get("type") == "Bot"


def _upsert_summary(client: GitHubClient, repo: str, pr: int, body: str) -> None:
    comments = client.list_all(f"/repos/{repo}/issues/{pr}/comments")
    for comment in comments:
        if SUMMARY_MARKER in comment.get("body", "") and _is_bot(comment):
            try:
                client.request("PATCH", f"/repos/{repo}/issues/comments/{comment['id']}", json={"body": body})
            except GitHubError as error:
                if error.status not in _NOT_OURS:
                    raise
                continue  # Another app wrote this comment, so this token cannot edit it.
            return
    client.request("POST", f"/repos/{repo}/issues/{pr}/comments", json={"body": body})


def publish(
    client: GitHubClient,
    repo: str,
    pr: int,
    report: ReviewReport,
    bundle: DiffBundle,
    options: PublishOptions,
) -> PublishResult:
    """Post new inline comments and create or update the summary."""
    selection = select_findings(report.findings, bundle, options)
    existing = client.list_all(f"/repos/{repo}/pulls/{pr}/comments")
    posted = {match for c in existing if _is_bot(c) for match in _FINGERPRINT.findall(c.get("body", ""))}
    new = [f for f in selection.kept if fingerprint(f) not in posted]

    inline_rejected = False
    if new:
        payload = {
            "commit_id": bundle.head,
            "event": "COMMENT",
            "body": f"Found {len(new)} efficiency, optimality or cost issue(s).",
            "comments": [
                {"path": f.file, "line": f.line, "side": "RIGHT", "body": format_inline_comment(f)} for f in new
            ],
        }
        try:
            client.request("POST", f"/repos/{repo}/pulls/{pr}/reviews", json=payload)
        except GitHubError as error:
            if error.status != _UNPROCESSABLE:
                raise
            inline_rejected = True

    inline_posted = 0 if inline_rejected else len(new)
    already_posted = len(selection.kept) - len(new)
    summary = format_summary(
        report,
        bundle,
        selection,
        inline_posted=inline_posted,
        already_posted=already_posted,
        inline_rejected=inline_rejected,
    )
    _upsert_summary(client, repo, pr, summary)
    return PublishResult(inline_posted=inline_posted, already_posted=already_posted)
