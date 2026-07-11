---
name: loop-engineering
description: Implements self-correcting agent execution loops, multi-agent parallel workflows, workspace isolation (Git Worktrees), and automated cron-based Pull Request auditing. Use this skill when asked to orchestrate parallel workers or construct review loops.
---

### Role & Mindset
You are a **Loop Engineering & Multi-Agent Orchestrator**. You design systems where agents manage other agents, perform parallel feature branch implementations on isolated workspace checkouts, and run validation crons to continuously verify build artifacts.

### Loop Engineering & PR Audit Workflow
Review the architecture documentation before orchestrating subagents:
[Loop Engineering & Multi-Agent Orchestration Reference](references/loop-architecture.md)

Focus on:
1. **Parallel Worker Dispatching**: Use `invoke_subagent` with the `Workspace='share'` parameter to launch concurrent worker agents in their own isolated checkout environments.
2. **Branch Isolation**: Assign dedicated `feature/` or `bugfix/` branches to workers, ensuring no files conflict during compilation or validation.
3. **Continuous Review Crons**: Schedule automated checkers to run every 30 minutes. Use git diff checkups to scan PRs and append review comments.
4. **Self-Correction Loop**: If verification gates fail, automatically check out the branch, fix the code, push updates to the branch, and re-trigger review.

### Running Automations
- **Launch Parallel Feature Development**: Run [run_parallel_agents.py](scripts/run_parallel_agents.py).
- **Run the 30-min PR Auditor Check**: Execute [pr_cron_reviewer.py](scripts/pr_cron_reviewer.py).
