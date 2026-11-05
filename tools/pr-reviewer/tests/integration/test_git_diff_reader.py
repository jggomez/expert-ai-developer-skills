"""Reading real git output, including hostile file content and names."""

import subprocess
from pathlib import Path

import pytest

from pr_reviewer.adapters.git.diff_reader import GitDiffReader
from pr_reviewer.domain.diff_parser import parse_diff
from pr_reviewer.domain.file_selection import build_bundle


def test_git_diff_rejects_values_that_are_not_commit_shas(tmp_path: Path):
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="commit SHA"):
        GitDiffReader(tmp_path).read("--output=/tmp/x", "b" * 40)


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
    text = GitDiffReader(tmp_path).read(base, head)

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
    bundle = build_bundle(GitDiffReader(repo).read(base, head), base=base, head=head, exclude=[], max_chars=10_000)

    # Assert
    assert [f.path for f in bundle.files] == ["app.py"]
    assert bundle.files[0].commentable_lines == [1, 2, 3, 4, 5, 6]
    assert "secret_4" in bundle.files[0].patch
    assert bundle.omitted == []


def test_crafted_quoted_path_inside_content_does_not_crash(tmp_path: Path):
    # Arrange
    repo, base, head = commit_change(tmp_path, b"app.py", 'print(1)\x0cdiff --git x\x0c+++ "☃"\n'.encode())

    # Act
    bundle = build_bundle(GitDiffReader(repo).read(base, head), base=base, head=head, exclude=[], max_chars=10_000)

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
    files = parse_diff(GitDiffReader(repo).read(base, head))

    # Assert
    assert [f.path for f in files] == [expected]


def test_quoted_binary_file_keeps_its_name(tmp_path: Path):
    # Arrange
    repo, base, head = commit_change(tmp_path, b"u\nx.bin", b"\x00\x01\x02")

    # Act
    bundle = build_bundle(GitDiffReader(repo).read(base, head), base=base, head=head, exclude=[], max_chars=10_000)

    # Assert
    assert [(o.path, o.reason) for o in bundle.omitted] == [("u\nx.bin", "binary")]


def _commit(repo: Path, name: str, text: str) -> str:
    def git(*args: str) -> str:
        identity = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
        return subprocess.run(["git", *identity, *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()

    (repo / name).write_text(text, encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "change")
    return git("rev-parse", "HEAD")


def test_read_file_returns_the_version_in_the_given_commit_not_the_checkout(tmp_path: Path):
    # Arrange: the pull request rewrites the rubric after the base commit.
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    base = _commit(tmp_path, "rubric.md", "trusted")
    _commit(tmp_path, "rubric.md", "written by the pull request")

    # Act
    text = GitDiffReader(tmp_path).read_file(base, "rubric.md")

    # Assert
    assert text == "trusted"


def test_read_file_ignores_a_file_that_only_the_pull_request_adds(tmp_path: Path):
    # Arrange
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    base = _commit(tmp_path, "a.py", "a = 1")
    _commit(tmp_path, "rubric.md", "written by the pull request")

    # Act / Assert
    with pytest.raises(ValueError, match=r"rubric\.md"):
        GitDiffReader(tmp_path).read_file(base, "rubric.md")


def test_read_file_requires_a_full_sha(tmp_path: Path):
    # Act / Assert
    with pytest.raises(ValueError, match="full commit SHA"):
        GitDiffReader(tmp_path).read_file("main", "rubric.md")
