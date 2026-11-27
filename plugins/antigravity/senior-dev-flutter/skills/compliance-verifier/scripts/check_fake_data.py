#!/usr/bin/env python3
"""Rejects fake data added to production UI code.

A green test suite says nothing about a screen that paints invented data. This check reads the
lines a change adds and fails on mock data, placeholder people, fake-data libraries and literals
returned after a simulated delay. Test code, fixtures and seeds are ignored, and so are folders that
never hold the app's UI: agent plugins and rules (`.claude/`, `.agents/`), docs, virtualenvs,
vendored dependencies, developer scripts (`scripts/`, where local stub servers live) and generated
code (`*.g.dart`, `*.freezed.dart`, `*_pb2.py`, `*.pb.go`, `generated/`). `tools/` and `bin/` stay
scanned: ADK agent tools and Dart servers live there.

Comment-only lines are checked only for a real source left for later: a comment that merely mentions a
mock or a fake describes the code, it does not ship data. An `InMemory...` class imported from a library
(`google.adk`, `a2a`, `@apollo/client`) is that library's own implementation, not a stand-in the project
wrote; one defined or imported from the project itself is still reported.

Fakes also hide below the screen, so the scan covers data layers and backends too: stand-in
classes (`InMemory...`), comments that promise a real source later, and fixed records returned from
repositories, services, API clients and data sources. A returned record is judged by where its
data comes from, not by its shape:
  - a value read at run time (`doc.id`, `client_id`, `new_id()`) makes it real;
  - a literal-only record (`{"error": "not found"}`, `{"missing": True}`) is a fallback or status
    response when its enclosing function reads a real source (database, Firestore, HTTP, SQL, file);
  - only a literal record in a function that reads nothing is reported as fixed data.

While git replays other commits (merge, cherry-pick, rebase), lines that arrive unchanged from them
are skipped: they were checked where they were written, and only what this change adds is judged.

It is a heuristic: it can flag a false positive, and it cannot see invented data with believable
names. Running the real app (`check_evidence.py`) is what proves the data is real.

A demo the user approved is allowed when the file carries `demo-data: approved` and a line of the
feature plan (`docs/<feature-name>/PLAN.md`, or a legacy root `PLAN.md`) or `docs/*/spec.md` holds
both that text and the file path.

Usage:
    python3 check_fake_data.py --repo .                 # uncommitted and untracked changes
    python3 check_fake_data.py --repo . --base main     # everything since main

Exit codes: 0 = PASS, 1 = FAIL (findings printed), 2 = usage error.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

APPROVAL = "demo-data: approved"
SCANNED_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue", ".svelte", ".html", ".dart",
                    ".py", ".go", ".kt", ".swift", ".java"}
IGNORED_PATH = re.compile(
    r"(^|/)(tests?|__tests__|__mocks__|e2e|integration_test|test_driver|mocks?|fixtures?|stories|cypress|"
    r"playwright|seeds?|migrations?|node_modules|build|dist|scripts?|generated"
    r"|\.claude|\.agents|\.gemini|\.cursor|\.venv|venv|docs?|context|vendor|coverage|\.dart_tool|\.next)(/|$)"
    r"|\.(test|spec|stories)\.|_test\.dart$|\.config\.[cm]?[jt]s$"
    r"|(^|/)test_[^/]*\.py$|_test\.(py|go)$|(^|/)conftest\.py$|(^|/)(testdata|androidTest|Tests)(/|$)"
    r"|\.(g|freezed|gr|pb|mocks)\.dart$|_pb2(_grpc)?\.py$|\.pb(\.gw)?\.go$|\.generated\.\w+$|\.min\.m?js$"
)
# A class that holds or serves the app's data; `InMemoryAccessors` (sorting helpers) is not one.
DATA_ROLES = (r"Repositor(?:y|ies)|Repo|Store|Storage|Db|Database|DataSource|Datasource|Source|Service|Client"
              r"|Api|Gateway|Dao|Backend|Provider")
# Patterns about identifiers are judged on code only: a string such as 'or with a fake in tests' is a
# message or course text, not data. The others (lorem ipsum, John Doe, faker imports) live in strings.
CODE_ONLY = {"mock or fake data", "sample data", "stand-in implementation"}
MINIFIED_LINE = 1000  # characters; a bundled or minified line is vendored code
# Math.random() as an index, a shuffle or a unique suffix produces no data a user sees.
RANDOM_NOT_DATA = re.compile(
    r"Math\.floor\(\s*Math\.random\(\)\s*\*\s*(?:\(\s*\w+\s*\+\s*1\s*\)|\w+\s*\+\s*1|[\w.]+\.length)\s*\)"
    r"|Math\.random\(\)\.toString\(\s*36\s*\)|Random\(\)\.nextInt\(\s*[\w.]+\.length\s*\)"
)
RANDOM_CALL = re.compile(r"\bMath\.random\(\)|\bRandom\(\)\.next")
# Imports from outside the project in languages whose imports do not name classes (Dart, Go, JVM, Swift).
DART_PACKAGE_IMPORT = re.compile(r"""^\s*import\s+['"]package:(\w+)/""")
OTHER_EXTERNAL_IMPORT = re.compile(r"""^\s*import\s+(?:\(|"[\w.-]+\.\w+/|[a-z]\w*(?:\.\w+)+\s*$|[A-Z]\w+\s*$)""")
# POSIX ERE for `git grep -E`: no \s or \b there.
DEFINITION = r"(class|struct|interface|type|object|enum|record|protocol)[[:space:]]+{name}([^A-Za-z0-9_]|$)"
COMMENT_LINE = re.compile(r"^\s*(?://|#|/\*|\*|<!--|--\s)")
LEFT_FOR_LATER = "real source left for later"
STAND_IN = "stand-in implementation"
IN_MEMORY_NAME = re.compile(r"\bInMemory\w*(?:" + DATA_ROLES + r")\w*")
PY_FROM_IMPORT = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+\(?([^#)]+)")
JS_IMPORT = re.compile(r"""^\s*import\s+(?:type\s+)?(.+?)\s+from\s+['"]([^'"]+)['"]""")
JS_LOCAL = re.compile(r"^(?:\.|/|@/|~/|#/)")
INPUT_HINT = re.compile(r"placeholder|hintText|helperText|labelText", re.IGNORECASE)
PATTERNS = (
    ("mock or fake data", re.compile(
        r"\b(?:[Mm]ock|[Ff]ake|[Dd]ummy|MOCK|FAKE|DUMMY)(?:[A-Z_][A-Za-z0-9_]*|s)?\b"
        r"|\b\w+(?:Mock|Fake|Dummy)[A-Z]\w*|\b\w+_(?:MOCK|FAKE|DUMMY)\w*"
    )),
    ("sample data", re.compile(
        r"\b[sS]ample(?:Data|Users?|Items?|Products?|Orders?|Records?|Rows?|Results?|List)\b|\bSAMPLE_[A-Z_]+\b"
    )),
    ("placeholder text", re.compile(r"lorem ipsum", re.IGNORECASE)),
    ("placeholder person", re.compile(r"\b(?:John|Jane) Doe\b")),
    ("fake-data library", re.compile(r"@faker-js|\bfaker\.|package:faker/|from ['\"]msw|\bsetupWorker\(")),
    ("random value", re.compile(r"\bMath\.random\(\)|\bRandom\(\)\.next")),
    ("stand-in implementation", re.compile(
        r"\bInMemory\w*(?:" + DATA_ROLES + r")\w*|\bin_memory_(?:repo|repository|store|db)\w*")),
    ("real source left for later", re.compile(
        r"(?:replace|swap|connect)\s+(?:this\s+|it\s+)?(?:with|to)\s+(?:the\s+|a\s+)?(?:real|actual)\s+"
        r"(?:api|backend|service|server|data|endpoint|source)|hard-?coded\s+(?:for\s+now|until|data|list)",
        re.IGNORECASE)),
)
DATA_LAYER = re.compile(
    r"(^|/)(data|datasources?|repositor(?:y|ies)|services?|api|clients?)(/|$)"
    r"|(repository|repositories|datasource|data_source|service|api|client)\.\w+$",
    re.IGNORECASE,
)
LITERAL_RECORDS = re.compile(
    r"\breturn\s+(?:const\s+)?(?:<[^>]+>\s*)?(?:\[\][A-Za-z_]\w*\s*)?[\[{]\s*(?:[{\['\"0-9]|[A-Z]\w*\s*[({])"
)
STRING_LITERAL = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`[^`]*`')
TRAILING_COMMENT = re.compile(r"(?://|#).*$")
# Keys and named arguments (`id:`) and type constructors (`Order(`, `Order{`) shape a record, they hold no value.
NOT_A_VALUE = re.compile(r"\b[A-Za-z_]\w*\s*(?=:)|\b[A-Z]\w*\s*(?=[({]|<[^>]*>\s*[({])")
LITERAL_WORDS = {"return", "const", "new", "true", "false", "True", "False", "None", "null", "nil",
                 "undefined", "nullptr"}
IDENTIFIER = re.compile(r"(?<![\w.])[A-Za-z_]\w*")
EXAMPLE_ADDRESS = re.compile(r"[\w.+-]*@?example\.(?:com|org|net)")
COMPREHENSION = re.compile(r"\sfor\s+\w+(?:\s*,\s*\w+)*\s+in\s")  # built from real rows
DELAY = re.compile(r"Future\.delayed\(|setTimeout\(|\bsleep\(")
LITERAL_RETURN = re.compile(r"\breturn\s+(?:const\s+)?(?:<[^>]+>\s*)?[\[{]|\bresolve\(\s*[\[{]")
DELAY_WINDOW = 6
# A function signature in the scanned languages: def/function/func/fun, arrow bodies and typed methods.
FUNCTION_HEADER = re.compile(
    r"^\s*(?:@\w+\s*)?(?:(?:async|export|default|public|private|protected|internal|static|override|suspend|final)"
    r"\s+)*(?:def|function|func|fun)\b"
    r"|=>\s*\{?\s*$"
    r"|^(?!\s*(?:if|for|while|switch|catch|else|try|with|do|return|when)\b)\s*[\w<>\[\]?,.\s]+\([^;]*\)\s*"
    r"(?:async\*?|throws\s+\w+)?\s*(?:->\s*[^{:]+|:\s*[\w<>\[\]?.]+)?\s*\{\s*$"
)
# Reading from outside the process: DB/Firestore/HTTP clients, query builders, SQL, files, decoded payloads.
SOURCE_READ = re.compile(
    r"\b(?:fetch|axios|requests|httpx|http|urllib|firestore|firebase|supabase|prisma|db|database|cursor|session"
    r"|conn(?:ection)?|bigquery|redis|mongo\w*|dynamo\w*|s3|knex|sequelize|gorm|sqlx?)\b"
    r"|\.(?:get|collection|doc|document|query|execute|select|find\w*|where|from|stream|snapshots|once|load"
    r"|read\w*|list|scan|fetch\w*|aggregate|rpc|invoke|request|call)\s*\("
    r"|\bSELECT\b|\bjson\.loads?\b|\bjsonDecode\b|\.json\(\)|\bopen\(",
    re.IGNORECASE,
)
MAX_FUNCTION_LINES = 150
# Refs git leaves while it replays other commits into the working tree.
REPLAY_HEADS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REBASE_HEAD")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def added_lines(repo: Path, base: str) -> dict[str, list[tuple[int, str]]]:
    """Maps each changed or untracked file to its added (line number, text) pairs."""
    added: dict[str, list[tuple[int, str]]] = {}
    current: list[tuple[int, str]] | None = None
    number = 0
    for line in git(repo, "diff", "--unified=0", "--no-color", "--no-ext-diff", base, "--").splitlines():
        if line.startswith("+++ "):
            current = None if line == "+++ /dev/null" else added.setdefault(line[6:], [])
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            number = int(match.group(1)) if match else 0
        elif line.startswith("+") and current is not None:
            current.append((number, line[1:]))
            number += 1
    for rel in git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
        try:
            text = (repo / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        added[rel] = list(enumerate(text.splitlines(), start=1))
    return added


def replayed_heads(repo: Path) -> list[str]:
    """The commits git is replaying right now (merge, cherry-pick, rebase); empty otherwise."""
    heads = []
    for head in REPLAY_HEADS:
        try:
            git(repo, "rev-parse", "-q", "--verify", head)
        except RuntimeError:
            continue
        heads.append(head)
    return heads


def incoming_lines(repo: Path, rel: str, heads: list[str]) -> set[str]:
    """Every line of `rel` in the replayed commits (empty when they lack the file)."""
    lines: set[str] = set()
    for head in heads:
        try:
            lines.update(git(repo, "show", f"{head}:{rel}").splitlines())
        except RuntimeError:
            continue
    return lines


def indent(line: str) -> int:
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


def enclosing_function(source: list[str], index: int) -> list[str]:
    """The body of the function holding `source[index]`, from below its signature down to that line.

    The signature is left out so a parameter named `db` or `client` does not count as a read."""
    level = indent(source[index])
    start = max(0, index - MAX_FUNCTION_LINES)
    for i in range(index - 1, start - 1, -1):
        line = source[i]
        if not line.strip():
            continue
        current = indent(line)
        if current < level:
            if FUNCTION_HEADER.search(line):
                return source[i + 1:index + 1]
            level = current
    return source[start:index + 1]


def reads_real_source(source: list[str], number: int) -> bool:
    """True when the function around line `number` (1-based) reads data from outside the process."""
    if not 1 <= number <= len(source):
        return False
    body = [STRING_LITERAL.sub('""', line) for line in enclosing_function(source, number - 1)]
    return any(SOURCE_READ.search(line) for line in body)


def built_from_literals(text: str) -> bool:
    """True when the returned record holds only literal values (no variable, field or call result)."""
    match = LITERAL_RECORDS.search(text)
    if match is None:
        return False
    body = STRING_LITERAL.sub('""', text[match.start():])
    body = TRAILING_COMMENT.sub("", body)
    body = NOT_A_VALUE.sub("", body)
    body = re.sub(r"\[\][A-Za-z_]\w*", "", body)  # Go slice types such as []Order
    return all(word in LITERAL_WORDS for word in IDENTIFIER.findall(body))


def is_scanned(rel: str) -> bool:
    return Path(rel).suffix.lower() in SCANNED_SUFFIXES and not IGNORED_PATH.search(rel)


def approved_demo(repo: Path, rel: str) -> bool:
    """A demo counts only when the file is marked and the plan or spec names that file as approved."""
    try:
        if APPROVAL not in (repo / rel).read_text(encoding="utf-8"):
            return False
    except (OSError, UnicodeDecodeError):
        return False
    for plan in [*sorted(repo.glob("docs/*/PLAN.md")), *sorted(repo.glob("docs/*/spec.md")), repo / "PLAN.md"]:
        try:
            lines = plan.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        if any(APPROVAL in line and rel in line for line in lines):
            return True
    return False


def python_module_is_local(repo: Path, rel: str, module: str) -> bool:
    """True when `module` resolves to a file or package of this repository (relative imports included)."""
    if module.startswith("."):
        return True
    parts = module.split(".")
    folder = Path(rel).parent
    bases = [repo / folder] + [repo / parent for parent in folder.parents]
    for base in bases:
        target = base.joinpath(*parts)
        if target.with_suffix(".py").is_file() or (target / "__init__.py").is_file() or target.is_dir():
            return True
    return False


def own_dart_package(repo: Path, rel: str) -> str | None:
    """The `name:` of the pubspec.yaml closest to `rel`, so `package:<own>/` imports count as local."""
    for folder in [Path(rel).parent, *Path(rel).parent.parents]:
        pubspec = repo / folder / "pubspec.yaml"
        if pubspec.is_file():
            match = re.search(r"^name:\s*(\w+)", pubspec.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
            return match.group(1) if match else None
    return None


def defined_in_repo(repo: Path, name: str, cache: dict[str, bool]) -> bool:
    """True when some tracked or untracked file of the repository defines `name`."""
    if name not in cache:
        result = subprocess.run(["git", "-C", str(repo), "grep", "-qE", "--untracked", DEFINITION.format(name=name)],
                                capture_output=True, text=True)
        cache[name] = result.returncode == 0
    return cache[name]


def library_names(repo: Path, rel: str, source: list[str], cache: dict[str, bool] | None = None) -> set[str]:
    """Names this file takes from third-party packages.

    Python and JS/TS imports name them; for Dart, Go, JVM and Swift, an `InMemory...` class the repository
    never defines counts as a library's when the file imports any external package.
    """
    cache = cache if cache is not None else {}
    names: set[str] = set()
    local_imports: set[str] = set()
    own = own_dart_package(repo, rel) if rel.endswith(".dart") else None
    external = False
    for line in source:
        dart = DART_PACKAGE_IMPORT.match(line)
        if dart:
            external = external or dart.group(1) != own
            continue
        if OTHER_EXTERNAL_IMPORT.match(line):
            external = True
        match = PY_FROM_IMPORT.match(line)
        if match:
            imported = set(re.findall(r"[A-Za-z_]\w*", re.sub(r"\bas\s+\w+", "", match.group(2))))
            (local_imports if python_module_is_local(repo, rel, match.group(1)) else names).update(imported)
            continue
        match = JS_IMPORT.match(line)
        if match:
            imported = set(re.findall(r"[A-Za-z_]\w*", re.sub(r"\bas\s+\w+", "", match.group(1))))
            (local_imports if JS_LOCAL.match(match.group(2)) else names).update(imported)
    if external:
        for name in set(IN_MEMORY_NAME.findall("\n".join(source))) - names - local_imports:
            if not defined_in_repo(repo, name, cache):
                names.add(name)
    return names


def findings_for(rel: str, lines: list[tuple[int, str]], source: list[str] | None = None,
                 libraries: set[str] | None = None) -> list[str]:
    """Findings on the added `lines` of `rel`.

    `source` is the whole current file (function context) and `libraries` the names it imports from
    third-party packages.
    """
    source = source if source is not None else []
    libraries = libraries if libraries is not None else set()
    findings: list[str] = []
    for index, (number, text) in enumerate(lines):
        if APPROVAL in text:
            continue  # the approval marker itself is not data
        if COMMENT_LINE.match(text):
            pattern = dict(PATTERNS)[LEFT_FOR_LATER]
            if pattern.search(text):
                findings.append(f"{rel}:{number} [{LEFT_FOR_LATER}] {text.strip()[:100]}")
            continue
        if len(text) > MINIFIED_LINE:
            continue
        code = TRAILING_COMMENT.sub("", STRING_LITERAL.sub('""', text))
        reason = next((label for label, pattern in PATTERNS
                       if pattern.search(code if label in CODE_ONLY else text)), None)
        if reason == "random value" and len(RANDOM_CALL.findall(text)) == len(RANDOM_NOT_DATA.findall(text)):
            reason = next((label for label, pattern in PATTERNS if label not in ("random value", STAND_IN)
                           and pattern.search(code if label in CODE_ONLY else text)), None)
        if reason == STAND_IN and all(name in libraries for name in IN_MEMORY_NAME.findall(text)) \
                and IN_MEMORY_NAME.search(text):
            reason = next((label for label, pattern in PATTERNS
                           if label != STAND_IN and pattern.search(code if label in CODE_ONLY else text)), None)
        if reason is None and EXAMPLE_ADDRESS.search(text) and not INPUT_HINT.search(text):
            reason = "placeholder address"
        if reason is None and DATA_LAYER.search(rel) and built_from_literals(text) \
                and not COMPREHENSION.search(text) and not reads_real_source(source, number):
            reason = "fixed records returned from the data layer"
        if reason is None and DELAY.search(text):
            window = lines[index:index + DELAY_WINDOW]
            if any(LITERAL_RETURN.search(later) for _, later in window):
                reason = "literal data returned after a simulated delay"
        if reason:
            findings.append(f"{rel}:{number} [{reason}] {text.strip()[:100]}")
    return findings


def check(repo: Path, base: str) -> list[str]:
    findings: list[str] = []
    heads = replayed_heads(repo)
    definitions: dict[str, bool] = {}
    for rel, lines in sorted(added_lines(repo, base).items()):
        if not is_scanned(rel) or approved_demo(repo, rel):
            continue
        if heads:
            theirs = incoming_lines(repo, rel, heads)
            lines = [(number, text) for number, text in lines if text not in theirs]
        try:
            source = (repo / rel).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            source = []
        findings.extend(findings_for(rel, lines, source, library_names(repo, rel, source, definitions)))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", type=Path, default=Path("."), help="repository root (default: current directory)")
    parser.add_argument("--base", default="HEAD", help="commit or branch to compare with (default: %(default)s)")
    args = parser.parse_args(argv)

    try:
        findings = check(args.repo.resolve(), args.base)
    except (RuntimeError, OSError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    if findings:
        print("FAIL: fake data in production code. Connect the real source, or ask the user to approve a demo")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print(f"PASS: no fake data in lines added since {args.base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
