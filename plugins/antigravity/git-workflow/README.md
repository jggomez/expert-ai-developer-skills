# Git Workflow Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-git--workflow-green?style=flat-square)](file:///./)

The `git-workflow` plugin packages git hygiene tooling — commit message standards, PR conventions, Gitflow branch safety gates, and clean-working-tree stop gates — for **Google Antigravity**.

- **Google Antigravity**: Install via `agy plugin install ./plugins/antigravity/git-workflow`.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing `commit-expert` or `pull-request-expert` under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/antigravity/git-workflow/
├── README.md                       # This usage manual
├── plugin.json                     # Antigravity plugin manifest
├── .claude-plugin/
│   └── plugin.json                 # Manifest compatibility marker
├── hooks.json                      # Hook registrations
├── hooks/
│   ├── gitflow-branch-gate.js      # Blocks git add/commit/push/merge directly on main or develop
│   └── git-clean-stop-gate.js      # Stop hook verifying clean git working state
├── rules/
│   └── gitflow-rules.md            # Git branching and commit guidelines
└── skills/
    ├── commit-expert/              # Conventional Commits guidelines & commit-msg validator
    └── pull-request-expert/        # PR size limits, templates, branch/commit auditor
```

---

## 2. Gitflow Branch Safety Gate & Clean Stop Gate

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`PreToolUse`** | `hooks/gitflow-branch-gate.js` | Intercepts `run_command` shell calls. If it detects `git add`, `git commit`, `git push`, or `git merge` while the active branch is `main`, `master`, or `develop`, it denies the command. Feature work must happen on a dedicated branch. |
| **`Stop`** | `hooks/git-clean-stop-gate.js` | Verifies that git working tree status is cleanly committed before session termination. |

---

## 3. Bundled Skills (2 Packaged Modules)

1. **`commit-expert`**: Conventional Commits regex formatting, the 7 rules of git messaging, and a `validate_commit_msg.py` hook script.
2. **`pull-request-expert`**: PR size limits, atomic-change guidelines, PR template, and a `validate_pr_content.py` branch/commit auditor.

---

## 4. Example Prompts

- "Write a Conventional Commits message for these staged changes." (`commit-expert`)
- "Validate this commit message file against Conventional Commits before I push." (`commit-expert`)
- "Prepare this branch for a pull request — check the diff size and generate the PR description from the template." (`pull-request-expert`)
- "Audit the last few commits on this branch for Conventional Commits compliance." (`pull-request-expert`)

---

## 5. Installation

```bash
agy plugin install ./plugins/antigravity/git-workflow
```
