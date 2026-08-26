from src.context_collector import FileContext
from src.diff_parser import ChangedLine
from src.reviewer import build_review_input


def test_build_review_input_contains_diff_and_context():
    changed_lines = [
        ChangedLine(
            file="src/user.py",
            line=2,
            content='return user["name"]',
        )
    ]

    contexts = [
        FileContext(
            file="src/user.py",
            start_line=1,
            end_line=3,
            content=(
                "1: def get_user(user):\n"
                '2:     return user["name"]\n'
                "3:"
            ),
        )
    ]

    result = build_review_input(
        diff="+return user['name']",
        changed_lines=changed_lines,
        file_contexts=contexts,
    )

    assert "src/user.py:2" in result
    assert "RAW DIFF" in result
    assert "REPOSITORY CONTEXT" in result
