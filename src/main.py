import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.config import load_action_config
from src.context_collector import collect_file_contexts
from src.diff_parser import parse_changed_lines
from src.filters import (
    MAX_CHANGED_FILES,
    MAX_DIFF_CHARS,
    filter_changed_lines,
    filter_reviewable_files,
    truncate_text,
)
from src.finding_validator import validate_findings
from src.github_publisher import publish_review, review_already_published
from src.reviewer import review_pull_request


def run(
    command: list[str],
    cwd: str,
) -> str:
    print(f"\nRunning: {' '.join(command)}")
    print(f"Working directory: {cwd}")

    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Exit code: {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        raise RuntimeError(f"Command failed: {' '.join(command)}")

    return result.stdout.strip()


def get_pull_request_info(
    event: dict[str, Any],
) -> dict[str, str | int]:
    try:
        pull_request = event["pull_request"]
        return {
            "pr_number": event["number"],
            "base_sha": pull_request["base"]["sha"],
            "head_sha": pull_request["head"]["sha"],
        }
    except (KeyError, TypeError) as error:
        raise RuntimeError(
            "Missing PR event data. This Action must run on "
            "pull_request opened/synchronize/reopened."
        ) from error


def load_github_event() -> dict[str, Any]:
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is not set")

    try:
        return json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"Failed to read GitHub event payload: {error}"
        ) from error


def main() -> None:
    config = load_action_config()

    event = load_github_event()
    pr = get_pull_request_info(event)

    workspace = os.environ.get("GITHUB_WORKSPACE")
    if not workspace:
        raise RuntimeError("GITHUB_WORKSPACE is not set")

    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        raise RuntimeError("GITHUB_REPOSITORY is not set")

    github_api_url = os.environ.get(
        "GITHUB_API_URL",
        "https://api.github.com",
    )

    run(
        [
            "git",
            "config",
            "--global",
            "--add",
            "safe.directory",
            workspace,
        ],
        cwd=workspace,
    )

    base_sha = str(pr["base_sha"])
    head_sha = str(pr["head_sha"])
    pr_number = int(pr["pr_number"])

    print("\nAI Code Review Agent")
    print(f"PR: #{pr_number}")
    print(f"Base SHA: {base_sha}")
    print(f"Head SHA: {head_sha}")
    print(f"Workspace: {workspace}")
    print(f"Model: {config.model}")
    print(f"Min confidence: {config.min_confidence}")
    print(f"Min severity: {config.min_severity}")
    print(f"Max comments: {config.max_comments}")

    if review_already_published(
        token=config.github_token,
        repository=repository,
        pr_number=pr_number,
        head_sha=head_sha,
        api_url=github_api_url,
    ):
        print("\nReview already published for this commit. Skipping.")
        return

    changed_files_raw = run(
        [
            "git",
            "diff",
            "--name-only",
            f"{base_sha}...{head_sha}",
        ],
        cwd=workspace,
    )

    all_files = [path for path in changed_files_raw.splitlines() if path]
    reviewable_files, skipped = filter_reviewable_files(all_files)

    for path, reason in skipped:
        print(f"Skipping {path}: {reason}")

    if len(reviewable_files) > MAX_CHANGED_FILES:
        print(
            f"Limiting reviewable files from {len(reviewable_files)} "
            f"to {MAX_CHANGED_FILES}."
        )
        reviewable_files = reviewable_files[:MAX_CHANGED_FILES]

    if not reviewable_files:
        print("\nNo reviewable files remain after filtering. Exiting.")
        return

    print(f"\nReviewable files ({len(reviewable_files)}):")
    for path in reviewable_files:
        print(f"  {path}")

    diff = run(
        [
            "git",
            "diff",
            "--unified=3",
            f"{base_sha}...{head_sha}",
            "--",
            *reviewable_files,
        ],
        cwd=workspace,
    )

    if not diff:
        print("\nNo pull request diff found.")
        return

    diff = truncate_text(diff, MAX_DIFF_CHARS, "diff")

    changed_lines = filter_changed_lines(
        parse_changed_lines(diff),
        set(reviewable_files),
    )

    if not changed_lines:
        print("\nNo reviewable changed lines found. Exiting.")
        return

    file_contexts = collect_file_contexts(
        workspace=workspace,
        changed_lines=changed_lines,
    )

    review = review_pull_request(
        api_key=config.openai_api_key,
        diff=diff,
        changed_lines=changed_lines,
        file_contexts=file_contexts,
        model=config.model,
    )

    validated_findings = validate_findings(
        findings=review.findings,
        changed_lines=changed_lines,
        changed_files=set(reviewable_files),
        min_confidence=config.min_confidence,
        min_severity=config.min_severity,
    )

    print("\nAI Review Summary:")
    print(review.summary)
    print(f"\nRaw AI findings: {len(review.findings)}")
    print(f"Validated findings: {len(validated_findings)}")

    print("\nValidated Findings:")
    if not validated_findings:
        print("No publishable issues found.")
    else:
        for finding in validated_findings:
            print(
                f"\n[{finding.severity.upper()}] "
                f"{finding.category} {finding.file}:{finding.line}"
            )
            print(f"Title: {finding.title}")
            print(f"Confidence: {finding.confidence:.2f}")
            print(f"Explanation: {finding.explanation}")
            if finding.suggested_fix:
                print(f"Suggested fix: {finding.suggested_fix}")

    published = publish_review(
        token=config.github_token,
        repository=repository,
        pr_number=pr_number,
        head_sha=head_sha,
        findings=validated_findings,
        api_url=github_api_url,
        max_comments=config.max_comments,
    )

    if published:
        print("\nGitHub review published.")
    else:
        print("\nReview already published for this commit. Skipping.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"\nError: {error}", file=sys.stderr)
        raise SystemExit(1) from error
