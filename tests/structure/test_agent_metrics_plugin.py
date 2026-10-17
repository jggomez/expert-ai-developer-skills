"""Structural and behavioral checks for the optional `agent-metrics` plugin pair.

The plugin is a thin, optional convenience channel for the standalone
`agent-meter` CLI (tools/agent-meter, PRD US-12, ADR-001 §3.10):

- Claude Code (`plugins/claude/agent-metrics`): `SessionEnd` + `Stop` hooks.
- Antigravity (`plugins/antigravity/agent-metrics`): one named hook with a
  `Stop` handler list. No top-level string keys such as `"description"`: the
  Antigravity loader rejects the whole file when one is present.

Both ship the same Node wrapper (`hooks/agent-meter-hook.js`), which runs
`agent-meter hook --host <h> --event <e>` with the payload on stdin, always
exits 0, prints exactly `{}` for Antigravity and nothing for Claude Code, and
prints a one-line install hint to stderr when the CLI is missing (HK-01..04).
"""
import ast
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time

import pytest
import yaml

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLAUDE_PLUGIN = os.path.join(WORKSPACE_ROOT, "plugins", "claude", "agent-metrics")
AGY_PLUGIN = os.path.join(WORKSPACE_ROOT, "plugins", "antigravity", "agent-metrics")
CANONICAL_SKILL = os.path.join(WORKSPACE_ROOT, "skills", "agent-metrics")
SETTINGS_MERGE = os.path.join(
    WORKSPACE_ROOT, "tools", "agent-meter", "src", "agent_meter", "setup", "settings_merge.py"
)
WRAPPER_REL = os.path.join("hooks", "agent-meter-hook.js")
REPO_URL = "https://github.com/jggomez/expert-ai-developer-skills"
STALE_REPO_URL = "github.com/jggomez/skills-programming-ai"
UV_INSTALL = f'uv tool install "git+{REPO_URL}#subdirectory=tools/agent-meter"'
INSTALL_HINT_PREFIX = "agent-meter not installed: see "
HOST_TIMEOUT_S = 10

CLAUDE_TOOL_NAMES = re.compile(
    r"\b(?:Bash|Glob|Grep|WebSearch|WebFetch|Agent)\b|`(?:Read|Write|Edit)`|\b(?:Read|Write|Edit)\("
)
ANTIGRAVITY_TOOL_NAMES = re.compile(
    r"\b(?:run_command|view_file|write_to_file|replace_file_content|invoke_subagent|"
    r"manage_subagents|send_message|call_mcp_tool|list_dir|grep_search|find_by_name)\b"
)
TEXT_SUFFIXES = {".md", ".json", ".js", ".py", ".sh", ".yaml", ".yml", ".txt", ".sql"}

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not available")
needs_posix = pytest.mark.skipif(os.name == "nt", reason="fake CLI is a POSIX shell script")


# ----------------------------------------------------------------------------- helpers


def _read(base, rel):
    with open(os.path.join(base, rel), encoding="utf-8") as f:
        return f.read()


def _json(base, rel):
    return json.loads(_read(base, rel))


def _text_files(base):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", "node_modules"}]
        for name in files:
            if os.path.splitext(name)[1].lower() in TEXT_SUFFIXES:
                yield os.path.join(root, name)


def _cli_claude_events():
    """(event, flag) pairs from the CLI's own settings merger — the single source of truth."""
    src = _read(WORKSPACE_ROOT, SETTINGS_MERGE)
    match = re.search(r"_CLAUDE_EVENTS: Final = (\(.*?\)\))\n", src, re.DOTALL)
    assert match, "could not find _CLAUDE_EVENTS in settings_merge.py"
    return ast.literal_eval(match.group(1))


def _cli_antigravity_suffix():
    src = _read(WORKSPACE_ROOT, SETTINGS_MERGE)
    match = re.search(r'_ANTIGRAVITY_SUFFIX: Final = "([^"]+)"', src)
    assert match, "could not find _ANTIGRAVITY_SUFFIX in settings_merge.py"
    return match.group(1)


