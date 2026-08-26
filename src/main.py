import json
import os
import subprocess
from pathlib import Path
from typing import Any

from reviewer import review_pull_request
from src.context_collector import collect_file_contexts
from src.diff_parser import parse_changed_lines


def run(command: list[str], cwd: str) -> str:
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
        "base_sha": pull_request["base"]["sha"],
        "head_sha": pull_request["head"]["sha"],
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
    # The repository is mounted into the Docker container
    # with a different owner than the container process.
    # Git blocks it unless we explicitly trust this workspace.
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

    print("\nAI Review Summary:")
    print(review.summary)

    print("\nFindings:")

    if not review.findings:
        print("No meaningful issues found.")
    else:
        for finding in review.findings:
            print(
                f"\n[{finding.severity.upper()}] "
                f"{finding.category} "
                f"{finding.file}:{finding.line}"
            )
            print(f"Title: {finding.title}")
            print(f"Confidence: {finding.confidence:.2f}")
            print(f"Explanation: {finding.explanation}")

            if finding.suggested_fix:
                print(f"Suggested fix: {finding.suggested_fix}")

    print("\nChanged files:")
    print(changed_files or "(none)")

    print("\nChanged lines:")

    if not changed_lines:
        print("(none)")
    else:
        for changed_line in changed_lines:
            print(f"{changed_line.file}:{changed_line.line} {changed_line.content}")

    print("\nRaw diff:")
    print(diff or "(empty)")
    print("\nChanged files:")
    print(changed_files or "(none)")

    print("\nDiff:")
    print(diff or "(empty)")

    print("\nRepository context:")

    if not file_contexts:
        print("(none)")
    else:
        for context in file_contexts:
            print(
                f"\n--- {context.file} "
                f"lines {context.start_line}-{context.end_line} ---"
            )
            print(context.content)


if __name__ == "__main__":
    main()
