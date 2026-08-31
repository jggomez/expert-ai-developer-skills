---
name: context-restore
description: Use at the start of a session, or when the user asks to "load context", "catch up", or "what was done before" — checks the shared context/ directory for prior AI sessions (Claude Code or Antigravity CLI), summarizes what is there, and loads decisions, flows, and preferences ONLY after the user confirms. Pairs with context-capture, which writes the records this reads.
---

# Context Restore

Bring a new session up to speed from `context/` — but never silently. The user
must choose what, if anything, to adopt.

## When to run

- **At session start**, if `context/` exists with at least one session. The
  plugin's `SessionStart` hook (Claude Code) / `rules/shared-context-rules.md`
  (Antigravity) will prompt you to do this.
- **On request** — "load context", "catch me up", "what was decided before".

## Procedure

### 1. See what exists (no side effects)

```bash
python3 ./skills/context-restore/scripts/context_list.py --json
```

`exists: false` → say there is no shared context and continue normally. Stop here.

### 2. Rank relevance

From the JSON, pick the sessions worth loading: most recent first, those whose
`task` overlaps the current request, and any with `status: blocked` or
`in-progress` (unfinished work). Ignore stale, unrelated sessions.

### 3. Ask the user before loading — this is mandatory

Present a short menu and wait for an answer. Do not load anything yet.

- **Full** — summaries + decisions + `architecture.md` + `preferences.md`
- **Light** — `architecture.md` + `preferences.md` only
- **Just list** — tell me what's there, load nothing
- **Skip** — start fresh

If `restore.askBeforeLoad` is `false` in `.contextrc.json`, you may load the
"Light" set without asking, but still report what you loaded.

### 4. Load what was approved

```bash
# read the loose files directly:
cat context/<date>/<session-id>/summary.md
cat context/<date>/<session-id>/decisions.md
cat context/architecture.md context/preferences.md

# a session whose detail is archived:
python3 ./skills/context-capture/scripts/context_pack.py --unpack <session-id>
cat context/<date>/<session-id>/flows.md
```

### 5. State what you adopted

Reply with an explicit list: which decisions you will now follow, which
preferences you will honor, and which open TODOs you are picking up. If a prior
decision conflicts with the current request, surface the conflict — do not
just override it.

## Reference

- [Restore checklist](references/restore-checklist.md)
