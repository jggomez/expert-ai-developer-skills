#!/usr/bin/env python3
"""Deterministic proof behind an E2E `PASSED` verdict.

Checks that an evidence directory (normally `docs/<feature-name>/evidence/`) holds real PNG
screenshots, written recently, covering every required viewport width. A text file renamed to
`.png`, a stale screenshot from an earlier run, or a missing viewport fails the check.

The orchestrator and the compliance-verifier run this before accepting `PASSED`; the tester
runs it before reporting. Standard library only.

Usage:
    python3 check_evidence.py docs/login/evidence
    python3 check_evidence.py docs/login/evidence --max-age-minutes 0   # skip the freshness check

Exit codes: 0 = PASS, 1 = FAIL (reasons printed), 2 = usage error.
"""
from __future__ import annotations

import argparse
import struct
import sys
import time
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MIN_PNG_BYTES = 100
DEFAULT_VIEWPORT_WIDTHS = (375, 768, 1280, 1920)
DEVICE_SCALE_FACTORS = (1, 2, 3)


def png_width(path: Path) -> int | None:
    """Returns the pixel width from the IHDR chunk, or None when the file is not a real PNG."""
    try:
        if path.stat().st_size < MIN_PNG_BYTES:
            return None
        with path.open("rb") as handle:
            header = handle.read(24)
    except OSError:
        return None
    if len(header) < 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        return None
    width = struct.unpack(">I", header[16:20])[0]
    return width or None


def covered_viewports(widths: list[int], viewports: tuple[int, ...]) -> set[int]:
    """Viewport widths matched by a screenshot, allowing retina/HiDPI scale factors."""
    return {vp for vp in viewports for w in widths if any(w == vp * s for s in DEVICE_SCALE_FACTORS)}


def check(evidence_dir: Path, viewports: tuple[int, ...], max_age_minutes: float) -> list[str]:
    """Returns the list of problems; an empty list means the evidence is valid."""
    if not evidence_dir.is_dir():
        return [f"evidence directory {evidence_dir} does not exist"]

    pngs = sorted(p for p in evidence_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".png")
    if not pngs:
        return [f"no .png screenshots in {evidence_dir}"]

    problems: list[str] = []
    widths: list[int] = []
    oldest_allowed = time.time() - max_age_minutes * 60 if max_age_minutes > 0 else None
    for png in pngs:
        width = png_width(png)
        if width is None:
            problems.append(f"{png} is not a real PNG (bad signature or under {MIN_PNG_BYTES} bytes)")
            continue
        if oldest_allowed is not None and png.stat().st_mtime < oldest_allowed:
            problems.append(f"{png} is older than {max_age_minutes:g} minutes (stale run?)")
            continue
        widths.append(width)

    missing = [vp for vp in viewports if vp not in covered_viewports(widths, viewports)]
    if missing:
        problems.append("no valid screenshot for viewport width(s): " + ", ".join(map(str, missing)))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("evidence_dir", type=Path, help="e.g. docs/<feature-name>/evidence")
    parser.add_argument("--viewports", default=",".join(map(str, DEFAULT_VIEWPORT_WIDTHS)),
                        help="comma-separated viewport widths (default: %(default)s)")
    parser.add_argument("--max-age-minutes", type=float, default=120,
                        help="reject screenshots older than this; 0 disables (default: %(default)s)")
    args = parser.parse_args(argv)

    try:
        viewports = tuple(int(v) for v in args.viewports.split(",") if v.strip())
    except ValueError:
        parser.error(f"--viewports must be comma-separated integers, got {args.viewports!r}")
    if not viewports or any(v <= 0 for v in viewports):
        parser.error("--viewports needs at least one positive width")

    problems = check(args.evidence_dir, viewports, args.max_age_minutes)
    if problems:
        print(f"FAIL: E2E evidence in {args.evidence_dir} does not back a PASSED verdict")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"PASS: real, recent screenshots for viewports {', '.join(map(str, viewports))} in {args.evidence_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
