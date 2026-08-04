"""Task 037: the relation-surface A/B — guard that the metric can actually distinguish surfaces.

The trap this file exists for: the 034 harness counts only per-call args+response, so a naive
"3 tools vs 1 tool" comparison returns **0 difference by construction** and looks like evidence.
These tests pin that the schema term is real and that the verdict flips across its break-even —
a comparison that cannot come out two ways is not a measurement.
"""

from __future__ import annotations

import hashlib
import importlib.util
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from tests.test_nav_tools import db_config, edge, node

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "relation_surface_ab.py"


def _load():
    spec = importlib.util.spec_from_file_location("relation_surface_ab", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ab = _load()


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def test_schema_term_separates_the_two_surfaces(tmp_path: Path, store: GraphStore) -> None:
    """Without a schema term both surfaces cost the same and the A/B is theatre."""
    config = db_config(tmp_path)
    relations = _ab.make_find_relations(config)
    from code_atlas.tools import find_callers, find_implementations, find_references

    surface_a = sum(
        _ab.schema_tokens(name, fn)
        for name, fn in (
            ("find_callers", find_callers.create(config)),
            ("find_references", find_references.create(config)),
            ("find_implementations", find_implementations.create(config)),
        )
    )
    surface_b = _ab.schema_tokens("find_relations", relations)
    assert surface_a > 0 and surface_b > 0
    assert surface_a != surface_b  # the term the 034 harness is blind to


def test_verdict_flips_across_the_break_even() -> None:
    """A verdict that cannot come out both ways would be a constant dressed as a finding."""
    result = {"schema_delta": -240, "call_delta": 21}
    assert _ab.verdict(result, sessions=1)["winner"] == "surface_b"
    assert _ab.verdict(result, sessions=100)["winner"] == "surface_a"
    break_even = _ab.verdict(result, sessions=1)["break_even_calls"]
    assert break_even == pytest.approx(240 / 21)


def test_verdict_reports_a_tie_and_no_break_even_when_calls_cost_the_same() -> None:
    assert _ab.verdict({"schema_delta": 0, "call_delta": 0}, sessions=7)["winner"] == "tie"
    flat = _ab.verdict({"schema_delta": -5, "call_delta": 0}, sessions=7)
    assert flat["break_even_calls"] is None


def test_recipe_rewrite_targets_only_the_relation_call() -> None:
    steps = [
        {"tool": "get_index_status", "args": {"detail_level": "minimal"}},
        {"tool": "find_callers", "args": {"qname": "\\A::b", "detail_level": "minimal"}},
    ]
    rewritten = _ab._as_relation_steps(steps)
    assert rewritten[0] == steps[0]  # untouched
    assert rewritten[1]["tool"] == "find_relations"
    assert rewritten[1]["args"]["relation"] == "callers"
    assert rewritten[1]["args"]["qname"] == "\\A::b"
    assert steps[1]["args"] == {"qname": "\\A::b", "detail_level": "minimal"}  # no mutation


def test_relation_questions_picks_only_relation_recipes() -> None:
    questions = [
        {"id": "a", "atlas_path": [{"tool": "find_references", "args": {}}]},
        {"id": "b", "atlas_path": [{"tool": "search_symbol", "args": {}}]},
        {"id": "c", "atlas_path": [{"tool": "get_index_status"}, {"tool": "find_callers"}]},
    ]
    assert [q["id"] for q in _ab.relation_questions(questions)] == ["a", "c"]


def test_candidate_dispatches_each_relation_and_rejects_nonsense(
    tmp_path: Path, store: GraphStore
) -> None:
    """Surface B must return the real tools' responses — otherwise its call cost is fiction."""
    body = b"<?php\nclass User {}\n"
    (tmp_path / "u.php").write_bytes(body)
    store.upsert_file("u.php", hashlib.sha256(body).hexdigest(), "php")
    store.replace_file_rows(
        "u.php",
        [
            node("Class", "User", "\\App\\User", "u.php"),
            node("Class", "Base", "\\App\\Base", "u.php"),
        ],
        [edge("EXTENDS", "\\App\\User", "\\App\\Base", "u.php", target_qname="\\App\\Base")],
    )
    relations = _ab.make_find_relations(db_config(tmp_path))
    impls = relations("\\App\\Base", relation="implementations", detail_level="minimal")
    assert isinstance(impls["results"], list) and len(impls["results"]) == 1
    refs = relations("\\App\\Base", relation="references", detail_level="minimal")
    assert refs["reason"] == "ok"
    callers = relations("\\App\\Base", relation="callers", detail_level="minimal")
    assert callers["reason"] == "no_matches"
    with pytest.raises(ValueError, match="relation must be"):
        relations("\\App\\Base", relation="siblings")  # type: ignore[arg-type]
