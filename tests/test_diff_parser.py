from src.diff_parser import ChangedLine, parse_changed_lines


def test_parse_added_lines_with_new_file_line_numbers():
    diff = """diff --git a/src/user.py b/src/user.py
--- a/src/user.py
+++ b/src/user.py
@@ -10,3 +10,3 @@
 context
-old_value = 1
+new_value = 2
 next
"""

    assert parse_changed_lines(diff) == [
        ChangedLine(
            file="src/user.py",
            line=11,
            content="new_value = 2",
        )
    ]
