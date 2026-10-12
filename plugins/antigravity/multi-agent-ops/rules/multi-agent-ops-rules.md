---
trigger: always_on
description: Multi-agent operations rules enforcing finite self-correction loops, Parallel Fan-Out/Fan-In workspace isolation (Disjoint Files vs Git Worktrees), parallel verification, Cross-AI LLM Wiki continuity, and token conservation.
---

# Multi-Agent Operations & Loop Engineering Rules

**Identifier**: `multi-agent-ops-rules`

## 1. Finite Self-Correction Protocol
- **Max 3 Retries**: When automated test suites or linters fail, the agent is permitted a maximum of **3 self-correction iterations**.
- **User Escalation**: If the error cannot be resolved within 3 iterations, the agent **MUST** pause and ask the user for clarification or guidance using `ask_question`, explaining the root cause and attempted remediations.
- **Infinite Loop Ban**: Never enter unbounded retry loops attempting blind variations of failing code.

## 2. Workspace & Context Isolation (Parallel Fan-Out / Fan-In)
- **Mode A — Disjoint File Partitioning (`Workspace: 'inherit'`) [Default]**:
  - When concurrent subagents operate on strictly non-overlapping `Owned Files` sets, dispatch them in parallel with `Workspace: 'inherit'` (or concurrent `Agent(...)` calls in Claude Code).
  - Each subagent prompt MUST list its `Exclusive Owned Files` and forbid edits outside that partition, achieving zero `git merge` or worktree overhead upon Fan-In.
- **Mode B — Git Worktree Isolation (`Workspace: 'branch'` / `'share'` or `git worktree`)**:
  - Used when concurrent subagents must touch shared files (`package.json`, `pubspec.yaml`, shared routers, DI containers) or run conflicting build processes.
  - Each parallel worker executes in an isolated git branch/worktree (`git worktree add ../wt-<track> -b feat/<track>`) and merges cleanly at Fan-In before final QA.
- **Parallel Verification Fan-Out**:
  - Run `qa-tester` (`exit code 0` empirical test proof) and `compliance-verifier` (read-only static, OWASP, and architectural invariant audit yielding `APPROVED`) concurrently upon implementation Fan-In.
- **Cross-AI LLM Wiki Continuity (`context/memory/`)**:
  - At **State 0**, silently read `context/memory/MEMORY.md` (~500 tokens) and open linked wiki pages (`architecture.md`, `conventions.md`, `log/YYYY-MM-DD.md`) only on demand.
  - At **State 5 (Ship & Finish)**, update `context/memory/MEMORY.md` in-place (<= 80-100 lines), update `architecture.md` / `conventions.md` in-place when applicable, and append a 5-8 line milestone entry to `context/memory/log/YYYY-MM-DD.md`. Never write checkpoints on intermediate turns.
- **Reactive Wakeup**: Do NOT poll in a loop for task or subagent status. Trust the system's reactive message delivery.

## 3. Token-Optimized Research
- Never dump multi-thousand-line files into the conversation context when locating a function or symbol. Use `grep_search` or slice notation (`StartLine` and `EndLine`) with `view_file`.
