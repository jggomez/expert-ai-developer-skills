---
name: context-restore
description: Use at the start of a session, or when the user asks to "load context", "catch up", or "what was done before" — checks the shared context/ directory for prior AI sessions (Claude Code or Antigravity CLI), summarizes what is there, and loads decisions, flows, and preferences ONLY after the user confirms. Pairs with context-capture, which writes the records this reads.
---

# Context Restore Skill

## Overview
This skill restores durable context, architectural decisions, and working state from previous AI sessions stored in `context/`. It acts as a Cross-Agent Context Restorer, ensuring that context hand-offs between Claude Code and Antigravity CLI occur safely, transparently, and only with explicit user confirmation—preventing unintended context pollution.

## When to Use
### Trigger Scenarios
- At session start when a `context/` directory exists with prior session records.
- On explicit user request: *"load context"*, *"catch me up"*, *"what was decided before"*.
- Resuming complex, multi-day engineering tasks across different machines or agent hosts.
- Checking historical architecture decisions in `context/architecture.md`.

### When NOT to Use
- **Repositories without a `context/` directory**: Proceed with standard prompt execution.
- **Explicit user instruction to start fresh**: Honor request and bypass context restoration.
- **Recording new context**: Route to `context-capture`.

## Process
### Phase 1: Non-Invasive Context Discovery
Scan the `context/` directory to inspect available sessions without side effects:
```bash
python3 ./skills/context-restore/scripts/context_list.py --json
```
If `exists: false`, inform the user that no prior shared context exists and continue normally.

### Phase 2: Relevance Ranking
Analyze the output JSON:
1. Sort by most recent sessions first.
2. Prioritize sessions whose `task` description matches or overlaps the current goal.
3. Identify any sessions marked `status: in-progress` or `status: blocked` (uncompleted work).
4. Filter out stale or unrelated legacy sessions.

### Phase 3: Mandatory User Confirmation Menu
Present a concise summary of findings to the user and request confirmation before loading:
- **Full**: Load summaries, decisions, `architecture.md`, and `preferences.md`.
- **Light**: Load `architecture.md` and `preferences.md` only.
- **Just list**: Display session overview without loading contents into working memory.
- **Skip**: Start fresh without adopting prior context.
*(Note: If `restore.askBeforeLoad` is `false` in `.contextrc.json`, you may load the Light set automatically, but still state what was loaded).*

### Phase 4: Approved Artifact Ingestion
Read only the files approved by the user:
```bash
# Read loose overview and decision files
cat context/<date>/<session-id>/summary.md
cat context/<date>/<session-id>/decisions.md
cat context/architecture.md context/preferences.md

# If detailed execution flow is needed, unpack the archive
python3 ./skills/context-capture/scripts/context_pack.py --unpack <session-id>
cat context/<date>/<session-id>/flows.md
```

### Phase 5: Explicit Adoption Statement
Report to the user explicitly:
- Which past architectural decisions are being honored.
- Which user preferences are adopted.
- Which pending TODOs are being resumed.
- If a past decision conflicts with the current prompt, surface the conflict explicitly rather than overriding it silently.

## Usage
### Commands & Automation Scripts
```bash
# Discover existing sessions in machine-readable JSON format
python3 ./skills/context-restore/scripts/context_list.py --json

# Human-readable session list
python3 ./skills/context-restore/scripts/context_list.py
```

### Example Prompts
- *"Check the shared context store and catch me up on what was worked on previously."*
- *"Load the architectural decisions from yesterday's session before we begin coding."*
- *"What were the open TODOs left by the last AI agent in context/?"*

### Host Execution Instructions
- **Claude Code**: Execute `context_list.py` at session start, prompt the user with choices, and read approved markdown files.
- **Antigravity**: Launch `context-keeper` subagent to query context and align on historical decisions.

## Red Flags
- Silently reading and adopting past context files without user awareness or confirmation.
- Dumping entire historical archives into the prompt context, blowing through token budgets.
- Blindly following an obsolete decision that contradicts new explicit user instructions without surfacing the conflict.
- Ignoring unresolved blockers recorded in previous `in-progress` sessions.

## Verification
- [ ] Context discovery script executes cleanly:
  ```bash
  python3 ./skills/context-restore/scripts/context_list.py --json
  ```
- [ ] User presented with selection options before files are ingested.
- [ ] Explicit adoption statement delivered outlining recognized decisions and preferences.
- [ ] Only relevant, approved session files loaded into active memory.

## References
- [Restore checklist](references/restore-checklist.md)

