"""Claude Code-specific sync configuration shared by sync_agents.py and sync_plugin_skills.py.

Canonical content lives in /skills and plugins/antigravity/. Everything that makes the
Claude Code copy different from the Antigravity one is declared here, in one place:

* translation of Antigravity tool names / syntax into Claude Code equivalents,
* plugin dependencies (Claude Code `plugin.json` "dependencies") instead of copied agents,
* per-agent overrides (preloaded skills, model, extra tools),
* Claude-only runtime appendices added to agent bodies,
* which plugins receive the shared hook library.
"""
from __future__ import annotations

import re

# --------------------------------------------------------------------------------------
# 1. Translation: Antigravity -> Claude Code
# --------------------------------------------------------------------------------------
# Tokens that must never survive into plugins/claude/ (checked by tests and sync warnings).
FORBIDDEN_CLAUDE_TOKENS = [
    "run_command",
    "write_to_file",
    "replace_file_content",
    "invoke_subagent",
    "manage_subagents",
    "call_mcp_tool",
    "view_file",
    "send_message",
    "list_dir",
    "grep_search",
    "find_by_name",
    "ask_question",
    "Subagents=[",
    "Workspace: '",
]

_PARALLEL = "several `Agent` calls in one message"


def sanitize_claude_content(text: str) -> str:
    """Translates Antigravity tool names and syntax into Claude Code equivalents."""
    # Subagent invocation syntax
    text = re.sub(r'invoke_subagent\(name="([^"]+)",\s*prompt="([^"]+)"\)', r'Agent(agent="\1", prompt="\2")', text)
    text = re.sub(r'invoke_subagent\(name="([^"]+)"\)', r'Agent(agent="\1")', text)
    text = re.sub(r"`invoke_subagent\(Subagents=\[\.\.\.\]\)`", _PARALLEL, text)
    text = re.sub(r"`Agent\(Subagents=\[\.\.\.\]\)`", _PARALLEL, text)
    text = re.sub(r"`Subagents=\[\.\.\.\]`", _PARALLEL, text)
    text = re.sub(r"invoke_subagent\(([^)]+)\)", r"Agent(\1)", text)

    # Workspace isolation modes -> Claude Code worktree isolation
    text = re.sub(r"`Workspace: 'share'`\s*/\s*`'branch'`", '`isolation: "worktree"`', text)
    text = re.sub(r"\(`Workspace: 'inherit'`\)", "(shared working tree)", text)
    text = re.sub(r"`Workspace: 'inherit'`", "shared working tree", text)
    text = re.sub(r"`Workspace: '(share|branch)'`", '`isolation: "worktree"`', text)

    # Execution policy
    text = re.sub(r"commandExecutionPolicy:\s*['\"]?auto['\"]?", "permissionMode: default", text)
    text = re.sub(r"\bcommandExecutionPolicy\b", "permissionMode", text)

    # Bare tool names
    text = re.sub(r"\bcall_mcp_tool\b", "mcp__<server>__<tool>", text)
    text = re.sub(r"\binvoke_subagent\b", "Agent", text)
    text = re.sub(r"\bmanage_subagents\b", "Agent", text)
    text = re.sub(r"\bsend_message\b", "SendMessage", text)
    text = re.sub(r"\bask_question\b", "AskUserQuestion", text)
    text = re.sub(r"\bwrite_to_file\b", "Write", text)
    text = re.sub(r"\breplace_file_content\b", "Edit", text)
    text = re.sub(r"\bview_file\b", "Read", text)
    text = re.sub(r"\brun_command\b", "Bash", text)
    text = re.sub(r"\blist_dir\b", "Glob", text)
    text = re.sub(r"\bgrep_search\b", "Grep", text)
    text = re.sub(r"\bfind_by_name\b", "Glob", text)
    text = re.sub(
        r"In \*\*Google Antigravity\*\*:\s*Use `Write` and `Edit`",
        "In **Claude Code**: Use `Write` and `Edit`",
        text,
    )
    return text


# --------------------------------------------------------------------------------------
# 2. Plugin dependencies (Claude Code resolves them at install time)
# --------------------------------------------------------------------------------------
# Antigravity has no plugin dependencies, so there the senior-dev specialists are copied
# into these plugins (sync_agents.BUNDLED_AGENTS). Claude Code declares a dependency instead.
CLAUDE_PLUGIN_DEPENDENCIES = {
    "senior-dev-flutter": ["senior-dev"],
    "python-backend": ["senior-dev"],
}

# Skills a dependent plugin keeps even if its dependency ships them too, because the
# plugin's own agents preload them by bare name in their `skills:` frontmatter.
KEEP_LOCAL_SKILLS = {"context-capture", "context-restore", "loop-engineering"}


def claude_excluded_skills(plugin: str, skills_by_plugin: dict[str, list[str]]) -> set[str]:
    """Skills NOT copied into plugins/claude/<plugin> because a dependency already ships them."""
    provided: set[str] = set()
    for dependency in CLAUDE_PLUGIN_DEPENDENCIES.get(plugin, []):
        provided.update(skills_by_plugin.get(dependency, []))
    return provided - KEEP_LOCAL_SKILLS


