from src.diff_parser import ChangedLine
from src.finding_validator import validate_findings
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