def _wrapper_args(command):
    """Arguments after the wrapper script path, e.g. '--host antigravity --event task-end'."""
    match = re.search(r"agent-meter-hook\.js\"?\s+(.*)$", command)
    assert match, f"hook command does not run the wrapper: {command!r}"
    return match.group(1).strip()


def _readme_bundled_skills(readme):
    section = re.search(r"## \d+\. Bundled Skills.*?(?=\n## |\Z)", readme, re.DOTALL)
    assert section, "README has no '## N. Bundled Skills' section"
    return set(re.findall(r"\*\*`([a-z0-9-]+)`\*\*", section.group(0)))


# ----------------------------------------------------------------------------- layout & manifests


@pytest.mark.parametrize(
    "base, files",
    [
        (CLAUDE_PLUGIN, [".claude-plugin/plugin.json", "hooks.json", WRAPPER_REL, "README.md",
                         "skills/agent-metrics/SKILL.md"]),
        (AGY_PLUGIN, ["plugin.json", ".claude-plugin/plugin.json", "hooks.json", WRAPPER_REL,
                      "README.md", "skills/agent-metrics/SKILL.md"]),
    ],
    ids=["claude", "antigravity"],
)
def test_expected_files_present(base, files):
    missing = [f for f in files if not os.path.isfile(os.path.join(base, f))]
    assert not missing, f"{base}: missing {missing}"


def test_plugin_ships_no_agents_mcp_or_rules():
    """The plugin is hooks + one skill only; it must not add agents or MCP servers."""
    for base in (CLAUDE_PLUGIN, AGY_PLUGIN):
        for extra in ("agents", "mcp", "rules", ".mcp.json", "mcp_config.json"):
            assert not os.path.exists(os.path.join(base, extra)), f"{base}: unexpected {extra}"


def test_manifests_are_named_agent_metrics():
    claude = _json(CLAUDE_PLUGIN, ".claude-plugin/plugin.json")
    assert claude["name"] == "agent-metrics"
    assert claude.get("description")
    assert claude.get("hooks") == "./hooks.json", "Claude manifest must point at the root hooks.json"
    assert _json(AGY_PLUGIN, "plugin.json") == {"name": "agent-metrics"}
    assert _json(AGY_PLUGIN, ".claude-plugin/plugin.json") == {"name": "agent-metrics"}


def test_marketplace_lists_agent_metrics():
    data = _json(WORKSPACE_ROOT, ".claude-plugin/marketplace.json")
    entries = [p for p in data["plugins"] if p.get("name") == "agent-metrics"]
    assert len(entries) == 1, "marketplace.json must list agent-metrics exactly once"
    assert entries[0]["source"] == "./plugins/claude/agent-metrics"
    assert entries[0].get("description")


# ----------------------------------------------------------------------------- hooks.json


def test_claude_hooks_json_mirrors_cli_registration():
    data = _json(CLAUDE_PLUGIN, "hooks.json")
    hooks = data["hooks"]
    expected = dict(_cli_claude_events())  # {"SessionEnd": "session-end", "Stop": "task-end"}
    assert set(hooks) == set(expected)
    for event, flag in expected.items():
        assert len(hooks[event]) == 1, event
        group = hooks[event][0]
        assert "enabled" not in group and "matcher" not in group
        assert len(group["hooks"]) == 1, event
        hook = group["hooks"][0]
        assert hook["type"] == "command"
        assert hook["timeout"] == HOST_TIMEOUT_S
        assert hook["command"].startswith('node "${CLAUDE_PLUGIN_ROOT}/hooks/agent-meter-hook.js" ')
        assert _wrapper_args(hook["command"]) == f"--host claude-code --event {flag}"


