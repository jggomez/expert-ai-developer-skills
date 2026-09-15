# Shared Context Rules

Antigravity auto-loads this file (it has no `SessionStart` hook event). These
rules make the shared-context behavior reliable regardless of the hooks.

## At the start of every session

1. Check whether a `context/` directory with prior sessions exists:
   `python3 ./skills/context-restore/scripts/context_list.py --json`
2. If `exists` is `false` → continue normally, say nothing.
3. If `exists` is `true` → **before doing other work**, follow the
   `context-restore` skill: summarize what is there and **ask the user** which
   set to load — Full / Light / Just list / Skip. Load nothing without an
   explicit answer. Honor `restore.askBeforeLoad` in `context/.contextrc.json`.
4. After loading, state exactly which decisions and preferences you will follow
   and which TODOs you are resuming.

## During the session

- Roughly every 25 tool calls or 10 minutes (see `autosave` in
  `.contextrc.json`), if meaningful work has happened, checkpoint via the
  `context-capture` skill: update `summary.md` / `decisions.md` and re-run
  `context_snapshot.py --session <id>`.

## Before ending the session

- If real work happened, flush the record: `context_snapshot.py --session <id>
  --status done`, then `context_rollup.py`, then `context_pack.py --auto`.
- Keep `decisions.md` bullets self-contained — they are copied verbatim into
  `context/architecture.md`.

## Always

- Never disable secret redaction (`--no-redact`) unless the content is certainly
  clean. Never echo a credential-looking string into a record or into chat.
- Never hand-edit `INDEX.md` or another session's files. `context/` is shared
  via git and a record may have been written by a teammate's agent.
