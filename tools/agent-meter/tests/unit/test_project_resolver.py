"""Tests for ``agent_meter.project_resolver`` (ADR §3.7; PR-01..06, BR-07/08)."""

from __future__ import annotations

import hashlib
import os
import subprocess
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import pytest

from agent_meter.project_resolver import (
    ProjectOverride,
    ProjectResolver,
    ProjectsConfig,
    ProjectsConfigError,
    load_projects_config,
    normalize_remote,
    path_hash,
    save_projects_config,
)

EMPTY = ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={})


class DictCache:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, path_hash: str) -> str | None:
        return self.data.get(path_hash)

    def put(self, path_hash: str, project_id: str) -> None:
        self.data[path_hash] = project_id


@pytest.fixture(autouse=True)
def hermetic_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@example.invalid")


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=20)


def make_repo(path: Path, remote: str | None = None, *, commit: bool = False) -> Path:
    path.mkdir(parents=True)
    git("init", "-q", cwd=path)
    if remote is not None:
        git("remote", "add", "origin", remote, cwd=path)
    if commit:
        git("commit", "-q", "--allow-empty", "-m", "init", cwd=path)
    return path


def resolver(
    tmp_path: Path,
    config: ProjectsConfig = EMPTY,
    cache: DictCache | None = None,
    temp_roots: tuple[str, ...] = (),
) -> ProjectResolver:
    return ProjectResolver(
        cache or DictCache(), config, home=tmp_path / "home", temp_roots=temp_roots
    )


def expected_git_id(normalized: str) -> str:
    return "git:" + hashlib.sha256(normalized.encode()).hexdigest()[:16]


# --- normalize_remote (PR-02) --------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:jggomez/skills-programming-ai.git",
        "https://github.com/jggomez/skills-programming-ai.git",
        "https://user:s3cret@GitHub.com/jggomez/skills-programming-ai/",
        "ssh://git@github.com:22/jggomez/skills-programming-ai.git",
        "http://github.com:8080/jggomez/skills-programming-ai",
        "git://github.com/jggomez/skills-programming-ai.git",
        "  https://github.com/jggomez/skills-programming-ai.git\n",
    ],
)
def test_normalize_remote_ssh_and_https_forms_are_equal(url: str) -> None:
    assert normalize_remote(url) == "github.com/jggomez/skills-programming-ai"


def test_normalize_remote_keeps_path_case_and_drops_credentials() -> None:
    result = normalize_remote("https://tok@GitLab.Example.com/Group/Sub/Repo.git")

    assert result == "gitlab.example.com/Group/Sub/Repo"
    assert "tok" not in (result or "")


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "/srv/git/repo.git",
        "file:///srv/git/repo.git",
        "../repo",
        "https://",
        "git@host:",
    ],
)
def test_normalize_remote_rejects_local_or_invalid(url: str) -> None:
    assert normalize_remote(url) is None


def test_path_hash_is_sha256_of_realpath(tmp_path: Path) -> None:
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)

    assert (
        path_hash(str(link))
        == hashlib.sha256(os.path.realpath(target).encode()).hexdigest()
    )
    assert (
        path_hash(str(tmp_path / "gone" / "x"))
        == hashlib.sha256(
            os.path.realpath(tmp_path / "gone" / "x").encode()
        ).hexdigest()
    )


# --- PR-01 / PR-02 / PR-06 --------------------------------------------------------------------


def test_same_repo_from_cwd_and_file_uri_gets_same_project(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "my repo", "git@github.com:me/my-repo.git")
    res = resolver(tmp_path)

    from_cwd = res.resolve(str(repo))
    from_uri = res.resolve("file://" + quote(str(repo)))
    from_subdir = res.resolve(str(repo / "."))

    assert from_cwd == from_uri == from_subdir
    assert from_cwd.project_id == expected_git_id("github.com/me/my-repo")
    assert from_cwd.kind == "remote" and from_cwd.remote_url == "github.com/me/my-repo"
    assert from_cwd.display_name == "my-repo"


def test_ssh_and_https_clones_are_one_project(tmp_path: Path) -> None:
    a = make_repo(tmp_path / "a", "git@github.com:me/x.git")
    b = make_repo(tmp_path / "b", "https://github.com/me/x")
    res = resolver(tmp_path)

    assert res.resolve(str(a)).project_id == res.resolve(str(b)).project_id


def test_moved_directory_with_same_remote_keeps_project(tmp_path: Path) -> None:
    old = make_repo(tmp_path / "old-location", "https://github.com/me/moved.git")
    before = resolver(tmp_path).resolve(str(old))
    new = tmp_path / "elsewhere" / "renamed"
    new.parent.mkdir()
    old.rename(new)

    after = resolver(tmp_path).resolve(str(new))

    assert after.project_id == before.project_id


