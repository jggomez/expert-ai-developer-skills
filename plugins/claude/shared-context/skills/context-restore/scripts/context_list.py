#!/usr/bin/env python3
"""List shared-context sessions, newest first.

Used by the ``context-restore`` skill and by the session-start hooks to decide
whether to prompt the user. Exit code is always 0 — the absence of a
``context/`` directory is a normal state, not an error. ``--json`` emits a
machine summary whose ``exists`` boolean the hooks branch on.

Examples
--------
    python3 context_list.py                 # human-readable
    python3 context_list.py --json          # for hooks / agents
    python3 context_list.py --full --limit 5
"""
import argparse
import json
import os
import re
import sys

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def resolve_context_dir(arg=None):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("SHARED_CONTEXT_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.abspath(os.path.join(os.getcwd(), "context"))


def iter_sessions(context_dir):
    if not os.path.isdir(context_dir):
        return
    for date_name in sorted(os.listdir(context_dir)):
        dp = os.path.join(context_dir, date_name)
        if not os.path.isdir(dp) or not _DATE_RE.match(date_name):
            continue
        for sess in sorted(os.listdir(dp)):
            sp = os.path.join(dp, sess)
            if os.path.isdir(sp):
                yield date_name, sess, sp


def load_manifest(sp):
    try:
        with open(os.path.join(sp, "manifest.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def first_paragraph(path):
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return ""
    for block in text.split("\n\n"):
        b = block.strip()
        if b and not b.startswith("#") and "_(" not in b:
            return " ".join(b.split())
    return ""


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--context-dir")
    p.add_argument("--json", action="store_true")
    p.add_argument("--full", action="store_true",
                   help="include each session summary's first paragraph")
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args(argv)

    context_dir = resolve_context_dir(args.context_dir)
    rows = []
    for date_name, sess, sp in iter_sessions(context_dir):
        m = load_manifest(sp)
        rows.append({
            "date": date_name,
            "session": sess,
            "path": sp,
            "started": m.get("started", ""),
            "updated": m.get("updated", ""),
            "host": m.get("host", "?"),
            "agent": m.get("agent", "?"),
            "model": m.get("model", "?"),
            "status": m.get("status", "?"),
            "task": (m.get("task") or "").replace("\n", " ").strip(),
            "archived": os.path.exists(os.path.join(sp, "full.tar.xz")),
            "summary": first_paragraph(os.path.join(sp, "summary.md")) if args.full else None,
        })
    rows.sort(key=lambda r: (r["date"], r["session"]), reverse=True)
    if args.limit > 0:
        rows = rows[: args.limit]

    exists = os.path.isdir(context_dir) and len(rows) > 0
    has_pref = os.path.exists(os.path.join(context_dir, "preferences.md"))
    has_arch = os.path.exists(os.path.join(context_dir, "architecture.md"))

    if args.json:
        print(json.dumps({
            "exists": exists,
            "contextDir": context_dir,
            "count": len(rows),
            "preferences": has_pref,
            "architecture": has_arch,
            "sessions": rows,
        }, indent=2))
        return 0

    if not exists:
        print(f"No shared context found at {context_dir}")
        return 0
    print(f"Shared context: {len(rows)} session(s) at {context_dir}")
    if has_pref:
        print("  + preferences.md")
    if has_arch:
        print("  + architecture.md")
    print()
    for r in rows:
        task = r["task"][:90] + ("…" if len(r["task"]) > 90 else "")
        flag = " (archived)" if r["archived"] else ""
        print(f"  {r['date']} {r['session']}  [{r['host']}/{r['agent']}, {r['status']}]{flag}")
        if task:
            print(f"      {task}")
        if args.full and r["summary"]:
            s = r["summary"][:240] + ("…" if len(r["summary"]) > 240 else "")
            print(f"      {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
