"""Task 359: a rule can require an edge — every source must reach a gate — not only forbid one.

A missing gate is an absence, so it is confirmed only over a walk whose every edge was RESOLVED;
any other edge met makes the source a candidate. Names are stand-ins (R2.4): handlers that must
reach `\\Guard\\Access::check`.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import ConfigError
from code_atlas.store import GraphStore
from code_atlas.tools import check_architecture_rules as tool
from code_atlas.tools.nav_result import REASON_RULE_MATCHED_NO_FILES
from tests.test_architecture_rules import _transitive_repo
from tests.test_nav_tools import db_config, edge, node, seed_file

RULES = "rules.json"
GATE = "\\Guard\\Access::check"
HANDLERS = "handlers/Write.aa"
HELPERS = "lib/Help.aa"
GUARD = "guard/Access.aa"


def _rule(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "writes-check-access",
        "sources": ["handlers/**"],
        "kind": "Method",
        "required": [GATE],
        "kinds": ["CALLS"],
        "depth": 2,
    }
    base.update(overrides)
    return base


def _call(source: str, target: str, path: str, *, tier: str = "RESOLVED") -> dict[str, object]:
    linked = None if tier == "unlinked" else target
    return edge(
        "CALLS",
        source,
        target,
        path,
        target_qname=linked,
        tier="HEURISTIC" if tier == "unlinked" else tier,
    )


def _repo(
    tmp_path: Path,
    handlers: dict[str, list[dict[str, object]]],
    helpers: dict[str, list[dict[str, object]]] | None = None,
    rules: list[dict[str, object]] | None = None,
):
    """Handlers (Method nodes) with their calls, optional helpers, and the gate."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    config = replace(
        db_config(tmp_path),
        architecture_rules=(RULES,),
        root=tmp_path,
        db_path=tmp_path / "graph.db",
    )
    (tmp_path / RULES).write_text(json.dumps({"rules": rules or [_rule()]}), encoding="utf-8")
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            HANDLERS,
            [node("Method", q.rsplit("::", 1)[-1], q, HANDLERS) for q in handlers],
            [call for calls in handlers.values() for call in calls],
            root=tmp_path,
        )
        if helpers:
            seed_file(
                store,
                HELPERS,
                [node("Method", q.rsplit("::", 1)[-1], q, HELPERS) for q in helpers],
                [call for calls in helpers.values() for call in calls],
                root=tmp_path,
            )
        seed_file(store, GUARD, [node("Method", "check", GATE, GUARD)], [], root=tmp_path)
    return config


def _sources(rows: list[dict[str, object]]) -> list[object]:
    return [row["source_qname"] for row in rows]


def test_one_handler_of_three_skips_the_gate(tmp_path: Path) -> None:
    """AC1: exactly one confirmed violation."""
    config = _repo(
        tmp_path,
        {
            "\\H::save": [_call("\\H::save", GATE, HANDLERS)],
            "\\H::drop": [_call("\\H::drop", GATE, HANDLERS)],
            "\\H::edit": [],
        },
    )

    payload = tool.create(config)()

    assert payload["total_count"] == 1
    assert _sources(payload["results"]) == ["\\H::edit"]
    assert payload["results"][0]["unresolved_outgoing"] == 0
    assert payload["candidate_count"] == 0


def test_a_gate_reached_only_through_an_unresolved_call_is_a_candidate(tmp_path: Path) -> None:
    """AC2: `$x->check()` with no linked target is never a confirmed absence."""
    config = _repo(
        tmp_path, {"\\H::save": [_call("\\H::save", "check", HANDLERS, tier="unlinked")]}
    )

    payload = tool.create(config)()

    assert payload["total_count"] == 0
    assert _sources(payload["candidates"]) == ["\\H::save"]
    assert payload["candidates"][0]["unresolved_outgoing"] >= 1


