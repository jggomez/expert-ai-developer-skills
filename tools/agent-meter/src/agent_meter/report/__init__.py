"""Static, self-contained HTML report (Option A, contracts.md §3.10, ADR §3.12)."""

from __future__ import annotations

from agent_meter.report.build import build_report, write_report
from agent_meter.report.data import ViewSource
from agent_meter.report.options import ReportOptions

__all__ = ["ReportOptions", "ViewSource", "build_report", "write_report"]
