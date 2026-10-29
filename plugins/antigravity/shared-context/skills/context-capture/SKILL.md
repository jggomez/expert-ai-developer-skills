---
name: context-capture
description: Use when finishing a task at State 5 (Ship & Finish) or when the user explicitly asks to "save context", "guarda contexto", "record decisions", or "hand off" — writes ultra-compact persistent memory to context/memory/ and ensures target-project root AGENTS.md (<= 90 lines) stays wired to DESIGN.md and MEMORY.md across Claude Code and Google Antigravity.
---

# Context Capture Skill

## Overview
This skill preserves durable project context, architectural decisions, conventions, and active handoff state across AI sessions using the **Cross-AI LLM Wiki (`context/memory/`)** shared seamlessly between **Claude Code** and **Google Antigravity**. At milestone completion (`State 5`), it updates living wiki pages in-place, appends a concise daily log block, and ensures target user repositories maintain a concise root **`AGENTS.md` (`<= 90 lines`)** wired to executable commands, root `DESIGN.md`, and `context/memory/MEMORY.md`. It also supports an optional scripted archive mode (`context/sessions/`).

## When to Use
### Token Conservation & Trigger Timing Rules
- **At `State 5 (Ship & Finish)`**: Run **ONLY** after QA verification (`exit code 0`) and compliance audit (`APPROVED`) pass.
- **On explicit user handoff request**: When the user asks to *"save context"*, *"guarda contexto"*, *"record decisions"*, or *"hand off"* between **Claude Code** and **Antigravity**.
- **Standalone `shared-context` checkpoints**: When closing a standalone session containing durable architectural or convention changes.

### When NOT to Use
- **Intermediate workflow states (`State 0`–`State 4`)**: Never checkpoint every few tool calls or mid-implementation.
- **Read-only Q&A or exploration**: Skip when zero code, architecture, or convention changes occurred.

## Process
### Mode A: Primary Cross-AI LLM Wiki (`context/memory/`) + Target-Project `AGENTS.md` Sync
1. **`context/memory/MEMORY.md` (Master Wiki Index & Handoff State, `<= 80-100 lines`)**:
   - Overwrite and compact in-place with three crisp blocks:
     1. **Active Handoff State**: Last AI host (`Claude Code` or `Antigravity`), active branch/task, completed milestone, and immediate next step.
     2. **Key Architecture & Conventions Summary**: High-signal bullets pointing to `` `[architecture.md]` (`./architecture.md`) `` and `` `[conventions.md]` (`./conventions.md`) ``.
     3. **Recent Daily Logs Index**: Relative pointers to the 5 latest daily logs: `` `[YYYY-MM-DD.md]` (`./log/YYYY-MM-DD.md`) ``.
2. **`context/memory/architecture.md` & `context/memory/conventions.md`**:
   - Update in-place only when structural decisions, module boundaries, or durable coding/tooling conventions changed.
3. **`context/memory/log/YYYY-MM-DD.md` (Single Daily Chronological Log)**:
   - Append one concise 5–8 line milestone block per completed task:
     ```markdown
     ## [HH:MM | Host: Claude Code | Antigravity] <Task Title>
     - **Outcome**: <1-2 lines of what was built and verified>
     - **Decisions**: <1-2 lines or pointer to ../architecture.md>
     - **Next / Pending**: <Immediate next step for the next AI session>
     ```
4. **Target-Project Root `AGENTS.md` Bootstrap / Sync (`<= 90 lines`)**:
   - When operating in a target user repository that lacks a root `AGENTS.md`—or when build/test/lint commands, tech stack, directory conventions, or root `DESIGN.md` changed—bootstrap or update root `AGENTS.md` (`<= 90 lines`, following the 4-section open `AGENTS.md` template in `skills/loop-engineering/references/project-agents-template.md`):
     1. `## 1. Project Overview & Tech Stack` (3–5 lines)
     2. `## 2. Executable Commands` (`Install`, `Dev`, `Test`, `Lint / Typecheck`, `Build`)
     3. `## 3. Architecture & Coding Conventions` (directory layout & non-obvious invariants)
     4. `## 4. Design & Persistent Memory` (explicit links to root `DESIGN.md` for UI tokens and `context/memory/MEMORY.md` + `architecture.md`/`conventions.md`/`log/` for silent cross-session AI memory).

### Mode B: Optional Scripted Session Archive (`context/sessions/`)
For standalone `shared-context` archive workflows with automated secret redaction (`«REDACTED:...»`) and `.tar.xz` compression:
```bash
python3 ./skills/context-capture/scripts/context_snapshot.py --task "<summary>" --agent "<model-id>" --status in-progress
python3 ./skills/context-capture/scripts/context_snapshot.py --session <id> --status done
python3 ./skills/context-capture/scripts/context_rollup.py
python3 ./skills/context-capture/scripts/context_pack.py --auto
```

## Usage
```bash
# Primary State 5 / handoff files:
# AGENTS.md                         (<= 90 lines in target projects; links DESIGN.md & MEMORY.md)
# context/memory/MEMORY.md          (<= 80-100 lines, compacted in-place)
# context/memory/architecture.md    (living ADR & boundary digest)
# context/memory/conventions.md     (durable stack & user conventions)
# context/memory/log/YYYY-MM-DD.md  (5-8 line milestone block appended)

# Optional unpack helper for archived sessions:
python3 ./skills/context-capture/scripts/context_pack.py --unpack <session-id>
```
- **Claude Code / Antigravity**: Update `context/memory/` (and bootstrap/sync target-project root `AGENTS.md` when missing or outdated) at `State 5` or explicit handoff.

## Red Flags
- ❌ Writing checkpoints on intermediate turns (`State 0`–`State 4`) or trivial Q&A prompts.
- ❌ Letting `context/memory/MEMORY.md` exceed `100 lines` or root `AGENTS.md` in target projects exceed `90 lines`.
- ❌ Leaving a target project without a root `AGENTS.md` pointing to `DESIGN.md` (when UI exists) and `context/memory/MEMORY.md`.
- ❌ Storing unredacted secrets, tokens, or credentials anywhere under `context/`.

## Verification
- [ ] `context/memory/MEMORY.md` updated in-place (`<= 80-100 lines`) with host, branch/task, summary links, and last 5 daily logs.
- [ ] `context/memory/architecture.md` and `context/memory/conventions.md` updated in-place if architecture or conventions changed.
- [ ] `context/memory/log/YYYY-MM-DD.md` has a 5–8 line milestone entry appended.
- [ ] Target-project root `AGENTS.md` (`<= 90 lines`) bootstrapped or updated when missing or when commands/architecture/`DESIGN.md` changed.

## References
- [Session-record schema & field guide](references/record-schema.md)
