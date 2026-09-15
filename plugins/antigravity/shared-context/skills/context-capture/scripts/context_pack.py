#!/usr/bin/env python3
"""Compress / decompress the detail files of shared-context sessions.

Each session keeps ``manifest.json`` + ``summary.md`` + ``decisions.md`` loose
(fast to browse and diff); the heavier detail (``flows.md``, ``topics.md``,
``files-touched.json``, ``git-context.md``, ``artifacts/``) is packed into
``detail.tar.xz``. The loose files are the source of truth: ``--pack`` rebuilds
the archive from whatever loose detail files are present and then removes them;
``--unpack`` restores them and deletes the archive.

Examples
--------
    python3 context_pack.py --pack 14-30-05-claude-code-jggomez
    python3 context_pack.py --unpack 14-30-05-claude-code-jggomez
    python3 context_pack.py --auto            # pack all but the newest N
"""
import argparse
import json
import os
import shutil
import sys
import tarfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import context_common as cc  # noqa: E402


def session_path(context_dir, ident):
    if os.path.isdir(ident):
        return os.path.abspath(ident)
    cand = os.path.join(context_dir, ident)
    if os.path.isdir(cand):
        return os.path.abspath(cand)
    for _date, sess, sp in cc.iter_session_dirs(context_dir):
        if sess == ident:
            return sp
    return None


def _safe_extract(tf, dest):
    dest = os.path.abspath(dest)
    for member in tf.getmembers():
        target = os.path.abspath(os.path.join(dest, member.name))
        if target != dest and not target.startswith(dest + os.sep):
            raise RuntimeError(f"unsafe path in archive: {member.name}")
    tf.extractall(dest)


def pack(sp):
    archive = os.path.join(sp, cc.DETAIL_ARCHIVE)
    members = [n for n in cc.DETAIL_MEMBERS if os.path.exists(os.path.join(sp, n))]
    if not members:
        return {"action": "pack", "session": os.path.basename(sp),
                "archive": None, "members": [], "note": "nothing to pack"}
    tmp = archive + ".tmp"
    with tarfile.open(tmp, "w:xz") as tf:
        for name in sorted(members):
            tf.add(os.path.join(sp, name), arcname=name)
    os.replace(tmp, archive)
    for name in members:
        path = os.path.join(sp, name)
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    return {"action": "pack", "session": os.path.basename(sp),
            "archive": archive, "members": sorted(members)}


def unpack(sp):
    archive = os.path.join(sp, cc.DETAIL_ARCHIVE)
    if not os.path.exists(archive):
        return {"action": "unpack", "session": os.path.basename(sp),
                "archive": None, "members": [], "note": "no archive"}
    with tarfile.open(archive, "r:xz") as tf:
        names = tf.getnames()
        _safe_extract(tf, sp)
    os.remove(archive)
    return {"action": "unpack", "session": os.path.basename(sp),
            "archive": archive, "members": sorted(names)}


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--context-dir")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--pack", metavar="SESSION")
    g.add_argument("--unpack", metavar="SESSION")
    g.add_argument("--auto", action="store_true",
                   help="pack every session except the newest keepUncompressedSessions")
    p.add_argument("--keep-uncompressed", type=int)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    context_dir = cc.resolve_context_dir(args.context_dir)
    if not os.path.isdir(context_dir):
        cc.eprint(f"error: no context dir at {context_dir}")
        return 2
    cfg = cc.load_config(context_dir)

    results = []
    if args.auto:
        keep = (args.keep_uncompressed if args.keep_uncompressed is not None
                else cfg["compression"]["keepUncompressedSessions"])
        sessions = sorted(sp for _d, _s, sp in cc.iter_session_dirs(context_dir))
        to_pack = sessions[:-keep] if keep > 0 else sessions
        results = [pack(sp) for sp in to_pack]
    elif args.pack:
        sp = session_path(context_dir, args.pack)
        if not sp:
            cc.eprint(f"error: session '{args.pack}' not found")
            return 2
        results.append(pack(sp))
    else:
        sp = session_path(context_dir, args.unpack)
        if not sp:
            cc.eprint(f"error: session '{args.unpack}' not found")
            return 2
        results.append(unpack(sp))

    cc.regenerate_index(context_dir)
    if args.json:
        print(json.dumps({"results": results}, indent=2))
    else:
        for r in results:
            note = f" ({r['note']})" if r.get("note") else ""
            print(f"{r['action']}: {r['session']} — {len(r['members'])} member(s){note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
