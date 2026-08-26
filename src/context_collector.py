from dataclasses import dataclass
from pathlib import Path

from src.diff_parser import ChangedLine


@dataclass
class FileContext:
    file: str
    start_line: int
    end_line: int
    content: str


def collect_file_contexts(
    workspace: str,
    changed_lines: list[ChangedLine],
    context_lines: int = 20,
) -> list[FileContext]:
    changed_by_file: dict[str, list[int]] = {}

    for changed_line in changed_lines:
        changed_by_file.setdefault(
            changed_line.file,
            [],
        ).append(changed_line.line)

    contexts: list[FileContext] = []

    for file, line_numbers in changed_by_file.items():
        file_path = Path(workspace) / file

        if not file_path.is_file():
            continue

        try:
            lines = file_path.read_text().splitlines()
        except UnicodeDecodeError:
            # Binary / non-text file.
            continue

        first_changed_line = min(line_numbers)
        last_changed_line = max(line_numbers)

        start_line = max(
            1,
            first_changed_line - context_lines,
        )

        end_line = min(
            len(lines),
            last_changed_line + context_lines,
        )

        selected_lines = lines[
            start_line - 1 : end_line
        ]

        numbered_content = "\n".join(
            f"{line_number}: {content}"
            for line_number, content in enumerate(
                selected_lines,
                start=start_line,
            )
        )

        contexts.append(
            FileContext(
                file=file,
                start_line=start_line,
                end_line=end_line,
                content=numbered_content,
            )
        )

    return contexts
