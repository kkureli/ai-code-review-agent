from src.finding_validator import (
    select_inline_findings,
    sort_findings,
    validate_findings,
)
from src.diff_parser import ChangedLine
from src.reviewer import ReviewFinding


def finding(
    *,
    file="src/user.py",
    line=10,
    severity="medium",
    category="correctness",
    confidence=0.90,
    title="Bug",
):
    return ReviewFinding(
        file=file,
        line=line,
        severity=severity,
        category=category,
        confidence=confidence,
        title=title,
        explanation="Concrete problem.",
        suggested_fix=None,
    )


def test_drops_unpublishable_findings():
    changed_lines = [
        ChangedLine(
            file="src/user.py",
            line=10,
            content="return user",
        )
    ]

    findings = [
        finding(line=10),
        finding(line=99, title="Wrong line"),
        finding(
            file="src/other.py",
            line=10,
            title="Wrong file",
        ),
        finding(
            line=10,
            confidence=0.60,
            title="Low confidence",
        ),
    ]

    result = validate_findings(
        findings=findings,
        changed_lines=changed_lines,
        changed_files={"src/user.py"},
    )

    assert result == [findings[0]]


def test_keeps_pr_level_test_finding_and_deduplicates():
    changed_lines = [
        ChangedLine(
            file="src/user.py",
            line=10,
            content="return user",
        )
    ]

    lower_confidence = finding(
        line=10,
        confidence=0.80,
        title="First version",
    )

    higher_confidence = finding(
        line=10,
        confidence=0.95,
        title="Better version",
    )

    test_finding = finding(
        line=None,
        category="tests",
        title="Missing regression test",
    )

    result = validate_findings(
        findings=[
            lower_confidence,
            higher_confidence,
            test_finding,
        ],
        changed_lines=changed_lines,
        changed_files={"src/user.py"},
    )

    assert result == [
        higher_confidence,
        test_finding,
    ]


def test_sort_findings_prefers_severity_then_confidence():
    findings = [
        finding(severity="low", confidence=0.99, title="Low"),
        finding(severity="high", confidence=0.80, title="High low conf"),
        finding(severity="high", confidence=0.95, title="High high conf"),
        finding(severity="medium", confidence=0.90, title="Medium"),
    ]

    sorted_findings = sort_findings(findings)

    assert [item.title for item in sorted_findings] == [
        "High high conf",
        "High low conf",
        "Medium",
        "Low",
    ]


def test_select_inline_findings_caps_comments_keeps_pr_level():
    findings = [
        finding(line=1, severity="low", confidence=0.80, title="L1"),
        finding(line=2, severity="high", confidence=0.99, title="H2"),
        finding(line=3, severity="medium", confidence=0.90, title="M3"),
        finding(
            line=None,
            category="tests",
            severity="medium",
            confidence=0.95,
            title="Tests",
        ),
    ]

    selected = select_inline_findings(findings, max_comments=2)

    titles = [item.title for item in selected]
    assert "H2" in titles
    assert "M3" in titles
    assert "Tests" in titles
    assert "L1" not in titles


def test_min_severity_medium_suppresses_low():
    changed_lines = [
        ChangedLine(file="src/user.py", line=10, content="x"),
        ChangedLine(file="src/user.py", line=11, content="y"),
        ChangedLine(file="src/user.py", line=12, content="z"),
    ]

    high = finding(line=10, severity="high", title="High")
    medium = finding(line=11, severity="medium", title="Medium")
    low = finding(line=12, severity="low", title="Low")

    result = validate_findings(
        findings=[high, medium, low],
        changed_lines=changed_lines,
        changed_files={"src/user.py"},
        min_severity="medium",
    )

    assert [item.title for item in result] == ["High", "Medium"]


def test_min_severity_low_keeps_all_severities():
    changed_lines = [
        ChangedLine(file="src/user.py", line=10, content="x"),
        ChangedLine(file="src/user.py", line=11, content="y"),
        ChangedLine(file="src/user.py", line=12, content="z"),
    ]

    high = finding(line=10, severity="high", title="High")
    medium = finding(line=11, severity="medium", title="Medium")
    low = finding(line=12, severity="low", title="Low")

    result = validate_findings(
        findings=[high, medium, low],
        changed_lines=changed_lines,
        changed_files={"src/user.py"},
        min_severity="low",
    )

    assert [item.title for item in result] == ["High", "Medium", "Low"]
