#!/usr/bin/env python3
"""Shared-context MCP server (stdio).

Exposes the shared-context store as MCP tools so an agent gets the *same* tool
names on Claude Code and Antigravity CLI (no ``Bash`` vs ``run_command`` split):

    context_list      list sessions (read-only; decides whether to prompt)
    context_snapshot  create / update this session's record
    context_read      read one file from a session or a long-lived file
    context_write     write or append one agent-editable markdown file
    context_pack      compress a session's detail (or --auto)
    context_unpack    restore a session's detail
    context_rollup    roll decisions into architecture.md + apply retention
    context_search    grep across the context/ tree

Needs the MCP Python SDK v1 (``mcp<2`` — it uses the v1 ``FastMCP`` API, which
mcp 2.x renamed). The bundled launcher ``mcp/run-server.sh`` handles this for
you via ``uv`` (no global install). If the SDK is unavailable the plugin's
scripts under ``skills/context-*/scripts/`` remain fully usable on their own —
this server is a convenience wrapper, not the only entry point.
"""
import json
import os
import re
import subprocess
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE = os.path.join(PLUGIN_ROOT, "skills", "context-capture", "scripts")
RESTORE = os.path.join(PLUGIN_ROOT, "skills", "context-restore", "scripts")
SNAPSHOT = os.path.join(CAPTURE, "context_snapshot.py")
PACK = os.path.join(CAPTURE, "context_pack.py")
ROLLUP = os.path.join(CAPTURE, "context_rollup.py")
LIST = os.path.join(RESTORE, "context_list.py")

# Files an agent may write through this server (everything else is generated).
WRITABLE = {"summary.md", "decisions.md", "flows.md", "topics.md",
            "files-touched.json", "preferences.md", "architecture.md"}
SEARCHABLE_EXT = (".md", ".json", ".txt")

sys.path.insert(0, CAPTURE)
try:
    from context_common import redact_text  # bundled copy
except Exception:  # pragma: no cover - fallback if the bundled copy is missing
    def redact_text(text):
        return text, []


def _context_dir(explicit=None):
    if explicit:
        return os.path.abspath(explicit)
    return os.path.abspath(
        os.environ.get("SHARED_CONTEXT_DIR") or os.path.join(os.getcwd(), "context")
    )


def _run(script, args):
    proc = subprocess.run([sys.executable, script, *args], capture_output=True, text=True)
    out = (proc.stdout or "").strip()
    try:
        parsed = json.loads(out)
    except ValueError:
        parsed = {"stdout": out}
    if proc.returncode != 0:
        parsed["error"] = (proc.stderr or "").strip() or f"exit {proc.returncode}"
    return parsed


def _safe_path(context_dir, rel):
    target = os.path.abspath(os.path.join(context_dir, rel))
    if target != context_dir and not target.startswith(context_dir + os.sep):
        raise ValueError(f"path escapes the context directory: {rel}")
    return target


# --- tool implementations (pure, unit-testable without the mcp package) ----

def tool_context_list(context_dir=None, full=False, limit=0):
    args = ["--context-dir", _context_dir(context_dir), "--json"]
    if full:
        args.append("--full")
    if limit:
        args += ["--limit", str(int(limit))]
    return _run(LIST, args)


def tool_context_snapshot(context_dir=None, session=None, task="", agent="",
                          model="", status="", host="", no_git=False):
    args = ["--context-dir", _context_dir(context_dir), "--json"]
    if session:
        args += ["--session", session]
    if task:
        args += ["--task", task]
    if agent:
        args += ["--agent", agent]
    if model:
        args += ["--model", model]
    if status:
        args += ["--status", status]
    if host:
        args += ["--host", host]
    if no_git:
        args.append("--no-git")
    return _run(SNAPSHOT, args)


def tool_context_pack(context_dir=None, session=None, auto=False, unpack=False,
                      keep_uncompressed=None):
    args = ["--context-dir", _context_dir(context_dir), "--json"]
    if auto:
        args.append("--auto")
        if keep_uncompressed is not None:
            args += ["--keep-uncompressed", str(int(keep_uncompressed))]
    elif unpack:
        args += ["--unpack", session or ""]
    else:
        args += ["--pack", session or ""]
    return _run(PACK, args)


def tool_context_unpack(context_dir=None, session=None):
    return tool_context_pack(context_dir=context_dir, session=session, unpack=True)


def tool_context_rollup(context_dir=None, no_retention=False):
    args = ["--context-dir", _context_dir(context_dir), "--json"]
    if no_retention:
        args.append("--no-retention")
    return _run(ROLLUP, args)


