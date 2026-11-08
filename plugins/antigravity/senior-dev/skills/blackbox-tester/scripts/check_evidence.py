#!/usr/bin/env python3
"""Deterministic proof behind an E2E `PASSED` verdict.

Checks that an evidence directory (normally `docs/<feature-name>/evidence/`) holds real PNG
screenshots, written recently, covering every required viewport width. A text file renamed to
`.png`, a stale screenshot from an earlier run, or a missing viewport fails the check.

It also needs proof that the app used real data: `run-*.json` manifests written by the
`e2e_recorder` helpers must show a data request answered by a server, a value compared with its
source, and, after any write, a value that survived a reload. Network stubs in the E2E tests fail.
A screen with no data source needs `data-source: none` in the feature plan (`docs/<feature-name>/PLAN.md`,
or a legacy root `PLAN.md`) or in `docs/*/spec.md`, and a demo needs `demo-data: approved` there.

The orchestrator and the compliance-verifier run this before accepting `PASSED`; the tester
runs it before reporting. Standard library only.

Usage:
    python3 check_evidence.py docs/login/evidence
    python3 check_evidence.py docs/login/evidence --max-age-minutes 0   # skip the freshness check
    python3 check_evidence.py --latest --root .                         # newest docs/*/evidence

Exit codes: 0 = PASS, 1 = FAIL (reasons printed), 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import time
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MIN_PNG_BYTES = 100
DEFAULT_VIEWPORT_WIDTHS = (375, 768, 1280, 1920)
DEVICE_SCALE_FACTORS = (1, 2, 3)
DEFAULT_MAX_AGE_MINUTES = 120
DATA_RESOURCE_TYPES = {"fetch", "xhr"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
STATIC_REQUEST = re.compile(
    r"/assets/|FontManifest|\.(?:js|mjs|css|wasm|woff2?|ttf|otf|png|jpe?g|gif|webp|svg|ico|map)(?:[?#]|$)",
    re.IGNORECASE,
)
NETWORK_STUB = re.compile(r"\.route\(|\.fulfill\(|route_from_har|routeFromHAR|setupServer\(|setupWorker\(")
E2E_SUFFIXES = {".ts", ".tsx", ".js", ".mjs", ".cjs", ".py"}


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


def project_root(evidence_dir: Path) -> Path:
    """The repository holding the evidence, or the evidence's parent outside a repository."""
    resolved = evidence_dir.resolve()
    for parent in resolved.parents:
        if (parent / ".git").exists():
            return parent
    return resolved.parent


def plan_files(root: Path) -> list[Path]:
    """Feature plans and specs (`docs/<feature-name>/PLAN.md`, `docs/*/spec.md`) plus a legacy root PLAN.md."""
    return [*sorted(root.glob("docs/*/PLAN.md")), *sorted(root.glob("docs/*/spec.md")), root / "PLAN.md"]


def declared_in_plan(root: Path, text: str) -> bool:
    for plan in plan_files(root):
        try:
            if text in plan.read_text(encoding="utf-8"):
                return True
        except (OSError, UnicodeDecodeError):
            continue
    return False


def stubbed_tests(root: Path) -> list[str]:
    e2e = root / "tests" / "e2e"
    if not e2e.is_dir():
        return []
    found: list[str] = []
    for path in sorted(p for p in e2e.rglob("*") if p.is_file() and p.suffix.lower() in E2E_SUFFIXES):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if NETWORK_STUB.search(text):
            found.append(f"{path} stubs the network: test against the real backend")
    return found


def is_real_data_request(request: dict) -> bool:
    status = request.get("status")
    return (
        request.get("resourceType") in DATA_RESOURCE_TYPES
        and request.get("remote") is not False
        and isinstance(status, int) and 200 <= status < 400
        and not STATIC_REQUEST.search(str(request.get("url", "")))
    )