def test_repo_subdirectory_resolves_to_repo(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r", "https://github.com/me/r.git")
    sub = repo / "pkg" / "src"
    sub.mkdir(parents=True)

    assert resolver(tmp_path).resolve(str(sub)).project_id == expected_git_id(
        "github.com/me/r"
    )


# --- PR-03 worktrees ------------------------------------------------------------------------------


def test_worktree_maps_to_main_repo_project(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "main", "git@github.com:me/wt.git", commit=True)
    worktree = repo / ".claude" / "worktrees" / "track-a"
    git("worktree", "add", "-q", str(worktree), cwd=repo)

    ref = resolver(tmp_path).resolve(str(worktree))

    assert ref.project_id == expected_git_id("github.com/me/wt")


def test_worktree_of_repo_without_remote_uses_main_repo_path(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "local-only", commit=True)
    worktree = tmp_path / "wt-elsewhere"
    git("worktree", "add", "-q", str(worktree), cwd=repo)
    res = resolver(tmp_path)

    assert res.resolve(str(worktree)) == res.resolve(str(repo))
    assert res.resolve(str(repo)).project_id == "path:" + path_hash(str(repo))[:16]


@pytest.mark.parametrize("segment", [".claude/worktrees", ".worktrees", "worktrees"])
def test_deleted_worktree_resolves_prefix_before_segment(
    tmp_path: Path, segment: str
) -> None:
    repo = make_repo(tmp_path / "proj", "https://github.com/me/proj.git")
    missing = repo / segment / "deleted-branch" / "sub"

    ref = resolver(tmp_path).resolve(str(missing))

    assert ref.project_id == expected_git_id("github.com/me/proj")


# --- PR-04 non-git and missing directories --------------------------------------------------------------


def test_non_git_directory_gets_path_id(tmp_path: Path) -> None:
    plain = tmp_path / "notes"
    plain.mkdir()

    ref = resolver(tmp_path).resolve(str(plain))

    assert (
        ref.project_id
        == "path:" + hashlib.sha256(os.path.realpath(plain).encode()).hexdigest()[:16]
    )
    assert ref.kind == "path" and ref.display_name == "notes" and ref.remote_url is None


def test_existing_directory_is_cached_and_missing_directory_uses_cache(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path / "cached", "https://github.com/me/cached.git")
    cache = DictCache()
    first = resolver(tmp_path, cache=cache).resolve(str(repo))
    subprocess.run(["rm", "-rf", str(repo)], check=True)

    later = resolver(tmp_path, cache=cache).resolve(str(repo))

    assert cache.data[path_hash(str(repo))] == first.project_id
    assert later.project_id == first.project_id and later.kind == "remote"


def test_missing_directory_without_cache_falls_back_to_path_id(tmp_path: Path) -> None:
    gone = tmp_path / "vanished" / "proj"

    ref = resolver(tmp_path).resolve(str(gone))

    assert (
        ref.project_id == "path:" + path_hash(str(gone))[:16]
        and ref.display_name == "proj"
    )


def test_moved_directory_old_missing_path_maps_to_existing_location(
    tmp_path: Path,
) -> None:
    # Arrange: the repo now lives under consultorias/; old transcripts still hold the
    # pre-move path, which no longer exists and was never cached.
    repo = make_repo(
        tmp_path / "consultorias" / "scrc-ai" / "svc", "https://github.com/me/svc.git"
    )
    old_path = f"file://{tmp_path}/scrc-ai/svc"
    cache = DictCache()
    current = resolver(tmp_path, cache=cache).resolve(str(repo))

    # Act: a later run (fresh resolver, same persisted cache) sees the old path.
    moved = resolver(tmp_path, cache=cache).resolve(old_path)

    # Assert
    assert current.kind == "remote"
    assert moved.project_id == current.project_id
    assert moved.display_name == current.display_name


def test_two_missing_locations_of_same_folder_share_project(tmp_path: Path) -> None:
    # Arrange
    first_old = tmp_path / "docs" / "ai-rag-docs"
    second_old = tmp_path / "consultorias" / "docs" / "ai-rag-docs"
    cache = DictCache()

    # Act
    first = resolver(tmp_path, cache=cache).resolve(str(first_old))
    second = resolver(tmp_path, cache=cache).resolve(f"file://{second_old}")

    # Assert
    assert second.project_id == first.project_id


def test_ambiguous_folder_name_is_not_relocated(tmp_path: Path) -> None:
    # Arrange: two distinct existing folders share a name; a missing one must not guess.
    (tmp_path / "a" / "app").mkdir(parents=True)
    (tmp_path / "b" / "app").mkdir(parents=True)
    r = resolver(tmp_path)
    first, second = r.resolve(str(tmp_path / "a" / "app")), r.resolve(str(tmp_path / "b" / "app"))

    # Act
    gone = r.resolve(str(tmp_path / "c" / "app"))

    # Assert
    assert gone.project_id not in {first.project_id, second.project_id}


def test_git_unavailable_falls_back_without_crashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path / "nogit", "https://github.com/me/nogit.git")
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))

    ref = resolver(tmp_path).resolve(str(repo))

    assert ref.kind == "path"


# --- BR-08 unassigned -------------------------------------------------------------------------------------


