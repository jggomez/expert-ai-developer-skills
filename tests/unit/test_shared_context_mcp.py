"""Unit tests for the shared-context MCP server's tool layer.

The `mcp` package is not required: the tool implementations are plain functions
and only `_serve()` needs the SDK. These tests import the module directly and
exercise the functions against a tmp context directory.
"""
import importlib.util
import os
import sys

import pytest

MCP_PATH = os.path.abspath("plugins/shared-context/mcp/mcp_server.py")


@pytest.fixture(scope="module")
def mcp_mod():
    spec = importlib.util.spec_from_file_location("shared_context_mcp_server", MCP_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_imports_without_mcp_package(mcp_mod):
    for fn in ("tool_context_list", "tool_context_snapshot", "tool_context_read",
               "tool_context_write", "tool_context_pack", "tool_context_unpack",
               "tool_context_rollup", "tool_context_search"):
        assert callable(getattr(mcp_mod, fn))


def test_list_snapshot_read_cycle(mcp_mod, tmp_path):
    ctx = str(tmp_path / "context")
    assert mcp_mod.tool_context_list(context_dir=ctx)["exists"] is False

    snap = mcp_mod.tool_context_snapshot(context_dir=ctx, session="s1",
                                         task="mcp test", agent="claude-sonnet-5",
                                         no_git=True)
    assert snap["created"] is True and snap["session"] == "s1"

    listing = mcp_mod.tool_context_list(context_dir=ctx)
    assert listing["exists"] is True and listing["count"] == 1

    read = mcp_mod.tool_context_read("architecture.md", context_dir=ctx)
    assert "Architecture" in read["content"]


def test_write_is_guarded_and_redacted(mcp_mod, tmp_path):
    ctx = str(tmp_path / "context")
    mcp_mod.tool_context_snapshot(context_dir=ctx, session="s1", no_git=True)

    # path traversal is refused
    assert "error" in mcp_mod.tool_context_write("../escape.md", "x", context_dir=ctx)
    # generated files are not agent-writable
    assert "error" in mcp_mod.tool_context_write("2000-01-01/s1/manifest.json", "{}", context_dir=ctx)

    res = mcp_mod.tool_context_write(
        "2000-01-01/s1/decisions.md",
        '# Decisions\n\n- **x** token="AKIAIOSFODNN7EXAMPLE"\n',
        context_dir=ctx,
    )
    assert res["redactions"] == ["aws-akid"]
    back = mcp_mod.tool_context_read("2000-01-01/s1/decisions.md", context_dir=ctx)
    assert "AKIAIOSFODNN7EXAMPLE" not in back["content"] and "REDACTED" in back["content"]


def test_pack_rollup_search(mcp_mod, tmp_path):
    ctx = str(tmp_path / "context")
    mcp_mod.tool_context_snapshot(context_dir=ctx, session="s1", no_git=True)
    mcp_mod.tool_context_write("2000-01-01/s1/decisions.md",
                               "# Decisions\n\n- **Commit context** — shared via git\n",
                               context_dir=ctx)

    roll = mcp_mod.tool_context_rollup(context_dir=ctx)
    assert any("Commit context" in d for d in roll["decisionsAdded"])

    hits = mcp_mod.tool_context_search("Commit context", context_dir=ctx)
    assert hits["matches"] and hits["matches"][0]["line"] >= 1

    packed = mcp_mod.tool_context_pack(context_dir=ctx, session="s1")
    assert packed["results"][0]["action"] == "pack"
    unpacked = mcp_mod.tool_context_unpack(context_dir=ctx, session="s1")
    assert unpacked["results"][0]["action"] == "unpack"
