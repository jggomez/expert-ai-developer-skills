"""Track 34: orchestrators stay lean and dispatch parallel work without workers colliding.

A well-specified multi-phase request must not run the full Tier 3 ceremony per phase, must not
grow scope, and parallel implementers must never share files, git index or codegen runs.
Worktree facts verified against the official docs (2026-11-02):
- Claude Code subagent worktrees branch from the default branch unless worktree.baseRef="head".
- Antigravity invoke_subagent workspaces: inherit | branch | share (branch base is undocumented).
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ORCHESTRATORS = [
    ("senior-dev", "senior-dev-orchestrator"),
    ("senior-dev-flutter", "flutter-feature-orchestrator"),
    ("python-backend", "python-backend-orchestrator"),
]
REQUIRED_RULES = [
    "### Lean Execution Defaults",
    "Scale alone never makes a task Tier 3",
    "**Scope discipline**",
    "**Multi-phase requests**",
    "### Safe Parallel Dispatch",
    "**Contract first**",
    "at most 3 implementers",
    "never run git writes",
    '"baseRef": "head"',
    "git merge-base --is-ancestor",
]


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("host", ["antigravity", "claude"])
@pytest.mark.parametrize("plugin,agent", ORCHESTRATORS)
def test_orchestrators_carry_the_lean_and_parallel_rules(host, plugin, agent):
    # Arrange
    body = _read("plugins", host, plugin, "agents", f"{agent}.md")
    # Act
    missing = [rule for rule in REQUIRED_RULES if rule not in body]
    # Assert
    assert not missing, f"{host}/{plugin}/{agent}.md is missing: {missing}"
    assert "Workspace: 'share'" not in body, "'share' semantics are undocumented; Mode B uses 'branch'"


def test_loop_engineering_skill_documents_the_protocol_without_fake_flags():
    # Arrange
    skill = _read("skills", "loop-engineering", "SKILL.md")
    # Act / Assert
    assert "--tasks" not in skill, "run_parallel_agents.py has no --tasks flag"
    for rule in ("### Safe Parallel Dispatch", "**Contract first**", '"baseRef": "head"',
                 "git merge-base --is-ancestor", "**Multi-phase requests**"):
        assert rule in skill, rule


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    main = tmp_path / "app"
    main.mkdir()
    _git(main, "init", "-q", "-b", "main")
    _git(main, "config", "user.email", "t@example.com")
    _git(main, "config", "user.name", "t")
    (main / "lib.py").write_text("x = 1\n")
    _git(main, "add", ".")
    _git(main, "commit", "-qm", "init")
    _git(main, "checkout", "-qb", "feat/x")
    return main


def test_parallel_worktree_script_requires_a_task_file(repo):
    # Arrange: run without arguments, as an agent following an old instruction might
    script = os.path.join(ROOT, "skills", "loop-engineering", "scripts", "run_parallel_agents.py")
    # Act
    result = subprocess.run([sys.executable, script], cwd=repo, capture_output=True, text=True, timeout=30)
    # Assert: no example worktrees are created and no PR is suggested
    assert result.returncode == 2
    assert "usage" in (result.stdout + result.stderr).lower()
    assert _git(repo, "worktree", "list").stdout.count("\n") == 1
    assert "draft PR" not in open(script, encoding="utf-8").read()


def test_parallel_worktree_script_branches_from_current_head(repo, tmp_path):
    # Arrange
    tasks = tmp_path / "tasks.json"
    tasks.write_text(json.dumps([{"task_name": "a", "branch_name": "feat/x-a", "instruction": "do a"}]))
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    script = os.path.join(ROOT, "skills", "loop-engineering", "scripts", "run_parallel_agents.py")
    # Act
    result = subprocess.run([sys.executable, script, str(tasks)], cwd=repo, capture_output=True, text=True,
                            timeout=30)
    # Assert
    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(repo, "rev-parse", "feat/x-a").stdout.strip() == head
    assert "commit" in result.stdout and "Do not push" in result.stdout


needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _worktree_without_plan(repo):
    # PLAN.md is untracked in the main checkout, so a fresh worktree does not contain it
    (repo / "PLAN.md").write_text("# plan\n")
    wt = repo.parent / "wt-a"
    _git(repo, "worktree", "add", "-q", "-b", "feat/x-a", str(wt))
    return wt


@needs_node
def test_find_plan_looks_in_the_main_checkout_from_a_worktree(repo):
    # Arrange
    wt = _worktree_without_plan(repo)
    lib = os.path.join(ROOT, "scripts", "hook-lib", "gate-utils.js")
    script = f"const g = require({json.dumps(lib)}); process.stdout.write(JSON.stringify([g.findPlan(process.argv[1]), g.findPlan(process.argv[2])]));"
    other = repo.parent / "no-plan"
    other.mkdir()
    # Act
    out = subprocess.run(["node", "-e", script, str(wt), str(other)], capture_output=True, text=True, check=True)
    found, missing = json.loads(out.stdout)
    # Assert
    assert found == os.path.realpath(repo / "PLAN.md") or found == str(repo / "PLAN.md")
    assert missing is None


@needs_node
@pytest.mark.parametrize("gate", [
    "senior-dev/hooks/orchestrator-role-gate.js",
    "senior-dev-flutter/hooks/flutter-pre-tool-gate.js",
    "python-backend/hooks/pre-tool-gate.js",
    "senior-data-engineer/hooks/data-safety-gate.js",
])
def test_claude_plan_first_gates_allow_worktree_implementers(repo, gate):
    # Arrange: a subagent in a worktree writes a whole new file (not a small edit)
    wt = _worktree_without_plan(repo)
    (wt / "pubspec.yaml").write_text("name: demo\n")
    ext = {"senior-dev-flutter": "dart", "senior-data-engineer": "sql"}.get(gate.split("/")[0], "py")
    target = wt / "lib" / f"feature.{ext}"
    payload = {"hook_event_name": "PreToolUse", "cwd": str(wt), "agent_type": "code-implementer",
               "tool_name": "Write", "tool_input": {"file_path": str(target), "content": "x\n" * 30}}
    # Act
    result = subprocess.run(["node", os.path.join(ROOT, "plugins", "claude", gate)], input=json.dumps(payload),
                            capture_output=True, text=True, timeout=30)
    # Assert
    assert result.returncode == 0, result.stderr
    assert "PLAN" not in (result.stdout + result.stderr), result.stdout + result.stderr
