import json
import os
import subprocess
from pathlib import Path
from typing import Any

from src.context_collector import (
    collect_file_contexts,
)
from src.diff_parser import (
    parse_changed_lines,
)
from src.finding_validator import (
    validate_findings,
)
from src.github_publisher import (
    publish_review,
)
from src.reviewer import (
    review_pull_request,
)


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
    pull_request = event["pull_request"]

    return {
        "pr_number": event["number"],
        "base_sha": (pull_request["base"]["sha"]),
        "head_sha": (pull_request["head"]["sha"]),
    }


def load_github_event() -> dict[str, Any]:
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is not set")

    return json.loads(Path(event_path).read_text())


def main() -> None:
    event = load_github_event()
    pr = get_pull_request_info(event)

    workspace = os.environ.get("GITHUB_WORKSPACE")

    if not workspace:
        raise RuntimeError("GITHUB_WORKSPACE is not set")

    api_key = os.environ.get("INPUT_OPENAI-API-KEY")

    if not api_key:
        raise RuntimeError("openai-api-key input is required")

    github_token = os.environ.get("INPUT_GITHUB-TOKEN")

    if not github_token:
        raise RuntimeError("github-token input is required")

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

    print("\nAI Code Review Agent")
    print(f"PR: #{pr['pr_number']}")
    print(f"Base SHA: {base_sha}")
    print(f"Head SHA: {head_sha}")
    print(f"Workspace: {workspace}")

    changed_files = run(
        [
            "git",
            "diff",
            "--name-only",
            f"{base_sha}...{head_sha}",
        ],
        cwd=workspace,
    )

    diff = run(
        [
            "git",
            "diff",
            "--unified=3",
            f"{base_sha}...{head_sha}",
        ],
        cwd=workspace,
    )

    if not diff:
        print("\nNo pull request diff found.")
        return

    changed_lines = parse_changed_lines(diff)

    file_contexts = collect_file_contexts(
        workspace=workspace,
        changed_lines=changed_lines,
    )

    review = review_pull_request(
        api_key=api_key,
        diff=diff,
        changed_lines=changed_lines,
        file_contexts=file_contexts,
    )

    changed_file_set = {file for file in changed_files.splitlines() if file}

    validated_findings = validate_findings(
        findings=review.findings,
        changed_lines=changed_lines,
        changed_files=changed_file_set,
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
                f"\n["
                f"{finding.severity.upper()}"
                f"] "
                f"{finding.category} "
                f"{finding.file}:"
                f"{finding.line}"
            )

            print(f"Title: {finding.title}")

            print(f"Confidence: {finding.confidence:.2f}")

            print(f"Explanation: {finding.explanation}")

            if finding.suggested_fix:
                print(f"Suggested fix: {finding.suggested_fix}")

        published = publish_review(
            token=github_token,
            repository=repository,
            pr_number=int(pr["pr_number"]),
            head_sha=head_sha,
            findings=validated_findings,
            api_url=github_api_url,
        )

    if published:
        print("\nGitHub review published.")
    else:
        print("\nReview already published for this commit. Skipping.")

    print("\nChanged files:")
    print(changed_files or "(none)")

    print("\nChanged lines:")

    if not changed_lines:
        print("(none)")
    else:
        for changed_line in changed_lines:
            print(f"{changed_line.file}:{changed_line.line} {changed_line.content}")


if __name__ == "__main__":
    main()
