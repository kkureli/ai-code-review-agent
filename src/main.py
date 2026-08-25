import json
import os
import subprocess
from pathlib import Path
from typing import Any


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

    print("\nChanged files:")
    print(changed_files or "(none)")

    print("\nDiff:")
    print(diff or "(empty)")


if __name__ == "__main__":
    main()