def tool_context_read(rel_path, context_dir=None):
    cdir = _context_dir(context_dir)
    try:
        path = _safe_path(cdir, rel_path)
    except ValueError as e:
        return {"error": str(e)}
    if not os.path.isfile(path):
        return {"error": f"not found: {rel_path}"}
    with open(path, encoding="utf-8", errors="replace") as f:
        return {"path": rel_path, "content": f.read()}


def tool_context_write(rel_path, content, mode="overwrite", context_dir=None):
    if os.path.basename(rel_path) not in WRITABLE:
        return {"error": f"{os.path.basename(rel_path)} is not agent-writable; "
                         f"allowed: {sorted(WRITABLE)}"}
    cdir = _context_dir(context_dir)
    try:
        path = _safe_path(cdir, rel_path)
    except ValueError as e:
        return {"error": str(e)}
    cleaned, found = redact_text(content)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if mode == "append" and os.path.isfile(path):
        with open(path, "a", encoding="utf-8") as f:
            f.write(("\n" if not cleaned.startswith("\n") else "") + cleaned)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned)
    return {"path": rel_path, "bytes": len(cleaned), "redactions": sorted(set(found))}


def tool_context_search(query, context_dir=None, max_results=100):
    cdir = _context_dir(context_dir)
    if not os.path.isdir(cdir):
        return {"error": f"no context dir at {cdir}", "matches": []}
    try:
        rx = re.compile(query, re.IGNORECASE)
    except re.error as e:
        return {"error": f"bad regex: {e}", "matches": []}
    matches = []
    for root, _dirs, files in os.walk(cdir):
        for fn in sorted(files):
            if not fn.endswith(SEARCHABLE_EXT):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if rx.search(line):
                            matches.append({
                                "path": os.path.relpath(fp, cdir),
                                "line": i,
                                "text": line.rstrip()[:300],
                            })
                            if len(matches) >= max_results:
                                return {"query": query, "matches": matches, "truncated": True}
            except OSError:
                continue
    return {"query": query, "matches": matches, "truncated": False}


def _serve():
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        sys.stderr.write(
            "shared-context: needs the MCP Python SDK v1 (mcp<2, which provides "
            "mcp.server.fastmcp.FastMCP). Use the launcher mcp/run-server.sh (it "
            "fetches it via uv), or `pip install \"mcp<2\"`. The context_*.py "
            "scripts work without it.\n"
        )
        return 1

    server = FastMCP("shared-context")

    @server.tool()
    def context_list(full: bool = False, limit: int = 0) -> dict:
        """List shared-context sessions, newest first. `exists` is false when there is none."""
        return tool_context_list(full=full, limit=limit)

    @server.tool()
    def context_snapshot(task: str = "", agent: str = "", model: str = "",
                         status: str = "", session: str = "",
                         no_git: bool = False) -> dict:
        """Create or update this session's record. On update, only fields you pass
        are changed (host/agent/model provenance is otherwise preserved)."""
        return tool_context_snapshot(session=session or None, task=task, agent=agent,
                                     model=model, status=status, no_git=no_git)

    @server.tool()
    def context_read(rel_path: str) -> dict:
        """Read one file under context/ (e.g. `2026-08-31/<id>/summary.md` or `architecture.md`)."""
        return tool_context_read(rel_path)

    @server.tool()
    def context_write(rel_path: str, content: str, mode: str = "overwrite") -> dict:
        """Write or append one agent-editable markdown file under context/ (redacted on write)."""
        return tool_context_write(rel_path, content, mode=mode)

    @server.tool()
    def context_pack(session: str = "", auto: bool = False,
                     keep_uncompressed: int = -1) -> dict:
        """Compress a session's detail into detail.tar.xz, or auto-pack all but the newest N."""
        return tool_context_pack(session=session or None, auto=auto,
                                 keep_uncompressed=None if keep_uncompressed < 0 else keep_uncompressed)

    @server.tool()
    def context_unpack(session: str) -> dict:
        """Restore a session's detail files from detail.tar.xz."""
        return tool_context_unpack(session=session)

    @server.tool()
    def context_rollup(no_retention: bool = False) -> dict:
        """Roll session decisions into architecture.md, regenerate INDEX.md, apply retention."""
        return tool_context_rollup(no_retention=no_retention)

    @server.tool()
    def context_search(query: str, max_results: int = 100) -> dict:
        """Case-insensitive regex search across the context/ tree."""
        return tool_context_search(query, max_results=max_results)

    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(_serve())
