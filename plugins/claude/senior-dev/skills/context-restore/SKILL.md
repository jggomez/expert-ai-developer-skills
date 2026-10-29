---
name: context-restore
description: Use at session start (State 0) or when asked to "load context", "catch up", or "what was done before" — prioritizes LLM Wiki Progressive Disclosure (context/memory/MEMORY.md) across Claude Code and Google Antigravity while supporting user-confirmed restore for scripted sessions (context/sessions/).
---

# Context Restore Skill

## Overview
This skill restores durable repository memory, decisions, conventions, and active handoff state across **Claude Code** and **Google Antigravity**. It prioritizes **LLM Wiki Progressive Disclosure (`context/memory/MEMORY.md`)** for ~500-token State 0 handoffs while preserving interactive, user-confirmed restoration for standalone scripted session stores (`context/sessions/`).

## When to Use
### Trigger Scenarios
- **Orchestrator State 0 Silent Restore**: When `context/memory/MEMORY.md` exists, silently absorb cross-AI handoff state (`<= 80-100 lines`) left by Claude Code or Antigravity.
- **Explicit User Handoff Resume**: *"load context"*, *"catch me up"*, *"resume where Claude Code / Antigravity left off"*.
- **Standalone Session Discovery**: Inspecting historical archives in `context/sessions/`.

### When NOT to Use
- **Repositories without `context/memory/` or `context/`**, or when the user explicitly asks to start fresh.
- **Saving new milestones or handoffs**: Route to `context-capture`.

## Process
### Mode A: LLM Wiki Progressive Disclosure (`context/memory/` — Primary)
1. **Read Master Index Only (`~500 tokens`)**: If `context/memory/MEMORY.md` exists, read **ONLY `context/memory/MEMORY.md`** (`<= 80-100 lines`) to absorb active host, branch/task, recent decisions, and pointers to root `AGENTS.md` (`<= 90 lines`), `DESIGN.md` (`<= 110 lines`), and the last 5 daily logs.
2. **Drill Down Strictly on Demand**: Open `context/memory/architecture.md`, `context/memory/conventions.md`, `DESIGN.md`, or a specific `context/memory/log/YYYY-MM-DD.md` **only** when the active task touches that domain.

### Mode B: Interactive Restore for Scripted Sessions (`context/sessions/`)
1. **Discover Sessions Non-Invasively**:
   ```bash
   python3 ./skills/context-restore/scripts/context_list.py --json
   ```
   If `exists: false`, continue normally without noise.
2. **Rank & Ask User Before Loading**: Rank recent, matching, or `in-progress`/`blocked` sessions first, then **ask the user** to select `Full` (`summary.md`, `decisions.md`, `architecture.md`, `preferences.md`), `Light` (`architecture.md` + `preferences.md`), `Just list`, or `Skip` (honoring `restore.askBeforeLoad` in `context/.contextrc.json`).
3. **Ingest Approved Scope & State Adoption**: Unpack flows only if needed (`python3 ./skills/context-capture/scripts/context_pack.py --unpack <session-id>`), then state adopted decisions, resumed TODOs, and any conflicts with the current prompt.

## Usage
### Commands & Progressive Disclosure Reads
```bash
# Mode A — Read master wiki index first; open linked pages only on demand
cat context/memory/MEMORY.md

# Mode B — List scripted sessions (JSON or human-readable)
python3 ./skills/context-restore/scripts/context_list.py --json
python3 ./skills/context-restore/scripts/context_list.py
```

### Host Execution Instructions
- **Claude Code**: Read `context/memory/MEMORY.md` silently in State 0; in standalone mode, run `context_list.py --json` via Bash and ask (`Full / Light / Just list / Skip`).
- **Antigravity**: Read `context/memory/MEMORY.md` silently in State 0; in standalone mode, use `context-keeper` or `context_list.py --json` with user confirmation.

## Red Flags
- Eager-reading all `context/memory/log/` files or unpacking archives upfront instead of reading **only `MEMORY.md`** first.
- Loading `context/sessions/` archives in standalone mode without asking the user (`Full / Light / Just list / Skip`).
- Silently following an outdated decision that conflicts with explicit new user instructions.

## Verification
- [ ] In State 0, **only `context/memory/MEMORY.md`** (`~500 tokens`) is read initially; linked pages load strictly on demand.
- [ ] In standalone `context/sessions/` mode, discovery runs cleanly and user confirms (`Full / Light / Just list / Skip`) before ingestion:
  ```bash
  python3 ./skills/context-restore/scripts/context_list.py --json
  ```
- [ ] Active branch, decisions, and pending items are honored without token bloat.

## References
- [Restore checklist](references/restore-checklist.md)
