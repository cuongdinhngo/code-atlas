"""Task 065: empty answers distinguish unmodelled relationships from genuine zeros."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from code_atlas.tools import find_implementations, find_references, include_graph
from code_atlas.tools.nav_result import (
    NAV_REASONS,
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_MATCHES,
    REASON_OK,
    REASON_PROXIMITY_CANDIDATES,
    REASON_RELATIONSHIP_NOT_MODELLED,
    REASON_RULE_MATCHED_NO_FILES,
    REASON_SUBJECT_AMBIGUOUS,
    REASON_SUBSTRING_MATCH,
    TRY_INSTEAD_HINT_METHOD_QNAME,
    TRY_INSTEAD_HINT_PATH_BASENAME,
    TRY_INSTEAD_SEARCH_SYMBOL,
)
from tests.test_nav_tools import db_config, edge, node, seed_file


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def test_find_references_unlinked_class_refs_are_not_no_matches(
    tmp_path: Path, store: GraphStore
) -> None:
    seed_file(
        store,
        "a.php",
        [node("Class", "RegionManager", "\\Src\\System\\RegionManager", "a.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "b.php",
        [node("Class", "Caller", "\\App\\Caller", "b.php")],
        [
            edge(
                "REFERENCES",
                "\\App\\Caller",
                "\\Src\\System\\RegionManager",
                "b.php",
            ),
        ],
        root=tmp_path,
    )
    seed_file(
        store,
        "c.php",
        [
            node("Method", "getActiveStatus", "\\ModelMember::getActiveStatus", "c.php"),
            node("Function", "useIt", "\\useIt", "c.php"),
        ],
        [
            edge(
                "CALLS",
                "\\useIt",
                "\\ModelMember::getActiveStatus",
                "c.php",
                target_qname="\\ModelMember::getActiveStatus",
            ),
        ],
        root=tmp_path,
    )
    config = db_config(tmp_path)
    refs = find_references.create(config)
    empty_class = refs("\\Src\\System\\RegionManager", detail_level="minimal")
    assert empty_class["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert empty_class["total_count"] == 0
    assert empty_class["results"] == []
    # 093: the route is callable, makes progress (not a self-route), and the qualifier is prose
    # in its own field, never in the identifier slot.
    assert empty_class["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
    assert empty_class["try_instead_hint"] == TRY_INSTEAD_HINT_METHOD_QNAME

    method = refs("\\ModelMember::getActiveStatus", detail_level="minimal")
    assert method["reason"] == REASON_OK
    assert method["total_count"] == 1
    assert "try_instead" not in method
    assert "try_instead_hint" not in method


def test_find_references_genuine_zero_stays_no_matches(
    tmp_path: Path, store: GraphStore
) -> None:
    seed_file(
        store,
        "a.php",
        [node("Class", "Lonely", "\\Lonely", "a.php")],
        [],
        root=tmp_path,
    )
    result = find_references.create(db_config(tmp_path))("\\Lonely", detail_level="minimal")
    assert result["reason"] == REASON_NO_MATCHES
    assert "try_instead" not in result


def test_find_implementations_empty_stays_modelled_zero(
    tmp_path: Path, store: GraphStore
) -> None:
    """IMPL kinds are linked — unlinked REFERENCES must not flip implementations empty."""
    seed_file(
        store,
        "a.php",
        [node("Class", "Base", "\\Base", "a.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "b.php",
        [node("Class", "Other", "\\Other", "b.php")],
        [edge("REFERENCES", "\\Other", "\\Base", "b.php")],
        root=tmp_path,
    )
    result = find_implementations.create(db_config(tmp_path))("\\Base", detail_level="minimal")
    assert result["reason"] == REASON_NO_MATCHES
    assert "try_instead" not in result


def test_include_graph_imported_by_omits_always_zero_and_flags_unlinked(
    tmp_path: Path, store: GraphStore
) -> None:
    seed_file(
        store,
        "lib.php",
        [node("File", "lib.php", "lib.php", "lib.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "app.php",
        [node("File", "app.php", "app.php", "app.php")],
        [
            edge(
                "INCLUDES",
                "app.php",
                "dirname(__DIR__) . '/lib.php'",
                "app.php",
                tier="DYNAMIC",
            )
        ],
        root=tmp_path,
    )
    tool = include_graph.create(db_config(tmp_path))
    inbound = tool("lib.php", direction="imported_by")
    assert "unresolved_includes" not in inbound
    assert inbound["results"] == []
    assert inbound["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    # Hint only: no registered tool reads unlinked include text, so 093 names none (061).
    assert inbound["try_instead_hint"] == TRY_INSTEAD_HINT_PATH_BASENAME
    assert "try_instead" not in inbound

    outbound = tool("app.php", direction="imports")
    assert outbound["unresolved_includes"] == 1
    assert outbound.get("reason") != REASON_RELATIONSHIP_NOT_MODELLED

    # "both" is the default direction — an outbound-only zero must not read as complete.
    default = tool("lib.php")
    assert default["results"] == []
    assert default["unresolved_includes"] == 0
    assert default["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert default["try_instead_hint"] == TRY_INSTEAD_HINT_PATH_BASENAME
    assert "try_instead" not in default


def test_include_graph_imported_by_genuine_empty_has_no_unresolved_field(
    tmp_path: Path, store: GraphStore
) -> None:
    seed_file(
        store,
        "orphan.php",
        [node("File", "orphan.php", "orphan.php", "orphan.php")],
        [],
        root=tmp_path,
    )
    tool = include_graph.create(db_config(tmp_path))
    inbound = tool("orphan.php", direction="imported_by")
    assert "unresolved_includes" not in inbound
    assert inbound["results"] == []
    assert inbound.get("reason") != REASON_RELATIONSHIP_NOT_MODELLED
    assert "try_instead" not in inbound
    # A hint can now stand alone (093), so a genuine empty must carry neither field.
    assert "try_instead_hint" not in inbound

    default = tool("orphan.php")
    assert default.get("reason") != REASON_RELATIONSHIP_NOT_MODELLED
    assert "try_instead" not in default
    assert "try_instead_hint" not in default


def test_reason_vocabulary_pins_relationship_not_modelled() -> None:
    assert REASON_RELATIONSHIP_NOT_MODELLED in NAV_REASONS
    assert REASON_CAPABILITY_NOT_CONFIGURED in NAV_REASONS
    assert REASON_NAME_NOT_QUALIFIED in NAV_REASONS
    # Newest-last: 078 appended subject_ambiguous, 138 rule_matched_no_files (tool vocab —
    # not CONTRACT_VERSION). The pin is that a new reason JOINS this tuple rather than forking it.
    assert REASON_SUBJECT_AMBIGUOUS in NAV_REASONS
    assert REASON_RULE_MATCHED_NO_FILES in NAV_REASONS
    # 167 appended substring_match; 186 appended relation_unmodelled_for_language after it.
    assert REASON_SUBSTRING_MATCH in NAV_REASONS
    assert NAV_REASONS[-1] == REASON_PROXIMITY_CANDIDATES
