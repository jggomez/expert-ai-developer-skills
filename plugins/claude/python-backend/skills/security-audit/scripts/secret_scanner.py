#!/usr/bin/env python3
import os
import sys
import re
import math

# Common API key and secret regex patterns
SECRET_PATTERNS = {
    "Stripe API Key": r"sk_live_[0-9a-zA-Z]{24}",
    "AWS Access Key ID": r"AKIA[0-9A-Z]{16}",
    "AWS Secret Access Key": r"(?i)aws_secret_access_key\s*[:=]\s*['\"][0-9a-zA-Z/+=]{40}['\"]",
    "OpenAI API Key": r"sk-[0-9a-zA-Z]{48}",
    "Generic Private Key": r"-----BEGIN [A-Z]+ PRIVATE KEY-----",
    "Slack Webhook URL": r"https://hooks.slack.com/services/T[0-9a-zA-Z_]+/B[0-9a-zA-Z_]+/[0-9a-zA-Z_]+",
    "Google OAuth Client Secret": r"AIzaSy[0-9a-zA-Z\-_]{33}",
    "High Entropy Variable (Possible Secret)": r"(?i)(api_key|secret|password|passwd|token|credential)\s*=\s*['\"][0-9a-zA-Z_\-]{16,}['\"]"
}

# Vulnerable code patterns
VULN_PATTERNS = {
    "SQL Injection Risk (f-string in SQL query)": r"(?i)\.execute\(\s*f['\"]SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*=.*\{.*\}['\"]",
    "SQL Injection Risk (concatenation in SQL query)": r"(?i)\.execute\(\s*['\"]SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*=.*['\"]\s*\+\s*",
    "Command Injection Risk (subprocess with shell=True)": r"subprocess\.(run|Popen|call)\(.*shell\s*=\s*True",
    "Insecure Code Evaluation (eval/exec)": r"\b(eval|exec)\s*\(",
    "Insecure Deserialization (pickle)": r"\bpickle\.(loads|load)\b",
    "Insecure Deserialization (unsafe yaml)": r"yaml\.load\(.*Loader\s*=\s*(yaml\.)?Loader",
    "Server-Side Request Forgery Risk (dynamic request url)": r"requests\.(get|post|put|delete|patch|head)\(\s*[a-zA-Z_][a-zA-Z0-9_]*\b",
    "Active Debug Configuration Flag": r"(?i)\bdebug\s*=\s*True\b"
}

def calculate_entropy(string):
    """Calculates the Shannon entropy of a string to detect potential high-entropy keys."""
    if not string:
        return 0
    entropy = 0
    for x in range(256):
        p_x = float(string.count(chr(x)))/len(string)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy

def scan_file(filepath):
    vulns = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or line_str.startswith("//"):
                continue
                
            # Scan for secrets using regex
            for name, pattern in SECRET_PATTERNS.items():
                match = re.search(pattern, line_str)
                if match:
                    # Double-check entropy of high-entropy generic var matches
                    if name == "High Entropy Variable (Possible Secret)":
                        extracted = re.search(r"=\s*['\"](.*?)['\"]", line_str)
                        if extracted:
                            secret_val = extracted.group(1)
                            # Exclude typical placeholder words
                            if any(p in secret_val.lower() for p in ["your_", "env", "placeholder", "test", "dummy", "my_"]):
                                continue
                            if calculate_entropy(secret_val) < 3.0:
                                continue
                                
                    vulns.append({
                        "file": filepath,
                        "line": line_num,
                        "category": "Credentials / Secrets",
                        "severity": "CRITICAL" if "live" in name.lower() or "private key" in name.lower() else "HIGH",
                        "description": f"Potential {name} found: {line_str}"
                    })
                    
            # Scan for code vulnerabilities using regex
            for name, pattern in VULN_PATTERNS.items():
                match = re.search(pattern, line_str)
                if match:
                    vulns.append({
                        "file": filepath,
                        "line": line_num,
                        "category": "Code Vulnerability",
                        "severity": "HIGH",
                        "description": f"{name} detected: {line_str}"
                    })
    except Exception as e:
        pass
    return vulns

def main():
    target_path = "."
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
        
    all_vulns = []
    
    # Files to ignore
    ignore_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env', '.gemini'}
    ignore_files = {'secret_scanner.py'} # don't scan ourselves to avoid false positives on patterns
    
    if os.path.isfile(target_path):
        all_vulns.extend(scan_file(target_path))
    else:
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if file in ignore_files:
                    continue
                filepath = os.path.join(root, file)
                all_vulns.extend(scan_file(filepath))
                
    if not all_vulns:
        print("✅ No hardcoded credentials or high-risk execution vulnerabilities detected.")
        sys.exit(0)
        
    print(f"⚠️ Found {len(all_vulns)} security issues:")
    print("=" * 80)
    for vuln in all_vulns:
        print(f"[{vuln['severity']}] Category: {vuln['category']}")
        print(f"  File: {vuln['file']}:{vuln['line']}")
        print(f"  Issue: {vuln['description']}")
        print("-" * 80)
    sys.exit(1)

if __name__ == "__main__":
    main()