def test_unassigned_paths(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    scratch_root = tmp_path / "scratch"
    (scratch_root / "x").mkdir(parents=True)
    ignored = tmp_path / "ignored"
    (ignored / "deep").mkdir(parents=True)
    config = ProjectsConfig(
        projects={}, path_aliases={}, ignore=(str(ignored),), merges={}
    )
    res = resolver(tmp_path, config=config, temp_roots=(str(scratch_root),))

    for path in (
        None,
        "",
        str(home),
        "/",
        str(scratch_root / "x"),
        str(ignored / "deep"),
        "file:///",
    ):
        ref = res.resolve(path)
        assert (ref.project_id, ref.kind, ref.remote_url) == (
            "(unassigned)",
            "unassigned",
            None,
        ), path


def test_default_temp_roots_include_tmp() -> None:
    res = ProjectResolver(DictCache(), EMPTY, home=Path("/nonexistent-home"))

    assert res.resolve("/tmp/some-scratch-dir").project_id == "(unassigned)"


# --- PR-05 projects.yaml overrides, aliases and merges -------------------------------------------------------


def test_projects_yaml_overrides_display_name(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r", "https://github.com/me/r.git")
    pid = expected_git_id("github.com/me/r")
    config = ProjectsConfig(
        projects={pid: ProjectOverride(display_name="Project X", client="Client Z")},
        path_aliases={},
        ignore=(),
        merges={},
    )

    assert (
        resolver(tmp_path, config=config).resolve(str(repo)).display_name == "Project X"
    )


def test_path_alias_and_merge_rekey_projects(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "survivor", "https://github.com/me/survivor.git")
    survivor = expected_git_id("github.com/me/survivor")
    old_dir = tmp_path / "old" / "place"
    plain = tmp_path / "plain"
    plain.mkdir()
    plain_id = "path:" + path_hash(str(plain))[:16]
    config = ProjectsConfig(
        projects={},
        path_aliases={str(tmp_path / "old"): survivor},
        ignore=(),
        merges={plain_id: survivor},
    )
    res = resolver(tmp_path, config=config)

    assert res.resolve(str(old_dir)).project_id == survivor
    assert res.resolve(str(plain)).project_id == survivor
    assert res.resolve(str(repo)).project_id == survivor


def test_merge_cycles_do_not_loop(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    pid = "path:" + path_hash(str(plain))[:16]
    config = ProjectsConfig(
        projects={},
        path_aliases={},
        ignore=(),
        merges={pid: "git:aaaa", "git:aaaa": pid},
    )

    assert resolver(tmp_path, config=config).resolve(str(plain)).project_id in {
        pid,
        "git:aaaa",
    }


def test_load_and_save_projects_config_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "projects.yaml"
    path.write_text(
        "version: 1\n"
        "projects:\n"
        '  "git:3f2a9c0d1e2b4a56": {display_name: "Project X", client: "Client Z", billing: hourly, rate: "80000", currency: COP}\n'
        '  "git:9a8b7c6d5e4f3a21": {client: "Client Z", billing: fixed, fixed_price: "2500", currency: USD}\n'
        "paths:\n"
        '  /Users/me/old/location: "git:3f2a9c0d1e2b4a56"\n'
        'ignore: ["/Users/me/scratch"]\n'
        'merges: {"path:0011223344556677": "git:3f2a9c0d1e2b4a56"}\n',
        encoding="utf-8",
    )

    cfg = load_projects_config(path)
    save_projects_config(cfg, tmp_path / "copy.yaml")
    again = load_projects_config(tmp_path / "copy.yaml")

    assert cfg.projects["git:3f2a9c0d1e2b4a56"] == ProjectOverride(
        display_name="Project X",
        client="Client Z",
        billing="hourly",
        rate=Decimal(80000),
        currency="COP",
    )
    assert cfg.projects["git:9a8b7c6d5e4f3a21"].fixed_price == Decimal(2500)
    assert cfg.path_aliases == {"/Users/me/old/location": "git:3f2a9c0d1e2b4a56"}
    assert cfg.ignore == ("/Users/me/scratch",)
    assert cfg.merges == {"path:0011223344556677": "git:3f2a9c0d1e2b4a56"}
    assert again == cfg


def test_missing_projects_file_is_empty_config(tmp_path: Path) -> None:
    assert load_projects_config(tmp_path / "absent.yaml") == EMPTY


@pytest.mark.parametrize(
    "body",
    [
        "version: 2\n",
        "version: 1\nprojects: {p: {billing: weekly}}\n",
        "version: 1\nprojects: {p: {rate: 80.5}}\n",
        "version: 1\nprojects: {p: {colour: red}}\n",
        "version: 1\nignore: /not/a/list\n",
        "version: 1\nprojects: [unclosed\n",
    ],
)
def test_invalid_projects_config_is_rejected(tmp_path: Path, body: str) -> None:
    path = tmp_path / "projects.yaml"
    path.write_text(body, encoding="utf-8")

    with pytest.raises(ProjectsConfigError):
        load_projects_config(path)
