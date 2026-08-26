from dataclasses import dataclass
from pathlib import Path

from src.diff_parser import ChangedLine
from src.filters import MAX_CONTEXT_CHARS, looks_binary


@dataclass
class FileContext:
    file: str
    start_line: int
    end_line: int
    content: str


def _merge_windows(
    line_numbers: list[int],
    *,
    context_lines: int,
    file_length: int,
) -> list[tuple[int, int]]:
    if not line_numbers:
        return []

    windows: list[tuple[int, int]] = []

    for line_number in sorted(set(line_numbers)):
        start = max(1, line_number - context_lines)
        end = min(file_length, line_number + context_lines)

        if not windows:
            windows.append((start, end))
            continue

        prev_start, prev_end = windows[-1]

        if start <= prev_end + 1:
            windows[-1] = (prev_start, max(prev_end, end))
        else:
            windows.append((start, end))

    return windows


def collect_file_contexts(
    workspace: str,
    changed_lines: list[ChangedLine],
    context_lines: int = 20,
    max_context_chars: int = MAX_CONTEXT_CHARS,
) -> list[FileContext]:
    changed_by_file: dict[str, list[int]] = {}

    for changed_line in changed_lines:
        changed_by_file.setdefault(
            changed_line.file,
            [],
        ).append(changed_line.line)

    contexts: list[FileContext] = []
    total_chars = 0

    for file, line_numbers in changed_by_file.items():
        file_path = Path(workspace) / file

        if not file_path.is_file():
            print(f"Skipping missing file for context: {file}")
            continue

        if looks_binary(file_path):
            print(f"Skipping binary/unreadable file for context: {file}")
            continue

        try:
            lines = file_path.read_text(
                encoding="utf-8",
                errors="strict",
            ).splitlines()
        except (OSError, UnicodeDecodeError) as error:
            print(f"Skipping unreadable file for context: {file} ({error})")
            continue

        windows = _merge_windows(
            line_numbers,
            context_lines=context_lines,
            file_length=len(lines),
        )

        for start_line, end_line in windows:
            selected_lines = lines[start_line - 1 : end_line]
            numbered_content = "\n".join(
                f"{line_number}: {content}"
                for line_number, content in enumerate(
                    selected_lines,
                    start=start_line,
                )
            )

            remaining = max_context_chars - total_chars
            if remaining <= 0:
                print(
                    "Reached MAX_CONTEXT_CHARS; "
                    "additional file context omitted."
                )
                return contexts

            if len(numbered_content) > remaining:
                numbered_content = (
                    numbered_content[:remaining]
                    + "\n...[context truncated]..."
                )
                print(
                    f"Truncating context for {file} "
                    f"lines {start_line}-{end_line}."
                )

            contexts.append(
                FileContext(
                    file=file,
                    start_line=start_line,
                    end_line=end_line,
                    content=numbered_content,
                )
            )
            total_chars += len(numbered_content)

            if total_chars >= max_context_chars:
                print(
                    "Reached MAX_CONTEXT_CHARS; "
                    "additional file context omitted."
                )
                return contexts

    return contexts
