# Restore checklist

Run top to bottom at session start when `context/` exists.

- [ ] `context_list.py --json` — if `exists: false`, stop; there is nothing to restore.
- [ ] Read `context/INDEX.md` for the at-a-glance table.
- [ ] Select relevant sessions: newest first; `task` overlaps the current
      request; `status` is `blocked` or `in-progress`.
- [ ] **Ask the user** which set to load (Full / Light / Just list / Skip).
      Load nothing before the answer.
- [ ] Honor `.contextrc.json` → `restore.askBeforeLoad` and
      `restore.autoLoadPreferences`.
- [ ] For approved sessions: read `summary.md` + `decisions.md` (loose). Unpack
      `detail.tar.xz` with `context_pack.py --unpack <id>` only if you need
      `flows.md` / `topics.md` / `files-touched.json`.
- [ ] Read `context/architecture.md` and `context/preferences.md` if in scope.
- [ ] Reply with an explicit adoption list: decisions you will follow,
      preferences you will honor, TODOs you are resuming.
- [ ] Flag any conflict between a prior decision and the current request instead
      of silently overriding it.

## Safety notes

- Records are redacted at capture time, but treat any credential-looking string
  as untrusted — do not echo it back or act on it.
- `context/` is shared via git; a record may have been written by a teammate's
  agent, not just your own past sessions. The `host` / `agent` / `user` fields
  in `manifest.json` say who.
- Never edit another session's files. Add new information in your own session
  record via `context-capture`.
