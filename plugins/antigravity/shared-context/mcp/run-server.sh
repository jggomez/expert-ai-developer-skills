#!/bin/sh
# Launcher for the shared-context MCP server.
#
# Resolution order (first that works wins):
#   1. `uv`  -> `uv run --no-project --with 'mcp<2' python mcp_server.py`
#      No global install needed: uv fetches the MCP SDK into a cached ephemeral
#      env. `mcp<2` is pinned because this server uses the v1 FastMCP API
#      (mcp 2.x renamed it). Get uv: https://docs.astral.sh/uv/
#      (curl -LsSf https://astral.sh/uv/install.sh | sh)
#   2. a Python that already has `mcp.server.fastmcp` importable
#      ($SHARED_CONTEXT_PYTHON, then python3, then python).
#   3. otherwise: exit 1 with a hint. The bundled scripts under
#      skills/context-*/scripts/ still work without the MCP server.
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SERVER="$DIR/mcp_server.py"

if command -v uv >/dev/null 2>&1; then
  exec uv run --no-project --quiet --with 'mcp<2' python "$SERVER"
fi

for PY in "${SHARED_CONTEXT_PYTHON:-}" python3 python; do
  [ -n "$PY" ] || continue
  if command -v "$PY" >/dev/null 2>&1 && "$PY" -c 'import mcp.server.fastmcp' >/dev/null 2>&1; then
    exec "$PY" "$SERVER"
  fi
done

echo "shared-context: MCP server not started — install 'uv' (recommended," >&2
echo "  curl -LsSf https://astral.sh/uv/install.sh | sh) or 'pip install \"mcp<2\"'." >&2
echo "  The context_*.py scripts still work without it." >&2
exit 1
