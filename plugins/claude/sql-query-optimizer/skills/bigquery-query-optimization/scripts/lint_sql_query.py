#!/usr/bin/env python3
"""Statically scan .sql files and SQL embedded in source code for common
BigQuery anti-patterns, without needing a live BigQuery connection.

Catches the rules in SKILL.md that are detectable from SQL text alone:
SELECT *, unbounded ORDER BY, avoidable REGEXP_CONTAINS, COUNT(DISTINCT),
and JavaScript UDFs. The JOIN-order/skew/partitioning rules need the real
query plan (via the connected `bigquery` MCP tools), not static text.

Usage:
  python3 lint_sql_query.py [path]   # defaults to "." if omitted

`path` can be a single .sql file, or a directory to scan recursively —
both standalone .sql files and SQL embedded as string literals in other
source files (.py, .js, .ts, .java, .go, .rb) are checked.
"""
import os
import re
import sys

SQL_FILE_EXTENSIONS = {".sql"}
SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".go", ".rb", ".scala"}
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env"}

# A string literal is treated as an embedded query if it contains both a
# DML keyword and FROM, case-insensitive, regardless of surrounding quotes.
EMBEDDED_QUERY_PATTERN = re.compile(
    r"""(['"]{3}|['"])((?:(?!\1).)*?\b(?:SELECT|INSERT|UPDATE|DELETE)\b(?:(?!\1).)*?\bFROM\b(?:(?!\1).)*?)\1""",
    re.IGNORECASE | re.DOTALL,
)

RULES = [
    {
        "id": "select-star",
        "pattern": re.compile(r"select\s+\*(?!\s*except)", re.IGNORECASE),
        "message": "SELECT * scans every column. Use explicit columns or SELECT * EXCEPT (...).",
    },
    {
        "id": "unbounded-order-by",
        "pattern": re.compile(
            r"order\s+by\b(?!(?:(?!;).)*?\blimit\b)", re.IGNORECASE | re.DOTALL
        ),
        "message": "ORDER BY without a LIMIT can overload a single slot on large results (Resources Exceeded risk). Add a LIMIT.",
    },
    {
        "id": "regexp-for-simple-match",
        "pattern": re.compile(r"regexp_contains\s*\([^,]+,\s*['\"]\.?\*", re.IGNORECASE),
        "message": "REGEXP_CONTAINS with a plain wildcard pattern is slower than LIKE '%...%' for simple matching.",
    },
    {
        "id": "count-distinct",
        "pattern": re.compile(r"count\s*\(\s*distinct\b", re.IGNORECASE),
        "message": "COUNT(DISTINCT ...) is exact but slower on high cardinality. Consider APPROX_COUNT_DISTINCT if ~1% error is acceptable.",
    },
    {
        "id": "javascript-udf",
        "pattern": re.compile(r"language\s+js\b", re.IGNORECASE),
        "message": "JavaScript UDFs spin up a V8 subprocess per call. Prefer a SQL UDF when the logic doesn't need JS.",
    },
]


def lint_sql_text(sql_text):
    findings = []
    for rule in RULES:
        if rule["pattern"].search(sql_text):
            findings.append(rule)
    return findings


def scan_sql_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return []
    findings = lint_sql_text(content)
    return [(filepath, None, finding) for finding in findings]


def scan_source_file_for_embedded_sql(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return []

    results = []
    for match in EMBEDDED_QUERY_PATTERN.finditer(content):
        query_text = match.group(2)
        line_num = content.count("\n", 0, match.start()) + 1
        for finding in lint_sql_text(query_text):
            results.append((filepath, line_num, finding))
    return results


def scan_path(target_path):
    all_findings = []

    if os.path.isfile(target_path):
        ext = os.path.splitext(target_path)[1]
        if ext in SQL_FILE_EXTENSIONS:
            all_findings.extend(scan_sql_file(target_path))
        elif ext in SOURCE_EXTENSIONS:
            all_findings.extend(scan_source_file_for_embedded_sql(target_path))
        return all_findings

    for root, dirs, files in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for filename in files:
            filepath = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1]
            if ext in SQL_FILE_EXTENSIONS:
                all_findings.extend(scan_sql_file(filepath))
            elif ext in SOURCE_EXTENSIONS:
                all_findings.extend(scan_source_file_for_embedded_sql(filepath))

    return all_findings


def main():
    target_path = sys.argv[1] if len(sys.argv) > 1 else "."
    findings = scan_path(target_path)

    if not findings:
        print("✅ No static BigQuery anti-patterns detected.")
        sys.exit(0)

    print(f"⚠️  Found {len(findings)} potential issue(s):")
    print("=" * 80)
    for filepath, line_num, rule in findings:
        location = f"{filepath}:{line_num}" if line_num else filepath
        print(f"[{rule['id']}] {location}")
        print(f"  {rule['message']}")
        print("-" * 80)

    sys.exit(1)


if __name__ == "__main__":
    main()
