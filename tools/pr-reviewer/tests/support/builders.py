"""Test data shared across layers."""

from pr_reviewer.domain.models import (
    DiffBundle,
    FileDiff,
    Finding,
    OmittedFile,
    ReviewReport,
    ReviewUsage,
)

HEAD = "b" * 40


def finding(**overrides) -> Finding:
    values = {
        "file": "app.py",
        "line": 10,
        "severity": "high",
        "category": "cost",
        "confidence": "high",
        "title": "Query inside a loop",
        "impact": "One query per order",
        "proposed_fix": "Use a join",
    }
    return Finding(**{**values, **overrides})


def bundle(omitted: list[OmittedFile] | None = None) -> DiffBundle:
    return DiffBundle(
        base="a" * 40,
        head=HEAD,
        files=[FileDiff(path="app.py", commentable_lines=[10, 11, 12])],
        omitted=omitted or [],
    )


def report(findings: list[Finding] | None = None) -> ReviewReport:
    return ReviewReport(
        status="ok",
        provider="antigravity",
        model="gemini-3.8-flash",
        findings=findings if findings is not None else [finding()],
        usage=ReviewUsage(input_tokens=40_000, output_tokens=4_000),
    )
