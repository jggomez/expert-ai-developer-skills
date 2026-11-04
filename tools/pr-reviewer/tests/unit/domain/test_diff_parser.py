"""Parsing unified diff text."""

from pr_reviewer.domain.diff_parser import parse_diff

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
