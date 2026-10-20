# Multi-Agent Ops Plugin (Claude Code)

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](https://github.com/jggomez/expert-ai-developer-skills)
[![Plugin](https://img.shields.io/badge/Plugin-multi--agent--ops-green?style=flat-square)](.)

The `multi-agent-ops` plugin packages manager-worker orchestration, **Mode A (Disjoint File Partitioning)** and **Mode B (Git Worktree Isolation)** parallel execution, self-correcting development loops, and context-guard safety gates for **Claude Code**.

---

## 1. Directory Tree & Architecture

```
plugins/claude/multi-agent-ops/
├── README.md                       # This usage manual
├── .claude-plugin/
│   └── plugin.json                 # Claude Code plugin manifest
├── hooks.json                      # Hook registrations
├── hooks/
│   └── context-guard-gate.js       # PreToolUse gate protecting token budget
└── skills/
    ├── loop-engineering/           # Manager-worker parallel-agent workflows (Mode A & Mode B)
    └── repo-research/              # Repository structure/dependency analysis & project-context generation
```

---

## 2. Bundled Skills (2 Packaged Modules)

1. **`loop-engineering`**: Guides parallel subagent dispatching via the `Agent` tool across **Mode A: Disjoint File Partitioning** (default in-tree parallel execution when workers own strictly non-overlapping files) and **Mode B: Git Worktree Isolation** (separate git worktrees when tracks touch shared files), concurrent `qa-tester` + `compliance-verifier` verification, self-correction loops bounded by the 3-loop cap, and PR review automation patterns.
2. **`repo-research`**: Analyzes a repository's structure, technologies, and dependency graph to produce or update a project context document.

---

## 3. Lifecycle Hooks & Token Guard

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`PreToolUse`** | `hooks/context-guard-gate.js` | Intercepts large file read operations, preventing massive token dumps and enforcing offset budgets. |

---

## 4. Installation

In Claude Code, install from marketplace or local path:
```bash
/plugin install multi-agent-ops
# or local:
claude plugin install plugins/claude/multi-agent-ops
```
