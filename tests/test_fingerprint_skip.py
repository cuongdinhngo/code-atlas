"""Task 213: whitespace-normalised fingerprint so a cosmetic edit is not re-parsed.

The byte-hash tier (``file_is_current``) skips files whose bytes are unchanged. This tier sits
one step up: when bytes change but the whitespace-normalised fingerprint does not, the file is
not parsed and the graph stays identical (R4.2). Comment and string-literal edits are *not*
caught — that is stated in the ticket, not a miss.

The normaliser keeps every newline and all leading whitespace, so a fingerprint hit is also a
guarantee that no line moved. Collapsing them would skip a reformat while ``line_start`` /
``line_end`` / ``edges.line`` stayed at their pre-reformat values, and the index would report
current — the two guards below pin that closed.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from code_atlas.indexer import _whitespace_fingerprint, file_is_current
from code_atlas.store import BUILD_COMPLETE_KEY, BUILD_INCOMPLETE, GraphStore
from code_atlas.tools.build_or_update_index import create as build_tool
from tests.test_incremental import snapshot
from tests.test_incremental_cost_tier import _commit, _config, _seeded, _write


def test_whitespace_reformat_is_not_reparsed_and_graph_is_identical(tmp_path: Path) -> None:
    """AC1 proving test: reformat skips parse; graph matches a parse-and-write run."""
    _seeded(tmp_path, files=2)
    config = _config(tmp_path)
    with GraphStore(config.db_path) as store:
        before = snapshot(store)
        assert store.file_fingerprint("src/f0.aa") is not None

    # A trailing-whitespace and line-ending sweep: no line moves, no token changes.
    _write(tmp_path, "src/f0.aa", "class Thing0 {}   \r\n")
    _commit(tmp_path)

    payload = build_tool(config)(full=False)
    assert payload["mode"] == "incremental"
    wrote = payload["wrote"]
    assert wrote["fingerprint_skipped"] >= 1
    assert wrote["parsed"] == 0

    with GraphStore(config.db_path) as store:
        after = snapshot(store)
        assert after["nodes"] == before["nodes"]
        assert after["edges"] == before["edges"]
        # Byte hash refreshed so the next run is a byte-hash hit.
        assert file_is_current(store, tmp_path, "src/f0.aa")


def test_a_line_shift_is_never_fingerprint_skipped(tmp_path: Path) -> None:
    """A reformat that moves a declaration must parse: the graph stores line numbers (R4.2).

    Observed red against a normaliser that collapsed newlines — the file skipped, and
    ``line_start`` stayed one line above where the declaration now lives.
    """
    _seeded(tmp_path, files=2)
    config = _config(tmp_path)
    _write(tmp_path, "src/f0.aa", "\n\nclass Thing0 {}\n")
    _commit(tmp_path)

    payload = build_tool(config)(full=False)
    wrote = payload["wrote"]
    assert wrote["fingerprint_skipped"] == 0
    assert wrote["parsed"] >= 1


def test_an_indentation_change_is_never_fingerprint_skipped(tmp_path: Path) -> None:
    """Leading whitespace is syntax in some languages, and the core cannot ask which (R1.1).

    Observed red against a normaliser that collapsed leading whitespace: the fixture adapter's
    ``# symbol:`` marker is column-sensitive, so the skip left a node a parse does not produce.
    """
    _seeded(tmp_path, files=2)
    config = _config(tmp_path)
    _write(tmp_path, "src/f0.aa", "class Thing0 {}\n# symbol: Alpha\n")
    _commit(tmp_path)
    build_tool(config)(full=False)

    def marker_names() -> list[str]:
        with GraphStore(config.db_path) as store:
            return sorted(
                row[0]
                for row in store._conn.execute(
                    "SELECT name FROM nodes WHERE file_path = 'src/f0.aa'"
                )
            )

    parsed = marker_names()
    assert "Alpha" in parsed

    _write(tmp_path, "src/f0.aa", "class Thing0 {}\n    # symbol: Alpha\n")
    _commit(tmp_path)
    payload = build_tool(config)(full=False)
    assert payload["wrote"]["fingerprint_skipped"] == 0
    assert marker_names() == ["Thing"]


def test_a_declaration_change_is_never_fingerprint_skipped(tmp_path: Path) -> None:
    """AC2: fingerprint change forces a parse — observed red without the guard."""
    _seeded(tmp_path, files=2)
    _write(tmp_path, "src/f0.aa", "class RenamedThing0 {}\n")
    _commit(tmp_path)

    payload = build_tool(_config(tmp_path))(full=False)
    wrote = payload["wrote"]
    assert wrote["fingerprint_skipped"] == 0
    assert wrote["parsed"] >= 1


def test_uncomputable_fingerprint_fails_loud_into_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3: empty fingerprint never skips — exhibits fail-into-parse (R5.3)."""
    assert _whitespace_fingerprint(tmp_path / "missing.aa") == ""

    _seeded(tmp_path, files=2)
    config = _config(tmp_path)
    with GraphStore(config.db_path) as store:
        fp = store.file_fingerprint("src/f0.aa")
        assert fp is not None
        # Stale byte hash so the byte-hash tier misses; fingerprint still matches on disk.
        store.touch_file_bytes("src/f0.aa", "not-the-real-hash", fp)

    monkeypatch.setattr("code_atlas.indexer._whitespace_fingerprint", lambda _path: "")
    from code_atlas.indexer import _fingerprint_skip

    with GraphStore(config.db_path) as store:
        # Without the empty-fingerprint guard this would skip; with it, parse wins.
        assert _fingerprint_skip(store, tmp_path, "src/f0.aa") is False
        assert store.file_hash("src/f0.aa") == "not-the-real-hash"


