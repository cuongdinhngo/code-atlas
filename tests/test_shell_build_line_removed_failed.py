"""Task 289 — shell build line names ``removed`` / ``failed`` when non-zero."""

from __future__ import annotations

import io
from contextlib import redirect_stderr

from code_atlas import cli


def _line(result: dict[str, object]) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stderr(buf):
        code = cli.exit_code(result)
    return code, buf.getvalue().rstrip("\n")


def test_removed_none_and_failed_none_keeps_today_line() -> None:
    """AC1 + AC4: zero removed/failed leaves the completion line unchanged (061)."""
    code, line = _line(
        {
            "mode": "incremental",
            "wrote": {"files": 3, "nodes": 10, "edges": 20, "removed": 0, "failed": 0},
        }
    )
    assert code == cli.OK
    assert line == "code-atlas build: incremental: 3 file(s), 10 node(s), 20 edge(s)"


def test_removed_files_print_removed_count() -> None:
    """AC1: an incremental run that removed files prints that count under the payload name."""
    code, line = _line(
        {
            "mode": "incremental",
            "wrote": {"files": 2, "nodes": 4, "edges": 5, "removed": 1212, "failed": 0},
        }
    )
    assert code == cli.OK
    assert line.endswith(", 1212 removed")
    assert "failed" not in line


def test_parse_failures_print_failed_count() -> None:
    """AC2: a run with parse failures prints ``failed`` under the payload name."""
    code, line = _line(
        {
            "mode": "full",
            "wrote": {"files": 5, "nodes": 1, "edges": 0, "removed": 0, "failed": 2},
        }
    )
    assert code == cli.OK
    assert line.endswith(", 2 failed")
    assert "removed" not in line


def test_both_counts_use_wrote_field_names() -> None:
    """AC3: shell field names match the ``wrote`` payload (``removed``, ``failed``)."""
    _, line = _line(
        {
            "mode": "incremental",
            "wrote": {"files": 1, "nodes": 1, "edges": 1, "removed": 3, "failed": 4},
        }
    )
    assert ", 3 removed, 4 failed" in line
    assert "files_removed" not in line


def test_exit_codes_unchanged_for_busy_and_nothing() -> None:
    """AC4: exit-code behaviour is unchanged for the non-completion paths."""
    code, line = _line({"mode": "busy"})
    assert code == cli.BUSY_PEER
    assert "another build is running" in line

    code, line = _line({"mode": "incremental", "wrote": {"files": 0, "nodes": 0, "edges": 0}})
    assert code == cli.NOTHING_TO_DO
    assert line == "code-atlas build: incremental: 0 file(s), 0 node(s), 0 edge(s)"
