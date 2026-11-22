#!/usr/bin/env python3
"""Workspace daemon sidecar for Google Antigravity.

Polls WORKSPACE_ROOT every 5 seconds and runs `ruff format` and `ruff check --fix` on each Python file whose
modification time changed. It never runs on files that existed unchanged since it started.

Caveat: it rewrites files on disk, so a save from the agent or editor in the same instant can race with it.
Use it on projects where automatic formatting is welcome.

Environment:
  WORKSPACE_ROOT          directory to watch (required; the daemon exits with code 2 without it)
  WORKSPACE_DAEMON_STATE  where the log is written (default: ~/.cache/workspace-daemon)
"""
import logging
import os
import subprocess
import sys
import time

IGNORED_DIRS = {"node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
POLL_SECONDS = 5
RETRY_SECONDS = 10

STATE_DIR = os.environ.get("WORKSPACE_DAEMON_STATE") or os.path.join(os.path.expanduser("~"), ".cache", "workspace-daemon")
LOG = logging.getLogger("workspace-daemon")


def _configure_logging() -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(STATE_DIR, "workspace_daemon.log")),
            logging.StreamHandler(sys.stdout),
        ],
    )


class WorkspaceWatcher:
    """Watches Python files under a directory and formats/lints the ones that change."""

    def __init__(self, watch_dir: str):
        self.watch_dir = os.path.abspath(watch_dir)
        self.file_registry: dict[str, float] = {}
        LOG.info("Workspace daemon started. Watching %s", self.watch_dir)

    def scan_files(self) -> None:
        """Walks the workspace once; the first sighting of a file only records its mtime."""
        for root, dirs, files in os.walk(self.watch_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in IGNORED_DIRS]
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    continue  # deleted between listing and stat
                self._check_file_changed(path, mtime)

    def _check_file_changed(self, file_path: str, current_mtime: float) -> None:
        last_mtime = self.file_registry.get(file_path)
        if last_mtime is not None and current_mtime > last_mtime:
            LOG.info("Change detected: %s", os.path.relpath(file_path, self.watch_dir))
            self._run_quality_tools(file_path)
            try:
                current_mtime = os.path.getmtime(file_path)  # ruff may have rewritten it
            except OSError:
                self.file_registry.pop(file_path, None)
                return
        self.file_registry[file_path] = current_mtime

    def _run_quality_tools(self, file_path: str) -> None:
        """Formats and auto-fixes one Python file. Lint that ruff cannot fix is reported, not treated as failure."""
        name = os.path.basename(file_path)
        try:
            fmt = subprocess.run(["ruff", "format", file_path], capture_output=True, text=True, check=False)
            lint = subprocess.run(["ruff", "check", "--fix", file_path], capture_output=True, text=True, check=False)
        except FileNotFoundError:
            LOG.warning("ruff is not installed; skipping %s", name)
            return
        if fmt.returncode != 0:
            LOG.warning("ruff format could not parse %s (exit %s)", name, fmt.returncode)
        elif lint.returncode == 0:
            LOG.info("Formatted and linted %s", name)
        elif lint.returncode == 1:
            LOG.info("Formatted %s; lint issues remain that need a manual fix", name)
        else:
            LOG.warning("ruff check stopped on %s (exit %s)", name, lint.returncode)

    def start_loop(self) -> None:
        while True:
            try:
                self.scan_files()
                time.sleep(POLL_SECONDS)
            except KeyboardInterrupt:
                LOG.info("Workspace daemon shutting down.")
                break
            except OSError as err:
                LOG.error("Watcher loop error: %s", err)
                time.sleep(RETRY_SECONDS)


def main() -> int:
    watch_target = os.environ.get("WORKSPACE_ROOT", "")
    if not watch_target or not os.path.isdir(watch_target):
        print("workspace-daemon: set WORKSPACE_ROOT to the project directory to watch", file=sys.stderr)
        return 2
    _configure_logging()
    WorkspaceWatcher(watch_target).start_loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
