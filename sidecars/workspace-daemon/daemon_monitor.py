#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import logging

# Setup logging
log_file = "workspace_daemon.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

class WorkspaceWatcher:
    """Monitors code changes in the active workspace and triggers auto-linting/formatting."""
    
    def __init__(self, watch_dir: str):
        self.watch_dir = os.path.abspath(watch_dir)
        self.file_registry = {}
        logging.info(f"Workspace Daemon started. Watching directory: {self.watch_dir}")
        
    def scan_files(self):
        """Recursively scans the workspace for Python and JavaScript files."""
        for root, dirs, files in os.walk(self.watch_dir):
            # Ignore hidden files, build artifacts, virtualenvs, and node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '.venv', 'venv', 'dist', 'build')]
            for file in files:
                if file.endswith(('.py', '.js', '.ts')):
                    file_path = os.path.join(root, file)
                    try:
                        mtime = os.path.getmtime(file_path)
                        self._check_file_changed(file_path, mtime)
                    except OSError:
                        # File might have been deleted mid-scan
                        pass

    def _check_file_changed(self, file_path: str, current_mtime: float):
        """Triggers formatters and linters if the file modification time changed."""
        if file_path in self.file_registry:
            last_mtime = self.file_registry[file_path]
            if current_mtime > last_mtime:
                logging.info(f"File modification detected: {os.path.basename(file_path)}")
                self._run_quality_tools(file_path)
        
        # Update registry with latest mtime
        self.file_registry[file_path] = current_mtime

    def _run_quality_tools(self, file_path: str):
        """Runs ruff (lint + format) on Python files."""
        if file_path.endswith('.py'):
            try:
                # 1. Run Ruff Formatter
                subprocess.run(
                    ["ruff", "format", file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                # 2. Run Ruff Lint Checker
                subprocess.run(
                    ["ruff", "check", "--fix", file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                logging.info(f"Successfully formatted & linted: {os.path.basename(file_path)}")
            except subprocess.CalledProcessError as e:
                logging.warning(f"Quality tools failed for {os.path.basename(file_path)} (Code: {e.returncode})")
            except FileNotFoundError:
                # Ruff is not installed in the environment
                pass

    def start_loop(self):
        """Runs the monitoring loop indefinitely."""
        while True:
            try:
                self.scan_files()
                time.sleep(5)  # Poll every 5 seconds
            except KeyboardInterrupt:
                logging.info("Workspace Daemon shutting down.")
                break
            except Exception as e:
                logging.error(f"Error in watcher loop: {str(e)}")
                time.sleep(10)  # Cool down before retrying

if __name__ == "__main__":
    # Determine directory to watch:
    # 1. Check workspace environment variable passed by Antigravity
    # 2. Default to parent directory of the sidecar folder
    watch_target = os.environ.get("WORKSPACE_ROOT")
    if not watch_target or not os.path.exists(watch_target):
        # Default to parent of sidecar directory (which is where the project lives if installed locally)
        # Or current working directory
        watch_target = os.path.abspath(os.path.join(os.getcwd(), ".."))
    
    watcher = WorkspaceWatcher(watch_target)
    watcher.start_loop()
