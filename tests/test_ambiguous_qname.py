"""Task 070: a non-unique qname is flagged, its definition sites listed, and none is picked.

Proving path is integration: build a corpus with the same qname defined in several files (one
``function_exists``-guarded, load-order dependent) and callers of each, then call the nav tools —
the layer where a silent merge across definitions would go unnoticed. In-memory seeded cases cover
the per-tool payload shape and the unique-qname byte-identical guarantee (AC2).
"""

from __future__ import annotations

import shlex
import shutil
import sqlite3
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references, read_symbol, search_symbol
from code_atlas.tools.nav_result import AMBIGUOUS_DEFINITIONS
from tests.test_nav_tools import PHP, PHP_ENTRY, db_config, edge, needs_php, node, seed_file

AMBIGUOUS_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "php" / "ambiguous"
# Node kinds that count as a definition for the multiplicity measurement (ticket §Evidence).
_DEFINITION_KINDS = ("Function", "Method", "Class")


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def ambiguous_repo(tmp_path: Path, store: GraphStore) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for fixture in sorted(AMBIGUOUS_FIXTURES.glob("*.php")):
        shutil.copy(fixture, src / fixture.name)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "2",
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        },
    )
    report = full_build(config, store)
    assert report.parsed == 4 and report.failed == 0


def _first_qname(config: Config, name: str) -> str:
    """The qname the search side reports for ``name`` — so nav need not guess its spelling."""
    hits = search_symbol.create(config)(name, detail_level="minimal")["results"]
    qnames = {str(hit["qname"]) for hit in hits}
    assert len(qnames) == 1, f"expected one qname for {name}, got {qnames}"
    return qnames.pop()


# ---- integration (real build) --------------------------------------------------------------


@needs_php
def test_find_callers_flags_ambiguous_subject_with_definition_sites(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1 proving test: an ambiguous subject's callers merge, but the payload names every def."""
    ambiguous_repo(tmp_path, store)
    config = db_config(tmp_path)
    qname = _first_qname(config, "getActiveStatus")

    result = find_callers.create(config)(qname, detail_level="minimal")

    assert result["indexed"] is True
    # Callers of all definitions are still merged (the pre-070 behaviour) ...
    assert result["total_count"] >= 3
    # ... but the payload now warns the subject is ambiguous and lists the definition sites.
    sites = result[AMBIGUOUS_DEFINITIONS]
    assert len(sites) >= 2
    files = {str(site["file"]) for site in sites}
    assert any(f.endswith("alpha.php") for f in files)
    assert any(f.endswith("beta.php") for f in files)
    for site in sites:
        assert set(site) == {"file", "line", "kind"}
        assert site["kind"] == "Function"


@needs_php
def test_ambiguous_distribution_measured_on_fixture_corpus(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC4: re-run the >1-definition measurement on the built corpus — a real distribution.

    Not a single hand-built pair: two distinct qnames are redefined, at differing multiplicity.
    """
    ambiguous_repo(tmp_path, store)
    placeholders = ",".join("?" for _ in _DEFINITION_KINDS)
    with sqlite3.connect(tmp_path / "graph.db") as conn:
        rows = conn.execute(
            f"SELECT qualified_name, COUNT(*) c FROM nodes "
            f"WHERE kind IN ({placeholders}) "
            f"GROUP BY qualified_name HAVING c > 1 ORDER BY qualified_name",
            _DEFINITION_KINDS,
        ).fetchall()

    distribution = {qname: count for qname, count in rows}
    # >= 2 distinct ambiguous qnames, one with >= 2 unconditional defs, none merged away.
    assert len(distribution) >= 2
    assert max(distribution.values()) >= 2


# ---- payload shape (in-memory seeded) ------------------------------------------------------


def _seed_two_defs(store: GraphStore, tmp_path: Path) -> None:
    """``\\dup`` defined in two files, each with a caller of it."""
    seed_file(
        store,
        "a.php",
        [node("Function", "dup", "\\dup", "a.php"), node("Function", "ca", "\\ca", "a.php")],
        [edge("CALLS", "\\ca", "dup", "a.php", target_qname="\\dup")],
        root=tmp_path,
    )
    seed_file(
        store,
        "b.php",
        [node("Function", "dup", "\\dup", "b.php"), node("Function", "cb", "\\cb", "b.php")],
        [edge("CALLS", "\\cb", "dup", "b.php", target_qname="\\dup")],
        root=tmp_path,
    )


def test_find_callers_signal_lists_both_definition_files(
    tmp_path: Path, store: GraphStore
) -> None:
    _seed_two_defs(store, tmp_path)
    result = find_callers.create(db_config(tmp_path))("\\dup", detail_level="minimal")
    sites = result[AMBIGUOUS_DEFINITIONS]
    assert {str(s["file"]) for s in sites} == {"a.php", "b.php"}
    assert result["total_count"] == 2  # both callers still merged


def test_find_references_flags_ambiguous_subject(tmp_path: Path, store: GraphStore) -> None:
    _seed_two_defs(store, tmp_path)
    result = find_references.create(db_config(tmp_path))("\\dup", detail_level="minimal")
    assert {str(s["file"]) for s in result[AMBIGUOUS_DEFINITIONS]} == {"a.php", "b.php"}


def test_read_symbol_refuses_body_when_ambiguous(
    tmp_path: Path, store: GraphStore
) -> None:
    """078: ambiguous qname ships the list and no silent single-site body."""
    _seed_two_defs(store, tmp_path)
    result = read_symbol.create(db_config(tmp_path))("\\dup", detail_level="minimal")
    assert result["found"] is True
    assert result["reason"] == "ok"
    assert result["source"] == ""
    assert "file" not in result
    assert "line_start" not in result and "line_end" not in result
    assert {str(s["file"]) for s in result[AMBIGUOUS_DEFINITIONS]} == {"a.php", "b.php"}


def test_unique_qname_payload_omits_the_ambiguity_key(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2: a unique qname's payload gains nothing — the key is absent across all three tools."""
    seed_file(
        store,
        "u.php",
        [node("Function", "solo", "\\solo", "u.php"), node("Function", "cu", "\\cu", "u.php")],
        [edge("CALLS", "\\cu", "solo", "u.php", target_qname="\\solo")],
        root=tmp_path,
    )
    config = db_config(tmp_path)
    callers = find_callers.create(config)("\\solo", detail_level="minimal")
    refs = find_references.create(config)("\\solo", detail_level="minimal")
    body = read_symbol.create(config)("\\solo", detail_level="minimal")
    assert AMBIGUOUS_DEFINITIONS not in callers
    assert AMBIGUOUS_DEFINITIONS not in refs
    assert AMBIGUOUS_DEFINITIONS not in body
    assert callers["total_count"] == 1  # the one caller, unchanged
    # Unique read still ships a body site (078 — unambiguous path unchanged).
    assert body["found"] is True
    assert body["source"]
    assert body["file"] == "u.php"
    assert "line_start" in body and "line_end" in body
