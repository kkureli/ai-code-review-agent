from pathlib import Path

from src.context_collector import collect_file_contexts
from src.diff_parser import ChangedLine


def test_collect_file_contexts_merges_nearby_windows(tmp_path: Path):
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "\n".join(f"line_{i}" for i in range(1, 101)),
        encoding="utf-8",
    )

    contexts = collect_file_contexts(
        workspace=str(tmp_path),
        changed_lines=[
            ChangedLine(file="sample.py", line=10, content="line_10"),
            ChangedLine(file="sample.py", line=12, content="line_12"),
            ChangedLine(file="sample.py", line=80, content="line_80"),
        ],
        context_lines=2,
    )

    assert len(contexts) == 2
    assert contexts[0].start_line == 8
    assert contexts[0].end_line == 14
    assert contexts[1].start_line == 78
    assert contexts[1].end_line == 82


def test_collect_file_contexts_skips_binary(tmp_path: Path):
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\x00\x01\x02\x03")

    contexts = collect_file_contexts(
        workspace=str(tmp_path),
        changed_lines=[
            ChangedLine(file="blob.bin", line=1, content="x"),
        ],
    )

    assert contexts == []
