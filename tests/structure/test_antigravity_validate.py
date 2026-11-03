"""Every Antigravity plugin must load cleanly in the real Antigravity plugin loader.

`agy plugin validate` "checks a plugin the way the plugin loader reads it". A hooks.json the
loader cannot parse is skipped whole, which silently disables every gate of the plugin, so
the loader's verdict is the source of truth here. Skipped when the agy CLI is not installed.
"""
import glob
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AGY_PLUGINS = sorted(d for d in glob.glob(os.path.join(ROOT, "plugins", "antigravity", "*")) if os.path.isdir(d))

needs_agy = pytest.mark.skipif(shutil.which("agy") is None, reason="agy CLI not installed")


def _validate(plugin_dir):
    result = subprocess.run(["agy", "plugin", "validate", "--json", plugin_dir],
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


@needs_agy
@pytest.mark.parametrize("plugin_dir", AGY_PLUGINS, ids=os.path.basename)
def test_antigravity_loader_accepts_the_plugin(plugin_dir):
    # Arrange / Act
    report = _validate(plugin_dir)
    problems = [f"{f['file']}: {f['message']}" for f in report["findings"]
                if f["severity"] in ("error", "warning")]
    # Assert
    assert not problems, "\n".join(problems)
    if os.path.isfile(os.path.join(plugin_dir, "hooks.json")):
        assert report["components"]["hooks"] > 0, "hooks.json present but the loader registered no hooks"


@pytest.mark.parametrize("plugin_dir", AGY_PLUGINS, ids=os.path.basename)
def test_hooks_json_only_holds_named_hook_groups(plugin_dir):
    """Antigravity reads every top-level key of hooks.json as a named hook group."""
    # Arrange
    path = os.path.join(plugin_dir, "hooks.json")
    if not os.path.isfile(path):
        pytest.skip("no hooks.json")
    with open(path, encoding="utf-8") as f:
        hooks = json.load(f)
    # Act
    bad = [key for key, value in hooks.items() if not isinstance(value, dict) or "enabled" not in value]
    claude_paths = "${CLAUDE_PLUGIN_ROOT}" in json.dumps(hooks)
    # Assert
    assert not bad, f"top-level keys that are not named hook groups: {bad}"
    assert not claude_paths, "Claude Code hook paths do not resolve in Antigravity (hooks run from the plugin root)"


@pytest.mark.parametrize("plugin_dir", AGY_PLUGINS, ids=os.path.basename)
def test_no_claude_mcp_file_in_antigravity_plugins(plugin_dir):
    # Arrange / Act / Assert: Antigravity never loads .mcp.json; servers belong in mcp_config.json
    assert not os.path.exists(os.path.join(plugin_dir, ".mcp.json"))
