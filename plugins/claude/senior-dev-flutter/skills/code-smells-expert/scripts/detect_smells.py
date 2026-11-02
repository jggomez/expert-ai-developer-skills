#!/usr/bin/env python3
import os
import sys
import ast

class CodeSmellDetector(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.smells = []
        self.current_class = None
        self.class_lines = 0

    def visit_ClassDef(self, node):
        prev_class = self.current_class
        self.current_class = node.name
        
        # Calculate class length (approximate via line numbers)
        class_len = node.end_lineno - node.lineno + 1
        if class_len > 300:
            self.smells.append({
                "file": self.filename,
                "type": "Large Class (God Class)",
                "target": f"class {node.name}",
                "metric": f"{class_len} lines (threshold: 300)",
                "line": node.lineno
            })
            
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node):
        # Calculate method/function length
        func_len = node.end_lineno - node.lineno + 1
        if func_len > 30:
            target_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
            self.smells.append({
                "file": self.filename,
                "type": "Long Method",
                "target": f"def {target_name}",
                "metric": f"{func_len} lines (threshold: 30)",
                "line": node.lineno
            })
            
        # Check parameter list size
        param_count = len(node.args.args)
        if param_count > 4:
            target_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
            self.smells.append({
                "file": self.filename,
                "type": "Long Parameter List",
                "target": f"def {target_name}",
                "metric": f"{param_count} parameters (threshold: 4)",
                "line": node.lineno
            })
            
        # Check complex conditional density (rough cyclomatic indicator)
        if_count = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.IfExp, ast.Compare)):
                if_count += 1
        if if_count > 8:
            target_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
            self.smells.append({
                "file": self.filename,
                "type": "High Complexity (Conditional Overuse)",
                "target": f"def {target_name}",
                "metric": f"{if_count} conditionals/comparisons (threshold: 8)",
                "line": node.lineno
            })
            
        self.generic_visit(node)

def analyze_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=filepath)
        detector = CodeSmellDetector(filepath)
        detector.visit(tree)
        return detector.smells
    except (SyntaxError, ValueError) as e:
        # Ignore files that fail to parse (e.g. non-python or invalid python)
        return []
    except Exception as e:
        return []

def main():
    target_path = "."
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
        
    all_smells = []
    
    if os.path.isfile(target_path):
        if target_path.endswith('.py'):
            all_smells.extend(analyze_file(target_path))
    else:
        for root, _, files in os.walk(target_path):
            # Ignore common cache / virtualenv directories
            if any(p in root for p in ['.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env', '.gemini']):
                continue
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    all_smells.extend(analyze_file(filepath))
                    
    if not all_smells:
        print("✅ No static code smells (Long Method, Large Class, Long Parameter List) detected in Python files.")
        return
        
    print(f"⚠️ Found {len(all_smells)} potential code smells:")
    print("=" * 80)
    for smell in all_smells:
        print(f"[{smell['type']}]")
        print(f"  File:   {smell['file']}:{smell['line']}")
        print(f"  Target: {smell['target']}")
        print(f"  Metric: {smell['metric']}")
        print("-" * 80)

if __name__ == "__main__":
    main()
