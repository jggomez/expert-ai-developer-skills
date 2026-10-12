---
name: context-restore
description: Use at the start of a session (State 0) or when the user asks to "load context", "catch up", or "what was done before" — prioritizes LLM Wiki Progressive Disclosure (context/memory/MEMORY.md) for fast cross-AI handoffs between Claude Code and Google Antigravity, while supporting interactive restoration for scripted session stores (context/sessions/).
---

# Context Restore Skill

## Overview
This skill restores durable context, architectural decisions, conventions, and active working state across AI sessions between **Claude Code** and **Google Antigravity**. It prioritizes **LLM Wiki Progressive Disclosure (`context/memory/`)** for zero-friction, token-efficient handoffs in orchestrator workflows (`State 0` of `senior-dev`), while preserving an interactive user-confirmed restore workflow for standalone scripted session stores (`context/sessions/`).

## When to Use
### Trigger Scenarios
- **Fast Silent Restore in Orchestrators (`State 0` of `senior-dev`)**: At task initiation when `context/memory/MEMORY.md` exists, silently absorb the active cross-AI handoff state (`<= 80-100 lines`, ~500 tokens) left by **Claude Code** or **Antigravity**.
- **On explicit user request**: *"load context"*, *"catch me up"*, *"what was decided before"*, *"resume from where Claude Code / Antigravity left off"*.
- **Interactive standalone session start**: When operating in standalone `shared-context` mode with historical records in `context/sessions/`.
- **On-demand architectural or historical lookup**: Consulting `context/memory/architecture.md`, `context/memory/conventions.md`, or `context/memory/log/YYYY-MM-DD.md` when a task touches those domains.

### When NOT to Use
- **Repositories without `context/memory/` or `context/`**: Proceed immediately with standard task execution.
- **Explicit user instruction to start fresh**: Honor the user's request and bypass context restoration.
- **Recording new context or handoffs**: Route to `context-capture`.

## Process
### Mode A: LLM Wiki Progressive Disclosure (`context/memory/` — Primary)
When invoked by an orchestrator (`State 0` of `senior-dev`) or resuming work in a repository using the Cross-AI LLM Wiki:

1. **Step 1 — Check & Read Master Index Only (`~500 tokens`)**:
   - Check whether `context/memory/MEMORY.md` exists.
   - If it exists, read **ONLY `context/memory/MEMORY.md`** (`<= 80-100 lines`) to immediately absorb:
     - **Active Handoff State**: Which AI host (`Claude Code` or `Antigravity`) ran last, active branch/task, what was just completed, and immediate next steps.
     - **Key Architectural Decisions & Conventions Summary**: High-signal summary bullets and topic pointers.
     - **Recent Daily Logs Index**: Pointers to the last 5 daily logs (`context/memory/log/YYYY-MM-DD.md`).
2. **Step 2 — On-Demand Progressive Drill-Down (Never Eager-Load All Files)**:
   - Navigate to linked wiki pages **only on demand** if the current task specifically requires deeper context on that topic or date:
     - Read `context/memory/architecture.md` only when making or reviewing architectural/module-boundary changes.
     - Read `context/memory/conventions.md` only when verifying stack conventions, patterns, or durable user preferences.
     - Read a specific `context/memory/log/YYYY-MM-DD.md` file only when investigating historical task outcomes from that date.

### Mode B: Interactive Restore for Legacy Session Stores (`context/sessions/`)
When operating in standalone `shared-context` mode with per-session archives in `context/sessions/`:

1. **Non-Invasive Context Discovery**:
   Scan the `context/` directory to inspect available sessions without side effects:
   ```bash
   python3 ./skills/context-restore/scripts/context_list.py --json
   ```
   If `exists: false`, inform the user that no prior shared context exists and continue normally.
2. **Relevance Ranking**:
   - Sort by most recent sessions first.
   - Prioritize sessions whose `task` description matches or overlaps the current goal.
   - Identify any sessions marked `status: in-progress` or `status: blocked` (uncompleted work).
3. **Mandatory User Confirmation Menu**:
   Present a concise summary of findings to the user and request confirmation before loading session archives:
   - **Full**: Load summaries, decisions, `architecture.md`, and `preferences.md`.
   - **Light**: Load `architecture.md` and `preferences.md` only.
   - **Just list**: Display session overview without loading contents into working memory.
   - **Skip**: Start fresh without adopting prior context.
   *(Note: If `restore.askBeforeLoad` is `false` in `.contextrc.json`, you may load the Light set automatically, but still state what was loaded).*
4. **Approved Artifact Ingestion & Explicit Adoption Statement**:
   ```bash
   cat context/<date>/<session-id>/summary.md
   cat context/<date>/<session-id>/decisions.md
   cat context/architecture.md context/preferences.md

   # If detailed execution flow is needed, unpack the archive
   python3 ./skills/context-capture/scripts/context_pack.py --unpack <session-id>
   cat context/<date>/<session-id>/flows.md
   ```
   Report explicitly which past architectural decisions, user preferences, and pending TODOs are being resumed, and surface any conflicts with the current prompt.

## Usage
### Commands & Progressive Disclosure Reads
```bash
# Primary Mode A — Fast LLM Wiki Progressive Disclosure (read index first, drill down on demand):
cat context/memory/MEMORY.md
# Only if needed for current task scope:
cat context/memory/architecture.md
cat context/memory/conventions.md
cat context/memory/log/YYYY-MM-DD.md

# Mode B — Discover existing scripted sessions in machine-readable JSON format:
python3 ./skills/context-restore/scripts/context_list.py --json

# Human-readable session list:
python3 ./skills/context-restore/scripts/context_list.py
```

### Example Prompts
- *"Read `context/memory/MEMORY.md` and resume the task where Claude Code left off."*
- *"Check the shared context store and catch me up on what was worked on previously."*
- *"Load the architectural decisions from `context/memory/architecture.md` before we refactor the auth module."*

### Host Execution Instructions
- **Claude Code**: In `senior-dev` `State 0`, read `context/memory/MEMORY.md` directly and follow links on demand; in standalone `shared-context` mode, run `context_list.py --json` and ask the user (`Full / Light / Just list / Skip`).
- **Antigravity**: In `senior-dev` `State 0`, read `context/memory/MEMORY.md` silently and drill down on demand; in standalone `shared-context` mode, use `context-keeper` or `context_list.py --json` with user confirmation.

## Red Flags
- Eagerly reading all files in `context/memory/log/` or unpacking all historical archives at startup instead of reading **only `context/memory/MEMORY.md`** first and drilling down on demand.
- Silently ingesting heavy legacy `context/sessions/` archives in standalone mode without asking the user (`Full / Light / Just list / Skip`).
- Blindly following an obsolete decision that contradicts new explicit user instructions without surfacing the conflict.
- Ignoring active `Next / Pending` handoff items recorded in `context/memory/MEMORY.md`.

## Verification
- [ ] If `context/memory/MEMORY.md` exists in orchestrator mode (`State 0`), **only `context/memory/MEMORY.md`** is read initially (`~500 tokens`), with `architecture.md`, `conventions.md`, or `log/YYYY-MM-DD.md` loaded strictly on demand.
- [ ] In standalone legacy session mode (`context/sessions/`), context discovery script executes cleanly:
  ```bash
  python3 ./skills/context-restore/scripts/context_list.py --json
  ```
- [ ] In standalone legacy session mode, user is presented with `Full / Light / Just list / Skip` before session archive files are ingested.
- [ ] Active handoff state, architectural decisions, and conventions are accurately honored without token bloat.

## References
- [Restore checklist](references/restore-checklist.md)

