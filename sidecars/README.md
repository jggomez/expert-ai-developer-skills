# Antigravity Sidecars Directory

Welcome to the **Developer Sidecars Catalog**. Sidecars are persistent background processes or scheduled recurring tasks that run alongside Google Antigravity. Antigravity manages their full lifecycle, automatically starting them and restarting them if they crash or error.

---

## 1. Directory Structure & Sitemap

This directory contains generic, highly reusable sidecar configurations that can be registered globally or inside plugins to automate background loops:

* [**README.md**](README.md): This index and sidecars documentation guide.
* [**pr-reviewer-cron/**](pr-reviewer-cron/sidecar.json): An hourly scheduled agent task that searches the repository for open PRs and audits their diffs for credentials leaks and TODO comments.
* [**incoming-reviews-alert/**](incoming-reviews-alert/sidecar.json): A 30-minute scheduled check that prompts the agent to fetch and list incoming code review assignments from the remote origin.
* [**workspace-daemon/**](workspace-daemon/sidecar.json): A persistent python background daemon that monitors files for modification and automatically triggers linters or formatters.

---

## 2. Installation Guide

Sidecars are **manual installs**: no plugin in this repo ships or registers them, so nothing runs until you copy a folder as shown below.

To register these sidecars in your Antigravity environment, you can install them as **Global Sidecars** or **Plugin Sidecars**.

### 2.1 Installing as Global Sidecars
Global sidecars are active across all workspaces and projects on your system.

Copy the sidecar folder(s) directly to your global `~/.gemini` configuration directory:

```bash
# 1. Create the global sidecars directory
mkdir -p ~/.gemini/config/sidecars/

# 2. Copy the desired sidecar (e.g. pr-reviewer-cron)
cp -r sidecars/pr-reviewer-cron ~/.gemini/config/sidecars/
```

### 2.2 Installing as Plugin Sidecars
Plugin sidecars are scoped to a specific plugin.

Copy the sidecar folder(s) to your plugin's sidecars directory:

```bash
# 1. Create the plugin sidecars directory
mkdir -p ~/.gemini/config/plugins/python-backend/sidecars/

# 2. Copy the desired sidecar (e.g. workspace-daemon)
cp -r sidecars/workspace-daemon ~/.gemini/config/plugins/python-backend/sidecars/
```

---

## 3. Sidecars Reference

### `pr-reviewer-cron` (Scheduled Agent)
Runs every hour (`0 * * * *`). It launches a new Antigravity conversation and instructs the agent to audit open feature branches for security violations, leftover TODO declarations, and formatting mismatches.

### `incoming-reviews-alert` (Scheduled Agent)
Runs every 30 minutes (`*/30 * * * *`). It launches a conversation instructing the agent to list all pending review assignments from GitHub/GitLab, keeping the developer informed of incoming work.

### `workspace-daemon` (Continuous Process)
A persistent background daemon. Every 5 seconds it looks for changed `.py` files under `WORKSPACE_ROOT` and runs `ruff format` and `ruff check --fix` on them. Files that were already there unchanged are never touched.

- `WORKSPACE_ROOT` is required; without it the daemon exits with code 2 instead of guessing a folder.
- The log goes to `~/.cache/workspace-daemon/workspace_daemon.log` (override with `WORKSPACE_DAEMON_STATE`), never into your project.
- Lint that ruff cannot fix is logged as "issues remain", not as a failure. If `ruff` is not installed it logs a warning and skips.
- It rewrites files on disk, so only use it on projects where automatic formatting is welcome.

---

## 4. Example Prompts

Sidecars trigger themselves on a schedule — you don't invoke them directly — but this is the exact prompt each one sends when it fires (see each `sidecar.json`), and what you'd type to run the same check manually right now:

- `pr-reviewer-cron` sends: *"Search the repository for open PR branches. Audit their diffs for security vulnerabilities, TODO leftovers, and styling violations, and output the report."* — run it yourself anytime with the same prompt, or with "Audit the open feature branches for quality gate failures" (`multi-agent-ops`'s `pr_cron_reviewer.py`).
- `incoming-reviews-alert` sends: *"Fetch and display a list of all incoming code review requests or PR assignments from the remote git repository."*
- `workspace-daemon` runs continuously with no prompt — it reacts to file-save events, not chat input.
