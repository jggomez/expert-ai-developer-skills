"""Unit tests for the shared-context plugin core scripts.

Covers the host-agnostic layer (Phase 1): session scaffolding, secret
redaction, compress/decompress round-trip, decision rollup idempotency,
retention archiving, and the read-only listing used by the hooks.
"""
import json
import os
import subprocess
import sys

CAPTURE = os.path.abspath("skills/context-capture/scripts")
RESTORE = os.path.abspath("skills/context-restore/scripts")
SNAPSHOT = os.path.join(CAPTURE, "context_snapshot.py")
PACK = os.path.join(CAPTURE, "context_pack.py")
ROLLUP = os.path.join(CAPTURE, "context_rollup.py")
LIST = os.path.join(RESTORE, "context_list.py")


def run(script, *args, cwd=None):
    return subprocess.run(
        [sys.executable, script, *args],
        capture_output=True, text=True, cwd=cwd,
    )


def snapshot(ctx, *args):
    return run(SNAPSHOT, "--context-dir", str(ctx), "--no-git", *args)


def test_scripts_exist():
    for path in (SNAPSHOT, PACK, ROLLUP, LIST,
                 os.path.join(CAPTURE, "context_common.py")):
        assert os.path.exists(path), f"missing {path}"


def test_snapshot_creates_session_and_index(tmp_path):
    ctx = tmp_path / "context"
    res = snapshot(ctx, "--session", "s1", "--task", "do the thing",
                   "--agent", "claude-sonnet-5", "--host", "claude-code", "--json")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert out["created"] is True
    sdir = tmp_path / "context" / out["dir"].split("/context/")[-1]

    for name in ("manifest.json", "summary.md", "decisions.md",
                 "flows.md", "topics.md", "files-touched.json"):
        assert (sdir / name).exists(), f"{name} not scaffolded"

    manifest = json.loads((sdir / "manifest.json").read_text())
    assert manifest["session"] == "s1"
    assert manifest["task"] == "do the thing"
    assert manifest["host"] == "claude-code"
    assert manifest["status"] == "in-progress"

    index = (ctx / "INDEX.md").read_text()
    assert "s1" in index and "do the thing" in index
    assert (ctx / ".contextrc.json").exists()
    assert (ctx / ".gitattributes").exists()
    assert ".session-state.json" in (ctx / ".gitignore").read_text()


def test_snapshot_update_keeps_markdown(tmp_path):
    ctx = tmp_path / "context"
    snapshot(ctx, "--session", "s1")
    sdir = next((ctx).glob("*/s1"))
    (sdir / "summary.md").write_text("# custom summary\n\nagent wrote this\n")

    res = snapshot(ctx, "--session", "s1", "--status", "done", "--model", "opus")
    assert res.returncode == 0, res.stderr
    assert "agent wrote this" in (sdir / "summary.md").read_text()
    manifest = json.loads((sdir / "manifest.json").read_text())
    assert manifest["status"] == "done"
    assert manifest["model"] == "opus"


def test_snapshot_redacts_secrets(tmp_path):
    ctx = tmp_path / "context"
    leak = 'api_key="AKIAIOSFODNN7EXAMPLE1"'
    res = snapshot(ctx, "--session", "s1", "--task", f"wire up {leak}", "--json")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert out["redactions"], "expected at least one redaction"

    sdir = next((ctx).glob("*/s1"))
    manifest_raw = (sdir / "manifest.json").read_text()
    assert "AKIAIOSFODNN7EXAMPLE1" not in manifest_raw
    assert "REDACTED" in manifest_raw


def test_snapshot_no_redact_flag(tmp_path):
    ctx = tmp_path / "context"
    res = snapshot(ctx, "--session", "s1", "--task", "AKIA1234567890ABCDEF",
                   "--no-redact", "--json")
    out = json.loads(res.stdout)
    assert out["redactions"] == []
    sdir = next((ctx).glob("*/s1"))
    assert "AKIA1234567890ABCDEF" in (sdir / "manifest.json").read_text()


