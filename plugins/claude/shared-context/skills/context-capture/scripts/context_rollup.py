#!/usr/bin/env python3
"""Roll session decisions up into ``context/architecture.md``, regenerate
``INDEX.md``, and apply retention.

- Every bullet / numbered item / ``##`` heading in a session's ``decisions.md``
  is appended to ``context/architecture.md`` under a per-session heading, keyed
  by a short hash so re-runs are idempotent (nothing is added twice).
- Retention: sessions older than ``retention.maxAgeDays`` or beyond
  ``retention.maxSessions`` are fully packed into ``full.tar.xz`` (``manifest.json``
  is kept loose so ``INDEX.md`` stays meaningful) and their loose files removed.

Run this on session end (via the Stop hook) or on demand.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import context_common as cc  # noqa: E402

ROLLUP_MARK = "<!-- shared-context:rollup -->"
_HASH_RE = re.compile(r"<!--([0-9a-f]{12})-->")


_ITEM_RE = re.compile(r"^(?:[-*+]\s+|\d+\.\s+|#{2,6}\s+)(.*)$")


def decision_items(text):
    """One entry per bullet / numbered item / sub-heading, with only the leading
    list marker removed (so `**bold**` in the body survives intact)."""
    items = []
    for line in text.splitlines():
        m = _ITEM_RE.match(line.strip())
        if not m:
            continue
        body = m.group(1).strip()
        if len(body) >= 4 and "_(" not in body and not body.startswith("("):
            items.append(body)
    return items


def _existing_hashes(text):
    return set(_HASH_RE.findall(text))


def rollup_architecture(context_dir):
    arch = os.path.join(context_dir, "architecture.md")
    existing = open(arch, encoding="utf-8").read() if os.path.exists(arch) else ""
    if not existing:
        existing = (
            "# Architecture & Key Decisions\n\n"
            f"{ROLLUP_MARK}\n"
            "_Accumulated from each session's `decisions.md` by `context_rollup.py`. "
            "Newest section appended at the end. Mark superseded decisions with "
            "`~~strikethrough~~` plus a note rather than deleting them._\n"
        )
    seen = _existing_hashes(existing)
    added, blocks = [], []
    for date_name, sess, sp in cc.iter_session_dirs(context_dir):
        dpath = os.path.join(sp, "decisions.md")
        if not os.path.exists(dpath):
            continue
        m = cc.read_manifest(sp)
        fresh = []
        for item in decision_items(open(dpath, encoding="utf-8").read()):
            h = hashlib.sha1(item.lower().encode("utf-8")).hexdigest()[:12]
            if h in seen:
                continue
            seen.add(h)
            fresh.append((h, item))
        if fresh:
            block = [f"### {date_name} · {sess} ({m.get('host', '?')}/{m.get('agent', '?')})", ""]
            for h, item in fresh:
                block.append(f"- {item} <!--{h}-->")
                added.append(item)
            block.append("")
            blocks.append("\n".join(block))

    if blocks:
        existing = existing.rstrip() + "\n\n" + "\n".join(blocks) + "\n"
    with open(arch, "w", encoding="utf-8") as f:
        f.write(existing)
    return added


def _full_archive(sp):
    fa = os.path.join(sp, cc.FULL_ARCHIVE)
    entries = [e for e in os.listdir(sp) if e != cc.FULL_ARCHIVE]
    removable = [e for e in entries if e != "manifest.json"]
    if not removable and os.path.exists(fa):
        return False
    tmp = fa + ".tmp"
    with tarfile.open(tmp, "w:xz") as tf:
        for e in sorted(entries):
            tf.add(os.path.join(sp, e), arcname=e)
    os.replace(tmp, fa)
    for e in removable:
        path = os.path.join(sp, e)
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    return True


def apply_retention(context_dir, cfg):
    sessions = list(cc.iter_session_dirs(context_dir))
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg["retention"]["maxAgeDays"])
    stale = set()
    for date_name, _sess, sp in sessions:
        try:
            ddate = datetime.strptime(date_name, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ddate < cutoff:
            stale.add(sp)

    ordered = sorted(sp for _d, _s, sp in sessions)
    max_sessions = cfg["retention"]["maxSessions"]
    if len(ordered) > max_sessions:
        stale.update(ordered[: len(ordered) - max_sessions])

    archived = []
    for sp in sorted(stale):
        if _full_archive(sp):
            archived.append(os.path.basename(sp))
    return archived


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--context-dir")
    p.add_argument("--no-retention", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    context_dir = cc.resolve_context_dir(args.context_dir)
    if not os.path.isdir(context_dir):
        cc.eprint(f"error: no context dir at {context_dir}")
        return 2
    cfg = cc.load_config(context_dir)

    added = rollup_architecture(context_dir)
    archived = [] if args.no_retention else apply_retention(context_dir, cfg)
    n = cc.regenerate_index(context_dir)

    if args.json:
        print(json.dumps({
            "decisionsAdded": added,
            "sessionsArchived": archived,
            "indexSessions": n,
        }, indent=2))
    else:
        print(f"rolled up {len(added)} new decision(s) into architecture.md")
        if archived:
            print(f"archived {len(archived)} old session(s): {', '.join(archived)}")
        print(f"INDEX.md now lists {n} session(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
