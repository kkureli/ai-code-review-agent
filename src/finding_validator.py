from src.diff_parser import ChangedLine
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
) -> list[ReviewFinding]:
    changed_line_keys = {(line.file, line.line) for line in changed_lines}

    valid_findings: list[ReviewFinding] = []

    for finding in findings:
        if finding.confidence < min_confidence:
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

    return list(deduplicated.values())
