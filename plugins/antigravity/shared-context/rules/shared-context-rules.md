---
trigger: always_on
description: Shared context working memory rules enforcing session restoration, periodic checkpointing, and secret redaction.
---

# Shared Context Rules

**Identifier**: `shared-context-rules`

These rules govern cross-agent persistent memory and architecture decision tracking.

## 1. At the Start of Every Session

1. Check whether a `context/` directory with prior sessions exists:
   `python3 ./skills/context-restore/scripts/context_list.py --json`
2. If `exists` is `false` → continue normally, say nothing.
3. If `exists` is `true` → **before doing other work**, follow the
   `context-restore` skill: summarize what is there and **ask the user** which
   set to load — Full / Light / Just list / Skip. Load nothing without an
   explicit answer. Honor `restore.askBeforeLoad` in `context/.contextrc.json`.
4. After loading, state exactly which decisions and preferences you will follow
   and which TODOs you are resuming.

## 2. During the Session

- Roughly every 25 tool calls or 10 minutes (see `autosave` in
  `.contextrc.json`), if meaningful work has happened, checkpoint via the
  `context-capture` skill: update `summary.md` / `decisions.md` and re-run
  `context_snapshot.py --session <id>`.

## 3. Before Ending the Session

- If real work happened, flush the record: `context_snapshot.py --session <id> --status done`, then `context_rollup.py`, then `context_pack.py --auto`.
- Keep `decisions.md` bullets self-contained — they are copied verbatim into `context/architecture.md`.

## 4. Security & Redaction Invariants

- Never disable secret redaction (`--no-redact`) unless the content is certainly clean. Never echo credentials into records or chat.
- Never hand-edit `INDEX.md` or another session's files.
