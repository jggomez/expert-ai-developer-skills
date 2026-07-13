# Rule: Context & Token Optimization

**Identifier**: `context-and-token-optimization`  
**Purpose**: Maximize code session efficiency, prevent token-window exhaustion, and reduce API usage costs by working modularly and utilizing local processing scripts.

---

## 1. Context Minimization Strategy

AI agents must actively manage their context window to avoid slower response times and token overflow:

* **Surgical Code Reads**: When reading files, specify exact line ranges (`StartLine` and `EndLine`) instead of reading whole files. Never read files larger than 1000 lines in full.
* **Directory Scopes**: Avoid listing very large directories recursively. List specific paths or use `grep` search with glob inclusions to find files.
* **Subagent Delegation**: For large tasks, define specialized subagents with narrow system prompts and task boundaries. This keeps the parent conversation clean.

---

## 2. Offloading Tasks to Local Scripts (Deterministic Code)

Instead of prompting the model to repeatedly process or parse raw datasets, text files, or git logs:

* **Create Helper Scripts**: Write small Python or Bash scripts to process text, run regex parses, or filter data.
* **Run Scripts Locally**: Run the script via the terminal and read the final summary output, rather than streaming raw logs into the agent conversation.
* **Avoid Repetitive Tool Execution**: Do not call `git status` or `list_dir` multiple times in a single loop if the workspace state has not changed.

---

## 3. RTK - Rust Token Killer Integration

When working in workspaces with `rtk` installed:

* **Transparent CLI hooks**: Always allow the Claude Code hook to rewrite standard Git and Dev commands through the token-optimized proxy.
* **Analytics Checks**: Developers can check execution analytics and token savings metrics using:
  ```bash
  rtk gain
  ```
* **Missed Opportunities Audit**: Analyze command history for token-saving optimizations using:
  ```bash
  rtk discover
  ```
* **Debug Bypass**: If a developer command fails due to hook filtering, run the raw command with:
  ```bash
  rtk proxy <cmd>
  ```