def test_pack_unpack_round_trip(tmp_path):
    ctx = tmp_path / "context"
    snapshot(ctx, "--session", "s1")
    sdir = next((ctx).glob("*/s1"))
    flows_before = "# flow\n\n1. tried X, it broke\n2. did Y instead\n"
    (sdir / "flows.md").write_text(flows_before)

    res = run(PACK, "--context-dir", str(ctx), "--pack", "s1", "--json")
    assert res.returncode == 0, res.stderr
    assert (sdir / "detail.tar.xz").exists()
    assert not (sdir / "flows.md").exists()
    assert not (sdir / "topics.md").exists()
    # loose "what/why" files stay
    assert (sdir / "manifest.json").exists()
    assert (sdir / "summary.md").exists()
    assert (sdir / "decisions.md").exists()

    res = run(PACK, "--context-dir", str(ctx), "--unpack", "s1", "--json")
    assert res.returncode == 0, res.stderr
    assert not (sdir / "detail.tar.xz").exists()
    assert (sdir / "flows.md").read_text() == flows_before


def test_pack_auto_keeps_newest(tmp_path):
    ctx = tmp_path / "context"
    for i in range(4):
        snapshot(ctx, "--session", f"2024-01-0{i+1}-s")  # session id sorts by name
    # place them under distinct date dirs so "newest" is well defined
    res = run(PACK, "--context-dir", str(ctx), "--auto",
              "--keep-uncompressed", "2", "--json")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    packed = [r for r in out["results"] if r["archive"]]
    assert len(packed) == 2, out


def test_rollup_is_idempotent(tmp_path):
    ctx = tmp_path / "context"
    snapshot(ctx, "--session", "s1")
    snapshot(ctx, "--session", "s2")
    for sid, text in (("s1", "- **Use tar.xz** — stdlib, good ratio\n"),
                      ("s2", "- **Commit context/** — shared via git\n")):
        sdir = next((ctx).glob(f"*/{sid}"))
        (sdir / "decisions.md").write_text(f"# Decisions\n\n{text}")

    r1 = run(ROLLUP, "--context-dir", str(ctx), "--json")
    assert r1.returncode == 0, r1.stderr
    arch = (ctx / "architecture.md").read_text()
    assert "Use tar.xz" in arch and "Commit context/" in arch
    assert json.loads(r1.stdout)["decisionsAdded"]

    r2 = run(ROLLUP, "--context-dir", str(ctx), "--json")
    assert json.loads(r2.stdout)["decisionsAdded"] == [], "rollup added duplicates"
    assert (ctx / "architecture.md").read_text().count("Use tar.xz") == 1


def test_rollup_retention_archives_old_sessions(tmp_path):
    ctx = tmp_path / "context"
    (ctx).mkdir()
    (ctx / ".contextrc.json").write_text(json.dumps({"retention": {"maxSessions": 1, "maxAgeDays": 3650}}))
    for sid in ("2024-01-01-a", "2024-01-02-b", "2024-01-03-c"):
        snapshot(ctx, "--session", sid)

    res = run(ROLLUP, "--context-dir", str(ctx), "--json")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert len(out["sessionsArchived"]) == 2, out

    archived_dir = next((ctx).glob("*/2024-01-01-a"))
    assert (archived_dir / "full.tar.xz").exists()
    assert (archived_dir / "manifest.json").exists()  # kept for INDEX
    assert not (archived_dir / "summary.md").exists()


def test_context_list_empty_and_populated(tmp_path):
    ctx = tmp_path / "context"
    res = run(LIST, "--context-dir", str(ctx), "--json")
    assert res.returncode == 0
    assert json.loads(res.stdout)["exists"] is False

    snapshot(ctx, "--session", "s1", "--task", "first task", "--agent", "gemini-pro")
    res = run(LIST, "--context-dir", str(ctx), "--json")
    out = json.loads(res.stdout)
    assert out["exists"] is True
    assert out["count"] == 1
    assert out["sessions"][0]["agent"] == "gemini-pro"
    assert out["sessions"][0]["task"] == "first task"


def test_context_list_human_output_no_context(tmp_path):
    res = run(LIST, "--context-dir", str(tmp_path / "nope"))
    assert res.returncode == 0
    assert "No shared context" in res.stdout
