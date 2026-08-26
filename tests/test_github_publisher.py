from src.github_publisher import (
    build_review_payload,
)
from src.reviewer import ReviewFinding


def test_builds_review_payload():
    findings = [
        ReviewFinding(
            file="src/user.py",
            line=6,
            severity="high",
            category="security",
            confidence=0.98,
            title="SQL injection",
            explanation=("User input is interpolated into SQL."),
            suggested_fix=("Use a parameterized query."),
        ),
        ReviewFinding(
            file="src/user.py",
            line=None,
            severity="medium",
            category="tests",
            confidence=0.90,
            title="Missing regression tests",
            explanation=("Security-sensitive behavior is untested."),
            suggested_fix=("Add regression coverage."),
        ),
    ]

    payload = build_review_payload(
        findings=findings,
        head_sha="abc123",
    )

    assert payload["commit_id"] == "abc123"

    assert payload["event"] == "COMMENT"

    assert len(payload["comments"]) == 1

    comment = payload["comments"][0]

    assert comment["path"] == "src/user.py"

    assert comment["line"] == 6

    assert comment["side"] == "RIGHT"

    assert "SQL injection" in comment["body"]

    assert "Missing regression tests" in payload["body"]
