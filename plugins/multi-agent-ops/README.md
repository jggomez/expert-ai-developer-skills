# Multi-Agent Ops Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-multi--agent--ops-green?style=flat-square)](file:///./)

The `multi-agent-ops` plugin packages the repository's manager-worker orchestration and repo-analysis skills as a minimal plugin for **both Antigravity CLI and Claude Code** — the two skills in this repo's catalog that weren't yet bundled into any other plugin. Since it's skills-only, the same plugin folder installs unchanged on either host. §3 below covers a real, separate platform gap around scheduled automation specifically (Antigravity has it via `sidecars/`, Claude Code doesn't have a plugin-bundleable equivalent).

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing either skill under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/multi-agent-ops/
├── README.md                       # This usage manual
├── plugin.json                     # Required plugin metadata descriptor
└── skills/
    ├── loop-engineering/           # Manager-worker parallel-agent workflows, isolated workspaces
    └── repo-research/              # Repository structure/dependency analysis & project-context generation
```

---

## 2. Bundled Skills (2 Packaged Modules)

1. **`loop-engineering`**: Guides parallel subagent dispatching in isolated workspaces (e.g. separate git worktrees per worker), self-correction loops, and PR review automation patterns.
2. **`repo-research`**: Analyzes a repository's structure, technologies, and dependency graph to produce or update a project context document — the same script the root `agents/README.md`/`plugins/senior-dev` topology can call on to ground itself before planning.

---

## 3. On Scheduled/Background Automation (Important Platform Gap)

This repository's root [`sidecars/`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars) directory describes **Antigravity-only** cron-scheduled background daemons (`pr-reviewer-cron`, `incoming-reviews-alert`, `workspace-daemon`) declared via a `sidecar.json` manifest that Antigravity's runtime auto-discovers.

**Claude Code plugins have no equivalent static manifest for recurring scheduled tasks.** Verified against current Claude Code plugin docs: there is no `cron/`, `schedule.json`, or sidecar-style directory a plugin can bundle to auto-register a periodic job. The closest Claude Code features are:
- **Routines** (the `/schedule` command) — created interactively per-account, not declared inside a plugin.
- **Monitors** (`monitors/monitors.json`) — session-lifetime background watchers triggered by conditions, not cron schedules; not used by this plugin since it's a different mechanism than what `sidecars/` provides and wasn't part of what this plugin set out to reuse.

So this plugin intentionally ships **only** the two skills above. If you want periodic PR/review checks under Claude Code, set them up yourself via `/schedule` after installing this plugin — it isn't something a plugin manifest can pre-declare on this platform.

---

## 4. Example Prompts

- "Analyze this repository and generate a project context document." (`repo-research`)
- "I have 3 independent features to build — provision isolated worktrees for each so I can dispatch a subagent per branch." (`loop-engineering`)
- "Audit the open feature branches for quality gate failures." (`loop-engineering`, via `pr_cron_reviewer.py`)
- "Once these subagents finish and push, review their branches before I merge." (`loop-engineering`)

---

## 5. Installation

**Claude Code**:
```bash
cp -r ./plugins/multi-agent-ops ~/.claude/plugins/multi-agent-ops
```

**Antigravity CLI**:
```bash
mkdir -p ~/.gemini/config/plugins/multi-agent-ops
cp -r ./plugins/multi-agent-ops/* ~/.gemini/config/plugins/multi-agent-ops/
```
