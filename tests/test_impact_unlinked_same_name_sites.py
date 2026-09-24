"""Task 330 — impact discloses unlinked same-name sites on Method seeds."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from code_atlas.tools import impact as impact_tool
from code_atlas.tools.nav_result import (
    CAVEAT_UNLINKED_SAME_NAME_SITES,
    TRY_INSTEAD_FIND_CALLERS,
    TRY_INSTEAD_HINT_UNLINKED_CALLS,
)
from tests.test_nav_tools import db_config, edge, node, seed_file

METHOD = "\\Base::display"
CALLER = "\\Controller::chart"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def test_impact_discloses_unlinked_method_call(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1: only caller is unlinked `$f->make()->display()` → disclose, not authoritative."""
    seed_file(
        store,
        "Base.php",
        [node("Method", "display", METHOD, "Base.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "Controller.php",
        [node("Method", "chart", CALLER, "Controller.php")],
        # Unlinked CALLS: target_raw names the method, target_qname empty.
        [
            edge(
                "CALLS",
                CALLER,
                "display",
                "Controller.php",
                target_qname="",
                tier="DYNAMIC",
            )
        ],
        root=tmp_path,
    )
    payload = impact_tool.create(db_config(tmp_path))(qnames=[METHOD])
    assert payload["unlinked_same_name_sites"] == 1
    assert payload["authoritative"] is False
    assert CAVEAT_UNLINKED_SAME_NAME_SITES in payload["authoritative_caveats"]
    assert payload["try_instead"] == TRY_INSTEAD_FIND_CALLERS
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_UNLINKED_CALLS


def test_signed_claim_carries_unlinked_count(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2: sign=true does not emit a claim that reads as a closed zero."""
    seed_file(
        store,
        "Base.php",
        [node("Method", "display", METHOD, "Base.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "Controller.php",
        [node("Method", "chart", CALLER, "Controller.php")],
        [
            edge(
                "CALLS",
                CALLER,
                "display",
                "Controller.php",
                target_qname="",
                tier="DYNAMIC",
            )
        ],
        root=tmp_path,
    )
    payload = impact_tool.create(db_config(tmp_path))(qnames=[METHOD], sign=True)
    claim = str(payload["claim"])
    assert "unlinked_same_name_sites=1" in claim
    assert payload["authoritative"] is False


def test_resolved_only_method_is_byte_identical(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC3: Method with only resolved dependents gains no unlinked field (061)."""
    seed_file(
        store,
        "Base.php",
        [node("Method", "display", METHOD, "Base.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "Controller.php",
        [node("Method", "chart", CALLER, "Controller.php")],
        [
            edge(
                "CALLS",
                CALLER,
                "display",
                "Controller.php",
                target_qname=METHOD,
                tier="RESOLVED",
            )
        ],
        root=tmp_path,
    )
    payload = impact_tool.create(db_config(tmp_path))(qnames=[METHOD])
    assert "unlinked_same_name_sites" not in payload
    assert "authoritative" not in payload
    assert "try_instead" not in payload
    # Linked caller expands the radius beyond the seed.
    assert len(payload["results"]) >= 1  # type: ignore[arg-type]
