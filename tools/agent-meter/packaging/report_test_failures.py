"""Turn a pytest JUnit file into GitHub annotations, which anyone can read without signing in."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Final

MAX_ANNOTATIONS: Final = 10  # GitHub keeps ten errors per step
MAX_MESSAGE: Final = 300


def _escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def failures(path: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for case in ET.parse(path).getroot().iter("testcase"):  # our own test output
        for problem in (*case.findall("failure"), *case.findall("error")):
            name = f"{case.get('classname', '')}.{case.get('name', '')}"
            found.append((name, (problem.get("message") or problem.text or "").strip()))
    return found


def annotations(found: list[tuple[str, str]]) -> list[str]:
    """Most failures on one system share a cause, so the most repeated messages come first."""
    grouped = Counter(message[:MAX_MESSAGE] for _name, message in found)
    lines = []
    for message, count in grouped.most_common(MAX_ANNOTATIONS):
        example = next(name for name, full in found if full[:MAX_MESSAGE] == message)
        lines.append(f"::error title={count} failed, e.g. {_escape(example)}::{_escape(message)}")
    return lines


def main() -> int:
    path = Path(sys.argv[1])
    if not path.exists():
        print("::error title=No test results::pytest did not write its results", flush=True)
        return 0
    for line in annotations(failures(path)):
        print(line, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
