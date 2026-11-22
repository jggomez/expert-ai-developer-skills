"""Claude Code copies must not tell Antigravity users to call Claude Code tools.

The sync scripts translate Antigravity tool names (run_command, write_to_file...) into Claude Code ones. A line
labelled for Antigravity that ends up naming `Bash` or `Write` is wrong for both hosts, so it must be dropped or
rewritten by the translator (scripts/claude_sync_config.py).
"""
import os
import re
import subprocess

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLAUDE_TOOLS = re.compile(r"`(?:Bash|Write|Edit|Read|Agent|Grep|Glob|AskUserQuestion|SendMessage)`")


def _claude_text_files():
    out = subprocess.run(["git", "ls-files", "plugins/claude"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return [p for p in out.stdout.splitlines() if p.endswith((".md", ".py", ".js"))]


def test_no_antigravity_line_names_claude_tools():
    offenders = []
    for rel in _claude_text_files():
        with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                if "Antigravity" in line and "Claude Code" not in line and CLAUDE_TOOLS.search(line):
                    offenders.append(f"{rel}:{number}: {line.strip()[:120]}")
    assert offenders == [], "\n".join(offenders)


@pytest.mark.parametrize(
    "source, expected",
    [
        (
            "- **Tool Mapping**:\n  - **Google Antigravity**: Use `run_command` to run tests.\n  - **Claude Code**: Use `Bash` to run tests.\n",
            "- **Tool Mapping**:\n  - **Claude Code**: Use `Bash` to run tests.\n",
        ),
        (
            "Run `bq` via shell (`Bash` in Claude Code; `run_command` in Antigravity) now.",
            "Run `bq` via shell (`Bash` in Claude Code) now.",
        ),
        (
            "invoked by Claude Code\n(`Bash`) or Antigravity CLI (`run_command`). Every",
            "invoked by Claude Code\n(`Bash`) or Antigravity CLI. Every",
        ),
        (
            "Antigravity CLI (`~/.gemini/antigravity-cli/`), Antigravity IDE",
            "Antigravity CLI (`~/.gemini/antigravity-cli/`), Antigravity IDE",
        ),
    ],
)
def test_translator_drops_antigravity_tool_advice(source, expected):
    import sys

    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    from claude_sync_config import sanitize_claude_content

    assert sanitize_claude_content(source) == expected
