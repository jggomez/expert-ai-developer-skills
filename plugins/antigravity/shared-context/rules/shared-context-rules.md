---
trigger: always_on
description: Shared context memory rules enforcing Cross-AI LLM Wiki (context/memory/) progressive disclosure, root AGENTS.md & Google DESIGN.md coordination, feature artifact separation (docs/<feature-name>/), State 5 milestone capture, and secret redaction.
---

# Shared Context Rules & Persistent Memory Protocol

**Identifier**: `shared-context-rules`

## 1. Scope Partitioning Across `context/memory/`, Root Governance & `docs/<feature-name>/`
- **Feature Directory (`docs/<feature-name>/`)**: Stores feature-scoped deliverables (`prd.md <= 70`, `design.md <= 35` delta, `adr-NNN-*.md <= 55`, `architecture.md <= 70`, `test-matrix.md <= 80`, verification reports `<= 50` lines).
- **Root Governance (`AGENTS.md` & `DESIGN.md`)**: Root `AGENTS.md` (`<= 90 lines`) holds verified build/test commands, conventions, and links to root Google `DESIGN.md` (`<= 110 lines` UI token spec) and `context/memory/MEMORY.md`.
- **Repository Memory (`context/memory/`)**: Durable Cross-AI LLM Wiki shared across **Claude Code** and **Google Antigravity**:
  - `MEMORY.md` (`<= 80-100 lines`, ~500 tokens): Active host, branch/task, key decisions, and pointers to `architecture.md`, `conventions.md`, `AGENTS.md`, `DESIGN.md`, and the last 5 daily logs (`log/YYYY-MM-DD.md`).
  - `architecture.md` & `conventions.md`: Updated in-place with durable cross-cutting invariants; `log/YYYY-MM-DD.md` holds append-only 5–8 line milestone entries.

## 2. Session Start Progressive Disclosure (State 0 of 3-Tier SDLC)
1. **Primary LLM Wiki (`context/memory/`)**: Check whether `context/memory/MEMORY.md` exists. If present, read **only `context/memory/MEMORY.md`** (~500 tokens) silently at State 0; open `architecture.md`, `conventions.md`, `DESIGN.md`, or `log/YYYY-MM-DD.md` strictly **on demand**.
2. **Standalone Scripted Session Store (`context/sessions/`)**: Check whether a `context/` directory with scripted sessions exists via:
   `python3 ./skills/context-restore/scripts/context_list.py --json`
   - If `exists` is `false` → continue normally, say nothing.
   - If `exists` is `true` → **before doing other work**, follow `context-restore`: summarize available sessions and **ask the user** which set to load (`Full / Light / Just list / Skip`), honoring `restore.askBeforeLoad` in `context/.contextrc.json`. State adopted decisions and resumed TODOs after loading.

## 3. Capture Timing & State 5 Rollover Protocol
- **Never save on intermediate turns, trivial Q&A, or tool loops.** Save **ONLY** at **State 5 (Ship & Finish)** after QA (`exit code 0`) and `compliance-verifier` (`APPROVED`) succeed, OR on explicit user handoff (*"save context"*, *"guarda contexto"*, *"hand off"*):
  1. Distill durable architectural invariants and conventions from `docs/<feature-name>/` into `context/memory/architecture.md` and `conventions.md` in-place (keeping feature-specific specs in `docs/<feature-name>/` and UI tokens in `DESIGN.md`).
  2. Append a 5–8 line block (`## [HH:MM | Host: Claude Code | Antigravity] <Task>`) to `context/memory/log/YYYY-MM-DD.md`.
  3. Overwrite `context/memory/MEMORY.md` in-place (`<= 80-100 lines`) and ensure root `AGENTS.md` (`<= 90 lines`) links remain synchronized if commands changed.
  4. When using scripted `context/sessions/`, flush via `context_snapshot.py --session <id> --status done`, `context_rollup.py`, and `context_pack.py --auto`.

## 4. Security & Redaction Invariants
- Never disable secret redaction (`--no-redact`) unless content is verified clean; never record credentials, tokens, or secrets in `context/` or chat, and never hand-edit `context/INDEX.md`.
