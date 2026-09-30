"""Tasks 075 + 076: a malformed or under-qualified subject is not reported as absence.

One language-agnostic classifier (``nav_result.classify_missing_subject``) serves both: a
leading-anchor difference (``Ns\\Sub\\Enum`` vs the stored ``\\Ns\\Sub\\Enum``) resolves as a
single candidate; a bare member name (``isEnabled``) surfaces as many → ``name_not_qualified``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools import (
    explain_path,
    file_outline,
    find_callers,
    find_implementations,
    find_references,
    find_view_data,
    impact,
    read_symbol,
    search_symbol,
)
from code_atlas.tools.nav_result import (
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_SUCH_SYMBOL,
    REASON_OK,
    TRY_INSTEAD_SEARCH_SYMBOL,
    SubjectResolution,
    shape_exact_miss,
)
from tests.test_nav_tools import db_config, edge, node, seed_file

_TOOLS_DIR = Path(__file__).resolve().parent.parent / "code_atlas" / "tools"
_ASKED = "Ns\\Sub\\Enum"
_STORED = "\\Ns\\Sub\\Enum"

# One indexed file. `\Ns\Sub\Enum` is unique (leading-anchor case); `isEnabled` is a member name
# two classes carry (bare/under-qualified case); one caller targets the qualified `isEnabled`.
_NODES = [
    node("Class", "Enum", "\\Ns\\Sub\\Enum", "app.php"),
    node("Class", "Flags", "\\Ns\\Sub\\Flags", "app.php"),
    node("Method", "isEnabled", "\\Ns\\Sub\\Flags::isEnabled", "app.php"),
    node("Class", "Toggle", "\\Ns\\Other\\Toggle", "app.php"),
    node("Method", "isEnabled", "\\Ns\\Other\\Toggle::isEnabled", "app.php"),
    node("Function", "caller", "\\Ns\\caller", "app.php"),
]
_EDGES = [
    edge(
        "CALLS",
        "\\Ns\\caller",
        "\\Ns\\Sub\\Flags::isEnabled",
        "app.php",
        target_qname="\\Ns\\Sub\\Flags::isEnabled",
    ),
    # Unique target for find_references / find_implementations leading-anchor (122).
    edge(
        "EXTENDS",
        "\\Ns\\Sub\\Flags",
        "Enum",
        "app.php",
        target_qname="\\Ns\\Sub\\Enum",
    ),
]


@pytest.fixture
def config(tmp_path: Path) -> Iterator[Config]:
    with GraphStore(tmp_path / "graph.db") as store:
        seed_file(store, "app.php", _NODES, _EDGES, root=tmp_path)
    yield db_config(tmp_path)


# --- 075: read_symbol -------------------------------------------------------------------------

def test_read_symbol_normalises_leading_anchor(config: Config) -> None:
    """PROVING TEST — both forms return the same found answer (pre-change: found:false/ok)."""
    tool = read_symbol.create(config)
    anchored = tool("\\Ns\\Sub\\Enum")
    bare_anchor = tool("Ns\\Sub\\Enum")
    assert anchored["found"] is True
    assert bare_anchor == anchored  # byte-identical (AC75.1)


def test_read_symbol_absent_is_no_such_symbol_never_ok(config: Config) -> None:
    result = read_symbol.create(config)("\\Nope\\Missing")
    assert result["found"] is False
    assert result["reason"] == REASON_NO_SUCH_SYMBOL  # never REASON_OK (075)


def test_read_symbol_ambiguous_bare_name_is_name_not_qualified(config: Config) -> None:
    result = read_symbol.create(config)("isEnabled")
    assert result["found"] is False
    assert result["reason"] == REASON_NAME_NOT_QUALIFIED
    assert result["candidate_count"] == 2
    assert result["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL


# --- 076: bare subject on the find_* family ---------------------------------------------------

def test_bare_name_subject_is_name_not_qualified(config: Config) -> None:
    result = find_callers.create(config)("isEnabled", detail_level="minimal")
    assert result["reason"] == REASON_NAME_NOT_QUALIFIED
    assert result["results"] == []
    assert result["candidate_count"] == 2
    assert result["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL


def test_bare_name_zero_candidates_stays_no_such_symbol(config: Config) -> None:
    result = find_callers.create(config)("totallyAbsentXyz", detail_level="minimal")
    assert result["reason"] == REASON_NO_SUCH_SYMBOL
    assert "candidate_count" not in result


def test_try_instead_route_reaches_the_symbol(config: Config) -> None:
    """AC75.3 — the named route (search_symbol) actually finds the candidates."""
    missed = find_callers.create(config)("isEnabled", detail_level="minimal")
    assert missed["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
    found = search_symbol.create(config)("isEnabled", detail_level="minimal")
    assert found["total_count"] >= 2


def test_qualified_form_unchanged(config: Config) -> None:
    """AC76.3 — the fully-qualified subject answers exactly as before, no extra fields."""
    result = find_callers.create(config)(
        "\\Ns\\Sub\\Flags::isEnabled", detail_level="minimal"
    )
    assert result["reason"] == REASON_OK
    assert result["total_count"] == 1
    assert "candidate_count" not in result
    assert "try_instead" not in result


@pytest.mark.parametrize("factory", [find_references.create, find_implementations.create])
def test_refs_and_impls_bare_name_is_name_not_qualified(config: Config, factory: object) -> None:
    result = factory(config)("isEnabled", detail_level="minimal")  # type: ignore[operator]
    assert result["reason"] == REASON_NAME_NOT_QUALIFIED
    assert result["candidate_count"] == 2
    assert result["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL


def test_find_view_data_bare_name_is_name_not_qualified(config: Config) -> None:
    result = find_view_data.create(config)("isEnabled", detail_level="minimal")
    assert result["reason"] == REASON_NAME_NOT_QUALIFIED
    assert result["candidate_count"] == 2


# --- 075/076 surface sweep: no tool pairs an empty answer with reason:ok ----------------------

def test_no_tool_returns_absence_with_reason_ok(config: Config) -> None:
    """AC75.2 — a not-found / empty answer never carries reason:ok anywhere on the surface."""
    absent = "\\Nope\\Missing"
    payloads = [
        read_symbol.create(config)(absent),
        find_callers.create(config)(absent, detail_level="minimal"),
        find_references.create(config)(absent, detail_level="minimal"),
        find_implementations.create(config)(absent, detail_level="minimal"),
        find_view_data.create(config)(absent, detail_level="minimal"),
        file_outline.create(config)("no/such/file.php"),
        # An impact answer whose every subject was lost says so too (task 102).
        impact.create(config)(qnames=[absent], detail_level="minimal"),
    ]
    for payload in payloads:
        # Assert the sweep still HAS something to check before checking it (191/R6.5). Every
        # payload above was asked about an absent subject, so a non-empty one means the sweep
        # silently stopped matching — which under an `if` read as a pass.
        empty = payload.get("found") is False or payload.get("results") == []
        assert empty, f"asked about {absent} and got a non-empty answer: {payload}"
        assert payload.get("reason") != REASON_OK, payload


# --- 075/076: multi-subject tools re-point a uniquely-resolvable under-anchored subject --------

def test_impact_seeds_repoint_unique_and_drop_ambiguous(config: Config) -> None:
    with GraphStore(config.db_path) as store:
        assert impact.resolve_seeds(
            store, paths=[], qnames=["Ns\\Sub\\Enum"], max_results=50
        ).seeds == ["\\Ns\\Sub\\Enum"]
        assert (
            impact.resolve_seeds(
                store, paths=[], qnames=["isEnabled"], max_results=50
            ).seeds
            == []
        )


def test_explain_path_endpoint_repoints_unique_only(config: Config) -> None:
    with GraphStore(config.db_path) as store:
        assert explain_path._resolve_endpoint(store, "Ns\\Sub\\Enum", 50) == "\\Ns\\Sub\\Enum"
        assert explain_path._resolve_endpoint(store, "\\Ns\\Sub\\Enum", 50) == "\\Ns\\Sub\\Enum"
        assert explain_path._resolve_endpoint(store, "isEnabled", 50) == "isEnabled"


# --- 122: resolved_unique is answered, not shaped as name_not_qualified ----------------------

def _classifier_caller_modules() -> list[str]:
    """Every tools/*.py that calls the classifier — derived, never listed (R6.7 / 066)."""
    names: list[str] = []
    for path in sorted(_TOOLS_DIR.glob("*.py")):
        if path.name == "nav_result.py":
            continue
        text = path.read_text(encoding="utf-8")
        # A helper with no tool factory (freshness names a miss's file, 354) answers nothing.
        if "classify_missing_subject(" in text and "def create(" in text:
            names.append(path.stem)
    return names


def _call_classifier_caller(name: str, config: Config, qname: str) -> dict[str, object]:
    if name == "read_symbol":
        return read_symbol.create(config)(qname)
    if name == "find_references":
        return find_references.create(config)(qname, detail_level="minimal")
    if name == "find_callers":
        return find_callers.create(config)(qname, detail_level="minimal")
    if name == "find_implementations":
        return find_implementations.create(config)(qname, detail_level="minimal")
    if name == "find_view_data":
        return find_view_data.create(config)(qname, detail_level="minimal")
    if name == "impact":
        return impact.create(config)(qnames=[qname], detail_level="minimal")
    if name == "explain_path":
        return explain_path.create(config)(qname, "\\Ns\\Sub\\Flags", detail_level="minimal")
    raise AssertionError(f"add an invoke arm for new classifier caller {name}")


def _empty_with_unique_candidate(payload: dict[str, object]) -> bool:
    results = payload.get("results")
    empty = payload.get("found") is False or results == []
    return empty and payload.get("candidate_count") == 1


def test_find_references_leading_anchor_matches_stored_form(config: Config) -> None:
    """PROVING TEST — unanchored find_references matches the leading-\\ form (122 AC2/AC3)."""
    tool = find_references.create(config)
    anchored = tool(_STORED, detail_level="minimal")
    asked = tool(_ASKED, detail_level="minimal")
    assert anchored["results"]
    assert asked["results"] == anchored["results"]
    assert asked["total_count"] == anchored["total_count"]
    assert [hit["confidence_tier"] for hit in asked["results"]] == [
        hit["confidence_tier"] for hit in anchored["results"]
    ]
    assert asked["resolved_qname"] == _STORED
    assert "resolved_qname" not in anchored
    exact = tool(_STORED, detail_level="minimal")
    assert exact == anchored  # exact hit byte-identical (AC3 / R4.2)


def test_every_classifier_caller_honours_resolved_unique(config: Config) -> None:
    """AC1 — denominator is the derived caller set; each honours resolved_unique."""
    callers = _classifier_caller_modules()
    assert callers, "classifier caller scan emptied itself"
    for name in callers:
        payload = _call_classifier_caller(name, config, _ASKED)
        assert not _empty_with_unique_candidate(payload), (name, payload)
        assert payload.get("reason") != REASON_NAME_NOT_QUALIFIED, (name, payload)
        if name == "read_symbol":
            assert payload["found"] is True
        elif name == "explain_path":
            assert payload["from_qname"] == _STORED
        elif name == "impact":
            assert payload.get("seeds_dropped", 0) == 0
        else:
            assert payload.get("resolved_qname") == _STORED


def test_shape_exact_miss_resolved_unique_is_not_name_not_qualified() -> None:
    """AC4 — the shaper itself cannot file a unique resolve as under-qualified."""
    miss: dict[str, object] = {"qname": _ASKED, "results": []}
    shaped = shape_exact_miss(
        miss, SubjectResolution("resolved_unique", _STORED, 1)
    )
    assert shaped.get("reason") != REASON_NAME_NOT_QUALIFIED
    assert "candidate_count" not in shaped
    assert shaped["resolved_qname"] == _STORED


def test_no_nav_tool_returns_empty_with_candidate_count_one(config: Config) -> None:
    """AC4 — candidate_count:1 + empty results is unreachable from any classifier caller."""
    for name in _classifier_caller_modules():
        for subject in (_ASKED, _STORED, "isEnabled", "\\Nope\\Missing"):
            payload = _call_classifier_caller(name, config, subject)
            assert not _empty_with_unique_candidate(payload), (name, subject, payload)


def test_ambiguous_path_unchanged_on_find_references(config: Config) -> None:
    """AC5 — many candidates stay a refusal; would fail if this change made ambiguity forgiving."""
    result = find_references.create(config)("isEnabled", detail_level="minimal")
    assert result["reason"] == REASON_NAME_NOT_QUALIFIED
    assert result["results"] == []
    assert result["candidate_count"] == 2
    assert result["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
    assert "resolved_qname" not in result
