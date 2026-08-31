"""End-to-end proof that the shared-context plugin lets one agent hand off to
another across hosts.

Scenario: Agent A works on "Antigravity", captures a session, marks it done,
rolls the decisions up and compresses. Agent B on "Claude Code" then discovers
the store, checks provenance, restores the compressed detail, and reads the
rolled-up architecture log. Also covers lossless compression, retention
archiving, and a real MCP stdio round-trip against the bundled server.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.abspath(".")
CAP = os.path.join(ROOT, "skills/context-capture/scripts")
RES = os.path.join(ROOT, "skills/context-restore/scripts")
SNAP = os.path.join(CAP, "context_snapshot.py")
PACK = os.path.join(CAP, "context_pack.py")
ROLL = os.path.join(CAP, "context_rollup.py")
LIST = os.path.join(RES, "context_list.py")
MCP_SERVER = os.path.join(ROOT, "plugins/shared-context/mcp/mcp_server.py")
MCP_LAUNCHER = os.path.join(ROOT, "plugins/shared-context/mcp/run-server.sh")
HOST_VARS = ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "CLAUDECODE", "ANTIGRAVITY", "AGY_PLUGIN_ROOT")


def _py(script, *args, env=None, cwd=None):
    e = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
    if env:
        e.update(env)
    r = subprocess.run([sys.executable, script, *args],
                       capture_output=True, text=True, env=e, cwd=cwd)
    assert r.returncode == 0, f"{os.path.basename(script)} {args}\nSTDOUT{r.stdout}\nSTDERR{r.stderr}"
    return r.stdout


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.co"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "app.py").write_text("def f():\n    return 1\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    return tmp_path


def test_two_agent_cross_host_handoff(repo):
    ctx = str(repo / "context")

    # --- Agent A on Antigravity: work + capture ---------------------------
    _py(SNAP, "--context-dir", ctx, "--host", "antigravity", "--agent", "gemini-pro",
        "--model", "pro", "--task", "add rate limiter", "--session", "A1",
        env={"ANTIGRAVITY": "1"}, cwd=str(repo))
    sdir = next((repo / "context").glob("*/A1"))
    (sdir / "summary.md").write_text(
        "# Session summary\n\nAdded a token-bucket rate limiter to the gateway. "
        "Works; still needs a load test.\n")
    (sdir / "decisions.md").write_text(
        "# Decisions\n\n- **Token bucket over sliding window** - simpler; "
        "sliding window rejected as overkill.\n")
    _py(SNAP, "--context-dir", ctx, "--session", "A1", "--status", "done", cwd=str(repo))
    _py(ROLL, "--context-dir", ctx, cwd=str(repo))
    _py(PACK, "--context-dir", ctx, "--auto", "--keep-uncompressed", "0", cwd=str(repo))

    assert (sdir / "detail.tar.xz").exists()
    assert (sdir / "summary.md").exists() and (sdir / "decisions.md").exists()
    assert not (sdir / "flows.md").exists()  # detail is packed away

    # --- Agent B on Claude Code: discover + restore ----------------------
    listing = json.loads(_py(LIST, "--context-dir", ctx, "--json",
                             env={"CLAUDE_PLUGIN_ROOT": "x"}, cwd=str(repo)))
    assert listing["exists"] is True and listing["count"] == 1
    session = listing["sessions"][0]
    # provenance survived the cross-host "--status done" update by Agent B's host
    assert session["host"] == "antigravity"
    assert session["agent"] == "gemini-pro"
    assert session["status"] == "done"
    assert session["task"] == "add rate limiter"

    _py(PACK, "--context-dir", ctx, "--unpack", "A1", cwd=str(repo))
    assert (sdir / "flows.md").exists()
    assert "Token bucket" in (sdir / "decisions.md").read_text()

    arch = (repo / "context" / "architecture.md").read_text()
    assert "**Token bucket over sliding window**" in arch  # bold survives the rollup
    index = (repo / "context" / "INDEX.md").read_text()
    assert "A1" in index and "antigravity" in index


def test_compression_round_trip_is_lossless(repo):
    ctx = str(repo / "context")
    _py(SNAP, "--context-dir", ctx, "--no-git", "--session", "s1", cwd=str(repo))
    sdir = next((repo / "context").glob("*/s1"))
    before = {p.name: p.read_bytes() for p in sdir.iterdir() if p.is_file()}

    _py(PACK, "--context-dir", ctx, "--pack", "s1", cwd=str(repo))
    assert (sdir / "detail.tar.xz").exists()
    _py(PACK, "--context-dir", ctx, "--unpack", "s1", cwd=str(repo))

    after = {p.name: p.read_bytes() for p in sdir.iterdir() if p.is_file()}
    assert after == before


def test_retention_fully_archives_old_sessions(repo):
    ctx = repo / "context"
    ctx.mkdir()
    (ctx / ".contextrc.json").write_text(json.dumps(
        {"retention": {"maxSessions": 2, "maxAgeDays": 36500}}))
    for sid in ("2024-01-01-a", "2024-01-02-b", "2024-01-03-c", "2024-01-04-d"):
        _py(SNAP, "--context-dir", str(ctx), "--no-git", "--session", sid, cwd=str(repo))

    out = json.loads(_py(ROLL, "--context-dir", str(ctx), "--json", cwd=str(repo)))
    assert len(out["sessionsArchived"]) == 2

    oldest = next(ctx.glob("*/2024-01-01-a"))
    assert (oldest / "full.tar.xz").exists()
    assert (oldest / "manifest.json").exists()   # kept so INDEX stays meaningful
    assert not (oldest / "summary.md").exists()
    newest = next(ctx.glob("*/2024-01-04-d"))
    assert not (newest / "full.tar.xz").exists()


@pytest.mark.skipif(importlib.util.find_spec("mcp") is None,
                    reason="the 'mcp' package is not installed")
def test_mcp_server_stdio_round_trip(repo):
    """Start the bundled MCP server as a subprocess and drive it with a real
    MCP client: list tools, then snapshot -> list -> write -> rollup -> search."""
    import anyio
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    server_env = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
    server_env["SHARED_CONTEXT_DIR"] = str(repo / "context")

    def payload(result):
        assert result.isError is False, result.content
        return json.loads(result.content[0].text)

    async def scenario():
        params = StdioServerParameters(
            command=sys.executable, args=[MCP_SERVER], env=server_env, cwd=str(repo),
        )
        with anyio.move_on_after(60) as scope:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    tool_names = {t.name for t in (await session.list_tools()).tools}
                    assert {
                        "context_list", "context_snapshot", "context_read",
                        "context_write", "context_pack", "context_unpack",
                        "context_rollup", "context_search",
                    } <= tool_names

                    assert payload(await session.call_tool("context_list", {}))["exists"] is False

                    await session.call_tool("context_snapshot", {
                        "session": "M1", "task": "wired via mcp",
                        "agent": "claude-sonnet-5", "no_git": True})
                    listed = payload(await session.call_tool("context_list", {}))
                    assert listed["count"] == 1 and listed["sessions"][0]["task"] == "wired via mcp"

                    sdir = next((repo / "context").glob("*/M1"))
                    rel = f"{sdir.parent.name}/M1/decisions.md"
                    w = payload(await session.call_tool("context_write", {
                        "rel_path": rel,
                        "content": '# Decisions\n\n- **Use MCP** - identical tool '
                                   'names on both hosts. leak="AKIAIOSFODNN7EXAMPLE"\n'}))
                    assert w["redactions"] == ["aws-akid"]

                    r = payload(await session.call_tool("context_read", {"rel_path": rel}))
                    assert "AKIAIOSFODNN7EXAMPLE" not in r["content"] and "REDACTED" in r["content"]

                    rolled = payload(await session.call_tool("context_rollup", {}))
                    assert any("Use MCP" in d for d in rolled["decisionsAdded"])

                    hits = payload(await session.call_tool("context_search", {"query": "Use MCP"}))
                    assert hits["matches"]

                    packed = payload(await session.call_tool("context_pack", {"session": "M1"}))
                    assert packed["results"][0]["action"] == "pack"
        assert not scope.cancel_called, "MCP round-trip timed out"

    anyio.run(scenario)


@pytest.mark.skipif(importlib.util.find_spec("mcp") is None,
                    reason="the 'mcp' package is not installed")
@pytest.mark.skipif(
    shutil.which("uv") is None and importlib.util.find_spec("mcp.server.fastmcp") is None,
    reason="launcher needs either 'uv' or an importable v1 MCP SDK",
)
def test_mcp_launcher_starts_the_server_as_shipped(repo):
    """Drive the server through ``sh mcp/run-server.sh`` — the exact command the
    .mcp.json / mcp_config.json ship — proving the uv-based launcher works with
    no manual ``pip install``."""
    import anyio
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    server_env = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
    server_env["SHARED_CONTEXT_DIR"] = str(repo / "context")

    async def scenario():
        params = StdioServerParameters(
            command="sh", args=[MCP_LAUNCHER], env=server_env, cwd=str(repo),
        )
        with anyio.move_on_after(180) as scope:  # first uv run may fetch mcp
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {t.name for t in (await session.list_tools()).tools}
                    assert {"context_list", "context_snapshot", "context_pack"} <= tools

                    r = await session.call_tool("context_snapshot", {
                        "session": "L1", "task": "via launcher",
                        "agent": "claude-sonnet-5", "no_git": True})
                    assert r.isError is False
                    listed = json.loads(
                        (await session.call_tool("context_list", {})).content[0].text)
                    assert listed["count"] == 1
        assert not scope.cancel_called, "launcher MCP round-trip timed out"

    anyio.run(scenario)
