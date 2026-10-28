"""Decoupling invariants for the optional agent-meter add-on (PLAN.md Track 11, DC-01..04).

agent-meter is opt-in: no existing plugin or canonical skill may reference,
bundle or depend on it, and the package under tools/agent-meter must install
and pass its own suite with no repo checkout around it.
"""
import importlib.util
import os
import re
import shutil
import subprocess

import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACKAGE_DIR = os.path.join(WORKSPACE_ROOT, "tools", "agent-meter")
MENTION = re.compile(r"agent[-_]meter|agent-metrics")

# Where agent-meter / agent-metrics may be mentioned (DC-01).
ALLOWED_PREFIXES = (
    "tools/agent-meter/",
    "plugins/claude/agent-metrics/",
    "plugins/antigravity/agent-metrics/",
    "skills/agent-metrics/",
    "docs/agent-metrics/",
)
ALLOWED_FILES = {
    "PLAN.md",
    "README.md",
    "skills/README.md",
    "plugins/README.md",
    ".claude-plugin/marketplace.json",
    "scripts/sync_plugin_skills.py",
    "scripts/sync_agents.py",
    "tests/structure/test_agent_metrics_plugin.py",
    "tests/structure/test_agent_meter_decoupling.py",
}
OWN_PLUGIN_DIRS = ("plugins/claude/agent-metrics/", "plugins/antigravity/agent-metrics/")
TRACK_PATHS = ("tools/agent-meter", "skills/agent-metrics", "docs/agent-metrics", *OWN_PLUGIN_DIRS)

needs_git = pytest.mark.skipif(
    shutil.which("git") is None or not os.path.isdir(os.path.join(WORKSPACE_ROOT, ".git")),
    reason="git checkout not available",
)


def _git(*args):
    result = subprocess.run(
        ["git", "-C", WORKSPACE_ROOT, *args], capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def _repo_files():
    """Tracked files plus untracked, non-ignored files (the would-be-committed tree)."""
    return sorted(set(_git("ls-files")) | set(_git("ls-files", "--others", "--exclude-standard")))


def _is_allowed(rel):
    return rel in ALLOWED_FILES or rel.startswith(ALLOWED_PREFIXES)


def _outside_own_plugins(paths):
    return sorted(p for p in paths if p.startswith("plugins/") and not p.startswith(OWN_PLUGIN_DIRS))


@needs_git
def test_dc01_no_file_outside_the_track_mentions_agent_meter():
    offenders = []
    for rel in _repo_files():
        if _is_allowed(rel):
            continue
        path = os.path.join(WORKSPACE_ROOT, rel)
        if not os.path.isfile(path):
            continue  # deleted in the working tree
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            continue  # binary file
        if MENTION.search(text):
            offenders.append(rel)
    assert not offenders, "agent-meter must stay opt-in; unexpected references in:\n" + "\n".join(offenders)


def _load_sync_plugin_skills():
    spec = importlib.util.spec_from_file_location(
        "sync_plugin_skills", os.path.join(WORKSPACE_ROOT, "scripts", "sync_plugin_skills.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dc02_skill_is_bundled_only_into_the_agent_metrics_plugin():
    mapping = _load_sync_plugin_skills().PLUGIN_BUNDLED_SKILLS
    assert mapping.get("agent-metrics") == ["agent-metrics"]
    others = sorted(p for p, skills in mapping.items() if p != "agent-metrics" and "agent-metrics" in skills)
    assert not others, f"agent-metrics skill must not be bundled into: {others}"

    on_disk = []
    for ecosystem in ("claude", "antigravity"):
        root = os.path.join(WORKSPACE_ROOT, "plugins", ecosystem)
        for plugin in sorted(os.listdir(root)):
            if os.path.isdir(os.path.join(root, plugin, "skills", "agent-metrics")):
                on_disk.append(f"{ecosystem}/{plugin}")
    assert sorted(on_disk) == ["antigravity/agent-metrics", "claude/agent-metrics"], (
        f"agent-metrics skill bundled in: {on_disk}"
    )


@needs_git
def test_dc04_track_commits_touch_no_existing_plugin():
    """Every commit that touches agent-meter paths leaves the other plugins alone."""
    offenders = {}
    for commit in _git("log", "--format=%H", "--", *TRACK_PATHS):
        touched = _outside_own_plugins(_git("show", "--name-only", "--format=", commit, "--", "plugins/"))
        if touched:
            offenders[commit[:10]] = touched
    assert not offenders, f"agent-meter commits modified existing plugins: {offenders}"


@needs_git
def test_dc04_uncommitted_track_work_touches_no_existing_plugin():
    """While the track is uncommitted, the working tree differs from HEAD only in its own dirs."""
    pending_track_work = _git("status", "--porcelain", "--untracked-files=all", "--", *TRACK_PATHS)
    if not pending_track_work:
        pytest.skip("no uncommitted agent-meter work; covered by the commit-scoped check")
    changed = set(_git("diff", "--name-only", "HEAD", "--", "plugins/"))
    changed |= set(_git("ls-files", "--others", "--exclude-standard", "--", "plugins/"))
    assert not _outside_own_plugins(changed), f"existing plugins changed: {_outside_own_plugins(changed)}"


_COPY_IGNORE = shutil.ignore_patterns(
    ".venv", "__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache", ".ruff_cache", "*.egg-info", "dist", "build"
)


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not available")
@pytest.mark.skipif(
    os.environ.get("AGENT_METER_RUN_DC03") != "1",
    reason="slow, disk-heavy clean-venv install; set AGENT_METER_RUN_DC03=1 to run",
)
def test_dc03_package_installs_and_passes_in_a_clean_venv_without_the_repo(tmp_path):
    """Copies tools/agent-meter alone to a temp dir and runs its default suite in a fresh venv."""
    isolated = tmp_path / "agent-meter"
    shutil.copytree(PACKAGE_DIR, isolated, ignore=_COPY_IGNORE)

    env = {k: v for k, v in os.environ.items() if not k.startswith(("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"))}
    env["UV_PROJECT_ENVIRONMENT"] = str(tmp_path / "venv")  # brand-new venv, never the repo's
    result = subprocess.run(
        ["uv", "run", "--frozen", "--python", "3.11", "--extra", "dev",
         "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=isolated, env=env, capture_output=True, text=True, timeout=900,
    )

    tail = "\n".join((result.stdout + result.stderr).splitlines()[-15:])
    assert result.returncode == 0, f"clean-venv run failed:\n{tail}"
    assert re.search(r"\d+ passed", result.stdout), tail
