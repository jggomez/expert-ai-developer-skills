# AI Developer Workflows Directory

Welcome to the **Developer Workflows Catalog**. This directory contains generic, highly optimized markdown-based workflows (`.workflows`) designed to guide developers and AI Coding Agents (such as Antigravity/AGY, Claude Code, Cursor, etc.) through step-by-step execution sequences.

Unlike **Rules** (which enforce constraints and passive checks) or **Skills** (which are code-executable tools), **Workflows** are active, step-by-step operational playbooks. They provide a standardized path to move from a task description to a fully verified, clean, secure, and integrated code change.

---

## 1. Directory Structure & Sitemap

These workflows cover the entire software development lifecycle (SDLC) and can be executed individually or referenced sequentially:

* [**README.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/README.md): This index and workflow execution guide.
* [**pull-request-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/pull-request-workflow.md): Step-by-step playbook for branch creation, preparation, writing descriptions, and submitting PRs.
* [**commit-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/commit-workflow.md): Step-by-step guide to staging changes, writing semantic Conventional Commits, and safely pushing changes.
* [**test-execution-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/test-execution-workflow.md): Workflow for identifying, running, and debugging unit, integration, and code coverage test suites.
* [**code-smell-review-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/code-smell-review-workflow.md): Review playbook to scan for cognitive complexity, duplication, SOLID violations, and refactoring candidates.
* [**secure-code-review-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/secure-code-review-workflow.md): Playbook for scanning credentials leakage, verifying injection preventions, and compliance checks.
* [**feature-development-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/feature-development-workflow.md): End-to-end development cycle combining design specs, TDD, code review, and merge procedures.

---

## 2. How to Use Workflows in AI Sessions

These files act as active instructions. You can guide your AI agent to follow a specific workflow by linking to it or prompting:

> *"Please follow the workflow detailed in [test-execution-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/test-execution-workflow.md) to run and verify tests before making changes."*

When an agent loads a workflow file, it must:
1. Parse the **Prerequisites** and ensure the environment matches.
2. Follow the **Workflow Steps** chronologically.
3. Validate each step against the specified **Quality Gates**.
4. Report back the execution summary with verification logs.

---

## 3. Registering Workflows as Slash Commands in Antigravity

In the **Google Antigravity** TUI and GUI environment, workflows stored inside the workspace configuration directory are automatically registered as native slash commands (e.g. typing `/feature-development-workflow` in the chat).

To enable these playbooks as active slash commands in your own project workspace:

1. Create a local workflows folder in your project's ignored configuration directory:
   ```bash
   mkdir -p .agents/workflows
   ```
2. Copy the desired workflow markdown file into it:
   ```bash
   cp workflows/feature-development-workflow.md .agents/workflows/
   ```
3. Open a new conversation session. The Antigravity agent will automatically index the workflow, allowing you to trigger it directly in the chat panel by typing `/feature-development-workflow`.

