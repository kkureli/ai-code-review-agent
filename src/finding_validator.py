from src.diff_parser import ChangedLine
from src.filters import SEVERITY_LEVEL, SEVERITY_RANK
from src.reviewer import ReviewFinding

INLINE_CATEGORIES = {
    "correctness",
    "security",
    "style",
}


def validate_findings(
    *,
    findings: list[ReviewFinding],
    changed_lines: list[ChangedLine],
    changed_files: set[str],
    min_confidence: float = 0.75,
    min_severity: str = "medium",
) -> list[ReviewFinding]:
    changed_line_keys = {(line.file, line.line) for line in changed_lines}
    min_severity_level = SEVERITY_LEVEL[min_severity]

    valid_findings: list[ReviewFinding] = []

    for finding in findings:
        if finding.confidence < min_confidence:
            continue

        finding_level = SEVERITY_LEVEL.get(finding.severity)
        if finding_level is None or finding_level < min_severity_level:
            continue

        if finding.file not in changed_files:
            continue

        if finding.category in INLINE_CATEGORIES:
            if finding.line is None:
                continue

            if (
                finding.file,
                finding.line,
            ) not in changed_line_keys:
                continue

        elif finding.category == "tests":
            if (
                finding.line is not None
                and (
                    finding.file,
                    finding.line,
                )
                not in changed_line_keys
            ):
                continue

        valid_findings.append(finding)

    deduplicated: dict[
        tuple[str, int | None, str],
        ReviewFinding,
    ] = {}

    for finding in valid_findings:
        key = (
            finding.file,
            finding.line,
            finding.category,
        )

        existing = deduplicated.get(key)

        if existing is None or finding.confidence > existing.confidence:
            deduplicated[key] = finding

    return sort_findings(list(deduplicated.values()))


def sort_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    return sorted(
        findings,
        key=lambda finding: (
            SEVERITY_RANK.get(finding.severity, 99),
            -finding.confidence,
            finding.file,
            finding.line is None,
            finding.line or 0,
        ),
    )


def select_inline_findings(
    findings: list[ReviewFinding],
    *,
    max_comments: int,
) -> list[ReviewFinding]:
    """Return sorted findings with inline comments capped at max_comments.

    PR-level / test findings are always kept for the summary.
    """
    inline: list[ReviewFinding] = []
    pr_level: list[ReviewFinding] = []

    for finding in sort_findings(findings):
        if finding.category == "tests" or finding.line is None:
            pr_level.append(finding)
        else:
            if len(inline) < max_comments:
                inline.append(finding)

    return sort_findings(inline + pr_level)
