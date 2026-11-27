"""The change map is built from the diff; the model only labels areas the diff already has."""

from pr_reviewer.domain.change_map import MAX_AREAS, build_change_map
from pr_reviewer.domain.models import (
    AreaChange,
    AreaLink,
    DiffBundle,
    FileDiff,
    PullRequestSummary,
)
from support.builders import finding


def _patch(added: int, deleted: int) -> str:
    return "--- a/x\n+++ b/x\n@@ -1 +1 @@\n" + "-old\n" * deleted + "+new\n" * added


def _bundle(*files: tuple[str, int, int]) -> DiffBundle:
    return DiffBundle(base="a" * 40, head="b" * 40,
                      files=[FileDiff(path=path, patch=_patch(add, rem)) for path, add, rem in files])


def test_files_are_grouped_by_the_shallowest_folder_that_splits_them():
    # Arrange
    diff = _bundle(("src/api/clients.py", 10, 2), ("src/api/routes.py", 5, 0), ("src/web/page.tsx", 7, 1))
    # Act
    change_map = build_change_map(diff, None, [])
    # Assert
    assert [(a.name, a.added, a.deleted, a.files) for a in change_map.areas] == [
        ("src/api", 15, 2, 2), ("src/web", 7, 1, 1)]


def test_root_files_get_their_own_area():
    # Arrange
    diff = _bundle(("README.md", 3, 0), ("app/main.py", 4, 4))
    # Act
    names = [a.name for a in build_change_map(diff, None, []).areas]
    # Assert
    assert names == ["(root)", "app"]


def test_many_folders_collapse_the_smallest_into_other():
    # Arrange
    diff = _bundle(*[(f"m{i}/f.py", 100 - i, 0) for i in range(12)])
    # Act
    areas = build_change_map(diff, None, []).areas
    # Assert
    assert len(areas) == MAX_AREAS
    assert areas[-1].name == "other"
    assert areas[-1].files == 12 - (MAX_AREAS - 1)


def test_model_labels_and_links_map_to_known_areas_only():
    # Arrange
    diff = _bundle(("api/clients.py", 10, 0), ("services/firestore.py", 5, 0), ("web/page.tsx", 3, 0))
    summary = PullRequestSummary(
        overview="Adds the Clients to Review page.",
        changes=[AreaChange(path="api/clients.py", what="new endpoint"),
                 AreaChange(path="services", what="reads Firestore"),
                 AreaChange(path="../etc/passwd", what="ignored")],
        links=[AreaLink(source="web/page.tsx", target="api"), AreaLink(source="api", target="services/firestore.py"),
               AreaLink(source="api", target="api/clients.py"), AreaLink(source="nowhere", target="api"),
               AreaLink(source="web", target="api")],
    )
    # Act
    change_map = build_change_map(diff, summary, [])
    # Assert
    assert {a.name: a.what for a in change_map.areas} == {"api": "new endpoint", "services": "reads Firestore", "web": ""}
    names = [a.name for a in change_map.areas]
    assert [(names[s], names[t]) for s, t in change_map.links] == [("web", "api"), ("api", "services")]
    assert change_map.overview == "Adds the Clients to Review page."


def test_each_area_carries_its_worst_finding():
    # Arrange
    diff = _bundle(("api/a.py", 1, 0), ("web/b.tsx", 1, 0))
    findings = [finding(file="api/a.py", severity="medium"), finding(file="api/a.py", severity="critical")]
    # Act
    areas = build_change_map(diff, None, findings).areas
    # Assert
    assert [(a.name, a.severity) for a in areas] == [("api", "critical"), ("web", None)]


def test_a_single_folder_descends_until_it_splits():
    # Arrange
    diff = _bundle(("tools/pr/src/a.py", 1, 0), ("tools/pr/tests/b.py", 1, 0))
    # Act
    names = [a.name for a in build_change_map(diff, None, []).areas]
    # Assert
    assert names == ["tools/pr/src", "tools/pr/tests"]
