---
trigger: model_decision
description: Optimize context window, prevent token bloat, leverage local processing scripts, and minimize unnecessary file reading.
---

# Rule: Context & Token Optimization

**Identifier**: `context-and-token-optimization`

## 1. Context Minimization Directives

* **MUST** specify exact line ranges (`StartLine`/`EndLine`) when viewing files. **NEVER** view full files >1000 lines.
* **MUST NOT** perform unconstrained recursive directory listings on large paths; use targeted `grep_search` with glob filters.
* **MUST** delegate isolated sub-tasks to subagents (`invoke_subagent`) to prevent main context exhaustion.
* **NEVER** re-read unchanged files or re-run duplicate shell/directory commands in the same turn loop.

## 2. Deterministic Scripting & Output Discipline

* **MUST** offload heavy data parsing, text processing, or log filtering to local Python/Bash scripts in `scratch/`.
* **MUST** prefer commands that summarize output (`--stat`, `-q`, `| tail`, `| head`) over raw verbose logs when the full output isn't needed.
* **MUST** inspect summarized script results rather than streaming raw logs into the agent context window.
