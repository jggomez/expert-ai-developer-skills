"""Agent-meter found 92% of test commands piped into a filter, which hides their exit code."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS = sorted(
    path
    for host in ("antigravity", "claude")
    for name in ("code-implementer", "flutter-implementer", "qa-tester")
    for path in (ROOT / "plugins" / host).glob(f"*/agents/{name}.md")
)
GUIDES = [
    ROOT / "rules" / "testing-after-changes.md",
    ROOT / "skills" / "code-implementer" / "SKILL.md",
    ROOT / "skills" / "flutter-test-strategy" / "SKILL.md",
    ROOT / "skills" / "qa-tester" / "SKILL.md",
]


def test_every_worker_that_runs_tests_is_covered() -> None:
    assert len(AGENTS) == 9  # Claude plugins reuse the senior-dev workers


@pytest.mark.parametrize("path", AGENTS + GUIDES, ids=lambda p: str(p.relative_to(ROOT)))
def test_test_commands_keep_their_exit_code_and_full_log(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    assert 'code=$?' in text
    assert 'tail -n 40 "$log"' in text


def test_token_rule_no_longer_suggests_piping_commands_blindly() -> None:
    text = (ROOT / "rules" / "context-and-token-optimization.md").read_text(encoding="utf-8")

    assert "`| tail`" not in text
    assert "exit code" in text
