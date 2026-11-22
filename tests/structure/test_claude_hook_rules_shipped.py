"""A Claude hook that reads rules/<file>.md must find that file inside its own plugin."""
import glob
import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RULE_REF = re.compile(r"""['"]rules['"]\s*,\s*['"]([\w.-]+\.md)['"]""")


def test_every_rule_read_by_a_claude_hook_is_shipped():
    missing = []
    for script in glob.glob(os.path.join(REPO_ROOT, "plugins", "claude", "*", "hooks", "*.js")):
        plugin_root = os.path.dirname(os.path.dirname(script))
        with open(script, encoding="utf-8") as fh:
            for name in RULE_REF.findall(fh.read()):
                if not os.path.isfile(os.path.join(plugin_root, "rules", name)):
                    missing.append(f"{os.path.relpath(script, REPO_ROOT)} -> rules/{name}")
    assert missing == []
