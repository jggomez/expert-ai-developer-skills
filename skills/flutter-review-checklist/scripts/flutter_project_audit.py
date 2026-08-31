#!/usr/bin/env python3
"""Advisory audit of a Flutter/Dart project — no `flutter` or `dart` binary
needed, reads files only. Reports SDK constraints, lint strictness, test &
coverage setup, flavors/config, and a few `lib/` smells.

Exit code is 0 unless run with --strict and a [block]-class finding exists.
`--json` emits a machine summary.

Usage:
    python3 ./skills/flutter-review-checklist/scripts/flutter_project_audit.py [PROJECT_DIR]
"""
import argparse
import json
import os
import re
import sys

SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd|client[_-]?secret)\s*[:=]\s*"
    r"['\"][0-9A-Za-z_\-./+=]{16,}['\"]"
)
GOOGLE_KEY_RE = re.compile(r"AIza[0-9A-Za-z\-_]{35}")


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def find_files(root, suffix, skip=("build", ".dart_tool", ".git", "ios/Pods")):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        if any(part in rel.split(os.sep) for part in (".git", "build", ".dart_tool")):
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.endswith(suffix):
                out.append(os.path.join(dirpath, fn))
    return out


def audit(root):
    findings = []  # (level, section, message)  level in ok|note|warn|block

    def add(level, section, msg):
        findings.append((level, section, msg))

    pubspec_path = os.path.join(root, "pubspec.yaml")
    pubspec = read(pubspec_path)
    if not pubspec:
        add("block", "project", f"no pubspec.yaml at {root} — not a Dart/Flutter project")
        return findings, {"isFlutterProject": False}

    is_flutter = "flutter:" in pubspec and "sdk: flutter" in pubspec

    # --- SDK constraints ---
    m = re.search(r"^\s*sdk:\s*['\"]?([^'\"\n]+)['\"]?", pubspec, re.M)
    add("ok" if m else "warn", "sdk",
        f"Dart SDK constraint: {m.group(1).strip()}" if m else "no `environment.sdk` constraint")
    mf = re.search(r"^\s*flutter:\s*['\"]?(>=[^'\"\n]+)['\"]?", pubspec, re.M)
    if is_flutter:
        add("ok" if mf else "note", "sdk",
            f"Flutter SDK constraint: {mf.group(1).strip()}" if mf
            else "no explicit `environment.flutter` constraint (relies on Dart constraint)")

    # --- dependency hygiene ---
    dep_block = re.search(r"\ndependencies:\s*\n(.*?)(?:\n\w|\Z)", pubspec, re.S)
    loose = []
    if dep_block:
        for line in dep_block.group(1).splitlines():
            dm = re.match(r"\s{2}([a-z0-9_]+):\s*(.+)$", line)
            if dm and dm.group(2).strip() in ("any", '"any"', "'any'"):
                loose.append(dm.group(1))
    if loose:
        add("warn", "deps", f"unpinned (`any`) dependencies: {', '.join(loose)}")
    else:
        add("ok", "deps", "no `any`-versioned direct dependencies")

    lint_pkgs = [p for p in ("flutter_lints", "very_good_analysis", "lints", "lint")
                 if re.search(rf"\n\s+{re.escape(p)}:", pubspec)]
    add("ok" if lint_pkgs else "warn", "lints",
        f"lint package: {', '.join(lint_pkgs)}" if lint_pkgs
        else "no lint package in dev_dependencies (flutter_lints / very_good_analysis)")

    # --- analysis_options.yaml ---
    ao = read(os.path.join(root, "analysis_options.yaml"))
    if not ao:
        add("warn", "lints", "no analysis_options.yaml")
    else:
        if "include:" in ao:
            add("ok", "lints", "analysis_options.yaml includes a ruleset")
        else:
            add("warn", "lints", "analysis_options.yaml has no `include:` of a ruleset")
        stricts = [k for k in ("strict-casts", "strict-inference", "strict-raw-types")
                   if re.search(rf"{k}:\s*true", ao)]
        add("ok" if stricts else "note", "lints",
            f"strict language modes on: {', '.join(stricts)}" if stricts
            else "no `language: strict-casts/strict-inference/strict-raw-types` enabled")
        if re.search(r"\n\s*errors:\s*\n", ao):
            downs = re.findall(r"\n\s{4}([a-z_]+):\s*(ignore|info|warning)\b", ao)
            if downs:
                add("warn", "lints",
                    "lint severities downgraded: "
                    + ", ".join(f"{a}->{b}" for a, b in downs))

    # --- tests & coverage ---
    test_files = find_files(os.path.join(root, "test"), "_test.dart") if os.path.isdir(
        os.path.join(root, "test")) else []
    add("ok" if test_files else "block" if is_flutter else "warn", "tests",
        f"{len(test_files)} *_test.dart file(s) under test/" if test_files
        else "no test/ directory with *_test.dart files")
    itest = os.path.isdir(os.path.join(root, "integration_test"))
    add("ok" if itest else "note", "tests",
        "integration_test/ present" if itest else "no integration_test/ directory")

    ci_files = find_files(os.path.join(root, ".github", "workflows"), ".yml") + \
        find_files(os.path.join(root, ".github", "workflows"), ".yaml")
    ci_text = "\n".join(read(p) for p in ci_files)
    if ci_files:
        add("ok" if "--coverage" in ci_text else "warn", "coverage",
            "CI runs tests with --coverage" if "--coverage" in ci_text
            else "CI present but no `--coverage` flag found")
    else:
        add("note", "coverage", "no .github/workflows CI found")

    # --- flavors / build config ---
    gradle = read(os.path.join(root, "android", "app", "build.gradle")) + \
        read(os.path.join(root, "android", "app", "build.gradle.kts"))
    has_flavors = "productFlavors" in gradle or "flavorDimensions" in gradle
    dart_define = "--dart-define" in ci_text or "--flavor" in ci_text or \
        os.path.exists(os.path.join(root, "dart_define.json"))
    add("ok" if has_flavors else "note", "config",
        "Android productFlavors configured" if has_flavors
        else "no Android product flavors (fine for a single-environment app)")
    add("ok" if dart_define else "note", "config",
        "--dart-define / --flavor used for build config" if dart_define
        else "no --dart-define(-from-file) config seen — check how env config is injected")

    # --- lib/ smells ---
    lib_files = find_files(os.path.join(root, "lib"), ".dart") if os.path.isdir(
        os.path.join(root, "lib")) else []
    prints, secrets, todos = [], [], 0
    for p in lib_files:
        txt = read(p)
        rel = os.path.relpath(p, root)
        for i, line in enumerate(txt.splitlines(), 1):
            if re.search(r"(?<![\w.])print\s*\(", line) and "// ignore" not in line:
                prints.append(f"{rel}:{i}")
            if SECRET_RE.search(line) or GOOGLE_KEY_RE.search(line):
                secrets.append(f"{rel}:{i}")
        todos += len(re.findall(r"//\s*(TODO|FIXME)\b", txt))
    add("ok" if not prints else "warn", "lib",
        "no bare print() in lib/" if not prints
        else f"{len(prints)} bare print() call(s) in lib/ — use a logger (first: {prints[0]})")
    add("ok" if not secrets else "block", "lib",
        "no obvious secrets in lib/" if not secrets
        else f"possible hard-coded secret(s): {', '.join(secrets[:5])}")
    add("note", "lib", f"{todos} TODO/FIXME marker(s) in lib/  ·  {len(lib_files)} .dart file(s)")

    summary = {
        "isFlutterProject": is_flutter,
        "dartSdk": (m.group(1).strip() if m else None),
        "flutterSdk": (mf.group(1).strip() if mf else None),
        "lintPackages": lint_pkgs,
        "testFiles": len(test_files),
        "integrationTests": itest,
        "ciCoverage": ("--coverage" in ci_text),
        "androidFlavors": has_flavors,
        "printsInLib": len(prints),
        "possibleSecrets": len(secrets),
    }
    return findings, summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project_dir", nargs="?", default=".")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero if any [block] finding exists")
    args = p.parse_args(argv)

    root = os.path.abspath(args.project_dir)
    findings, summary = audit(root)

    if args.json:
        print(json.dumps({
            "project": root,
            "summary": summary,
            "findings": [{"level": lv, "section": s, "message": msg} for lv, s, msg in findings],
        }, indent=2))
    else:
        order = {"block": 0, "warn": 1, "ok": 2, "note": 3}
        icon = {"block": "✗", "warn": "!", "ok": "✓", "note": "·"}
        print(f"Flutter project audit — {root}\n")
        for lv, section, msg in sorted(findings, key=lambda f: (order[f[0]], f[1])):
            print(f"  {icon[lv]} [{section}] {msg}")
        blocks = sum(1 for lv, _, _ in findings if lv == "block")
        warns = sum(1 for lv, _, _ in findings if lv == "warn")
        print(f"\n{blocks} blocking · {warns} warnings")

    if args.strict and any(lv == "block" for lv, _, _ in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
