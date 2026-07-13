# Antigravity Sidecars Directory

Welcome to the **Developer Sidecars Catalog**. Sidecars are persistent background processes or scheduled recurring tasks that run alongside Google Antigravity. Antigravity manages their full lifecycle, automatically starting them and restarting them if they crash or error.

---

## 1. Directory Structure & Sitemap

This directory contains generic, highly reusable sidecar configurations that can be registered globally or inside plugins to automate background loops:

* [**README.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/README.md): This index and sidecars documentation guide.
* [**pr-reviewer-cron/**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/pr-reviewer-cron/sidecar.json): An hourly scheduled agent task that searches the repository for open PRs and audits their diffs for credentials leaks and TODO comments.
* [**incoming-reviews-alert/**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/incoming-reviews-alert/sidecar.json): A 30-minute scheduled check that prompts the agent to fetch and list incoming code review assignments from the remote origin.
* [**workspace-daemon/**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/workspace-daemon/sidecar.json): A persistent python background daemon that monitors files for modification and automatically triggers linters or formatters.

---

## 2. Installation Guide

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
A persistent file-watching background daemon. If files are changed, it executes static checks and formats code automatically. Antigravity will automatically restart this script if it exits.
