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
1. **Parallel Worker Dispatching**: Provision one isolated git worktree + branch per task, then launch one subagent per worktree via the host's Agent/subagent tool. Subagents are always launched live by the model in-session — there is no importable SDK for spawning one from a standalone script, on either Antigravity or Claude Code.
2. **Branch Isolation**: Assign dedicated `feature/` or `bugfix/` branches to workers, ensuring no files conflict during compilation or validation.
3. **Continuous Review Crons**: Schedule automated checkers to run periodically. Use git diff checkups to scan PRs and append review comments.
4. **Self-Correction Loop**: If verification gates fail, automatically check out the branch, fix the code, push updates to the branch, and re-trigger review.

### Running Automations
- **Provision Parallel Worktrees**: Run [run_parallel_agents.py](scripts/run_parallel_agents.py) to create one isolated git worktree + branch per task; it prints the exact prompt to hand each subagent you then launch via your host's Agent/subagent tool.
- **Run the PR Auditor Check**: Execute [pr_cron_reviewer.py](scripts/pr_cron_reviewer.py) to scan open `feature/`/`bugfix/` branches and run quality gates on their diffs.
