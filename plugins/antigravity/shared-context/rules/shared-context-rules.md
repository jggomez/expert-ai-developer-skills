---
trigger: always_on
description: Shared context working memory rules enforcing Cross-AI LLM Wiki (context/memory/) progressive disclosure, feature artifact separation (docs/<feature-name>/), milestone capture, session restoration, and secret redaction.
---

# Shared Context Rules & Persistent Memory Protocol

**Identifier**: `shared-context-rules`

These rules govern cross-agent persistent memory across **Claude Code** and **Google Antigravity** using the **Cross-AI LLM Wiki (`context/memory/`)** alongside the scripted `context/` session store, enforcing strict separation between repository-level memory and feature-level discovery artifacts.

## 1. Scope Partitioning: Repository Memory (`context/memory/`) vs. Feature Artifacts (`docs/<feature-name>/`)

- **Feature Directory (`docs/<feature-name>/`)**:
  - Dedicated to feature-scoped discovery deliverables (`prd.md`, `design.md`, `architecture.md`, `adr-*.md`) and verification deliverables (`test-matrix.md`, `critic-review.md`, `adversarial-report.md`, `blackbox-report.md`).
  - Scoped strictly to the specific feature or epic lifecycle; preserves fine-grained acceptance criteria, wireframe specifications, and test execution matrices.
- **Repository Memory (`context/memory/`)**:
  - Dedicated to durable, cross-AI persistent repository memory shared seamlessly across **Claude Code** and **Google Antigravity**.
  - `MEMORY.md`: Active cross-AI handoff index (`<= 80-100 lines`, ~500 tokens) capturing active host platform, current branch/task, key decisions, and links to topic pages and recent daily logs.
  - `architecture.md`: Repository-wide architectural invariants, layer boundaries, system topology, and durable patterns. Updated in-place.
  - `conventions.md`: Durable coding standards, testing rules, and project-wide conventions. Updated in-place.
  - `log/YYYY-MM-DD.md`: Append-only daily milestone log capturing high-level progress entries.
- **State 5 Rollover Protocol**:
  - At **State 5 (Ship & Finish)**, after QA (`exit code 0`) and compliance verification (`APPROVED`) succeed:
    1. Distill enduring, repository-wide architectural decisions from `docs/<feature-name>/architecture.md` into `context/memory/architecture.md` in-place.
    2. Record durable conventions into `context/memory/conventions.md` in-place.
    3. Append a concise 5-8 line milestone block (`## [HH:MM | Host: Claude Code | Antigravity] <Task Title>`) to `context/memory/log/YYYY-MM-DD.md`.
    4. Compact and overwrite `context/memory/MEMORY.md` in-place (`<= 80-100 lines`) with latest state and updated log links.
    5. Fine-grained feature specs, wireframes, and verification matrices remain permanently archived in `docs/<feature-name>/`.

## 2. At the Start of Every Session (Progressive Disclosure)

1. **LLM Wiki Progressive Disclosure (`context/memory/` — Orchestrator `State 0`)**:
   - Check whether `context/memory/MEMORY.md` exists.
   - If it exists, read **only `context/memory/MEMORY.md`** (`<= 80-100 lines`, ~500 tokens) to absorb the active cross-AI handoff state (`Claude Code` or `Antigravity`), key decisions, and recent log index.
   - Navigate to `context/memory/architecture.md`, `context/memory/conventions.md`, or `context/memory/log/YYYY-MM-DD.md` **only on demand** when the current task requires deeper context on that topic or date.
2. **Standalone Scripted Session Store (`context/sessions/`)**:
   - When operating in standalone `shared-context` mode, check whether a `context/` directory with prior scripted sessions exists:
     `python3 ./skills/context-restore/scripts/context_list.py --json`
   - If `exists` is `false` → continue normally, say nothing.
   - If `exists` is `true` → **before doing other work**, follow the `context-restore` skill: summarize what is there and **ask the user** which set to load — Full / Light / Just list / Skip. Load nothing from `context/sessions/` without an explicit answer. Honor `restore.askBeforeLoad` in `context/.contextrc.json`.
   - After loading, state exactly which decisions and preferences you will follow and which TODOs you are resuming.

## 3. Token-Conserving Capture Timing (When to Save)

- **Never save on intermediate turns, trivial Q&A, or every few tool calls** during orchestrated development.
- Save context **ONLY**:
  1. At **`State 5 (Ship & Finish)`** in `senior-dev` after both `qa-tester` (`exit 0`) and `compliance-verifier` (`APPROVED`) succeed (plus full adversarial review committee for Tier 3), OR
  2. When the user explicitly requests a handoff (*"save context"*, *"guarda contexto"*, *"hand off"*) before switching between **Claude Code** and **Antigravity**.

## 4. Updating the Cross-AI LLM Wiki & Session Store

- **Primary LLM Wiki (`context/memory/`)**:
  - Overwrite and compact `context/memory/MEMORY.md` in-place (`<= 80-100 lines`) with the active handoff state, links to `[architecture.md](./architecture.md)` and `[conventions.md](./conventions.md)`, and the last 5 daily logs (`[YYYY-MM-DD.md](./log/YYYY-MM-DD.md)`).
  - Update `context/memory/architecture.md` and `context/memory/conventions.md` in-place when architectural decisions or durable conventions change.
  - Append a concise 5-8 line milestone block (`## [HH:MM | Host: Claude Code | Antigravity] <Task Title>`) to `context/memory/log/YYYY-MM-DD.md`.
- **Optional Scripted Session Store (`context/sessions/`)**:
  - If using scripted session archives, flush the record: `context_snapshot.py --session <id> --status done`, then `context_rollup.py`, then `context_pack.py --auto`.
  - Keep `decisions.md` bullets self-contained — they are copied verbatim into `context/architecture.md`.

## 5. Security & Redaction Invariants

- Never disable secret redaction (`--no-redact`) unless the content is certainly clean. Never echo credentials into `context/` records or chat.
- Never hand-edit `INDEX.md` or another session's archive files directly.