def check_manifests(evidence_dir: Path, oldest_allowed: float | None) -> list[str]:
    """Merges the `run-*.json` manifests and proves the run used real data."""
    paths = sorted(evidence_dir.rglob("run-*.json"))
    if not paths:
        return [f"no run-*.json manifest in {evidence_dir}: record the run with the e2e_recorder helper"]

    problems: list[str] = []
    pages: list[str] = []
    requests: list[dict] = []
    kinds: set[str] = set()
    no_data_source = False
    demo = False
    for path in paths:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("expected a JSON object")
            pages += list(manifest.get("pages") or [])
            requests += [r for r in manifest.get("requests") or [] if isinstance(r, dict)]
            kinds |= {str(c.get("kind")) for c in manifest.get("dataChecks") or [] if isinstance(c, dict)}
        except (OSError, UnicodeDecodeError, ValueError, AttributeError) as err:
            problems.append(f"{path} is not a valid manifest: {err}")
            continue
        no_data_source = no_data_source or bool(manifest.get("noDataSource"))
        demo = demo or manifest.get("demo") is True
        if oldest_allowed is not None and path.stat().st_mtime < oldest_allowed:
            problems.append(f"{path} is too old or was written before the last change (stale run?)")
    if not pages:
        problems.append("the manifests list no visited page")

    root = project_root(evidence_dir)
    if demo:
        if not declared_in_plan(root, "demo-data: approved"):
            problems.append("the run is a demo, but docs/<feature>/PLAN.md or docs/*/spec.md has no `demo-data: approved`")
        return problems
    problems += stubbed_tests(root)
    if no_data_source:
        if not declared_in_plan(root, "data-source: none"):
            problems.append("no data source used, but docs/<feature>/PLAN.md or docs/*/spec.md has no `data-source: none`")
        return problems

    data_requests = [r for r in requests if is_real_data_request(r)]
    if not data_requests:
        problems.append("no real data request answered by a server was recorded")
    if "source-on-screen" not in kinds:
        problems.append("no `source-on-screen` check: compare a value from the source with the screen")
    if any(str(r.get("method")).upper() in WRITE_METHODS for r in data_requests):
        if "persisted-after-reload" not in kinds:
            problems.append("the run wrote data but has no `persisted-after-reload` check")
    return problems


def latest_evidence_dir(root: Path) -> Path | None:
    """The `docs/*/evidence` directory with the newest screenshot or manifest."""
    newest: tuple[float, Path] | None = None
    for directory in root.glob("docs/*/evidence"):
        times = [p.stat().st_mtime for p in directory.rglob("*") if p.is_file()]
        if times and (newest is None or max(times) > newest[0]):
            newest = (max(times), directory)
    return newest[1] if newest else None


def check(evidence_dir: Path, viewports: tuple[int, ...], max_age_minutes: float, min_mtime: float = 0) -> list[str]:
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
        if png.stat().st_mtime < min_mtime:
            problems.append(f"{png} was taken before the last change: run the app again")
            continue
        widths.append(width)

    missing = [vp for vp in viewports if vp not in covered_viewports(widths, viewports)]
    if missing:
        problems.append("no valid screenshot for viewport width(s): " + ", ".join(map(str, missing)))
    oldest_manifest = max(oldest_allowed or 0, min_mtime) or None
    return problems + check_manifests(evidence_dir, oldest_manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("evidence_dir", type=Path, nargs="?", help="e.g. docs/<feature-name>/evidence")
    parser.add_argument("--latest", action="store_true", help="check the newest docs/*/evidence under --root")
    parser.add_argument("--root", type=Path, default=Path("."), help="project root for --latest")
    parser.add_argument("--min-mtime", type=float, default=0,
                        help="reject evidence older than this Unix time, such as the last UI change")
    parser.add_argument("--viewports", default=",".join(map(str, DEFAULT_VIEWPORT_WIDTHS)),
                        help="comma-separated viewport widths (default: %(default)s)")
    parser.add_argument("--max-age-minutes", type=float, default=DEFAULT_MAX_AGE_MINUTES,
                        help="reject screenshots older than this; 0 disables (default: %(default)s)")
    args = parser.parse_args(argv)

    try:
        viewports = tuple(int(v) for v in args.viewports.split(",") if v.strip())
    except ValueError:
        parser.error(f"--viewports must be comma-separated integers, got {args.viewports!r}")
    if not viewports or any(v <= 0 for v in viewports):
        parser.error("--viewports needs at least one positive width")

    evidence_dir = args.evidence_dir
    if args.latest:
        evidence_dir = latest_evidence_dir(args.root)
        if evidence_dir is None:
            print(f"FAIL: no evidence in {args.root}/docs/*/evidence: the UI was not run")
            return 1
    elif evidence_dir is None:
        parser.error("give an evidence directory or --latest")

    problems = check(evidence_dir, viewports, args.max_age_minutes, args.min_mtime)
    if problems:
        print(f"FAIL: E2E evidence in {evidence_dir} does not back a PASSED verdict")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"PASS: real, recent screenshots for viewports {', '.join(map(str, viewports))} and real data in {evidence_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