def test_depth_bounds_the_walk_through_a_helper(tmp_path: Path) -> None:
    """AC3: handler → helper → gate passes at depth 2 and violates at depth 1."""
    handlers = {"\\H::save": [_call("\\H::save", "\\L::guard", HANDLERS)]}
    helpers = {"\\L::guard": [_call("\\L::guard", GATE, HELPERS)]}

    deep = _repo(tmp_path / "deep", handlers, helpers, [_rule(depth=2)])
    shallow = _repo(tmp_path / "shallow", handlers, helpers, [_rule(depth=1)])

    assert tool.create(deep)()["total_count"] == 0
    assert _sources(tool.create(shallow)()["results"]) == ["\\H::save"]


def test_a_helper_with_an_unresolved_call_still_passes_when_the_gate_is_reached(
    tmp_path: Path,
) -> None:
    """AC8, first half: reaching the gate wins over an unresolved sibling call."""
    handlers = {"\\H::save": [_call("\\H::save", "\\L::guard", HANDLERS)]}
    helpers = {
        "\\L::guard": [
            _call("\\L::guard", "log", HELPERS, tier="unlinked"),
            _call("\\L::guard", GATE, HELPERS),
        ]
    }

    payload = tool.create(_repo(tmp_path, handlers, helpers))()

    assert payload["total_count"] == 0 and payload["candidate_count"] == 0


def test_an_unresolved_call_deeper_in_the_walk_keeps_the_handler_a_candidate(
    tmp_path: Path,
) -> None:
    """AC8, second half (Scope 2): the unresolved edge is the helper's, not the handler's."""
    handlers = {"\\H::save": [_call("\\H::save", "\\L::guard", HANDLERS)]}
    helpers = {"\\L::guard": [_call("\\L::guard", "check", HELPERS, tier="unlinked")]}

    payload = tool.create(_repo(tmp_path, handlers, helpers))()

    assert payload["total_count"] == 0
    assert _sources(payload["candidates"]) == ["\\H::save"]


def test_a_heuristic_edge_to_the_gate_is_not_a_pass(tmp_path: Path) -> None:
    """Only a RESOLVED edge reaches the gate; a name-matched one leaves a candidate."""
    config = _repo(tmp_path, {"\\H::save": [_call("\\H::save", GATE, HANDLERS, tier="HEURISTIC")]})

    payload = tool.create(config)()

    assert payload["total_count"] == 0
    assert _sources(payload["candidates"]) == ["\\H::save"]


def test_calibration_names_the_expectation_the_rule_missed(tmp_path: Path) -> None:
    """AC4 (and Scope 3): a qname expected to violate that passes reads calibration_failed."""
    handlers = {
        "\\H::save": [_call("\\H::save", GATE, HANDLERS)],
        "\\H::edit": [],
    }
    wrong = _rule(expect={"violating": ["\\H::save"], "passing": ["\\H::edit"]})
    right = _rule(expect={"violating": ["\\H::edit"], "passing": ["\\H::save"]})

    failed = tool.create(_repo(tmp_path / "wrong", handlers, rules=[wrong]))()
    held = tool.create(_repo(tmp_path / "right", handlers, rules=[right]))()

    report = failed["rules"][0]
    assert report["status"] == "calibration_failed"
    assert report["expected_found"] == 0
    assert report["expected_missed"] == ["\\H::edit", "\\H::save"]
    assert _sources(failed["results"]) == ["\\H::edit"]  # rows still returned
    assert held["rules"][0]["status"] == "checked"
    assert held["rules"][0]["expected_found"] == 2


def test_sources_that_match_no_symbol_say_so(tmp_path: Path) -> None:
    """AC6: zero matched sources is `rule_matched_no_files`, never a clean zero."""
    config = _repo(
        tmp_path,
        {"\\H::save": []},
        rules=[_rule(name="^nothing_named_this$")],
    )

    payload = tool.create(config)()

    assert payload["reason"] == REASON_RULE_MATCHED_NO_FILES
    assert payload["rules"][0]["sources_matched"] == 0


def test_a_required_target_the_index_lacks_checks_nothing(tmp_path: Path) -> None:
    """A misspelt gate would flag every handler; the rule says it matched no target instead."""
    config = _repo(tmp_path, {"\\H::save": []}, rules=[_rule(required=["\\No\\Such::gate"])])

    payload = tool.create(config)()

    assert payload["reason"] == REASON_RULE_MATCHED_NO_FILES
    assert payload["rules"][0]["targets_matched"] == 0


