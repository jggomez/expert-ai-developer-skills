"""Tests for skills/blackbox-tester/scripts/check_evidence.py.

The script is the deterministic proof behind an E2E `PASSED` verdict: the orchestrator and the
compliance-verifier run it instead of trusting the tester's report (Antigravity has no
SubagentStop hook to enforce this automatically).
"""
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


def _write_set(evidence, widths=VIEWPORT_WIDTHS, scale=1):
    evidence.mkdir(parents=True, exist_ok=True)
    for w in widths:
        (evidence / f"home-{w}.png").write_bytes(_png(w * scale))


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
