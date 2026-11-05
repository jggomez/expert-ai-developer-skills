"""Splitting a large pull request into groups."""

from pr_reviewer.domain.models import DiffBundle, FileDiff, OmittedFile
from pr_reviewer.domain.sharding import SHARD_TARGET_CHARS, split_into_shards


def make_bundle(*sizes: tuple[str, int]) -> DiffBundle:
    files = [FileDiff(path=path, patch="x" * size) for path, size in sizes]
    return DiffBundle(base="a" * 40, head="b" * 40, files=files, omitted=[OmittedFile(path="z", reason="binary")])


def test_a_small_pull_request_stays_whole():
    # Arrange
    bundle = make_bundle(("a.py", 100), ("b.py", 100))

    # Act / Assert
    assert split_into_shards(bundle) == [bundle]


def test_every_file_lands_in_exactly_one_group_within_the_limit():
    # Arrange
    bundle = make_bundle(*[(f"pkg{i}/mod.py", SHARD_TARGET_CHARS // 2) for i in range(20)])

    # Act
    shards = split_into_shards(bundle, max_shards=4)

    # Assert
    paths = [file.path for shard in shards for file in shard.files]
    assert len(shards) == 4
    assert sorted(paths) == sorted(file.path for file in bundle.files)


def test_neighboring_paths_stay_together_and_order_of_the_diff_does_not_matter():
    # Arrange
    size = SHARD_TARGET_CHARS // 2
    bundle = make_bundle(("b/2.py", size), ("a/1.py", size), ("b/1.py", size), ("a/2.py", size))

    # Act
    shards = split_into_shards(bundle, max_shards=2)

    # Assert
    assert [[file.path for file in shard.files] for shard in shards] == [["a/1.py", "a/2.py"], ["b/1.py", "b/2.py"]]


def test_one_group_when_splitting_is_turned_off():
    # Arrange
    bundle = make_bundle(("a.py", SHARD_TARGET_CHARS), ("b.py", SHARD_TARGET_CHARS))

    # Act / Assert
    assert split_into_shards(bundle, max_shards=1) == [bundle]


def test_a_single_huge_file_stays_alone():
    # Arrange
    bundle = make_bundle(("big.py", SHARD_TARGET_CHARS * 3), ("small.py", 10))

    # Act
    shards = split_into_shards(bundle, max_shards=2)

    # Assert
    assert len(shards) == 2


def test_groups_do_not_repeat_the_omitted_list():
    # Arrange
    bundle = make_bundle(("a.py", SHARD_TARGET_CHARS), ("b.py", SHARD_TARGET_CHARS))

    # Act
    shards = split_into_shards(bundle)

    # Assert
    assert all(not shard.omitted for shard in shards)
