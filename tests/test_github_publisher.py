from src.github_publisher import (
    build_review_payload,
    review_marker,
)
from src.reviewer import ReviewFinding


def test_review_marker_format():
    assert review_marker("abc123") == "<!-- ai-code-review-agent:abc123 -->"


def test_builds_review_payload_with_marker_and_inline():
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
    assert review_marker("abc123") in payload["body"]
    assert len(payload["comments"]) == 1

    comment = payload["comments"][0]
    assert comment["path"] == "src/user.py"
    assert comment["line"] == 6
    assert comment["side"] == "RIGHT"
    assert "SQL injection" in comment["body"]
    assert "Missing regression tests" in payload["body"]


def test_empty_findings_payload_still_has_marker():
    payload = build_review_payload(findings=[], head_sha="def456")

    assert review_marker("def456") in payload["body"]
    assert "No meaningful issues found" in payload["body"]
    assert "comments" not in payload


def test_max_comments_limits_inline_only():
    findings = [
        ReviewFinding(
            file="src/a.py",
            line=i,
            severity="medium",
            category="correctness",
            confidence=0.90 - (i * 0.01),
            title=f"Issue {i}",
            explanation="Concrete problem.",
            suggested_fix=None,
        )
        for i in range(1, 6)
    ]
    findings.append(
        ReviewFinding(
            file="src/a.py",
            line=None,
            severity="medium",
            category="tests",
            confidence=0.95,
            title="Missing tests",
            explanation="Behavior changed.",
            suggested_fix=None,
        )
    )

    payload = build_review_payload(
        findings=findings,
        head_sha="abc123",
        max_comments=2,
    )

    assert len(payload["comments"]) == 2
    assert "Missing tests" in payload["body"]
    assert "Issue 1" in payload["body"]
    assert "capped" in payload["body"].lower()


def test_duplicate_detection_uses_marker_in_body():
    marker = review_marker("abc123")
    reviews = [
        {"body": "unrelated"},
        {"body": f"hello\n{marker}\nworld"},
    ]

    assert any(marker in (review.get("body") or "") for review in reviews)
    assert not any(
        review_marker("zzz") in (review.get("body") or "")
        for review in reviews
    )
