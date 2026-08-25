import os
import subprocess


def run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> None:
    pr_number = os.environ.get("PR_NUMBER", "")
    base_sha = os.environ.get("BASE_SHA", "")
    head_sha = os.environ.get("HEAD_SHA", "")

    print("AI Code Review Agent")
    print(f"PR: #{pr_number}")
    print(f"Base SHA: {base_sha}")
    print(f"Head SHA: {head_sha}")

    if not base_sha or not head_sha:
        raise RuntimeError("BASE_SHA and HEAD_SHA are required")

    changed_files = run(
        ["git", "diff", "--name-only", f"{base_sha}...{head_sha}"]
    )

    diff = run(
        ["git", "diff", "--unified=3", f"{base_sha}...{head_sha}"]
    )

    print("\nChanged files:")
    print(changed_files or "(none)")

    print("\nDiff:")
    print(diff or "(empty)")


if __name__ == "__main__":
    main()
