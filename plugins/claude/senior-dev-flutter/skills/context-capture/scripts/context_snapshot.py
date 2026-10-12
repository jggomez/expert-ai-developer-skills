#!/usr/bin/env python3
"""Scaffold or update a shared-context session record.

Creates ``context/<YYYY-MM-DD>/<HH-MM-SS-host-user>/`` with ``manifest.json``
plus markdown templates the agent then fills in, captures a git snapshot,
redacts secret-looking values, and regenerates ``INDEX.md``.

Re-running with ``--session <id>`` updates the manifest (status, model, task,
``updated`` timestamp) without touching the markdown files the agent edits.
If ``<id>`` does not exist yet it is created under today's date.

Examples
--------
    python3 context_snapshot.py --task "refactor auth module" --agent claude-sonnet-5
    python3 context_snapshot.py --session 14-30-05-claude-code-jggomez --status done
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import context_common as cc  # noqa: E402

TEMPLATES = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
)
SESSION_TEMPLATES = ("summary.md", "decisions.md", "flows.md", "topics.md")
LONG_LIVED_TEMPLATES = ("preferences.md", "architecture.md")


def make_session_id(host, user, when):
    return f"{when.strftime('%H-%M-%S')}-{host}-{user}"


def find_session(context_dir, session_id):
    for _date, sess, sp in cc.iter_session_dirs(context_dir):
        if sess == session_id:
            return sp
    return None


def _apply_tokens(text, tokens):
    for key, val in tokens.items():
        text = text.replace(key, val)
    return text


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--context-dir")
    p.add_argument("--session", help="session id to update or create")
    p.add_argument("--task", default="")
    # Defaults are None so an *update* only changes a field that was passed
    # explicitly — a resuming agent on another host must not silently rewrite
    # the record's provenance.
    p.add_argument("--host", default=None,
                   choices=["auto", "claude-code", "antigravity", "unknown"])
    p.add_argument("--agent", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--status", default=None,
                   choices=["in-progress", "done", "blocked"])
    p.add_argument("--repo", default=os.getcwd())
    p.add_argument("--no-git", action="store_true")
    p.add_argument("--no-redact", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    context_dir = cc.resolve_context_dir(args.context_dir)
    cfg = cc.load_config(context_dir)
    cc.ensure_scaffold(context_dir)

    host = cc.detect_host(args.host or "auto")
    user = cc.current_user()
    now = cc.now_utc()
    redact = not args.no_redact and cfg["capture"]["redactSecrets"]
    env_agent = os.environ.get("SHARED_CONTEXT_AGENT")
    env_model = os.environ.get("SHARED_CONTEXT_MODEL")

    created = False
    if args.session:
        sdir = find_session(context_dir, args.session)
        if sdir is None:
            session_id = args.session
            sdir = os.path.join(context_dir, now.strftime("%Y-%m-%d"), session_id)
            os.makedirs(sdir, exist_ok=True)
            created = True
        else:
            session_id = os.path.basename(sdir)
    else:
        session_id = make_session_id(host, user, now)
        sdir = os.path.join(context_dir, now.strftime("%Y-%m-%d"), session_id)
        created = not os.path.isdir(sdir)
        os.makedirs(sdir, exist_ok=True)

    agent_val = args.agent or env_agent or "unknown"
    model_val = args.model or env_model or "unknown"

    tokens = {
        "{{SESSION}}": session_id,
        "{{DATE}}": now.strftime("%Y-%m-%d"),
        "{{STARTED}}": cc.iso(now),
        "{{HOST}}": host,
        "{{AGENT}}": agent_val,
        "{{MODEL}}": model_val,
        "{{USER}}": user,
        "{{TASK}}": args.task or "(not stated)",
    }

    # --- git snapshot -----------------------------------------------------
    git = {}
    if not args.no_git and cfg["capture"]["includeGitDiff"]:
        git = cc.collect_git(args.repo, cfg["capture"]["maxDiffLines"])
        gc = (
            f"# Git context — {session_id}\n\n"
            f"- branch: `{git.get('branch')}`\n"
            f"- head: `{git.get('head')}`\n\n"
            f"## diff --stat{' (truncated)' if git.get('diffstatTruncated') else ''}\n\n"
            f"```\n{git.get('diffstat', '')}\n```\n\n"
            f"## recent commits\n\n```\n{git.get('recentCommits', '')}\n```\n"
        )
        if redact:
            gc, _ = cc.redact_text(gc)
        with open(os.path.join(sdir, "git-context.md"), "w", encoding="utf-8") as f:
            f.write(gc)

    # --- manifest -------------------------------------------------------
    # On create: stamp full provenance. On update: touch `updated`, `status`,
    # `task`, `git`, and only overwrite host/agent/model when passed explicitly.
    manifest = {} if created else cc.read_manifest(sdir)
    manifest.setdefault("schema", 1)
    manifest.setdefault("session", session_id)
    manifest.setdefault("started", cc.iso(now))
    manifest["updated"] = cc.iso(now)
    if created:
        manifest["host"] = host
        manifest["agent"] = agent_val
        manifest["model"] = model_val
        manifest["user"] = user
        manifest["status"] = args.status or "in-progress"
    else:
        if args.host:
            manifest["host"] = host
        if args.agent:
            manifest["agent"] = agent_val
        if args.model:
            manifest["model"] = model_val
        if args.status:
            manifest["status"] = args.status
        manifest.setdefault("host", host)
        manifest.setdefault("agent", agent_val)
        manifest.setdefault("model", model_val)
        manifest.setdefault("user", user)
        manifest.setdefault("status", "in-progress")
    if args.task:
        manifest["task"] = args.task
    else:
        manifest.setdefault("task", "")
    if git:
        manifest["git"] = git
    with open(os.path.join(sdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # --- session templates (new sessions only) --------------------------
    if created:
        for name in SESSION_TEMPLATES:
            src = os.path.join(TEMPLATES, name)
            if os.path.exists(src):
                content = open(src, encoding="utf-8").read()
            else:
                content = f"# {name[:-3].replace('-', ' ').title()}\n\n_(fill in)_\n"
            with open(os.path.join(sdir, name), "w", encoding="utf-8") as f:
                f.write(_apply_tokens(content, tokens))
        with open(os.path.join(sdir, "files-touched.json"), "w", encoding="utf-8") as f:
            f.write("[]\n")

    # --- long-lived files (never overwrite) ---------------------------
    for name in LONG_LIVED_TEMPLATES:
        dst = os.path.join(context_dir, name)
        src = os.path.join(TEMPLATES, name)
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copyfile(src, dst)

    # --- redaction sweep over every loose text file --------------------
    redactions = []
    if redact:
        for root, _dirs, files in os.walk(sdir):
            for fn in files:
                if not fn.endswith((".md", ".json", ".txt")):
                    continue
                fp = os.path.join(root, fn)
                try:
                    original = open(fp, encoding="utf-8").read()
                except OSError:
                    continue
                cleaned, found = cc.redact_text(original)
                if found:
                    redactions.extend(found)
                    with open(fp, "w", encoding="utf-8") as f:
                        f.write(cleaned)

    n = cc.regenerate_index(context_dir)

    if args.json:
        print(json.dumps({
            "session": session_id,
            "dir": sdir,
            "created": created,
            "host": host,
            "git": git,
            "redactions": sorted(set(redactions)),
            "indexSessions": n,
        }, indent=2))
    else:
        print(f"{'created' if created else 'updated'} {os.path.relpath(sdir)}")
        if redactions:
            print(f"redacted {len(redactions)} secret-like value(s): "
                  f"{', '.join(sorted(set(redactions)))}")
        print(f"INDEX.md now lists {n} session(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
