"""Task 020: node facts the conformance harness does not assert (it checks kinds + edges).

Lives here rather than beside the CLI helper because ``pytest``'s default ``python_files`` is
``test_*.py``: a guard in ``tests/python_adapter_cli.py`` is collected only when that path is named
on the command line, so a full-suite run never ran it (R6.5 — an absent check is not a pass).
"""

from __future__ import annotations

from tests.python_adapter_cli import ROOT, needs_python, parse_file

pytestmark = needs_python


def test_file_line_end_covers_source() -> None:
    """ast.Module has no end_lineno — File spans must still cover the source (challenger 020)."""
    path = "tests/fixtures/python/module.py"
    result = parse_file(path)
    assert result["ok"] is True
    file_node = next(n for n in result["nodes"] if n["kind"] == "File")
    expected = len((ROOT / path).read_text(encoding="utf-8").splitlines())
    assert file_node["line_end"] == expected
    assert expected > 1
