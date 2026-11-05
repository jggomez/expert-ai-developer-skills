"""Which findings deserve to be published."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pr_reviewer.domain.models import SEVERITY_RANK, DiffBundle, Finding, Severity

DEFAULT_MAX_FINDINGS = 10


@dataclass(frozen=True)
class PublishOptions:
    max_findings: int = DEFAULT_MAX_FINDINGS
    min_severity: Severity = "low"


@dataclass(frozen=True)
class Selection:
    kept: list[Finding]
    outside_diff: int = 0
    filtered: int = 0
    over_limit: int = 0


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
