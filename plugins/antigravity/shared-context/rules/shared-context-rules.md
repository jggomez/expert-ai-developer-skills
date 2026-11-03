---
trigger: model_decision
description: Load when reading, restoring or saving project memory in context/ (context/memory/MEMORY.md or archived context/sessions/), or when the user asks to save, hand off or catch up.
---

# Shared Context Rules

- **Read lightly**: read only `context/memory/MEMORY.md` (~500 tokens) at the start of work; open `architecture.md`, `conventions.md` or `log/YYYY-MM-DD.md` only when the task needs them.
- **Archived sessions**: if `python3 ./skills/context-restore/scripts/context_list.py --json` reports `exists: true`, summarize the sessions and ask the user which ones to load (Full / Light / Just list / Skip) before loading any; honor `restore.askBeforeLoad` in `context/.contextrc.json`.
- **Save only at milestones**: when a task ships (tests exit `0`) or the user asks to save or hand off. Never on intermediate turns or simple Q&A.
- **What goes where**: feature specs stay in `docs/<feature-name>/`, UI tokens in root `DESIGN.md`, commands in root `AGENTS.md` (`<= 90` lines); `context/memory/` keeps durable decisions: `MEMORY.md` (`<= 100` lines, updated in place: active branch and task, key decisions, pointers), `architecture.md` / `conventions.md` (in place), and a 5-8 line entry appended to `log/YYYY-MM-DD.md`.
- **Secrets**: never write credentials or tokens into `context/`; never pass `--no-redact` unless the content is verified clean; never hand-edit `context/INDEX.md`.
