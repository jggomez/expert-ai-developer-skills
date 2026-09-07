# AI Developer Workflows Directory

Welcome to the **Developer Workflows Catalog**. This directory contains generic, highly optimized markdown-based workflows (`.workflows`) designed to guide developers and AI Coding Agents (such as Antigravity/AGY, Claude Code, Cursor, etc.) through step-by-step execution sequences.

Unlike **Rules** (which enforce constraints and passive checks) or **Skills** (which are code-executable tools), **Workflows** are active, step-by-step operational playbooks. They provide a standardized path to move from a task description to a fully verified, clean, secure, and integrated code change.

---

## 1. The Core 9-Stage Command Framework

These 9 core playbooks align directly with user slash commands and engineering principles:

| What you're doing | Command | Key Principle | Playbook File | Primary Focus |
| :--- | :--- | :--- | :--- | :--- |
| **Define what to build** | `/spec` | Spec before code | [spec-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/spec-workflow.md) | Requirements, PRD, acceptance criteria, boundaries |
| **Plan how to build it** | `/plan` | Small, atomic tasks | [plan-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/plan-workflow.md) | Architecture ADR, task decomposition, subagent delegation |
| **Build incrementally** | `/build` | One slice at a time | [build-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/build-workflow.md) | TDD implementation, vertical slices, official skills |
| **Prove it works** | `/test` | Tests are proof | [test-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/test-workflow.md) | Unit, integration, widget, E2E tests, AAA pattern |
| **Set the quality bar** | `/constraints` | Decide it once, enforce it everywhere | [constraints-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/constraints-workflow.md) | NFRs, security gates, secrets, linter rules |
| **Review before merge** | `/review` | Improve code health | [review-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/review-workflow.md) | PR review, static analysis, leaks, code smells |
| **Audit performance** | `/perf` | Measure before you optimize | [perf-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/perf-workflow.md) | Profiling first, jank/slots/query bottlenecks |
| **Simplify the code** | `/code-simplify` | Clarity over cleverness | [code-simplify-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/code-simplify-workflow.md) | Dead code elimination, cyclomatic complexity, DRY/KISS |
| **Ship to production** | `/ship` | Faster is safer | [ship-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/ship-workflow.md) | Conventional commits, changelog, versioning, PR/deploy |

### Specialized Operational Playbooks
* [**feature-development-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/feature-development-workflow.md): Comprehensive end-to-end SDLC lifecycle playbook.
* [**pull-request-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/pull-request-workflow.md): Branch preparation, commit rebasing, PR templates.
* [**commit-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/commit-workflow.md): Staging changes, Conventional Commits format, git safety.
* [**test-execution-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/test-execution-workflow.md): Locating, executing, and reporting coverage test suites.
* [**code-smell-review-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/code-smell-review-workflow.md): Scanning for architectural code smells and debt.
* [**secure-code-review-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/secure-code-review-workflow.md): Credential scanning, OWASP Top 10, security rules audit.
* [**grill-me-alignment-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/grill-me-alignment-workflow.md): Structured requirements interview and design review.

---

## 2. How to Use Workflows in AI Sessions

These files act as active instructions. You can guide your AI agent to follow a specific workflow by linking to it or prompting:

> *"Please follow the workflow detailed in [test-workflow.md](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/test-workflow.md) to run and verify tests before making changes."*

More example prompts, one per workflow:
- "Follow the pull-request-workflow to prepare this branch and write the PR description." (`pull-request-workflow.md`)
- "Follow the commit-workflow to stage and commit these changes." (`commit-workflow.md`)
- "Follow the test-execution-workflow to locate and run this project's test suite with coverage." (`test-execution-workflow.md`)
- "Follow the code-smell-review-workflow to audit this module for God classes and high complexity." (`code-smell-review-workflow.md`)
- "Follow the secure-code-review-workflow before I merge this branch." (`secure-code-review-workflow.md`)
- "Follow the feature-development-workflow to build the new notifications feature end to end." (`feature-development-workflow.md`)
- "Follow the grill-me-alignment-workflow to interview me about this design before you start coding." (`grill-me-alignment-workflow.md`)

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

