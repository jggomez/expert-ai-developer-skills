# Session-record schema & field guide

Every session lives at `context/<YYYY-MM-DD>/<HH-MM-SS-host-user>/`.

## `manifest.json` (written by `context_snapshot.py` — do not hand-edit)

| Field | Type | Notes |
| :--- | :--- | :--- |
| `schema` | int | currently `1` |
| `session` | string | the session-id; matches the directory name |
| `started` | string | ISO-8601 UTC, set once at creation |
| `updated` | string | ISO-8601 UTC, refreshed on every run |
| `host` | string | `claude-code` \| `antigravity` \| `unknown` (auto-detected) |
| `agent` | string | model id passed via `--agent`, e.g. `claude-sonnet-5` |
| `model` | string | free-form, `--model` |
| `user` | string | sanitized `$USER` |
| `status` | string | `in-progress` \| `done` \| `blocked` |
| `task` | string | one-line task description |
| `git` | object | `branch`, `head`, `diffstat`, `diffstatTruncated`, `recentCommits` |

## Markdown files

- **`summary.md`** — three sections: *What was done*, *Current state*,
  *Next steps*. Written for someone who did not see the conversation. Stays
  uncompressed.
- **`decisions.md`** — one bullet per decision. Format:
  `**decision** — why, and what was rejected.` Each bullet is copied verbatim
  into `context/architecture.md` by the rollup, so keep it self-contained.
  Stays uncompressed.
- **`flows.md`** — numbered steps of the approach, including dead ends and why
  they were abandoned. Compressed into `detail.tar.xz`.
- **`topics.md`** — conversation topics, open questions / TODO checkboxes, and
  user preferences observed this session. Compressed.
- **`files-touched.json`** — array of `{ "path": ..., "reason": ... }`.
  Compressed. Keep it to files whose *purpose* is not obvious from the diff.
- **`git-context.md`** — auto-generated git snapshot. Compressed.

## Long-lived files (repo-level, not per session)

- **`context/preferences.md`** — cross-session user preferences. Add only what
  the user stated explicitly. `context-restore` must ask before adopting these.
- **`context/architecture.md`** — append-only decision log built by the rollup.
  Mark superseded entries with `~~strikethrough~~` + a note; never delete.
- **`context/INDEX.md`** — generated table of every session. Never hand-edit.

## `context/.contextrc.json`

```json
{
  "autosave":    { "everyNToolCalls": 25, "everyMinutes": 10, "onStop": true },
  "compression": { "format": "tar.xz", "keepUncompressedSessions": 5 },
  "retention":   { "maxSessions": 100, "maxAgeDays": 90 },
  "capture":     { "includeGitDiff": true, "maxDiffLines": 400, "redactSecrets": true },
  "restore":     { "askBeforeLoad": true, "autoLoadPreferences": false }
}
```

Partial overrides are merged over the defaults, so a file containing only
`{"retention": {"maxSessions": 20}}` is valid.

## Git & size

`context/` is committed. `context/.gitattributes` marks `*.tar.xz` binary;
`context/.session-state.json` (hook bookkeeping) is git-ignored. Retention plus
`--auto` compression keep the committed footprint bounded.
