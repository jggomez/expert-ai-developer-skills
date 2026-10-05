# Git Workflow Plugin (Claude Code)

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-git--workflow-green?style=flat-square)](file:///./)

The `git-workflow` plugin packages git hygiene tooling — commit message standards, PR conventions, Gitflow branch safety gates, and clean-working-tree stop gates — for **Claude Code**.

---

## 1. Directory Tree & Architecture

```
plugins/claude/git-workflow/
├── README.md                       # This usage manual
├── .claude-plugin/
│   └── plugin.json                 # Claude Code plugin manifest
├── hooks.json                      # Hook registrations
├── hooks/
│   ├── gitflow-branch-gate.js      # Blocks git add/commit/push/merge directly on main or develop
│   └── git-clean-stop-gate.js      # Stop hook verifying clean git working state
└── skills/
    ├── commit-expert/              # Conventional Commits guidelines & commit-msg validator
    └── pull-request-expert/        # PR size limits, templates, branch/commit auditor
```

---

## 2. Gitflow Branch Safety Gate & Clean Stop Gate

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`PreToolUse`** | `hooks/gitflow-branch-gate.js` | Intercepts `Bash` shell calls. If it detects `git add`, `git commit`, `git push`, or `git merge` while the active branch is `main`, `master`, or `develop`, it returns a deny decision. Feature work must happen on a dedicated branch. |
| **`Stop`** | `hooks/git-clean-stop-gate.js` | Verifies that git working tree status is cleanly committed before session termination. |

---

## 3. Bundled Skills (2 Packaged Modules)

1. **`commit-expert`**: Conventional Commits formatting, the 7 rules of git messaging, and `validate_commit_msg.py`.
2. **`pull-request-expert`**: PR size limits, atomic-change guidelines, PR template, and `validate_pr_content.py`.

---

## 4. Example Prompts

- "Write a Conventional Commits message for these staged changes." (`commit-expert`)
- "Validate this commit message file against Conventional Commits before I push." (`commit-expert`)
- "Prepare this branch for a pull request — check the diff size and generate the PR description from the template." (`pull-request-expert`)
- "Audit the last few commits on this branch for Conventional Commits compliance." (`pull-request-expert`)

---

## 5. Installation

```bash
/plugin install git-workflow
# or local:
claude plugin install plugins/claude/git-workflow
```
