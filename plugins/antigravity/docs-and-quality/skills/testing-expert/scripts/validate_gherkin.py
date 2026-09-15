#!/usr/bin/env python3
import os
import re
import sys

class GherkinValidator:
    """Statically analyzes Gherkin .feature files for structural correctness."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.errors = []
        self.total_checked = 0

    def validate_feature_file(self, file_path: str):
        self.total_checked += 1
        rel_path = os.path.relpath(file_path, self.workspace_path)
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        has_feature_keyword = False
        scenarios = []
        current_scenario = None
        has_examples = False
        background_seen = False
        scenarios_seen = False
        
        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
                
            # 1. Feature definition check
            if line.startswith("Feature:"):
                has_feature_keyword = True
                continue
                
            # 2. Background check (must come before Scenarios)
            if line.startswith("Background:"):
                background_seen = True
                if scenarios_seen:
                    self.errors.append(
                        f"{rel_path}:L{line_num}: Background keyword found after Scenarios. "
                        "Background setup steps must be specified first."
                    )
                continue
                
            # 3. Scenario headers
            if line.startswith("Scenario:") or line.startswith("Scenario Outline:"):
                scenarios_seen = True
                
                # If the previous scenario was an Outline, check if it had Examples
                if current_scenario and current_scenario["is_outline"] and not has_examples:
                    self.errors.append(
                        f"{rel_path}:L{current_scenario['line']}: Scenario Outline '{current_scenario['name']}' "
                        "is missing its corresponding 'Examples:' block."
                    )
                
                scenario_name = line.split(":", 1)[1].strip()
                is_outline = "Scenario Outline:" in line
                
                current_scenario = {
                    "name": scenario_name,
                    "line": line_num,
                    "is_outline": is_outline,
                    "steps": []
                }
                
                # Check for duplicate names
                if scenario_name in [s["name"] for s in scenarios]:
                    self.errors.append(
                        f"{rel_path}:L{line_num}: Duplicate Scenario name found: '{scenario_name}'."
                    )
                scenarios.append(current_scenario)
                has_examples = False  # Reset for next outline
                continue

            # 4. Gherkin Steps
            step_match = re.match(r"^(Given|When|Then|And|But)\s+", line)
            if step_match:
                if current_scenario:
                    current_scenario["steps"].append(line)
                elif not background_seen:
                    self.errors.append(
                        f"{rel_path}:L{line_num}: Step '{line}' found outside of any Scenario or Background context."
                    )
                continue

            # 5. Examples block check
            if line.startswith("Examples:"):
                has_examples = True
                continue

        # Check the last scenario outline if any
        if current_scenario and current_scenario["is_outline"] and not has_examples:
            self.errors.append(
                f"{rel_path}:L{current_scenario['line']}: Scenario Outline '{current_scenario['name']}' "
                "is missing its corresponding 'Examples:' block."
            )
            
        # Overall validations
        if not has_feature_keyword:
            self.errors.append(f"{rel_path}: File does not contain a 'Feature:' definition block.")
            
        for s in scenarios:
            if not s["steps"]:
                self.errors.append(
                    f"{rel_path}:L{s['line']}: Scenario '{s['name']}' has 0 steps defined."
                )

    def scan_workspace(self):
        print(f"Scanning Gherkin files in workspace: {self.workspace_path} ...")
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                if file.endswith(".feature"):
                    self.validate_feature_file(os.path.join(root, file))
                    
        print(f"\nScan complete. Checked {self.total_checked} Gherkin .feature files.")
        if self.errors:
            print(f"Found {len(self.errors)} Gherkin syntax issue(s):")
            for error in self.errors:
                print(f" - {error}")
            sys.exit(1)
        else:
            print("Success! All Gherkin features are syntactically correct.")
            sys.exit(0)

if __name__ == "__main__":
    workspace = os.getcwd()
    validator = GherkinValidator(workspace)
    validator.scan_workspace()