def test_antigravity_hooks_json_is_named_hook_only():
    data = _json(AGY_PLUGIN, "hooks.json")
    non_objects = [k for k, v in data.items() if not isinstance(v, dict)]
    assert not non_objects, f"Antigravity rejects top-level non-object keys: {non_objects}"
    assert "description" not in data
    assert "hooks" not in data, "the Claude 'hooks' key would be parsed as an Antigravity named hook"
    assert list(data) == ["agent-metrics"]

    named = data["agent-metrics"]
    assert named["enabled"] is True
    assert set(named) == {"enabled", "Stop"}, "Antigravity has no SessionEnd event"
    handlers = named["Stop"]
    assert len(handlers) == 1
    handler = handlers[0]
    assert handler["type"] == "command"
    assert handler["timeout"] == HOST_TIMEOUT_S
    assert handler["command"].startswith("node ./hooks/agent-meter-hook.js ")
    expected_args = _cli_antigravity_suffix().replace(" hook ", "", 1).strip()
    assert _wrapper_args(handler["command"]) == expected_args
    assert "CLAUDE_PLUGIN_ROOT" not in _read(AGY_PLUGIN, "hooks.json")


def test_wrapper_is_identical_in_both_plugins():
    assert _read(CLAUDE_PLUGIN, WRAPPER_REL) == _read(AGY_PLUGIN, WRAPPER_REL)


