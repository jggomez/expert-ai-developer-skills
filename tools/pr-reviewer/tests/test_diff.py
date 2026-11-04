"""Diff parsing, filtering and size budget."""

import subprocess
from pathlib import Path

import pytest

from pr_reviewer.diff import build_bundle, git_diff, parse_diff

DIFF = """\
diff --git a/app/db.py b/app/db.py
index 111..222 100644
--- a/app/db.py
+++ b/app/db.py
@@ -10,3 +10,4 @@ def load():
 keep = 1
-old = 2
+new = 2
+++weird = 3
 tail = 4
\\ No newline at end of file
diff --git a/uv.lock b/uv.lock
index 111..222 100644
--- a/uv.lock
+++ b/uv.lock
@@ -1 +1 @@
-a
+b
diff --git a/gone.py b/gone.py
deleted file mode 100644
index 111..000
--- a/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-x
diff --git a/logo.png b/logo.png
index 111..222 100644
Binary files a/logo.png and b/logo.png differ
diff --git a/old name.py b/new name.py
similarity index 90%
rename from old name.py
rename to new name.py
index 111..222 100644
--- a/old name.py\t
+++ b/new name.py\t
@@ -1 +1 @@
-a
+b
"""


def test_parse_commentable_lines_use_new_file_numbers_and_ignore_plus_content():
    # Arrange / Act
    files = {f.path: f for f in parse_diff(DIFF)}

    # Assert: context + added lines; "+++weird" is content, not a header
    assert files["app/db.py"].commentable_lines == [10, 11, 12, 13]
    assert len(files) == 5


def test_parse_marks_deleted_binary_and_renamed_files():
    # Arrange / Act
    files = {f.path: f for f in parse_diff(DIFF)}

    # Assert
    assert files["gone.py"].deleted is True
    assert files["logo.png"].binary is True
    assert files["new name.py"].commentable_lines == [1]


def test_bundle_reports_every_omitted_file_with_its_reason():
    # Arrange / Act
    bundle = build_bundle(DIFF, base="a" * 40, head="b" * 40, exclude=[], max_chars=10_000)

    # Assert
    assert sorted(f.path for f in bundle.files) == ["app/db.py", "new name.py"]
    assert {o.path: o.reason for o in bundle.omitted} == {
        "uv.lock": "excluded",
        "gone.py": "deleted",
        "logo.png": "binary",
    }


def test_user_exclude_supports_directories_and_basenames():
    # Arrange / Act
    bundle = build_bundle(DIFF, base="a" * 40, head="b" * 40, exclude=["app/*", "new name.*"], max_chars=10_000)

    # Assert
    assert bundle.files == []
    assert {o.path: o.reason for o in bundle.omitted}["app/db.py"] == "excluded"


def test_size_budget_keeps_source_before_tests_and_declares_the_rest():
    # Arrange
    def file_diff(path: str, lines: int) -> str:
        body = "\n".join(f"+line{i}" for i in range(lines))
        return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -0,0 +1,{lines} @@\n{body}\n"

    text = file_diff("tests/test_big.py", 5) + file_diff("src/small.py", 5) + file_diff("src/huge.py", 500)

    # Act
    bundle = build_bundle(text, base="a" * 40, head="b" * 40, exclude=[], max_chars=250)

    # Assert
    assert [f.path for f in bundle.files] == ["src/small.py"]
    assert {o.path: o.reason for o in bundle.omitted} == {
        "tests/test_big.py": "size-limit",
        "src/huge.py": "size-limit",
    }


def test_git_diff_rejects_values_that_are_not_commit_shas(tmp_path: Path):
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="commit SHA"):
        git_diff(tmp_path, "--output=/tmp/x", "b" * 40)


def test_git_diff_reads_merge_base_changes_and_ignores_textconv(tmp_path: Path):
    # Arrange
    def git(*args: str) -> str:
        env_args = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
        return subprocess.run(["git", *env_args, *args], cwd=tmp_path, check=True, capture_output=True, text=True).stdout.strip()

    git("init", "-q")
    (tmp_path / "a.py").write_text("one\n")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / ".gitattributes").write_text("*.py diff=evil\n")
    (tmp_path / "a.py").write_text("one\ntwo\n")
    git("config", "diff.evil.textconv", "false")
    git("add", ".")
    git("commit", "-qm", "head")
    head = git("rev-parse", "HEAD")

    # Act
    text = git_diff(tmp_path, base, head)

    # Assert
    assert "+two" in text


def commit_change(tmp_path: Path, name: bytes, content: bytes) -> tuple[Path, str, str]:
    def git(*args: str) -> str:
        identity = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
        return subprocess.run(["git", *identity, *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()

    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q")
    (repo / "seed.txt").write_text("seed\n")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    with open(bytes(repo) + b"/" + name, "wb") as handle:
        handle.write(content)
    git("add", ".")
    git("commit", "-qm", "head")
    return repo, base, git("rev-parse", "HEAD")


@pytest.mark.parametrize("separator", [b"\x0c", b"\r", b"\xe2\x80\xa8", b"\xc2\x85"])
def test_line_separators_inside_a_file_cannot_forge_diff_structure(tmp_path: Path, separator: bytes):
    # Arrange: content tries to start a fake file section, then real code follows
    forged = b"x = 1" + (separator + b"+y") * 5 + separator + b"diff --git a/f.lock b/f.lock\n"
    content = forged + b"".join(b"secret_%d = 1\n" % i for i in range(5))
    repo, base, head = commit_change(tmp_path, b"app.py", content)

    # Act
    bundle = build_bundle(git_diff(repo, base, head), base=base, head=head, exclude=[], max_chars=10_000)

    # Assert
    assert [f.path for f in bundle.files] == ["app.py"]
    assert bundle.files[0].commentable_lines == [1, 2, 3, 4, 5, 6]
    assert "secret_4" in bundle.files[0].patch
    assert bundle.omitted == []


def test_crafted_quoted_path_inside_content_does_not_crash(tmp_path: Path):
    # Arrange
    repo, base, head = commit_change(tmp_path, b"app.py", 'print(1)\x0cdiff --git x\x0c+++ "☃"\n'.encode())

    # Act
    bundle = build_bundle(git_diff(repo, base, head), base=base, head=head, exclude=[], max_chars=10_000)

    # Assert
    assert [f.path for f in bundle.files] == ["app.py"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [(b"u\nx.py", "u\nx.py"), ('café"q.py'.encode(), 'café"q.py'), (b"back\\slash.py", "back\\slash.py")],
)
def test_quoted_file_names_are_decoded_exactly(tmp_path: Path, name: bytes, expected: str):
    # Arrange
    repo, base, head = commit_change(tmp_path, name, b"x = 1\n")

    # Act
    files = parse_diff(git_diff(repo, base, head))

    # Assert
    assert [f.path for f in files] == [expected]


def test_quoted_binary_file_keeps_its_name(tmp_path: Path):
    # Arrange
    repo, base, head = commit_change(tmp_path, b"u\nx.bin", b"\x00\x01\x02")

    # Act
    bundle = build_bundle(git_diff(repo, base, head), base=base, head=head, exclude=[], max_chars=10_000)

    # Assert
    assert [(o.path, o.reason) for o in bundle.omitted] == [("u\nx.bin", "binary")]
