"""Data exchanged between the diff, review and publish steps."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["critical", "high", "medium", "low"]
Category = Literal["security", "performance", "scalability", "design", "best_practice", "cost"]
Confidence = Literal["high", "medium", "low"]
OmitReason = Literal["excluded", "deleted", "binary", "size-limit"]

SEVERITY_RANK: dict[str, int] = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class Finding(BaseModel):
    """One actionable problem in the changed code."""

    file: str = Field(description="Path relative to the repository root, exactly as shown in the diff.")
    line: int = Field(ge=1, description="Line number in the new version of the file.")
    severity: Severity
    category: Category
    confidence: Confidence
    title: str = Field(description="One short sentence naming the problem.")
    impact: str = Field(description="What gets slower, bigger or more expensive, and at what scale.")
    proposed_fix: str = Field(default="", description="Concrete change to make, as code when possible.")


class ReviewResult(BaseModel):
    """Structured answer every provider must return."""

    findings: list[Finding] = Field(default_factory=list)


class ReviewUsage(BaseModel):
    """Tokens consumed by one review."""

    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reported_cost_usd: float | None = None


class FileDiff(BaseModel):
    """One changed file."""

    path: str
    patch: str = ""
    commentable_lines: list[int] = Field(default_factory=list)
    deleted: bool = False
    binary: bool = False


class OmittedFile(BaseModel):
    """A changed file the agent did not review, and why."""

    path: str
    reason: OmitReason


class DiffBundle(BaseModel):
    """Output of the diff step."""

    model_config = ConfigDict(frozen=True)

    base: str
    head: str
    files: list[FileDiff] = Field(default_factory=list)
    omitted: list[OmittedFile] = Field(default_factory=list)


class ReviewReport(BaseModel):
    """Output of the review step. A failed review is reported, never raised to the job."""

    status: Literal["ok", "partial", "failed"]
    provider: str
    model: str = ""
    findings: list[Finding] = Field(default_factory=list)
    usage: ReviewUsage = Field(default_factory=ReviewUsage)
    error: str = ""
    unreviewed: list[str] = Field(default_factory=list, description="Files of the groups that failed.")
