#!/usr/bin/env python3
"""Provision isolated git worktrees for parallel feature work.

Subagents run inside a live agent session (Antigravity or Claude Code) and
are launched by the model itself via its Agent/subagent tool — there is no
importable SDK for spawning one from a standalone script. What IS scriptable,
and genuinely useful on its own, is the isolation half of parallel work: a
dedicated branch + worktree per task, so multiple subagents never touch the
same working directory.

This script creates one worktree per task and prints the prompt to hand each
corresponding subagent.

Usage:
  python3 run_parallel_agents.py              # uses the example tasks below
  python3 run_parallel_agents.py tasks.json    # [{"task_name", "branch_name", "instruction"}, ...]
"""
import json
import logging
import os
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

DEFAULT_TASKS = [
    {
        "task_name": "auth",
        "branch_name": "feature/add-oauth-flow",
        "instruction": "Implement a secure OAuth2 authentication flow with token validation.",
    },
    {
        "task_name": "billing",
        "branch_name": "feature/integrate-stripe",
        "instruction": "Integrate the Stripe checkout webhook listener and update subscription status in the DB.",
    },
]


def branch_exists(branch_name: str, repo_root: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", branch_name],
        cwd=repo_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def create_worktree(task_name: str, branch_name: str, repo_root: str) -> str:
    worktree_path = os.path.join(os.path.dirname(repo_root), f"worktree-{task_name}")

    if os.path.exists(worktree_path):
        logging.info(f"Worktree already exists at '{worktree_path}', skipping creation.")
        return worktree_path

    if branch_exists(branch_name, repo_root):
        cmd = ["git", "worktree", "add", worktree_path, branch_name]
    else:
        cmd = ["git", "worktree", "add", "-b", branch_name, worktree_path]

    subprocess.run(cmd, cwd=repo_root, check=True)
    logging.info(f"Created worktree for '{task_name}' at '{worktree_path}' on branch '{branch_name}'.")
    return worktree_path


def main():
    repo_root = os.getcwd()
    tasks = DEFAULT_TASKS
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            tasks = json.load(f)

    logging.info(f"Provisioning {len(tasks)} isolated worktree(s) for parallel work...")

    for task in tasks:
        worktree_path = create_worktree(task["task_name"], task["branch_name"], repo_root)
        print("\n" + "=" * 80)
        print(f"Task: {task['task_name']}  |  Branch: {task['branch_name']}  |  Worktree: {worktree_path}")
        print("Launch one subagent per task via your host's Agent/subagent tool with this prompt:")
        print("-" * 80)
        print(
            f"Working directory: {worktree_path}\n"
            f"Implement: {task['instruction']}\n"
            f"Write tests, commit your changes, and open a draft PR from '{task['branch_name']}'."
        )

    print("\n" + "=" * 80)
    print(
        "Worktrees are ready. Dispatch one subagent per task above, then run "
        "pr_cron_reviewer.py once they've pushed to audit the resulting branches."
    )


if __name__ == "__main__":
    main()