def test_name_and_kind_narrow_the_sources(tmp_path: Path) -> None:
    """Scope 1: a name regex and a node kind select which symbols the rule applies to."""
    handlers = {"\\H::saveOrder": [], "\\H::render": []}

    payload = tool.create(_repo(tmp_path, handlers, rules=[_rule(name="^save")]))()

    assert _sources(payload["results"]) == ["\\H::saveOrder"]
    assert payload["rules"][0]["sources_matched"] == 1


def test_a_forbidden_rule_answers_byte_for_byte_as_before(tmp_path: Path) -> None:
    """AC5: digests recorded on the pre-359 tree for 138's two fixtures."""
    for sub in ("resolved", "heuristic"):
        (tmp_path / sub).mkdir()
    resolved = tool.create(_transitive_repo(tmp_path / "resolved"))()
    heuristic = tool.create(_transitive_repo(tmp_path / "heuristic", heuristic_last=True))()

    assert resolved["digest"] == (
        "bcfc414d93ee1225b1fbe84da271e2188c2f378d400db714b924cd53ea20238f"
    )
    assert heuristic["digest"] == (
        "7d2c8a3b6a60cb86dd6145c6e2c55bf9fb73c08533f9b3c46ef80f88723f6329"
    )
    assert set(resolved["results"][0]) == {
        "confidence_tier",
        "forbidden_file",
        "rule_id",
        "source_file",
        "via_qname",
    }


@pytest.mark.parametrize(
    ("broken", "needle"),
    [
        ({"depth": 0}, "depth"),
        ({"depth": None}, "depth"),
        ({"required": []}, "required"),
        ({"name": "("}, "regex"),
        ({"kind": "Widget"}, "kind"),
        ({"forbidden": ["x/**"]}, "do not apply"),
        ({"expect": {"violators": []}}, "expect"),
    ],
)
def test_an_invalid_required_rule_fails_loudly_at_load(
    tmp_path: Path, broken: dict[str, object], needle: str
) -> None:
    """AC5, second half (R5.3): the whole check refuses, naming the field."""
    config = _repo(tmp_path, {"\\H::save": []}, rules=[_rule(**broken)])

    with pytest.raises(ConfigError, match=needle):
        tool.create(config)()


def test_both_rule_modes_share_one_answer(tmp_path: Path) -> None:
    """A forbidden and a required rule together: each keeps its own row shape and report."""
    forbidden = {"id": "no-guard-from-lib", "sources": ["lib/**"], "forbidden": ["guard/**"]}
    handlers = {"\\H::save": [_call("\\H::save", "\\L::guard", HANDLERS)]}
    helpers = {"\\L::guard": [_call("\\L::guard", GATE, HELPERS)]}

    payload = tool.create(_repo(tmp_path, handlers, helpers, [forbidden, _rule(depth=1)]))()

    assert payload["total_count"] == 2
    assert payload["results"][0]["forbidden_file"] == GUARD
    assert payload["results"][1]["source_qname"] == "\\H::save"
    assert [rule["rule_id"] for rule in payload["rules"]] == [
        "no-guard-from-lib",
        "writes-check-access",
    ]


def test_a_gate_inside_the_sources_is_not_its_own_violation(tmp_path: Path) -> None:
    """A source that is itself a required target is reached at hop 0, like a reachable_from seed."""
    config = _repo(tmp_path, {"\\H::save": []}, rules=[_rule(sources=["**"])])

    payload = tool.create(config)()

    assert _sources(payload["results"]) == ["\\H::save"]


def test_a_partly_missing_target_list_names_what_it_lacks(tmp_path: Path) -> None:
    """One gate present, one misspelt: the rule runs on the one, and names the other."""
    gates = [GATE, "\\Guard\\Acess::check"]
    config = _repo(
        tmp_path,
        {"\\H::save": [_call("\\H::save", GATE, HANDLERS)]},
        rules=[_rule(required=gates)],
    )

    report = tool.create(config)()["rules"][0]

    assert report["targets_matched"] == 1
    assert report["targets_missing"] == ["\\Guard\\Acess::check"]
