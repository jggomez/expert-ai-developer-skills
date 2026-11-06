"""Build the unsigned desktop app for this machine: a ``.dmg`` on macOS and an ``.exe`` on Windows.

Run from ``tools/agent-meter`` with the ``app`` extra and PyInstaller installed. Mac and Windows
apps can only be built on their own system, so CI runs this once per platform.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final

from agent_meter import __version__
from agent_meter.app.desktop import SELF_TEST_FLAG
from agent_meter.paths import HOME_ENV

NAME: Final = "agent-meter"
SELF_TEST_TIMEOUT_S: Final = 180
ROOT: Final = Path(__file__).resolve().parent.parent
DIST: Final = ROOT / "dist"
COMMON: Final = (
    "--noconfirm", "--clean", "--windowed", "--name", NAME,
    "--collect-data", "agent_meter", "--collect-all", "duckdb", "--collect-all", "tzdata",
    "--collect-all", "pytz",  # DuckDB imports it at run time, so PyInstaller cannot see it
    "--copy-metadata", NAME, "--distpath", str(DIST), "--workpath", str(ROOT / "build"),
    "--specpath", str(ROOT / "build"),
)


def artifact_label() -> str:
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}[platform.machine().lower()]
    return f"{NAME}-{__version__}-{'mac' if sys.platform == 'darwin' else 'windows'}-{arch}"


def self_test(binary: Path) -> None:
    """Exercises the bundle without a window, because a missing module only fails when used."""
    with tempfile.TemporaryDirectory() as home:
        subprocess.run([str(binary), SELF_TEST_FLAG], check=True, timeout=SELF_TEST_TIMEOUT_S, env={**os.environ, HOME_ENV: home})


def build(extra: tuple[str, ...]) -> None:
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", *COMMON, *extra, str(ROOT / "packaging" / "desktop_entry.py")],
        check=True, cwd=ROOT,
    )


def build_mac() -> Path:
    build(("--osx-bundle-identifier", "dev.agent-meter.app"))
    self_test(DIST / f"{NAME}.app" / "Contents" / "MacOS" / NAME)
    stage = DIST / "dmg"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir()
    shutil.move(DIST / f"{NAME}.app", stage / f"{NAME}.app")
    (stage / "Applications").symlink_to("/Applications")
    target = DIST / f"{artifact_label()}.dmg"
    target.unlink(missing_ok=True)
    subprocess.run(["hdiutil", "create", "-volname", NAME, "-srcfolder", str(stage), "-format", "UDZO", str(target)], check=True)
    return target


def build_windows() -> Path:
    build(("--onefile", "--collect-submodules", "pystray"))
    self_test(DIST / f"{NAME}.exe")
    target = DIST / f"{artifact_label()}.exe"
    target.unlink(missing_ok=True)
    (DIST / f"{NAME}.exe").rename(target)
    return target


def main() -> int:
    if sys.platform == "darwin":
        target = build_mac()
    elif sys.platform == "win32":
        target = build_windows()
    else:
        print("the desktop app is built on macOS and Windows only", file=sys.stderr)
        return 1
    print(f"built {target} ({target.stat().st_size // 1_000_000} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
