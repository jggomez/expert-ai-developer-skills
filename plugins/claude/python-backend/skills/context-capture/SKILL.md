---
name: context-capture
description: Use when finishing a task at State 5 (Ship & Finish) or when the user explicitly asks to "save context", "guarda contexto", "record decisions", or "hand off" — writes ultra-compact persistent memory to the Cross-AI LLM Wiki (context/memory/) shared seamlessly between Claude Code and Google Antigravity, alongside optional scripted session archives.
---

# Context Capture Skill

## Overview
This skill preserves durable context, architectural decisions, conventions, and active handoff state across AI sessions using the **Cross-AI LLM Wiki (`context/memory/`)** as the primary, ultra-compact persistent memory architecture shared seamlessly between **Claude Code** and **Google Antigravity**. By updating living topic wiki pages in-place and appending concise milestone blocks to a single daily log, subsequent sessions resume with zero context amnesia and minimal token overhead. It also supports an optional scripted session-archive mode (`context/sessions/`) for full session snapshotting, secret redaction, and `.tar.xz` compression.

## When to Use
### Token Conservation & Trigger Timing Rules
- **At `State 5 (Ship & Finish)` in `senior-dev`**: Save context **ONLY at `State 5 (Ship & Finish)`** after both `qa-tester` (`exit 0`) and `compliance-verifier` (`APPROVED`) succeed.
- **On explicit user handoff request**: When the user explicitly asks to save state (*"save context"*, *"guarda contexto"*, *"record this decision"*, *"prepare handoff"*) before switching between **Claude Code** and **Antigravity**.
- **Standalone `shared-context` checkpoints**: When explicitly requested or closing a standalone session with significant architectural decisions.

### When NOT to Use
- **Intermediate turns or every few tool calls**: Never save on intermediate workflow states (`State 0` through `State 4`), routine file edits, or every few tool invocations.
- **Trivial Q&A or exploration**: Do not capture sessions that involved pure question-answering, read-only exploration, or zero architectural/code changes.
- **Temporary troubleshooting chatter**: Discard intermediate dead ends unless their failure establishes a durable constraint in `context/memory/architecture.md`.

## Process
### Mode A: Primary Cross-AI LLM Wiki (`context/memory/`)
Maintain the 4-part self-compacting LLM Wiki under `context/memory/` so both **Claude Code** and **Google Antigravity** share a deterministic, low-token handoff store:

1. **`context/memory/MEMORY.md` (Master Wiki Home Index & Active Handoff State)**:
   - Strictly capped at **`<= 80-100 lines`**, overwritten and compacted in-place so it never bloats.
   - Must contain three structured blocks:
     1. **Active Handoff State**: Last AI host (`Claude Code` or `Antigravity`), active branch/task, what was just completed, and immediate next steps.
     2. **Key Architectural Decisions & Conventions Summary**: High-signal bullet points referencing the topic wiki pages: `` `[architecture.md]` (`./architecture.md`) `` and `` `[conventions.md]` (`./conventions.md`) ``.
     3. **Recent Daily Logs Index**: Relative pointers to the last 5 daily log files: `` `[YYYY-MM-DD.md]` (`./log/YYYY-MM-DD.md`) ``.
2. **`context/memory/architecture.md` (Living Architecture & ADR Digest)**:
   - Updated in-place when architectural decisions, module boundaries, or trade-offs are established, avoiding duplicate per-session decision files.
3. **`context/memory/conventions.md` (Durable Stack Conventions & Preferences)**:
   - Updated in-place with durable coding conventions, tooling patterns, and explicit cross-session user preferences.
4. **`context/memory/log/YYYY-MM-DD.md` (Single Daily Chronological Log)**:
   - One file per calendar date. Each completed milestone (`State 5: Ship & Finish` in `senior-dev`) or explicit user handoff appends a concise 5-8 line block:
     ```markdown
     ## [HH:MM | Host: Claude Code | Antigravity] <Task Title>
     - **Outcome**: <1-2 lines of what was built and verified>
     - **Decisions**: <1-2 lines or link to ../architecture.md>
     - **Next / Pending**: <Immediate next step for the next AI session>
     ```

### Mode B: Optional Scripted Session Archive (`context/sessions/`)
When operating in standalone `shared-context` scripted archive mode, use the CLI utilities to scaffold, roll up, and compress per-session records:

1. **Session Scaffolding**:
   ```bash
   python3 ./skills/context-capture/scripts/context_snapshot.py \
     --task "<one line task summary>" --agent "<model-id>" --status in-progress
   ```
   The script auto-detects the host, records git diff stats, and applies an automated secret redaction sweep (`«REDACTED:...»`).
