#!/usr/bin/env python3
"""Provision isolated git worktrees for parallel feature work (Mode B).

Subagents are launched by the model through its host's Agent/subagent tool; there is no SDK for
spawning one from a script. What IS scriptable is the isolation half: one branch + worktree per
task, created from the CURRENT HEAD so every worker starts from the in-progress feature branch
(Claude Code's own subagent worktrees start from the default branch unless worktree.baseRef is
"head"). Each worker commits on its branch; the orchestrator merges the branches one at a time.

Usage:
  python3 run_parallel_agents.py tasks.json
  tasks.json = [{"task_name": "app-admin", "branch_name": "feat/x-admin", "instruction": "..."}, ...]

Exit codes: 0 = worktrees ready, 1 = git failure, 2 = usage error.
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

REQUIRED_KEYS = ("task_name", "branch_name", "instruction")


def branch_exists(branch_name: str, repo_root: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", branch_name],
        cwd=repo_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def create_worktree(task_name: str, branch_name: str, repo_root: str) -> str:
    """Creates <repo>-wt-<task> next to the repository; a new branch starts at the current HEAD."""
    worktree_path = os.path.join(os.path.dirname(repo_root), f"{os.path.basename(repo_root)}-wt-{task_name}")

    if os.path.exists(worktree_path):
        logging.info(f"Worktree already exists at '{worktree_path}', skipping creation.")
        return worktree_path

    if branch_exists(branch_name, repo_root):
        cmd = ["git", "worktree", "add", worktree_path, branch_name]
    else:
        cmd = ["git", "worktree", "add", "-b", branch_name, worktree_path, "HEAD"]

    subprocess.run(cmd, cwd=repo_root, check=True, capture_output=True, text=True)
    logging.info(f"Created worktree for '{task_name}' at '{worktree_path}' on branch '{branch_name}'.")
    return worktree_path


def load_tasks(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks.json must be a non-empty JSON list")
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError(f"task {task!r} must be an object")
        missing = [k for k in REQUIRED_KEYS if not task.get(k)]
        if missing:
            raise ValueError(f"task {task!r} is missing {missing}")
    return tasks


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_parallel_agents.py tasks.json  "
              '(tasks.json = [{"task_name", "branch_name", "instruction"}, ...])', file=sys.stderr)
        return 2
    try:
        tasks = load_tasks(sys.argv[1])
    except (OSError, ValueError) as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2

    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    if top.returncode != 0:
        print("error: run this inside a git repository", file=sys.stderr)
        return 1
    repo_root = top.stdout.strip()

    logging.info(f"Provisioning {len(tasks)} isolated worktree(s) from the current HEAD...")
    try:
        for task in tasks:
            worktree_path = create_worktree(task["task_name"], task["branch_name"], repo_root)
            print("\n" + "=" * 80)
            print(f"Task: {task['task_name']}  |  Branch: {task['branch_name']}  |  Worktree: {worktree_path}")
            print("Dispatch one implementer with this brief:")
            print("-" * 80)
            print(
                f"Working directory: {worktree_path}\n"
                f"Implement: {task['instruction']}\n"
                f"Run only the tests for your files, then commit on '{task['branch_name']}'. "
                "Do not push and do not open a PR; report the branch name and the test exit code."
            )
    except subprocess.CalledProcessError as exc:
        logging.error(f"git worktree failed: {(exc.stderr or '').strip() or exc}")
        return 1

    print("\n" + "=" * 80)
    print("Worktrees are ready. After the workers return, merge each branch one at a time "
          "(git merge --no-ff <branch>), run the affected tests after each merge, then "
          "remove the worktree (git worktree remove <path>).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
