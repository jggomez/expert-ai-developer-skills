"""Unit tests for flutter_project_audit.py (senior-dev-flutter plugin).

The script reads files only — no `flutter`/`dart` binary — so these run
anywhere.
"""
import json
import os
import subprocess
import sys

SCRIPT = os.path.abspath(
    "skills/flutter-review-checklist/scripts/flutter_project_audit.py")


def run(project_dir, *args):
    return subprocess.run(
        [sys.executable, SCRIPT, str(project_dir), *args],
        capture_output=True, text=True,
    )


def make_project(root, *, pubspec=None, analysis=None, lib=None, tests=True,
                 ci=None, gradle=None):
    root.mkdir(parents=True, exist_ok=True)
    (root / "pubspec.yaml").write_text(pubspec if pubspec is not None else (
        "name: demo\n"
        "environment:\n  sdk: '>=3.5.0 <4.0.0'\n  flutter: '>=3.24.0'\n"
        "dependencies:\n  flutter:\n    sdk: flutter\n"
        "dev_dependencies:\n  flutter_lints: ^4.0.0\n"
        "flutter:\n  uses-material-design: true\n"
    ))
    if analysis is not None:
        (root / "analysis_options.yaml").write_text(analysis)
    libdir = root / "lib"
    libdir.mkdir(exist_ok=True)
    (libdir / "main.dart").write_text(lib if lib is not None else "void main() {}\n")
    if tests:
        (root / "test").mkdir(exist_ok=True)
        (root / "test" / "widget_test.dart").write_text("void main() {}\n")
    if ci is not None:
        wf = root / ".github" / "workflows"
        wf.mkdir(parents=True, exist_ok=True)
        (wf / "ci.yml").write_text(ci)
    if gradle is not None:
        gd = root / "android" / "app"
        gd.mkdir(parents=True, exist_ok=True)
        (gd / "build.gradle").write_text(gradle)


def test_not_a_flutter_project(tmp_path):
    r = run(tmp_path)
    assert r.returncode == 0            # advisory: no crash
    assert "not a Dart/Flutter project" in r.stdout
    r = run(tmp_path, "--strict")
    assert r.returncode == 1            # strict: block finding -> non-zero


def test_healthy_project_reports_ok(tmp_path):
    p = tmp_path / "app"
    make_project(
        p,
        analysis="include: package:flutter_lints/flutter.yaml\n"
                 "analyzer:\n  language:\n    strict-casts: true\n",
        ci="jobs:\n  t:\n    steps:\n      - run: flutter test --coverage\n",
        gradle="android { productFlavors { dev {} prod {} } }\n",
    )
    out = json.loads(run(p, "--json").stdout)
    s = out["summary"]
    assert s["isFlutterProject"] is True
    assert s["dartSdk"] == ">=3.5.0 <4.0.0"
    assert s["lintPackages"] == ["flutter_lints"]
    assert s["testFiles"] == 1
    assert s["ciCoverage"] is True
    assert s["androidFlavors"] is True
    assert s["printsInLib"] == 0
    assert s["possibleSecrets"] == 0
    levels = {f["level"] for f in out["findings"]}
    assert "block" not in levels


def test_flags_missing_tests_prints_and_loose_deps(tmp_path):
    p = tmp_path / "app"
    make_project(
        p,
        pubspec="name: demo\nenvironment:\n  sdk: '>=3.5.0 <4.0.0'\n"
                "dependencies:\n  flutter:\n    sdk: flutter\n  http: any\n",
        lib='void main() { print("debug"); }\n',
        tests=False,
    )
    out = json.loads(run(p, "--json").stdout)
    msgs = {f["level"]: [] for f in out["findings"]}
    for f in out["findings"]:
        msgs.setdefault(f["level"], []).append(f["message"])
    assert any("no test/ directory" in m for m in msgs.get("block", []))
    assert any("print()" in m for m in msgs.get("warn", []))
    assert any("unpinned (`any`)" in m for m in msgs.get("warn", []))
    assert out["summary"]["printsInLib"] == 1
    # --strict exits non-zero because "no tests" is a block finding
    assert run(p, "--strict").returncode == 1


def test_detects_hardcoded_secret_in_lib(tmp_path):
    p = tmp_path / "app"
    # A name-keyed assignment of a 16+ char token — deliberately an obvious
    # placeholder so it trips the audit's heuristic without being a real secret
    # shape (no vendor prefix / low entropy).
    fake = "PLACEHOLDER_do_not_ship_" + "x" * 12
    make_project(p, lib=f'const apiKey = "{fake}";\n')
    out = json.loads(run(p, "--json").stdout)
    assert out["summary"]["possibleSecrets"] >= 1
    assert any(f["level"] == "block" and "secret" in f["message"]
               for f in out["findings"])
