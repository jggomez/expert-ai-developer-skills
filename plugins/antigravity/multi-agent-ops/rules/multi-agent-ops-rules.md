---
trigger: always_on
description: Multi-agent operations rules enforcing finite self-correction loops, token conservation, and subagent workspace isolation.
---

# Multi-Agent Operations & Loop Engineering Rules

**Identifier**: `multi-agent-ops-rules`

## 1. Finite Self-Correction Protocol
- **Max 3 Retries**: When automated test suites or linters fail, the agent is permitted a maximum of **3 self-correction iterations**.
- **User Escalation**: If the error cannot be resolved within 3 iterations, the agent **MUST** pause and ask the user for clarification or guidance using `ask_question`, explaining the root cause and attempted remediations.
- **Infinite Loop Ban**: Never enter unbounded retry loops attempting blind variations of failing code.

## 2. Workspace & Context Isolation
- **No Concurrent Overlap**: Multiple parallel subagents must never be assigned to edit the same file simultaneously without isolated branch workspaces (`Workspace: 'branch'`).
- **Reactive Wakeup**: Do NOT poll in a loop for task or subagent status. Trust the system's reactive message delivery.

## 3. Token-Optimized Research
- Never dump multi-thousand-line files into the conversation context when locating a function or symbol. Use `grep_search` or slice notation (`StartLine` and `EndLine`) with `view_file`.
