"""Report entry points called by ``cli.py report`` (contracts.md §3.10)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from agent_meter.report.data import ViewSource, load_report_data
from agent_meter.report.options import ReportOptions
from agent_meter.report.render import render_report

__all__ = ["ReportOptions", "build_report", "write_report"]


def build_report(store: ViewSource, options: ReportOptions) -> str:
    """Build the full self-contained HTML report from the §6 views only.

    ``store`` is a ``store.Store`` (anything with its ``query`` method). An empty store
    or an empty filter scope yields a valid page with a friendly empty state (SM-03).
    """
    return render_report(load_report_data(store, options))


def write_report(html: str, out: Path) -> Path:
    """Atomically write ``html`` to ``out`` (mode 0600) and return ``out``.

    The page is written to a temporary file in the target directory, flushed to disk
    and moved into place with ``os.replace``; on failure the temporary file is removed
    and the previous report, if any, is left untouched.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{out.name}.", suffix=".tmp", dir=out.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(html)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, out)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return out
