"""Filtering and the size budget."""

from pr_reviewer.domain.file_selection import build_bundle

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
