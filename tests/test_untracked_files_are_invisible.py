"""Task 092: an untracked indexable file is a visible skip, not ``no_such_symbol``.

``collect()`` walks ``git ls-files``, so a newly written file is never seen. The census must name
that skip, and a single-subject lookup must return ``not_indexed`` with a real-tool ``try_instead``
until ``git add`` + rebuild. ``dirty_indexed_files`` stays 0 — a different question (073).
"""

from __future__ import annotations

from pathlib import Path

from code_atlas.build_info import server_provenance
from code_atlas.main import build_server
from code_atlas.tools.build_or_update_index import NAME as BUILD
from code_atlas.tools.find_callers import NAME as CALLERS
from code_atlas.tools.find_implementations import NAME as IMPLS
from code_atlas.tools.find_references import NAME as REFS
from code_atlas.tools.find_view_data import NAME as VIEW_DATA
from code_atlas.tools.get_index_status import NAME as STATUS
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    TRY_INSTEAD_BUILD_OR_UPDATE_INDEX,
    TRY_INSTEAD_HINT_UNTRACKED,
)
from code_atlas.tools.read_symbol import NAME as READ
from tests.test_incremental import committed, config_for, git, write
from tests.test_mcp_server import call

UNTRACKED = "src/SiteMaintenanceController.aa"
# Fake adapter qname is ``{path}::Thing`` — the same string before and after ``git add``.
SUBJECT = f"{UNTRACKED}::Thing"
NOWHERE = "src/NoSuchClassAnywhere.aa::Thing"


def _082_closes(col: dict[str, object]) -> None:
    assert col["collected"] - col["skipped"]["suffix"] - col["skipped"]["ignore"] == col["kept"]


def test_untracked_indexable_file_is_visible_not_absent(tmp_path: Path) -> None:
    """Proving test: census names the skip; lookup says ``not_indexed`` until ``git add``."""
    committed(tmp_path, {"src/a.aa": "class A {}\n"})
    write(tmp_path, UNTRACKED, "class SiteMaintenanceController {}\n")
    config = config_for(tmp_path)
    server = build_server(config)

    built = call(server, BUILD, {"full": True, "detail_level": "standard"})
    status = call(server, STATUS, {"detail_level": "verbose"})

    assert built["collection"]["skipped"]["untracked"] == 1
    assert status["collection"]["skipped"]["untracked"] == 1
    assert status["dirty_indexed_files"] == 0
    _082_closes(built["collection"])
    _082_closes(status["collection"])
    assert status["collection"]["collected"] - status["collection"]["skipped"]["suffix"] - status[
        "collection"
    ]["skipped"]["ignore"] == status["collection"]["kept"]
    assert "untracked" not in built["wrote"]

    callers = call(server, CALLERS, {"qname": SUBJECT})
    assert callers == {
        "indexed": True,
        "qname": SUBJECT,
        "results": [],
        "truncated": False,
        "reason": REASON_NOT_INDEXED,
        "total_count": 0,
        "index_root": config.index_root,
        "depth": 1,
        "frontier_skipped_non_resolved": 0,
        "try_instead": TRY_INSTEAD_BUILD_OR_UPDATE_INDEX,
        "try_instead_hint": TRY_INSTEAD_HINT_UNTRACKED,
        "untracked_path": UNTRACKED,
        **server_provenance(),
    }

    read = call(server, READ, {"qname": SUBJECT})
    assert read["reason"] == REASON_NOT_INDEXED
    assert read["try_instead"] == TRY_INSTEAD_BUILD_OR_UPDATE_INDEX
    assert read["untracked_path"] == UNTRACKED
    assert read["found"] is False
    assert read["indexed"] is True

    for name in (REFS, IMPLS, VIEW_DATA):
        payload = call(server, name, {"qname": SUBJECT})
        assert payload["reason"] == REASON_NOT_INDEXED, name
        assert payload["try_instead"] == TRY_INSTEAD_BUILD_OR_UPDATE_INDEX, name
        assert payload["untracked_path"] == UNTRACKED, name

    git(tmp_path, "add", UNTRACKED)
    git(tmp_path, "commit", "-qm", "add controller")
    rebuilt = call(server, BUILD, {"full": True, "detail_level": "standard"})
    assert rebuilt["collection"]["skipped"]["untracked"] == 0

    after = call(server, CALLERS, {"qname": SUBJECT})
    assert after["reason"] == REASON_NO_MATCHES
    assert after["indexed"] is True
    assert "try_instead" not in after
    assert "untracked_path" not in after

    missing = call(server, CALLERS, {"qname": NOWHERE})
    assert missing["reason"] == REASON_NO_SUCH_SYMBOL
    assert "try_instead" not in missing


def test_untracked_match_is_the_stem_not_the_extension(tmp_path: Path) -> None:
    """A path-shaped subject matches on its stem: ``Missing.aa`` is not an untracked ``aa.aa``."""
    committed(tmp_path, {"src/x.aa": "class X {}\n"})
    write(tmp_path, "src/aa.aa", "class Aa {}\n")
    server = build_server(config_for(tmp_path))
    call(server, BUILD, {"full": True, "detail_level": "standard"})

    missed = call(server, CALLERS, {"qname": "src/Missing.aa::Thing"})
    assert missed["reason"] == REASON_NO_SUCH_SYMBOL
    assert "untracked_path" not in missed

    hit = call(server, CALLERS, {"qname": "src/aa.aa::Aa"})
    assert hit["reason"] == REASON_NOT_INDEXED
    assert hit["untracked_path"] == "src/aa.aa"
