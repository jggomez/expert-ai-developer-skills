"""Parse unified diff text into changed files."""

from __future__ import annotations

import re

from pr_reviewer.domain.models import FileDiff

_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_QUOTED_PATH = re.compile(r'"(?:[^"\\]|\\.)*"')
_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


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
