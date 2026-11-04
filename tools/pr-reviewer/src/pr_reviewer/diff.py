"""Read a pull request diff and decide what the agent reviews."""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path, PurePosixPath

from pr_reviewer.models import DiffBundle, FileDiff, OmittedFile

DEFAULT_MAX_CHARS = 120_000

DEFAULT_EXCLUDE = (
    "*.lock",
    "*.lockb",
    "package-lock.json",
    "pnpm-lock.yaml",
    "go.sum",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.snap",
    "*.svg",
    "*.g.dart",
    "*.freezed.dart",
    "*.pb.go",
    "*_pb2.py",
    "*_pb2_grpc.py",
    "dist/*",
    "*/dist/*",
    "build/*",
    "*/build/*",
    "vendor/*",
    "*/vendor/*",
    "node_modules/*",
    "*/node_modules/*",
)

_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_QUOTED_PATH = re.compile(r'"(?:[^"\\]|\\.)*"')
_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}
_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|(^|/)test_|_test\.|\.test\.|\.spec\.")


def git_diff(repo: Path, base: str, head: str) -> str:
    """Return the three-dot diff between two commits.

    External diff drivers and textconv are disabled because both can be
    configured to run commands, and the repository content is untrusted.
    """
    for sha in (base, head):
        if not _SHA.fullmatch(sha):
            raise ValueError(f"Expected a full commit SHA, got {sha!r}")
    completed = subprocess.run(
        [
            "git",
            "-c",
            "core.quotePath=false",
            "diff",
            "--no-color",
            "--no-ext-diff",
            "--no-textconv",
            "--find-renames",
            f"{base}...{head}",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    # Decoded from bytes: text mode would turn a lone CR in a file into a new line.
    return completed.stdout.decode("utf-8", "replace")


def parse_diff(text: str) -> list[FileDiff]:
    """Parse unified diff text into one entry per changed file."""
    files: list[FileDiff] = []
    for section in _split_files(text):
        files.append(_parse_file(section))
    return files


def _split_files(text: str) -> list[list[str]]:
    sections: list[list[str]] = []
    remaining_old = remaining_new = 0
    # Split on "\n" only. splitlines() also breaks on form feeds and Unicode
    # separators, which would let file content forge diff structure.
    for line in text.split("\n"):
        in_hunk = remaining_old > 0 or remaining_new > 0
        if line.startswith("diff --git ") and not in_hunk:
            sections.append([line])
            continue
        if not sections:
            continue
        sections[-1].append(line)
        match = _HUNK.match(line) if not in_hunk else None
        if match:
            remaining_old = int(match.group(1) or 1)
            remaining_new = int(match.group(3) or 1)
        elif in_hunk:
            if line.startswith(" "):
                remaining_old -= 1
                remaining_new -= 1
            elif line.startswith("-"):
                remaining_old -= 1
            elif line.startswith("+"):
                remaining_new -= 1
    return sections


def _parse_file(lines: list[str]) -> FileDiff:
    path = _path_from_header(lines[0])
    deleted = binary = False
    commentable: list[int] = []
    new_line = 0
    in_hunk = False

    for line in lines[1:]:
        match = _HUNK.match(line)
        if match:
            in_hunk = True
            new_line = int(match.group(2))
        elif in_hunk:
            if line.startswith((" ", "+")):
                commentable.append(new_line)
                new_line += 1
        elif line.startswith("+++ "):
            target = line[4:].rstrip("\t")
            if target == "/dev/null":
                deleted = True
            else:
                path = _strip_prefix(_unquote(target))
        elif line.startswith("--- ") and path == "":
            path = _strip_prefix(_unquote(line[4:].rstrip("\t")))
        elif line.startswith("rename to "):
            path = _unquote(line.removeprefix("rename to "))
        elif line.startswith("deleted file mode"):
            deleted = True
        elif line.startswith(("Binary files ", "GIT binary patch")):
            binary = True

    return FileDiff(
        path=path,
        patch="\n".join(lines) + "\n",
        commentable_lines=commentable,
        deleted=deleted,
        binary=binary,
    )


def _path_from_header(header: str) -> str:
    body = header.removeprefix("diff --git ")
    quoted = _QUOTED_PATH.match(body)
    if quoted:
        return _strip_prefix(_unquote(quoted.group(0)))
    # Both sides are equal unless the file was renamed, and renames are read later.
    middle = len(body) // 2
    left, right = body[:middle], body[middle + 1:]
    if left.removeprefix("a/") == right.removeprefix("b/"):
        return left.removeprefix("a/")
    return ""


def _strip_prefix(path: str) -> str:
    return path[2:] if path.startswith(("a/", "b/")) else path


def _unquote(value: str) -> str:
    """Decode git's C-style path quoting. Malformed input is kept, never raised."""
    if len(value) < 2 or not (value.startswith('"') and value.endswith('"')):
        return value
    decoded = bytearray()
    source = value[1:-1]
    index = 0
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        octal = source[index + 1 : index + 4]
        if char != "\\":
            decoded += char.encode("utf-8")
            index += 1
        elif following in _ESCAPES and following:
            decoded.append(_ESCAPES[following])
            index += 2
        elif len(octal) == 3 and all(c in "01234567" for c in octal) and int(octal, 8) < 256:
            decoded.append(int(octal, 8))
            index += 4
        else:
            decoded += char.encode("utf-8")
            index += 1
    return decoded.decode("utf-8", "replace")


def is_excluded(path: str, patterns: tuple[str, ...] | list[str]) -> bool:
    """Match a pattern against the whole path or the file name."""
    name = PurePosixPath(path).name
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in patterns)


def _priority(file: FileDiff) -> tuple[bool, int]:
    return (bool(_TEST_PATH.search(file.path)), len(file.patch))


def build_bundle(
    text: str,
    *,
    base: str,
    head: str,
    exclude: list[str],
    max_chars: int = DEFAULT_MAX_CHARS,
) -> DiffBundle:
    """Choose the files to review: source first, then smallest, within the size budget."""
    patterns = [*DEFAULT_EXCLUDE, *exclude]
    selected: list[FileDiff] = []
    omitted: list[OmittedFile] = []

    candidates: list[FileDiff] = []
    for file in parse_diff(text):
        if file.deleted:
            omitted.append(OmittedFile(path=file.path, reason="deleted"))
        elif file.binary:
            omitted.append(OmittedFile(path=file.path, reason="binary"))
        elif is_excluded(file.path, patterns):
            omitted.append(OmittedFile(path=file.path, reason="excluded"))
        elif file.commentable_lines:
            candidates.append(file)

    used = 0
    for file in sorted(candidates, key=_priority):
        if used + len(file.patch) <= max_chars:
            selected.append(file)
            used += len(file.patch)
        else:
            omitted.append(OmittedFile(path=file.path, reason="size-limit"))

    return DiffBundle(base=base, head=head, files=selected, omitted=omitted)