# --------------------------------------------------------------------------------------
# 3. Agent overrides for Claude Code
# --------------------------------------------------------------------------------------
CLAUDE_WORKER_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"]
# AskUserQuestion only works on the main thread (`claude --agent ...`); subagents drop it.
CLAUDE_ORCHESTRATOR_TOOLS = CLAUDE_WORKER_TOOLS + ["Agent", "AskUserQuestion"]

PLAYWRIGHT_MCP_TOOLS = [
    f"mcp__plugin_senior-dev_playwright__{tool}"
    for tool in (
        "browser_navigate",
        "browser_navigate_back",
        "browser_snapshot",
        "browser_click",
        "browser_type",
        "browser_press_key",
        "browser_select_option",
        "browser_hover",
        "browser_wait_for",
        "browser_resize",
        "browser_take_screenshot",
        "browser_console_messages",
        "browser_network_requests",
        "browser_close",
    )
]

# skills: only the agent's core skill is preloaded (full SKILL.md enters context at start);
# everything else stays loadable on demand through the Skill tool.
# model: cheaper models for template/checklist-driven roles; `inherit` where reasoning depth matters.
CLAUDE_AGENT_OVERRIDES = {
    "senior-dev-orchestrator": {"skills": ["senior-dev-orchestrator", "loop-engineering"]},
    "flutter-feature-orchestrator": {"skills": ["flutter-senior-orchestration", "loop-engineering"]},
    "python-backend-orchestrator": {"skills": ["loop-engineering"]},
    "code-implementer": {"skills": ["code-implementer"]},
    "critic": {"skills": ["code-critic"]},
    "challenger": {"skills": ["adversarial-challenger"]},
    "compliance-verifier": {"skills": ["compliance-verifier"], "model": "sonnet"},
    "product-analyst": {"model": "sonnet"},
    "ui-ux-designer": {"model": "sonnet"},
    "qa-tester": {"model": "sonnet"},
    "e2e-blackbox-tester": {"model": "sonnet", "extra_tools": PLAYWRIGHT_MCP_TOOLS},
    "flutter-release-engineer": {"model": "sonnet"},
    "context-keeper": {"model": "haiku"},
}


def _subagent_types(plugin: str, own_agents: list[str], dependency_agents: dict[str, list[str]]) -> str:
    names = [f"`{plugin}:{a}`" for a in own_agents]
    for dep, agents in dependency_agents.items():
        names += [f"`{dep}:{a}`" for a in agents]
    return ", ".join(names)


def orchestrator_appendix(name: str, plugin: str, own_agents: list[str], dependency_agents: dict[str, list[str]]) -> str:
    """Claude Code runtime notes appended to orchestrator agent bodies."""
    workers = [a for a in own_agents if a != name]
    return f"""

# Claude Code Runtime Notes
- **Run as the main thread** so the alignment gate can ask the user: `claude --agent {plugin}:{name}` (or `"agent": "{plugin}:{name}"` in `.claude/settings.json`). `AskUserQuestion` is removed inside subagents: if it is unavailable, return the alignment summary as your final message and stop for approval.
- **Exact `subagent_type` values**: {_subagent_types(plugin, workers, dependency_agents)}.
- **Parallel fan-out** = several `Agent` calls in one message. **Mode B** = `isolation: "worktree"` on the `Agent` call, only after confirming `"worktree": {{"baseRef": "head"}}` in `.claude/settings.json`, `.claude/settings.local.json` or `~/.claude/settings.json` (otherwise the worktree starts from the default branch).
- **Skills on demand**: only your core skills are preloaded; load others with the `Skill` tool when a state needs them (e.g. `context-restore` at State 0, `context-capture` at State 5).
- **Stop gates are cached**: the Stop hook re-runs tests only when code changed since the last green run and blocks at most 3 times per turn.
"""


E2E_APPENDIX = """

# Claude Code Runtime Notes
- **Drive the real browser with the Playwright MCP tools** (`mcp__plugin_senior-dev_playwright__*`): `browser_navigate` -> `browser_snapshot` -> interactions -> `browser_console_messages` / `browser_network_requests` -> `browser_resize` per viewport -> `browser_take_screenshot` with an **absolute** `filename` under `docs/<feature-name>/evidence/`. Scripted `npx playwright test` is the fallback when the MCP is unavailable.
- **Evidence gate (SubagentStop hook)**: a `PASSED` or `REJECTED` verdict is rejected unless your own transcript shows a successful `browser_navigate` and `browser_take_screenshot` (or a successful Bash `playwright` run) and the screenshots exist on disk as real PNGs. If the browser or server cannot start, end with `Verdict: BLOCKED - <exact error>`; with no web UI, `Verdict: SKIPPED - <reason>`.
- End your final message with exactly one verdict line: `Verdict: PASSED|REJECTED|BLOCKED|SKIPPED - <one-line reason>`.
"""


# --------------------------------------------------------------------------------------
# 4. Shared hook library
# --------------------------------------------------------------------------------------
# Claude plugins whose hooks import hooks/shared/gate-utils.js (canonical: scripts/hook-lib/).
GATED_PLUGINS = [
    "senior-dev",
    "python-backend",
    "senior-dev-flutter",
    "senior-data-engineer",
    "docs-and-quality",
    "git-workflow",
]
