import re
from dataclasses import dataclass

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass
class ChangedLine:
    file: str
    line: int
    content: str


def parse_changed_lines(diff: str) -> list[ChangedLine]:
    changed_lines: list[ChangedLine] = []

    current_file: str | None = None
    new_line_number: int | None = None

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[len("+++ b/") :]
            continue

        hunk_match = HUNK_HEADER.match(line)

        if hunk_match:
            new_line_number = int(hunk_match.group(1))
            continue

        if current_file is None or new_line_number is None:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            changed_lines.append(
                ChangedLine(
                    file=current_file,
                    line=new_line_number,
                    content=line[1:],
                )
            )

            new_line_number += 1

        elif line.startswith("-"):
            continue

        else:
            new_line_number += 1

    return changed_lines
