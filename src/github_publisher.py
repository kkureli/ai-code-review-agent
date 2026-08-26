import json
import urllib.error
import urllib.request
from typing import Any

from src.finding_validator import select_inline_findings
from src.reviewer import ReviewFinding

REVIEW_MARKER = "ai-code-review-agent"


def review_marker(head_sha: str) -> str:
    return f"<!-- {REVIEW_MARKER}:{head_sha} -->"


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
    max_comments: int = 10,
) -> dict[str, Any]:
    publishable = select_inline_findings(
        findings,
        max_comments=max_comments,
    )

    inline_comments: list[dict[str, Any]] = []

    summary_lines = [
        review_marker(head_sha),
        "",
        "## AI Code Review",
        "",
        (f"**Publishable findings:** {len(findings)}"),
    ]

    omitted = max(0, len(findings) - len(publishable))
    if omitted:
        summary_lines.append(
            f"**Inline comments capped at {max_comments}.** "
            f"{omitted} lower-priority finding(s) omitted from inline comments."
        )

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

        for finding in publishable:
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
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        method=method,
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
                return None

            return json.loads(body)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")

        if error.code in {401, 403}:
            raise RuntimeError(
                "GitHub API permission failure "
                f"({error.code}). Ensure the workflow has "
                "`pull-requests: write` and a valid github-token. "
                f"Details: {error_body[:500]}"
            ) from error

        if error.code == 422:
            raise RuntimeError(
                "GitHub rejected the review payload (422). "
                "An inline comment may target an invalid line/path. "
                f"Details: {error_body[:500]}"
            ) from error

        raise RuntimeError(
            f"GitHub API request failed ({error.code}): {error_body[:500]}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"GitHub API network error: {error.reason}"
        ) from error


def review_already_published(
    *,
    token: str,
    repository: str,
    pr_number: int,
    head_sha: str,
    api_url: str,
) -> bool:
    reviews = github_request(
        method="GET",
        url=(f"{api_url}/repos/{repository}/pulls/{pr_number}/reviews"),
        token=token,
    )

    marker = review_marker(head_sha)

    for review in reviews or []:
        body = review.get("body") or ""

        if marker in body:
            return True

    return False


def publish_review(
    *,
    token: str,
    repository: str,
    pr_number: int,
    head_sha: str,
    findings: list[ReviewFinding],
    api_url: str = "https://api.github.com",
    max_comments: int = 10,
) -> bool:
    if review_already_published(
        token=token,
        repository=repository,
        pr_number=pr_number,
        head_sha=head_sha,
        api_url=api_url,
    ):
        return False

    payload = build_review_payload(
        findings=findings,
        head_sha=head_sha,
        max_comments=max_comments,
    )

    github_request(
        method="POST",
        url=(f"{api_url}/repos/{repository}/pulls/{pr_number}/reviews"),
        token=token,
        payload=payload,
    )

    return True
