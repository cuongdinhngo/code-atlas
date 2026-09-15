"""Task 245 — truncated substring_match answers carry the narrowing route.

Field shape (rounds 16–17): search_symbol(ClassName, kind=Method) returns a short page of
near-misses with total_count far above max_results and no try_instead. The route is the existing
FILE_OUTLINE plus HINT_NARROW_BY_QNAME, the near-miss sibling of the class-level hint; this pins
both on the single and batch paths, and keeps a complete confident answer byte-identical (061).
"""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import (
    REASON_KIND_EXCLUDED,
    REASON_OK,
    REASON_SUBSTRING_MATCH,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_NARROW_BY_QNAME,
)
from tests.test_nav_tools import (  # noqa: F401 — store is a fixture
    db_config,
    node,
    seed_file,
    store,
)

CLASS = "QuickAccessModel"
LIMIT = 5
METHOD_COUNT = 15


def _seed_class_method_flood(graph: GraphStore, root: Path) -> None:
    """Class-name Method flood: every hit is a substring near-miss; test doubles included."""
    for i in range(METHOD_COUNT):
        # Name holds the class as a mid-string so FTS hits but is_direct_match is false.
        name = f"get{CLASS}Thing{i}"
        # One method per file — replace_file_rows would collapse same-path seeds.
        path = f"tests/doubles/fake_{i}.php" if i < 4 else f"src/Model/{CLASS}_{i}.php"
        qname = f"App\\{CLASS}::{name}"
        seed_file(graph, path, [node("Method", name, qname, path)], [], root=root)


def test_substring_match_truncated_carries_file_outline_route(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC1: class name, kind=Method, test doubles, truncated near-miss → route+hint."""
    _seed_class_method_flood(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))(CLASS, kind="Method", limit=LIMIT)
    assert payload["reason"] == REASON_SUBSTRING_MATCH
    assert payload["truncated"] is True
    assert payload["total_count"] == METHOD_COUNT
    assert len(payload["results"]) == LIMIT  # type: ignore[arg-type]
    assert payload["try_instead"] == TRY_INSTEAD_FILE_OUTLINE
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_NARROW_BY_QNAME


def test_batch_path_carries_route_per_subject_not_on_envelope(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC2 / 101: queries path attaches inside the subject entry, never on the envelope."""
    _seed_class_method_flood(store, tmp_path)
    # One confident exact Function so the envelope has mixed subjects.
    seed_file(
        store,
        "src/exact.php",
        [node("Function", "alone", "alone", "src/exact.php")],
        [],
        root=tmp_path,
    )
    envelope = search_symbol.create(db_config(tmp_path))(
        queries=[CLASS, "alone"], kind="Method", limit=LIMIT
    )
    assert "try_instead" not in envelope
    assert "try_instead_hint" not in envelope
    by_q = {str(s["query"]): s for s in envelope["subjects"]}  # type: ignore[index]
    flooded = by_q[CLASS]
    assert flooded["reason"] == REASON_SUBSTRING_MATCH
    assert flooded["try_instead"] == TRY_INSTEAD_FILE_OUTLINE
    assert flooded["try_instead_hint"] == TRY_INSTEAD_HINT_NARROW_BY_QNAME
    # kind=Method drops Function — exact other-kind is kind_excluded (275), not a miss.
    alone = by_q["alone"]
    assert alone.get("total_count", 0) == 0
    assert alone["reason"] == REASON_KIND_EXCLUDED
    assert alone["kind_excluded"] == ["Function"]


def test_complete_confident_answer_is_byte_identical(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC3 / 061: a full exact page gains no try_instead keys."""
    path = f"src/{CLASS}.php"
    seed_file(
        store,
        path,
        [node("Class", CLASS, f"App\\{CLASS}", path)],
        [],
        root=tmp_path,
    )
    payload = search_symbol.create(db_config(tmp_path))(CLASS, kind="Class", limit=8)
    assert payload["reason"] == REASON_OK
    assert payload["truncated"] is False
    assert "try_instead" not in payload
    assert "try_instead_hint" not in payload
