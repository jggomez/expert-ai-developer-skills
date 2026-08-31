---
name: context-capture
description: Use when finishing a task, at a periodic checkpoint, or when the user asks to "save context", "record decisions", or "hand off" — writes what was done, why, and how into a shared context/ directory that other AI agents (Claude Code, Antigravity CLI) can later load. Covers the session-record schema, secret redaction, tar.xz compression of old sessions, and rolling decisions up into an architecture log.
---

# Context Capture

Record the durable parts of this session into `context/` so a different agent —
on Claude Code or Antigravity CLI — can pick up where this one left off. Pair
with the `context-restore` skill, which reads what this one writes.

## When to run

- **On session end / task done** — always, if any real work happened.
- **Periodic checkpoint** — when a hook nudges you (default every 25 tool calls
  or 10 minutes), or before a risky/large step.
- **On explicit request** — "save context", "record this decision", "hand off".

Do **not** capture for pure question-answering with no edits and no decisions.

## What to capture (the bar for "relevant")

Write something down only if another agent would be worse off not knowing it:

| File | Put here | Skip |
| :--- | :--- | :--- |
| `summary.md` | outcome in plain language, current state, next steps | blow-by-blow narration |
| `decisions.md` | choices with a real trade-off or that others must respect | trivial local choices |
| `flows.md` | the path taken, including dead ends and why they failed | steps that worked first try and are obvious from the diff |
| `topics.md` | conversation topics, open questions, TODOs, preferences observed | resolved chatter |
| `context/preferences.md` | long-lived, cross-session user preferences (explicit only) | one-off asks |

## How to run

All scripts are stdlib-only and host-neutral. Run from the repo root.

```bash
# 1. Scaffold (or update) this session's record. Re-run with the same --session
#    to refresh the manifest without touching the markdown you edited.
python3 ./skills/context-capture/scripts/context_snapshot.py \
  --task "<one line>" --agent "<model id>" --status in-progress

# 2. Edit the markdown files it created under context/<date>/<session-id>/.
#    Fill summary.md and decisions.md first; they stay uncompressed.

# 3. On session end: mark done, roll decisions up, compress old sessions.
python3 ./skills/context-capture/scripts/context_snapshot.py --session <id> --status done
python3 ./skills/context-capture/scripts/context_rollup.py        # -> architecture.md + retention
python3 ./skills/context-capture/scripts/context_pack.py --auto    # compress all but newest 5
```

`--json` on any script gives machine output. `context_snapshot.py` auto-detects
the host, captures `git diff --stat` + recent commits, and runs a secret
redaction sweep (`«REDACTED:...»`) over everything it writes — never disable
`--no-redact` unless you are certain the content is clean.

## Compression model

Each session keeps `manifest.json` + `summary.md` + `decisions.md` **loose**
(fast to browse, diffs cleanly in a PR). The heavier detail is packed into
`detail.tar.xz` by `context_pack.py`. To read an archived session:

```bash
python3 ./skills/context-capture/scripts/context_pack.py --unpack <session-id>
```

## Rollup & retention

`context_rollup.py` appends every new decision line to `context/architecture.md`
(keyed by hash, so it is idempotent) and, past `retention.maxSessions` /
`retention.maxAgeDays` in `context/.contextrc.json`, fully archives the oldest
sessions into `full.tar.xz`.

## Reference

- [Session-record schema & field guide](references/record-schema.md)
