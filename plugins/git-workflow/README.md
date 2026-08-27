# Git Workflow Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-git--workflow-green?style=flat-square)](file:///./)

The `git-workflow` plugin packages the repository's git hygiene tooling — commit message standards, PR conventions, and the Gitflow branch safety gate — as a small, language-agnostic plugin for **both Antigravity CLI and Claude Code**. It bundles nothing new: the hook is the Gitflow-branch-check portion of `plugins/python-backend/hooks/pre-tool-gate.js`, extracted on its own since it has no dependency on Python or cloud MCP servers, and the two skills already exist in the root `/skills` catalog.

`hooks.json` carries both hosts' hook registrations in one file (Claude Code's `"hooks"` key plus Antigravity's separate `"gitflow-branch-safety"` named group), and the script detects the host at runtime to emit the right decision format for each — verified against each platform's official schema, not assumed.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing `commit-expert` or `pull-request-expert` under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/git-workflow/
├── README.md                       # This usage manual
├── plugin.json                     # Required plugin metadata descriptor
├── hooks.json                      # PreToolUse hook registration
├── hooks/
│   └── gitflow-branch-gate.js      # Blocks git add/commit/push/merge directly on main or develop
└── skills/
    ├── commit-expert/              # Conventional Commits guidelines & commit-msg validator
    └── pull-request-expert/        # PR size limits, templates, branch/commit auditor
```

---

## 2. Gitflow Branch Safety Gate

The `PreToolUse` hook intercepts `Bash` (Claude Code) or `run_command` (Antigravity) shell calls. If it detects `git add`, `git commit`, `git push`, or `git merge` while the active branch is `main` or `develop`, it returns a `deny` decision — the command never runs. Feature and bugfix work must happen on a dedicated branch and land via Pull Request.

This plugin intentionally does **not** include the deployment or cloud-MCP guardrails from `python-backend` — those are backend/cloud-specific; this plugin is scoped to git hygiene only, usable in any language or stack.

---

## 3. Bundled Skills (2 Packaged Modules)

1. **`commit-expert`**: Conventional Commits formatting, the 7 rules of git messaging, and a `validate_commit_msg.py` hook script.
2. **`pull-request-expert`**: PR size limits, atomic-change guidelines, PR template, and a `validate_pr_content.py` branch/commit auditor.

---

## 4. Example Prompts

- "Write a Conventional Commits message for these staged changes." (`commit-expert`)
- "Validate this commit message file against Conventional Commits before I push." (`commit-expert`)
- "Prepare this branch for a pull request — check the diff size and generate the PR description from the template." (`pull-request-expert`)
- "Audit the last few commits on this branch for Conventional Commits compliance." (`pull-request-expert`)

To see the safety gate itself, try: "Commit directly to main" — the hook should deny it and tell you to use a feature branch instead.

---

## 5. Installation

**Claude Code**:
```bash
cp -r ./plugins/git-workflow ~/.claude/plugins/git-workflow
```

**Antigravity CLI**:
```bash
mkdir -p ~/.gemini/config/plugins/git-workflow
cp -r ./plugins/git-workflow/* ~/.gemini/config/plugins/git-workflow/
```
