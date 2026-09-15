#!/usr/bin/env python3
import os
import re
import sys

class DocValidator:
    """Statically validates markdown files, checking links, hierarchy, and absolute leaks."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.errors = []
        self.total_checked = 0

    def check_file(self, file_path: str):
        self.total_checked += 1
        rel_path = os.path.relpath(file_path, self.workspace_path)
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            content = "".join(lines)
            
        # 1. Check for empty files
        if not content.strip():
            self.errors.append(f"{rel_path}: File is completely empty.")
            return

        # 2. Check for absolute links (local machine leaks)
        absolute_patterns = [r"file:///", r"/Users/", r"/home/"]
        for pattern in absolute_patterns:
            if re.search(pattern, content):
                self.errors.append(f"{rel_path}: Contains absolute local path leaks matching '{pattern}'.")

        # 3. Check for broken relative file links
        # Matches [Label](relative/path.md)
        link_regex = r"\[[^\]]+\]\(([^)]+\.md)(#[^)]+)?\)"
        links = re.findall(link_regex, content)
        for link, _ in links:
            if link.startswith("http://") or link.startswith("https://") or link.startswith("mailto:"):
                continue
            
            # Resolve relative link from the current file's directory
            file_dir = os.path.dirname(file_path)
            target_path = os.path.abspath(os.path.join(file_dir, link))
            
            if not os.path.exists(target_path):
                self.errors.append(f"{rel_path}: Broken relative link to non-existent file '{link}'")

        # 4. Check heading nesting (H1 -> H2 -> H3)
        current_level = 0
        in_code_block = False
        for line_num, line in enumerate(lines, 1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            match = re.match(r"^(#{1,6})\s+", line)
            if match:
                level = len(match.group(1))
                if level > current_level + 1 and current_level > 0:
                    self.errors.append(
                        f"{rel_path}:L{line_num}: Heading hierarchy skipped. "
                        f"Found H{level} directly under H{current_level}."
                    )
                current_level = level

    def validate_workspace(self):
        print(f"Scanning markdown files in workspace: {self.workspace_path} ...")
        for root, dirs, files in os.walk(self.workspace_path):
            # Skip hidden folders
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            
            for file in files:
                if file.endswith(".md"):
                    self.check_file(os.path.join(root, file))
                    
        print(f"\nScan complete. Checked {self.total_checked} markdown files.")
        if self.errors:
            print(f"Found {len(self.errors)} validation issue(s):")
            for error in self.errors:
                print(f" - {error}")
            sys.exit(1)
        else:
            print("Success! All quality gates and relative links verified successfully.")
            sys.exit(0)

if __name__ == "__main__":
    workspace = os.getcwd()
    validator = DocValidator(workspace)
    validator.validate_workspace()