def test_fingerprint_skip_is_visible_on_the_build_report(tmp_path: Path) -> None:
    """AC4: skipped ≠ parsed — the report names fingerprint_skipped separately."""
    _seeded(tmp_path, files=2)
    _write(tmp_path, "src/f0.aa", "class Thing0 {}   \r\n")
    _commit(tmp_path)
    payload = build_tool(_config(tmp_path))(full=False)
    wrote = payload["wrote"]
    assert "fingerprint_skipped" in wrote
    assert wrote["fingerprint_skipped"] >= 1
    assert wrote["parsed"] == 0


def test_correctness_escalation_outranks_the_fingerprint_tier(tmp_path: Path) -> None:
    """AC5: an incomplete index still escalates to full regardless of fingerprints."""
    _seeded(tmp_path, files=2)
    config = _config(tmp_path)
    with GraphStore(config.db_path) as store:
        store.set_meta(BUILD_COMPLETE_KEY, BUILD_INCOMPLETE)
    _write(tmp_path, "src/f0.aa", "class  Thing0  {}\n\n")
    _commit(tmp_path)
    payload = build_tool(config)(full=False)
    assert payload["mode"] == "full"
    assert "incomplete_index" in payload


def test_cost_tier_still_outranks_after_fingerprint_filter(tmp_path: Path) -> None:
    """AC5: 212's cost tier decides on to_parse after the fingerprint filter."""
    _seeded(tmp_path, files=3)
    for index in range(2):
        _write(tmp_path, f"src/f{index}.aa", f"class Changed{index} {{}}\n")
    _commit(tmp_path)
    payload = build_tool(_config(tmp_path, full_build_crossover=2))(full=False)
    assert payload["mode"] == "full"
    assert "delta_too_large" in payload


def test_the_normaliser_equates_only_line_preserving_edits() -> None:
    """R4.2 on the normaliser itself: what it equates, and what it must not."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "a.aa"

        def fingerprint(raw: bytes) -> str:
            path.write_bytes(raw)
            return _whitespace_fingerprint(path)

        base = fingerprint(b"a\nb\n")
        assert base != ""
        # Trailing whitespace, line endings and a missing final newline: no line moves.
        assert fingerprint(b"a  \t\r\nb\r\n") == base
        assert fingerprint(b"a\rb") == base
        # A moved line and a changed indent both reach the graph — never equated.
        assert fingerprint(b"a\n\nb\n") != base
        assert fingerprint(b"a\n    b\n") != base
