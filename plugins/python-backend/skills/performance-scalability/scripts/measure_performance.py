#!/usr/bin/env python3
import os
import sys
import re
import time
import tracemalloc
import importlib.util

# Regex patterns for finding potential performance issues in code
PERF_PATTERNS = {
    "N+1 Query Risk (Database query inside loop)": r"(?s)(for|while)\b.*?:\s*.*?\b(db|session|cursor|conn|query|execute|select|update|delete|insert)\b",
    "Synchronous HTTP request inside loop": r"(?s)(for|while)\b.*?:\s*.*?\b(requests|urllib|http\.client)\.(get|post|put|delete|request)\b",
    "File write inside loop without buffering": r"(?s)(for|while)\b.*?:\s*.*?\b(write|savefig)\b",
    "Nested Loop complexity (potential O(N^2) or worse)": r"(?s)(for|while)\b.*?:\s*.*?\b(for|while)\b.*?:",
}

def scan_performance_code_smells(target_path):
    """Scans code files for potential performance bottlenecks."""
    issues = []
    ignore_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env', '.gemini'}
    
    def scan_file(filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            for name, pattern in PERF_PATTERNS.items():
                for match in re.finditer(pattern, content):
                    # Get line number of match
                    line_num = content.count('\n', 0, match.start()) + 1
                    snippet = content[match.start():match.end()].strip().split('\n')[0]
                    issues.append({
                        "file": filepath,
                        "line": line_num,
                        "type": name,
                        "snippet": snippet
                    })
        except Exception:
            pass

    if os.path.isfile(target_path):
        scan_file(target_path)
    else:
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if file.endswith('.py') or file.endswith('.js') or file.endswith('.ts'):
                    scan_file(os.path.join(root, file))
                    
    return issues

def profile_function(module_path, func_name, *args, **kwargs):
    """Profiles a specific python function in a module, measuring time and memory."""
    if not os.path.exists(module_path):
        print(f"Error: File {module_path} not found.")
        return
        
    try:
        # Load module dynamically
        spec = importlib.util.spec_from_file_location("temp_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        func = getattr(module, func_name)
    except Exception as e:
        print(f"Error loading function {func_name} from {module_path}: {e}")
        return

    print(f"Profiling {func_name} in {module_path}...")
    
    # Initialize memory tracing
    tracemalloc.start()
    
    start_time = time.perf_counter()
    
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        print(f"Error executing function: {e}")
        tracemalloc.stop()
        return
        
    end_time = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    exec_time = end_time - start_time
    
    print("=" * 80)
    print(f"Performance Profile for {func_name}():")
    print(f"  Execution Time: {exec_time:.6f} seconds")
    print(f"  Peak Memory:    {peak / 1024 / 1024:.3f} MB")
    print(f"  Current Memory: {current / 1024 / 1024:.3f} MB")
    print("=" * 80)
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Scan performance smells: python3 measure_performance.py scan [directory_or_file]")
        print("  Profile python function: python3 measure_performance.py profile [file.py] [function_name]")
        sys.exit(1)
        
    mode = sys.argv[1]
    
    if mode == "scan":
        target = sys.argv[2] if len(sys.argv) > 2 else "."
        issues = scan_performance_code_smells(target)
        if not issues:
            print("✅ No static performance code smells detected.")
            return
            
        print(f"⚠️ Found {len(issues)} potential performance bottlenecks:")
        print("=" * 80)
        for issue in issues:
            print(f"[{issue['type']}]")
            print(f"  Location: {issue['file']}:{issue['line']}")
            print(f"  Snippet:  {issue['snippet']}")
            print("-" * 80)
            
    elif mode == "profile":
        if len(sys.argv) < 4:
            print("Error: Missing file or function name arguments for profiling.")
            sys.exit(1)
        filepath = sys.argv[2]
        func_name = sys.argv[3]
        profile_function(filepath, func_name)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
