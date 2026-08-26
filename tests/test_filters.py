from src.filters import (
    filter_reviewable_files,
    ignore_reason,
    truncate_text,
)


def test_ignore_lockfiles_and_minified():
    assert ignore_reason("package-lock.json") == "lockfile"
    assert ignore_reason("frontend/yarn.lock") == "lockfile"
    assert ignore_reason("assets/app.min.js") == "minified"
    assert ignore_reason("styles/theme.min.css") == "minified"


def test_ignore_binary_and_build_paths():
    assert ignore_reason("logo.png") is not None
    assert ignore_reason("dist/bundle.js") is not None
    assert ignore_reason("build/output.js") is not None
    assert ignore_reason("coverage/lcov.info") is not None
    assert ignore_reason("src/app.ts") is None


def test_filter_reviewable_files_logs_skips():
    reviewable, skipped = filter_reviewable_files(
        [
            "src/app.ts",
            "package-lock.json",
            "dist/out.js",
            "src/utils.py",
        ]
    )

    assert reviewable == ["src/app.ts", "src/utils.py"]
    assert [path for path, _ in skipped] == [
        "package-lock.json",
        "dist/out.js",
    ]


def test_truncate_text():
    text = "abcdefghij"
    assert truncate_text(text, 100, "diff") == text
    truncated = truncate_text(text, 5, "diff")
    assert truncated.startswith("abcde")
    assert "truncated" in truncated