2. **Relevant Artifact Authoring (`context/sessions/` or `context/<date>/<session-id>/`)**:

   | File | What to Include | What to Skip |
   | :--- | :--- | :--- |
   | **`summary.md`** | High-level outcome in plain language, current state, immediate next steps. | Detailed blow-by-blow narration. |
   | **`decisions.md`** | Architectural choices with real trade-offs that future agents must respect. | Trivial localized syntax choices. |
   | **`flows.md`** | The execution path taken, including dead ends and why they failed. | Obvious steps clear from the git diff. |
   | **`topics.md`** | Discussion topics, open questions, and pending TODOs. | Ephemeral conversational chatter. |
   | **`context/preferences.md`** | Explicit, durable, cross-session user preferences. | One-off prompt instructions. |

3. **Rollup, Retention & Compression**:
   ```bash
   # 1. Mark session as done
   python3 ./skills/context-capture/scripts/context_snapshot.py --session <id> --status done

   # 2. Roll up decisions into architecture.md and apply retention policies
   python3 ./skills/context-capture/scripts/context_rollup.py

   # 3. Compress older session details into detail.tar.xz (keeping newest loose)
   python3 ./skills/context-capture/scripts/context_pack.py --auto
   ```

## Usage
### LLM Wiki Handoff & Automated CLI Scripts
```bash
# Primary LLM Wiki structure maintained at State 5 or explicit handoff:
# context/memory/MEMORY.md          (<= 80-100 lines, overwritten in-place)
# context/memory/architecture.md    (living ADR & architecture digest)
# context/memory/conventions.md     (durable stack conventions & user preferences)
# context/memory/log/YYYY-MM-DD.md  (5-8 line milestone block appended per task)

# Optional scripted session archive mode:
python3 ./skills/context-capture/scripts/context_snapshot.py --task "Implement OAuth2 flow" --agent "gemini-3.8-flash" --status in-progress
python3 ./skills/context-capture/scripts/context_snapshot.py --session <session-id> --status done
python3 ./skills/context-capture/scripts/context_rollup.py
python3 ./skills/context-capture/scripts/context_pack.py --auto
python3 ./skills/context-capture/scripts/context_pack.py --unpack <session-id>
```

### Example Prompts
- *"Save context (`guarda contexto`) in `context/memory/` so I can switch from Claude Code to Antigravity and resume immediately."*
- *"Record this decision to use JWT tokens with RSA-256 in `context/memory/architecture.md` and update `MEMORY.md`."*
- *"We finished State 5 verification—update `context/memory/MEMORY.md` and append the milestone entry to today's `context/memory/log/YYYY-MM-DD.md`."*

### Host Execution Instructions
- **Claude Code**: Update `context/memory/MEMORY.md`, `architecture.md`, `conventions.md`, and `log/YYYY-MM-DD.md` at `State 5` or on explicit handoff (or run the snapshot/rollup scripts in scripted mode).
- **Antigravity**: Update `context/memory/` at `State 5` or launch `context-keeper` subagent to persist the LLM Wiki handoff state and optional session archives.

## Red Flags
- Saving context on intermediate turns, trivial Q&A, or every few tool calls instead of waiting for `State 5 (Ship & Finish)` or an explicit user handoff request.
- Allowing `context/memory/MEMORY.md` to exceed 100 lines or appending endlessly without compacting in-place.
- Creating duplicate per-task architecture files instead of updating `context/memory/architecture.md` and `context/memory/conventions.md` in-place.
- Disabling the automated secret redaction scanner (`--no-redact`) or storing unredacted passwords, JWT tokens, or cloud credentials in `context/`.
- Recording verbose narrative logs instead of crisp, actionable 5-8 line daily log entries.

## Verification
- [ ] `context/memory/MEMORY.md` is updated in-place, strictly `<= 80-100 lines`, and records the active host (`Claude Code` or `Antigravity`), branch/task, completed work, next steps, wiki links, and last 5 daily logs.
- [ ] `context/memory/architecture.md` and `context/memory/conventions.md` are updated in-place when architectural decisions or durable conventions changed.
- [ ] `context/memory/log/YYYY-MM-DD.md` has a concise 5-8 line milestone block appended (`Outcome`, `Decisions`, `Next / Pending`).
- [ ] If using optional scripted archive mode, snapshot, rollup, and compression scripts execute cleanly:
  ```bash
  python3 ./skills/context-capture/scripts/context_snapshot.py --status done
  python3 ./skills/context-capture/scripts/context_rollup.py
  python3 ./skills/context-capture/scripts/context_pack.py --auto
  ```

## References
- [Session-record schema & field guide](references/record-schema.md)

