---
name: context-capture
description: Use when finishing a task, at a periodic checkpoint, or when the user asks to "save context", "record decisions", or "hand off" — writes what was done, why, and how into a shared context/ directory that other AI agents (Claude Code, Antigravity CLI) can later load. Covers the session-record schema, secret redaction, tar.xz compression of old sessions, and rolling decisions up into an architecture log.
---

# Context Capture Skill

## Overview
This skill preserves durable context, architectural decisions, execution flows, and long-term user preferences across AI sessions. It acts as a Cross-Agent Memory Coordinator, writing structured records to a shared `context/` directory so that subsequent agents—whether running on Claude Code or Antigravity CLI—can seamlessly resume ongoing work without context amnesia.

## When to Use
### Trigger Scenarios
- **On session end or task completion**: Always record context if meaningful code edits or architectural choices were made.
- **Periodic checkpoints**: When nudged by session hooks (e.g. every 25 tool calls) or before embarking on a high-risk refactoring step.
- **On explicit user request**: *"save context"*, *"record this decision"*, *"prepare handoff"*.

### When NOT to Use
- **Pure question-answering**: Do not capture sessions that involved no repository modifications and zero architectural decisions.
- **Temporary troubleshooting chatter**: Discard intermediate dead ends unless their failure provides a crucial rationale against repeating them.

## Process
### Phase 1: Session Scaffolding
Initialize or refresh the active session's record using the automated snapshot tool:
```bash
python3 ./skills/context-capture/scripts/context_snapshot.py \
  --task "<one line task summary>" --agent "<model-id>" --status in-progress
```
The script auto-detects the host, records git diff stats, and applies an automated secret redaction sweep (`«REDACTED:...»`).

### Phase 2: Relevant Artifact Authoring
Populate the generated markdown files under `context/<date>/<session-id>/`:

| File | What to Include | What to Skip |
| :--- | :--- | :--- |
| **`summary.md`** | High-level outcome in plain language, current state, immediate next steps. | Detailed blow-by-blow narration. |
| **`decisions.md`** | Architectural choices with real trade-offs that future agents must respect. | Trivial localized syntax choices. |
| **`flows.md`** | The execution path taken, including dead ends and why they failed. | Obvious steps clear from the git diff. |
| **`topics.md`** | Discussion topics, open questions, and pending TODOs. | Ephemeral conversational chatter. |
| **`context/preferences.md`** | Explicit, durable, cross-session user preferences. | One-off prompt instructions. |

### Phase 3: Rollup, Retention & Compression
When closing the session or completing the task:
```bash
# 1. Mark session as done
python3 ./skills/context-capture/scripts/context_snapshot.py --session <id> --status done

# 2. Roll up decisions into architecture.md and apply retention policies
python3 ./skills/context-capture/scripts/context_rollup.py

# 3. Compress older session details into detail.tar.xz (keeping newest loose)
python3 ./skills/context-capture/scripts/context_pack.py --auto
```

## Usage
### Commands & Automation Scripts
```bash
# Start or update session record
python3 ./skills/context-capture/scripts/context_snapshot.py --task "Implement OAuth2 flow" --agent "gemini-3.8-flash" --status in-progress

# Finalize session and roll up decisions
python3 ./skills/context-capture/scripts/context_snapshot.py --session <session-id> --status done
python3 ./skills/context-capture/scripts/context_rollup.py
python3 ./skills/context-capture/scripts/context_pack.py --auto

# Unpack an archived historical session for inspection
python3 ./skills/context-capture/scripts/context_pack.py --unpack <session-id>
```

### Example Prompts
- *"Save the context of this session so the next agent can resume from where we left off."*
- *"Record this decision to use JWT tokens with RSA-256 in the shared context architecture log."*
- *"Capture our current progress as a checkpoint before we start refactoring the database layer."*

### Host Execution Instructions
- **Claude Code**: Run the snapshot and rollup scripts directly in bash at session checkpoints.
- **Antigravity**: Launch `context-keeper` subagent or execute capture scripts before ending complex runs.

## Red Flags
- Disabling the automated secret redaction scanner (`--no-redact`) without verification.
- Recording verbose narrative logs instead of crisp, actionable outcomes and decisions.
- Overwriting `context/preferences.md` with temporary, task-specific instructions.
- Storing unredacted passwords, JWT tokens, or cloud credentials in context files.

## Verification
- [ ] Session snapshot script executes without errors:
  ```bash
  python3 ./skills/context-capture/scripts/context_snapshot.py --status done
  ```
- [ ] `summary.md` and `decisions.md` populated with clear, concise content.
- [ ] Decision rollup executed and appended to `context/architecture.md`:
  ```bash
  python3 ./skills/context-capture/scripts/context_rollup.py
  ```
- [ ] Older session details compressed cleanly via `context_pack.py --auto`.

## References
- [Session-record schema & field guide](references/record-schema.md)

