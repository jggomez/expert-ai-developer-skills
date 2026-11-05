"""Tests for skills/blackbox-tester/scripts/check_evidence.py.

The script is the deterministic proof behind an E2E `PASSED` verdict: the orchestrator and the
compliance-verifier run it instead of trusting the tester's report (Antigravity has no
SubagentStop hook to enforce this automatically).
"""
import json
import os
import struct
import subprocess
import sys
import time
import zlib

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(ROOT, "skills", "blackbox-tester", "scripts", "check_evidence.py")
VIEWPORT_WIDTHS = (375, 768, 1280, 1920)


def _png(width, height=10):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    raw = b"".join(b"\x00" + os.urandom(width * 3) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _request(url="http://localhost:3000/api/items", method="GET", status=200, resource="fetch", remote=True):
    return {"method": method, "url": url, "status": status, "resourceType": resource, "remote": remote}


def _manifest(**overrides):
    return {"version": 1, "pages": ["http://localhost:3000/"], "requests": [_request()],
            "dataChecks": [{"kind": "source-on-screen", "detail": "item 42 from the API is listed"}], **overrides}


def _write_manifest(evidence, name="run-a.json", **overrides):
    (evidence / name).write_text(json.dumps(_manifest(**overrides)))


def _write_set(evidence, widths=VIEWPORT_WIDTHS, scale=1, manifest=True):
    evidence.mkdir(parents=True, exist_ok=True)
    for w in widths:
        (evidence / f"home-{w}.png").write_bytes(_png(w * scale))
    if manifest:
        _write_manifest(evidence)


def _run(*args):
    return subprocess.run([sys.executable, SCRIPT, *map(str, args)], capture_output=True, text=True, timeout=30)


def test_passes_with_a_real_screenshot_per_viewport(tmp_path):
    # Arrange
    evidence = tmp_path / "docs" / "login" / "evidence"
    _write_set(evidence)
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_accepts_retina_screenshots(tmp_path):
    # Arrange: deviceScaleFactor 2 doubles the pixel width
    evidence = tmp_path / "evidence"
    _write_set(evidence, scale=2)
    # Act / Assert
    assert _run(evidence).returncode == 0


def test_fails_when_the_directory_is_missing(tmp_path):
    # Act
    result = _run(tmp_path / "nope")
    # Assert
    assert result.returncode == 1 and "FAIL" in result.stdout


def test_fails_when_a_viewport_is_missing(tmp_path):
    # Arrange
    evidence = tmp_path / "evidence"
    _write_set(evidence, widths=(375, 768, 1280))
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1 and "1920" in result.stdout


def test_fails_on_fake_png_files(tmp_path):
    # Arrange: a hallucinated "screenshot" is just text with a .png name
    evidence = tmp_path / "evidence"
    _write_set(evidence, widths=(375, 768, 1280))
    (evidence / "home-1920.png").write_text("screenshot of the home page at 1920px" * 10)
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1 and "not a real PNG" in result.stdout


def test_fails_on_stale_screenshots(tmp_path):
    # Arrange
    evidence = tmp_path / "evidence"
    _write_set(evidence)
    old = time.time() - 3 * 3600
    for png in evidence.iterdir():
        os.utime(png, (old, old))
    # Act
    stale = _run(evidence, "--max-age-minutes", 60)
    no_age_check = _run(evidence, "--max-age-minutes", 0)
    # Assert
    assert stale.returncode == 1 and "older than 60" in stale.stdout
    assert no_age_check.returncode == 0


def test_script_is_bundled_wherever_the_skill_is():
    # Arrange
    import glob
    skill_dirs = glob.glob(os.path.join(ROOT, "plugins", "*", "*", "skills", "blackbox-tester"))
    # Act
    missing = [d for d in skill_dirs if not os.path.isfile(os.path.join(d, "scripts", "check_evidence.py"))]
    # Assert
    assert len(skill_dirs) >= 4 and not missing, f"run scripts/sync_plugin_skills.py: {missing}"


def test_screenshots_without_a_run_manifest_fail(tmp_path):
    # Arrange
    evidence = tmp_path / "evidence"
    _write_set(evidence, manifest=False)
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1
    assert "manifest" in result.stdout


def test_a_broken_manifest_fails(tmp_path):
    # Arrange
    evidence = tmp_path / "evidence"
    _write_set(evidence, manifest=False)
    (evidence / "run-a.json").write_text("{not json")
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1


def test_a_run_with_no_real_data_request_fails(tmp_path):
    # Arrange: only static files were loaded, so the screen cannot show data from a source
    evidence = tmp_path / "evidence"
    _write_set(evidence, manifest=False)
    _write_manifest(evidence, requests=[_request("http://localhost:3000/assets/FontManifest.json"),
                                        _request("http://localhost:3000/main.js", resource="script")])
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1
    assert "data request" in result.stdout


@pytest.mark.parametrize("request_overrides", [{"remote": False}, {"status": 500}])
def test_a_stubbed_or_failed_data_request_does_not_count(tmp_path, request_overrides):
    # Arrange
    evidence = tmp_path / "evidence"
    _write_set(evidence, manifest=False)
    _write_manifest(evidence, requests=[_request(**request_overrides)])
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1


def test_a_run_that_never_compared_data_with_its_source_fails(tmp_path):
    # Arrange
    evidence = tmp_path / "evidence"
    _write_set(evidence, manifest=False)
    _write_manifest(evidence, dataChecks=[])
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1
    assert "source-on-screen" in result.stdout


def test_a_write_flow_must_prove_it_persisted(tmp_path):
    # Arrange
    evidence = tmp_path / "evidence"
    _write_set(evidence, manifest=False)
    _write_manifest(evidence, requests=[_request(), _request(method="POST", status=201)])
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1
    assert "persisted-after-reload" in result.stdout


def test_a_write_flow_with_persistence_proof_passes(tmp_path):
    # Arrange
    evidence = tmp_path / "evidence"
    _write_set(evidence, manifest=False)
    _write_manifest(evidence, requests=[_request(), _request(method="POST", status=201)],
                    dataChecks=[{"kind": "source-on-screen", "detail": "a"},
                                {"kind": "persisted-after-reload", "detail": "b"}])
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 0, result.stdout


def test_several_manifests_are_merged(tmp_path):
    # Arrange: one test file per journey, each writing its own manifest
    evidence = tmp_path / "evidence"
    _write_set(evidence, manifest=False)
    _write_manifest(evidence, "run-a.json", dataChecks=[])
    _write_manifest(evidence, "run-b.json", requests=[])
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 0, result.stdout


def test_network_stubs_in_the_e2e_tests_fail(tmp_path):
    # Arrange
    evidence = tmp_path / "docs" / "items" / "evidence"
    _write_set(evidence)
    (tmp_path / ".git").mkdir()
    spec = tmp_path / "tests" / "e2e" / "items.spec.ts"
    spec.parent.mkdir(parents=True)
    spec.write_text("await page.route('**/api/items', (r) => r.fulfill({ json: [] }));\n")
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1
    assert "items.spec.ts" in result.stdout


def test_an_undeclared_screen_without_data_source_fails(tmp_path):
    # Arrange
    evidence = tmp_path / "docs" / "about" / "evidence"
    _write_set(evidence, manifest=False)
    (tmp_path / ".git").mkdir()
    _write_manifest(evidence, requests=[], dataChecks=[], noDataSource="static about page")
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 1
    assert "data-source: none" in result.stdout


def test_a_screen_declared_without_data_source_in_the_plan_passes(tmp_path):
    # Arrange
    evidence = tmp_path / "docs" / "about" / "evidence"
    _write_set(evidence, manifest=False)
    (tmp_path / ".git").mkdir()
    (tmp_path / "PLAN.md").write_text("| About | data-source: none |\n")
    _write_manifest(evidence, requests=[], dataChecks=[], noDataSource="static about page")
    # Act
    result = _run(evidence)
    # Assert
    assert result.returncode == 0, result.stdout


def test_a_demo_needs_approval_in_the_plan(tmp_path):
    # Arrange
    evidence = tmp_path / "docs" / "demo" / "evidence"
    _write_set(evidence, manifest=False)
    (tmp_path / ".git").mkdir()
    _write_manifest(evidence, requests=[], dataChecks=[], demo=True)
    # Act
    rejected = _run(evidence)
    (tmp_path / "PLAN.md").write_text("| Users | src/Demo.tsx | demo-data: approved |\n")
    approved = _run(evidence)
    # Assert
    assert rejected.returncode == 1
    assert approved.returncode == 0, approved.stdout


def test_latest_picks_the_newest_evidence_directory(tmp_path):
    # Arrange
    (tmp_path / ".git").mkdir()
    old = tmp_path / "docs" / "old" / "evidence"
    _write_set(old, manifest=False)
    new = tmp_path / "docs" / "new" / "evidence"
    _write_set(new)
    stale = time.time() - 3600
    for item in old.iterdir():
        os.utime(item, (stale, stale))
    # Act
    result = subprocess.run([sys.executable, SCRIPT, "--latest", "--root", str(tmp_path)], capture_output=True,
                            text=True, timeout=30)
    # Assert
    assert result.returncode == 0, result.stdout
    assert "new" in result.stdout


def test_latest_without_evidence_fails(tmp_path):
    # Act
    result = subprocess.run([sys.executable, SCRIPT, "--latest", "--root", str(tmp_path)], capture_output=True,
                            text=True, timeout=30)
    # Assert
    assert result.returncode == 1
    assert "no evidence" in result.stdout


def test_evidence_older_than_the_last_ui_change_fails(tmp_path):
    # Arrange
    evidence = tmp_path / "evidence"
    _write_set(evidence)
    # Act
    result = _run(evidence, "--min-mtime", time.time() + 60)
    # Assert
    assert result.returncode == 1
    assert "before the last change" in result.stdout