@needs_node
@pytest.mark.parametrize("base", [CLAUDE_PLUGIN, AGY_PLUGIN], ids=["claude", "antigravity"])
def test_wrapper_is_valid_javascript(base):
    r = subprocess.run([NODE, "--check", os.path.join(base, WRAPPER_REL)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# ----------------------------------------------------------------------------- tool bleed


def test_antigravity_plugin_has_no_claude_tool_names():
    leaks = []
    for path in _text_files(AGY_PLUGIN):
        with open(path, encoding="utf-8") as f:
            for match in CLAUDE_TOOL_NAMES.finditer(f.read()):
                leaks.append(f"{os.path.relpath(path, WORKSPACE_ROOT)}: {match.group(0)}")
    assert not leaks, "\n".join(leaks)


def test_claude_plugin_has_no_antigravity_tool_names():
    leaks = []
    for path in _text_files(CLAUDE_PLUGIN):
        with open(path, encoding="utf-8") as f:
            for match in ANTIGRAVITY_TOOL_NAMES.finditer(f.read()):
                leaks.append(f"{os.path.relpath(path, WORKSPACE_ROOT)}: {match.group(0)}")
    assert not leaks, "\n".join(leaks)


def test_canonical_skill_is_host_neutral():
    text = _read(CANONICAL_SKILL, "SKILL.md")
    assert not CLAUDE_TOOL_NAMES.search(text), CLAUDE_TOOL_NAMES.search(text).group(0)
    assert not ANTIGRAVITY_TOOL_NAMES.search(text), ANTIGRAVITY_TOOL_NAMES.search(text).group(0)


# ----------------------------------------------------------------------------- skill & docs


def test_canonical_skill_frontmatter_and_content():
    text = _read(CANONICAL_SKILL, "SKILL.md")
    match = re.search(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert match, "SKILL.md has no frontmatter"
    fm = yaml.safe_load(match.group(1))
    assert fm["name"] == "agent-metrics"
    assert len(fm["description"]) > 30
    for needle in ("agent-meter setup", "--local", "--cloud", "devhack-3f0c2", "billing", "sandbox",
                   "agent-meter doctor", "agent-meter pricing", "DuckDB", "BigQuery", "agent-meter uninstall",
                   UV_INSTALL):
        assert needle in text, f"SKILL.md does not cover {needle!r}"


@pytest.mark.parametrize("base", [CLAUDE_PLUGIN, AGY_PLUGIN], ids=["claude", "antigravity"])
def test_plugin_readme_covers_install_opt_in_and_uninstall(base):
    readme = _read(base, "README.md")
    for needle in (UV_INSTALL, "agent-meter setup", "agent-meter uninstall", "optional"):
        assert needle in readme, f"{base}/README.md does not mention {needle!r}"
    assert _readme_bundled_skills(readme) == {"agent-metrics"}


def test_docs_readme_links_resolve():
    docs = os.path.join(WORKSPACE_ROOT, "docs", "agent-metrics")
    readme = _read(docs, "README.md")
    links = re.findall(r"\[[^\]]*\]\((?!https?:|#|mailto:)([^)\s]+)\)", readme)
    for required in ("PRD.md", "ADR-001-agent-meter.md", "contracts.md", "looker-studio.md"):
        assert required in links, f"docs/agent-metrics/README.md does not link {required}"
    broken = [link for link in links
              if not os.path.exists(os.path.normpath(os.path.join(docs, link.split("#")[0])))]
    assert not broken, f"broken links: {broken}"
    for needle in ("Option A", "Option B", UV_INSTALL, "agent-meter setup", "agent-meter uninstall"):
        assert needle in readme, f"docs README does not mention {needle!r}"


def test_track_files_use_the_canonical_repository_url():
    """The canonical slug is the git remote (expert-ai-developer-skills), never the old plan URL."""
    roots = [CLAUDE_PLUGIN, AGY_PLUGIN, CANONICAL_SKILL,
             os.path.join(WORKSPACE_ROOT, "docs", "agent-metrics", "README.md"),
             os.path.join(WORKSPACE_ROOT, "tools", "agent-meter", "README.md"),
             os.path.join(WORKSPACE_ROOT, "tools", "agent-meter", "pyproject.toml"),
             os.path.join(WORKSPACE_ROOT, "README.md")]
    stale = []
    for root in roots:
        paths = [root] if os.path.isfile(root) else list(_text_files(root))
        for path in paths:
            with open(path, encoding="utf-8") as f:
                if STALE_REPO_URL in f.read():
                    stale.append(os.path.relpath(path, WORKSPACE_ROOT))
    assert not stale, f"stale repository URL in: {stale}"


def test_sync_agents_keeps_marketplace_entry_and_manifest_hooks_pointer(tmp_path):
    """Running scripts/sync_agents.py (in a temp copy) must be a no-op for agent-metrics."""
    for rel in ("scripts", "plugins", ".claude-plugin"):
        shutil.copytree(os.path.join(WORKSPACE_ROOT, rel), tmp_path / rel,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    manifest_rel = os.path.join("plugins", "claude", "agent-metrics", ".claude-plugin", "plugin.json")
    marketplace_rel = os.path.join(".claude-plugin", "marketplace.json")

    result = subprocess.run([sys.executable, str(tmp_path / "scripts" / "sync_agents.py")],
                            capture_output=True, text=True, timeout=120)

    assert result.returncode == 0, result.stderr
    for rel in (manifest_rel, marketplace_rel):
        assert _read(str(tmp_path), rel) == _read(WORKSPACE_ROOT, rel), f"sync_agents.py rewrote {rel}"
    assert _json(str(tmp_path), manifest_rel)["hooks"] == "./hooks.json"
    names = [p["name"] for p in _json(str(tmp_path), marketplace_rel)["plugins"]]
    assert names.count("agent-metrics") == 1


# ----------------------------------------------------------------------------- wrapper behavior


def _fake_cli(directory, body):
    """Writes an executable `agent-meter` shell script into `directory`."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "agent-meter")
    with open(path, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\n" + body + "\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _recording_cli(directory, record_dir, stdout_noise="noise-on-stdout"):
    return _fake_cli(directory, (
        f'printf "%s\\n" "$@" > "{record_dir}/argv"\n'
        f'/bin/cat > "{record_dir}/stdin"\n'
        f'printf "{stdout_noise}"\n'
        "exit 3"
    ))


def _run_wrapper(base, args, tmp_path, *, path_dirs=(), stdin=b"{}", extra_env=None, timeout=20):
    env = {
        "PATH": os.pathsep.join(path_dirs) if path_dirs else str(tmp_path / "empty-bin"),
        "HOME": str(tmp_path / "home"),
    }
    env.update(extra_env or {})
    os.makedirs(tmp_path / "empty-bin", exist_ok=True)
    os.makedirs(tmp_path / "home", exist_ok=True)
    started = time.monotonic()
    result = subprocess.run(
        [NODE, os.path.join(base, WRAPPER_REL), *args],
        input=stdin, capture_output=True, env=env, timeout=timeout,
    )
    return result, time.monotonic() - started


CLAUDE_ARGS = ["--host", "claude-code", "--event", "task-end"]
AGY_ARGS = ["--host", "antigravity", "--event", "task-end"]


@needs_node
@pytest.mark.parametrize(
    "base, args, expected_stdout",
    [(CLAUDE_PLUGIN, CLAUDE_ARGS, b""), (AGY_PLUGIN, AGY_ARGS, b"{}\n")],
    ids=["claude", "antigravity"],
)
def test_missing_cli_exits_zero_with_stderr_hint(base, args, expected_stdout, tmp_path):
    result, _ = _run_wrapper(base, args, tmp_path, stdin=b'{"session_id": "s1"}')

    assert result.returncode == 0
    assert result.stdout == expected_stdout
    stderr_lines = result.stderr.decode().strip().splitlines()
    assert len(stderr_lines) == 1, result.stderr
    assert stderr_lines[0].startswith(INSTALL_HINT_PREFIX)
    assert stderr_lines[0] == f"{INSTALL_HINT_PREFIX}{REPO_URL}/blob/main/docs/agent-metrics/README.md"


@needs_node
@needs_posix
@pytest.mark.parametrize(
    "base, args, expected_stdout",
    [(CLAUDE_PLUGIN, CLAUDE_ARGS, b""), (AGY_PLUGIN, AGY_ARGS, b"{}\n")],
    ids=["claude", "antigravity"],
)
def test_forwards_args_and_stdin_and_ignores_cli_stdout_and_exit_code(base, args, expected_stdout, tmp_path):
    bin_dir, record = tmp_path / "bin", tmp_path / "record"
    record.mkdir()
    _recording_cli(str(bin_dir), str(record))
    payload = json.dumps({"session_id": "abc", "transcript_path": "/x/y.jsonl", "cwd": "/p"}).encode()

    result, _ = _run_wrapper(base, args, tmp_path, path_dirs=[str(bin_dir)], stdin=payload)

    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_stdout
    assert (record / "argv").read_text().splitlines() == ["hook", *args]
    assert (record / "stdin").read_bytes() == payload


def test_wrapper_never_prints_error_messages():
    # L-9 / ADR 3.13.3: stderr carries the error class or code only; messages may hold paths.
    source = _read(CLAUDE_PLUGIN, WRAPPER_REL)

    assert ".message" not in source
    assert "${cli}" not in source


@needs_node
@needs_posix
@pytest.mark.parametrize(
    "base, args, expected_stdout",
    [(CLAUDE_PLUGIN, CLAUDE_ARGS, b""), (AGY_PLUGIN, AGY_ARGS, b"{}\n")],
    ids=["claude", "antigravity"],
)
def test_spawn_failure_reports_code_only_without_paths(base, args, expected_stdout, tmp_path):
    # Arrange: an executable CLI whose interpreter is missing makes spawn fail with ENOENT and
    # an error.message that embeds the CLI path (here a private-looking directory name).
    private_dir = tmp_path / "PRIVATE-CLIENT-DIR-7f3a"
    _fake_cli(str(private_dir), "exit 0")
    script = private_dir / "agent-meter"
    script.write_text("#!/nonexistent/PRIVATE-INTERPRETER-7f3a\nexit 0\n", encoding="utf-8")

    # Act
    result, _ = _run_wrapper(base, args, tmp_path, path_dirs=(str(private_dir),))

    # Assert
    stderr = result.stderr.decode()
    assert result.returncode == 0
    assert result.stdout == expected_stdout
    assert "ENOENT" in stderr
    assert "PRIVATE" not in stderr and str(tmp_path) not in stderr


@needs_node
@needs_posix
def test_finds_cli_in_user_local_bin_when_not_on_path(tmp_path):
    record = tmp_path / "record"
    record.mkdir()
    _recording_cli(str(tmp_path / "home" / ".local" / "bin"), str(record))

    result, _ = _run_wrapper(CLAUDE_PLUGIN, CLAUDE_ARGS, tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert (record / "argv").read_text().splitlines() == ["hook", *CLAUDE_ARGS]


@needs_node
@needs_posix
@pytest.mark.parametrize(
    "base, args, expected_stdout",
    [(CLAUDE_PLUGIN, CLAUDE_ARGS, b""), (AGY_PLUGIN, AGY_ARGS, b"{}\n")],
    ids=["claude", "antigravity"],
)
def test_hung_cli_is_killed_at_timeout_and_wrapper_exits_zero(base, args, expected_stdout, tmp_path):
    bin_dir = tmp_path / "bin"
    _fake_cli(str(bin_dir), "exec /bin/sleep 30")

    result, elapsed = _run_wrapper(
        base, args, tmp_path, path_dirs=[str(bin_dir)],
        extra_env={"AGENT_METER_HOOK_TIMEOUT_MS": "300"},
    )

    assert result.returncode == 0
    assert result.stdout == expected_stdout
    assert elapsed < 5, f"wrapper did not enforce its timeout ({elapsed:.1f}s)"
    assert b"timed out" in result.stderr


@needs_node
@needs_posix
def test_stdin_that_never_closes_still_times_out(tmp_path):
    bin_dir = tmp_path / "bin"
    _fake_cli(str(bin_dir), "/bin/cat > /dev/null")
    (tmp_path / "home").mkdir()
    env = {"PATH": str(bin_dir), "HOME": str(tmp_path / "home"), "AGENT_METER_HOOK_TIMEOUT_MS": "300"}

    proc = subprocess.Popen(
        [NODE, os.path.join(AGY_PLUGIN, WRAPPER_REL), *AGY_ARGS],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    try:
        proc.stdin.write(b'{"conversationId": "c1"')  # partial payload, pipe left open
        proc.stdin.flush()
        returncode = proc.wait(timeout=5)  # output is tiny, so the stdout pipe cannot fill up
        stdout = proc.stdout.read()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            stream.close()

    assert returncode == 0
    assert stdout == b"{}\n"


@needs_node
@pytest.mark.parametrize("stdin", [b"", b"not json at all", b"\xff\xfe\x00"], ids=["empty", "garbage", "binary"])
def test_malformed_stdin_exits_zero(stdin, tmp_path):
    result, _ = _run_wrapper(AGY_PLUGIN, AGY_ARGS, tmp_path, stdin=stdin)

    assert result.returncode == 0
    assert result.stdout == b"{}\n"


@needs_node
@needs_posix
@pytest.mark.parametrize(
    "args",
    [[], ["--host", "bogus", "--event", "task-end"], ["--host", "antigravity", "--event", "session-end"],
     ["--host", "claude-code", "--event", "task-end", "--extra", "x"]],
    ids=["none", "unknown-host", "unsupported-event", "extra-args"],
)
def test_invalid_arguments_never_run_the_cli_and_exit_zero(args, tmp_path):
    bin_dir, record = tmp_path / "bin", tmp_path / "record"
    record.mkdir()
    _recording_cli(str(bin_dir), str(record))

    result, _ = _run_wrapper(CLAUDE_PLUGIN, args, tmp_path, path_dirs=[str(bin_dir)])

    assert result.returncode == 0
    assert not (record / "argv").exists(), "the CLI must not run with invalid arguments"
    assert b"invalid arguments" in result.stderr
