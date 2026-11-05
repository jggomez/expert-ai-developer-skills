"""Turning two commits into the files to review."""

from pr_reviewer.application.prepare_diff import prepare_diff

BASE, HEAD = "a" * 40, "b" * 40
PATCH = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -0,0 +1 @@\n+y\n"


class StubReader:
    def read(self, base: str, head: str) -> str:
        assert (base, head) == (BASE, HEAD)
        return PATCH


def test_reader_output_is_parsed_into_a_bundle_for_those_commits():
    # Act
    bundle = prepare_diff(StubReader(), base=BASE, head=HEAD, exclude=[])

    # Assert
    assert (bundle.base, bundle.head) == (BASE, HEAD)
    assert [f.path for f in bundle.files] == ["x.py"]


def test_exclusions_are_applied():
    # Act
    bundle = prepare_diff(StubReader(), base=BASE, head=HEAD, exclude=["x.py"])

    # Assert
    assert bundle.files == []
