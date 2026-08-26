"""Conservative V1 file filtering and size limits."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from src.diff_parser import ChangedLine

MAX_COMMENTS = 10
MAX_CHANGED_FILES = 30
MAX_DIFF_CHARS = 60_000
MAX_CONTEXT_CHARS = 40_000

# Higher number = more severe. Used for min-severity filtering (>=).
SEVERITY_LEVEL = {
    "low": 0,
    "medium": 1,
    "high": 2,
}

# Sort order: lower number first (high → medium → low).
SEVERITY_RANK = {
    severity: -level for severity, level in SEVERITY_LEVEL.items()
}

IGNORED_FILENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    "Gemfile.lock",
    "composer.lock",
}

IGNORED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".rar",
    ".7z",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".o",
    ".a",
    ".pyc",
    ".pyo",
    ".wasm",
}

IGNORED_DIR_PARTS = {
    "dist",
    "build",
    "coverage",
    "node_modules",
    "vendor",
    ".git",
}


def ignore_reason(path: str) -> str | None:
    """Return a short reason if the path should be ignored, else None."""
    normalized = path.replace("\\", "/").lstrip("./")
    name = PurePosixPath(normalized).name
    lower_name = name.lower()
    suffix = PurePosixPath(normalized).suffix.lower()

    if name in IGNORED_FILENAMES or lower_name in IGNORED_FILENAMES:
        return "lockfile"

    if lower_name.endswith(".min.js") or lower_name.endswith(".min.css"):
        return "minified"

    if suffix in IGNORED_EXTENSIONS:
        return f"binary/asset extension ({suffix})"

    parts = PurePosixPath(normalized).parts
    for part in parts[:-1]:
        if part in IGNORED_DIR_PARTS:
            return f"ignored directory ({part})"

    return None


def filter_reviewable_files(files: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Split files into reviewable vs skipped with reasons."""
    reviewable: list[str] = []
    skipped: list[tuple[str, str]] = []

    for path in files:
        if not path:
            continue

        reason = ignore_reason(path)
        if reason is not None:
            skipped.append((path, reason))
            continue

        reviewable.append(path)

    return reviewable, skipped


def truncate_text(text: str, max_chars: int, label: str) -> str:
    if len(text) <= max_chars:
        return text

    print(
        f"Truncating {label} from {len(text)} to {max_chars} characters."
    )
    return text[:max_chars] + f"\n\n...[{label} truncated]..."


def filter_changed_lines(
    changed_lines: list[ChangedLine],
    reviewable_files: set[str],
) -> list[ChangedLine]:
    return [line for line in changed_lines if line.file in reviewable_files]


def looks_binary(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:2048]
    except OSError:
        return True

    if b"\x00" in sample:
        return True

    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return True

    return False
