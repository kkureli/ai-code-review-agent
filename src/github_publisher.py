import json
import urllib.error
import urllib.request
from typing import Any

from src.reviewer import ReviewFinding


def format_finding(
    finding: ReviewFinding,
) -> str:
    body = (
        f"**{finding.severity.upper()} · "
        f"{finding.category}**\n\n"
        f"### {finding.title}\n\n"
        f"{finding.explanation}\n\n"
        f"**Confidence:** "
        f"{finding.confidence:.2f}"
    )

    if finding.suggested_fix:
        body += f"\n\n**Suggested fix:**\n\n{finding.suggested_fix}"

    return body


def build_review_payload(
    *,
    findings: list[ReviewFinding],
    head_sha: str,
) -> dict[str, Any]:
    inline_comments: list[dict[str, Any]] = []

    summary_lines = [
        "## AI Code Review",
        "",
        f"**Publishable findings:** {len(findings)}",
    ]

    if not findings:
        summary_lines.extend(
            [
                "",
                "✅ No meaningful issues found.",
            ]
        )

    else:
        summary_lines.extend(
            [
                "",
                "### Findings",
            ]
        )

        for finding in findings:
            if finding.line is None:
                location = f"`{finding.file}`"
            else:
                location = f"`{finding.file}:{finding.line}`"

            summary_lines.append(
                f"- **{finding.severity.upper()} · "
                f"{finding.category}** — "
                f"{finding.title} "
                f"({location})"
            )

            if finding.category != "tests" and finding.line is not None:
                inline_comments.append(
                    {
                        "path": finding.file,
                        "line": finding.line,
                        "side": "RIGHT",
                        "body": format_finding(finding),
                    }
                )

        pr_level_findings = [
            finding
            for finding in findings
            if finding.category == "tests" or finding.line is None
        ]

        if pr_level_findings:
            summary_lines.extend(
                [
                    "",
                    "### PR-level details",
                ]
            )

            for finding in pr_level_findings:
                summary_lines.extend(
                    [
                        "",
                        (
                            f"**{finding.severity.upper()} · "
                            f"{finding.category} — "
                            f"{finding.title}**"
                        ),
                        "",
                        finding.explanation,
                    ]
                )

                if finding.suggested_fix:
                    summary_lines.extend(
                        [
                            "",
                            "**Suggested fix:**",
                            "",
                            finding.suggested_fix,
                        ]
                    )

    payload: dict[str, Any] = {
        "commit_id": head_sha,
        "body": "\n".join(summary_lines),
        "event": "COMMENT",
    }

    if inline_comments:
        payload["comments"] = inline_comments

    return payload


def github_request(
    *,
    url: str,
    token: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Authorization": (f"Bearer {token}"),
            "Accept": ("application/vnd.github+json"),
            "X-GitHub-Api-Version": ("2026-03-10"),
            "Content-Type": ("application/json"),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            body = response.read().decode("utf-8")

            if not body:
                return {}

            return json.loads(body)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8")

        raise RuntimeError(
            f"GitHub API request failed ({error.code}): {error_body}"
        ) from error


def publish_review(
    *,
    token: str,
    repository: str,
    pr_number: int,
    head_sha: str,
    findings: list[ReviewFinding],
    api_url: str = "https://api.github.com",
) -> None:
    payload = build_review_payload(
        findings=findings,
        head_sha=head_sha,
    )

    github_request(
        url=(f"{api_url}/repos/{repository}/pulls/{pr_number}/reviews"),
        token=token,
        payload=payload,
    )
