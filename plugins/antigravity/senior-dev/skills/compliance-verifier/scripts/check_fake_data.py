#!/usr/bin/env python3
"""Rejects fake data added to production UI code.

A green test suite says nothing about a screen that paints invented data. This check reads the
lines a change adds and fails on mock data, placeholder people, fake-data libraries and literals
returned after a simulated delay. Test code, fixtures and seeds are ignored, and so are folders that
never hold the app's UI: agent plugins and rules (`.claude/`, `.agents/`), docs, virtualenvs and
vendored dependencies (their own comments legitimately talk about "mock" and "fake" data).

It is a heuristic: it can flag a false positive, and it cannot see invented data with believable
names. Running the real app (`check_evidence.py`) is what proves the data is real.

A demo the user approved is allowed when the file carries `demo-data: approved` and a line of the
feature plan (`docs/<feature-name>/PLAN.md`, or a legacy root `PLAN.md`) or `docs/*/spec.md` holds
both that text and the file path.

Usage:
    python3 check_fake_data.py --repo .                 # uncommitted and untracked changes
    python3 check_fake_data.py --repo . --base main     # everything since main

Exit codes: 0 = PASS, 1 = FAIL (findings printed), 2 = usage error.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

APPROVAL = "demo-data: approved"
SCANNED_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue", ".svelte", ".html", ".dart"}
IGNORED_PATH = re.compile(
    r"(^|/)(tests?|__tests__|__mocks__|e2e|integration_test|test_driver|mocks?|fixtures?|stories|cypress|"
    r"playwright|seeds?|migrations?|node_modules|build|dist"
    r"|\.claude|\.agents|\.gemini|\.cursor|\.venv|venv|docs?|context|vendor|coverage|\.dart_tool|\.next)(/|$)"
    r"|\.(test|spec|stories)\.|_test\.dart$|\.config\.[cm]?[jt]s$"
)
INPUT_HINT = re.compile(r"placeholder|hintText|helperText|labelText", re.IGNORECASE)
PATTERNS = (
    ("mock or fake data", re.compile(
        r"\b(?:[Mm]ock|[Ff]ake|[Dd]ummy|MOCK|FAKE|DUMMY)(?:[A-Z_][A-Za-z0-9_]*|s)?\b"
        r"|\b\w+(?:Mock|Fake|Dummy)[A-Z]\w*|\b\w+_(?:MOCK|FAKE|DUMMY)\w*"
    )),
    ("sample data", re.compile(
        r"\b[sS]ample(?:Data|Users?|Items?|Products?|Orders?|Records?|Rows?|Results?|List)\b|\bSAMPLE_[A-Z_]+\b"
    )),
    ("placeholder text", re.compile(r"lorem ipsum", re.IGNORECASE)),
    ("placeholder person", re.compile(r"\b(?:John|Jane) Doe\b")),
    ("fake-data library", re.compile(r"@faker-js|\bfaker\.|package:faker/|from ['\"]msw|\bsetupWorker\(")),
    ("random value", re.compile(r"\bMath\.random\(\)|\bRandom\(\)\.next")),
)
EXAMPLE_ADDRESS = re.compile(r"[\w.+-]*@?example\.(?:com|org|net)")
DELAY = re.compile(r"Future\.delayed\(|setTimeout\(|\bsleep\(")
LITERAL_RETURN = re.compile(r"\breturn\s+(?:const\s+)?(?:<[^>]+>\s*)?[\[{]|\bresolve\(\s*[\[{]")
DELAY_WINDOW = 6


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def added_lines(repo: Path, base: str) -> dict[str, list[tuple[int, str]]]:
    """Maps each changed or untracked file to its added (line number, text) pairs."""
    added: dict[str, list[tuple[int, str]]] = {}
    current: list[tuple[int, str]] | None = None
    number = 0
    for line in git(repo, "diff", "--unified=0", "--no-color", "--no-ext-diff", base, "--").splitlines():
        if line.startswith("+++ "):
            current = None if line == "+++ /dev/null" else added.setdefault(line[6:], [])
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            number = int(match.group(1)) if match else 0
        elif line.startswith("+") and current is not None:
            current.append((number, line[1:]))
            number += 1
    for rel in git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
        try:
            text = (repo / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        added[rel] = list(enumerate(text.splitlines(), start=1))
    return added


def is_scanned(rel: str) -> bool:
    return Path(rel).suffix.lower() in SCANNED_SUFFIXES and not IGNORED_PATH.search(rel)


def approved_demo(repo: Path, rel: str) -> bool:
    """A demo counts only when the file is marked and the plan or spec names that file as approved."""
    try:
        if APPROVAL not in (repo / rel).read_text(encoding="utf-8"):
            return False
    except (OSError, UnicodeDecodeError):
        return False
    for plan in [*sorted(repo.glob("docs/*/PLAN.md")), *sorted(repo.glob("docs/*/spec.md")), repo / "PLAN.md"]:
        try:
            lines = plan.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        if any(APPROVAL in line and rel in line for line in lines):
            return True
    return False


def findings_for(rel: str, lines: list[tuple[int, str]]) -> list[str]:
    findings: list[str] = []
    for index, (number, text) in enumerate(lines):
        reason = next((label for label, pattern in PATTERNS if pattern.search(text)), None)
        if reason is None and EXAMPLE_ADDRESS.search(text) and not INPUT_HINT.search(text):
            reason = "placeholder address"
        if reason is None and DELAY.search(text):
            window = lines[index:index + DELAY_WINDOW]
            if any(LITERAL_RETURN.search(later) for _, later in window):
                reason = "literal data returned after a simulated delay"
        if reason:
            findings.append(f"{rel}:{number} [{reason}] {text.strip()[:100]}")
    return findings


def check(repo: Path, base: str) -> list[str]:
    findings: list[str] = []
    for rel, lines in sorted(added_lines(repo, base).items()):
        if is_scanned(rel) and not approved_demo(repo, rel):
            findings.extend(findings_for(rel, lines))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", type=Path, default=Path("."), help="repository root (default: current directory)")
    parser.add_argument("--base", default="HEAD", help="commit or branch to compare with (default: %(default)s)")
    args = parser.parse_args(argv)

    try:
        findings = check(args.repo.resolve(), args.base)
    except (RuntimeError, OSError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    if findings:
        print("FAIL: fake data in production code. Connect the real source, or ask the user to approve a demo")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print(f"PASS: no fake data in lines added since {args.base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
