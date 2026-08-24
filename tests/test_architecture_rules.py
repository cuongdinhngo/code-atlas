"""Task 138 — architecture rules checked against the graph, not a regex.

Evidence gate (written before the change): a transitive CALLS chain domain → service → http
is invisible to a token grep over a single module's text. The graph sees the closure.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from code_atlas.store import GraphStore
from code_atlas.tools import check_architecture_rules as tool
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_RULE_MATCHED_NO_FILES,
)
from tests.test_nav_tools import db_config, edge, node, seed_file

DOMAIN = "domain/Model.aa"
SERVICE = "service/Bridge.aa"
HTTP = "http/Front.aa"
RULES = "rules.json"
FIXTURE_RULES = Path("tests/fixtures/architecture_rules") / RULES


def _transitive_repo(tmp_path: Path, *, heuristic_last: bool = False):
    """domain → service → http; the last hop may be HEURISTIC for the candidate bucket."""
    config = replace(
        db_config(tmp_path),
        architecture_rules=(RULES,),
        root=tmp_path,
    )
    (tmp_path / RULES).write_text(FIXTURE_RULES.read_text(encoding="utf-8"), encoding="utf-8")
    last_tier = "HEURISTIC" if heuristic_last else "RESOLVED"
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            DOMAIN,
            [node("Class", "Model", "\\Domain\\Model", DOMAIN)],
            [
                edge(
                    "CALLS",
                    "\\Domain\\Model",
                    "\\Service\\Bridge",
                    DOMAIN,
                    target_qname="\\Service\\Bridge",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            SERVICE,
            [node("Class", "Bridge", "\\Service\\Bridge", SERVICE)],
            [
                edge(
                    "CALLS",
                    "\\Service\\Bridge",
                    "\\Http\\Front",
                    SERVICE,
                    target_qname="\\Http\\Front",
                    tier=last_tier,
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            HTTP,
            [node("Class", "Front", "\\Http\\Front", HTTP)],
            [],
            root=tmp_path,
        )
    return config


def test_ac1_transitive_violation_is_confirmed(tmp_path: Path) -> None:
    """AC1 — fixture where the violating edge exists only transitively (R6.5)."""
    config = _transitive_repo(tmp_path)
    payload = tool.create(config)()
    assert payload["reason"] == "ok"
    assert payload["total_count"] == 1
    assert payload["candidate_count"] == 0
    hit = payload["results"][0]
    assert hit["rule_id"] == "domain-must-not-reach-http"
    assert hit["source_file"] == DOMAIN
    assert hit["forbidden_file"] == HTTP
    assert hit["confidence_tier"] == "RESOLVED"


def test_ac2_heuristic_only_path_is_candidate_not_confirmed(tmp_path: Path) -> None:
    """AC2 — HEURISTIC-only evidence never reads as confirmed."""
    config = _transitive_repo(tmp_path, heuristic_last=True)
    payload = tool.create(config)()
    assert payload["total_count"] == 0
    assert payload["candidate_count"] == 1
    assert payload["results"] == []
    assert payload["candidates"][0]["confidence_tier"] == "HEURISTIC"


def test_ac3_empty_answers_name_their_cause(tmp_path: Path) -> None:
    """AC3 — not indexed / not configured / no source files / no violation."""
    missing = replace(db_config(tmp_path), db_path=tmp_path / "missing.db")
    assert tool.create(missing)()["reason"] == REASON_NOT_INDEXED

    bare_root = tmp_path / "bare"
    bare_root.mkdir()
    bare = replace(db_config(bare_root), db_path=bare_root / "graph.db")
    with GraphStore(bare.db_path) as store:
        seed_file(
            store,
            DOMAIN,
            [node("Class", "Model", "\\Domain\\Model", DOMAIN)],
            [],
            root=bare_root,
        )
    assert tool.create(bare)()["reason"] == "capability_not_configured"

    no_match_root = tmp_path / "nomatch"
    no_match_root.mkdir()
    no_match = replace(
        db_config(no_match_root),
        architecture_rules=(RULES,),
        root=no_match_root,
        db_path=no_match_root / "graph.db",
    )
    (no_match_root / RULES).write_text(FIXTURE_RULES.read_text(encoding="utf-8"), encoding="utf-8")
    with GraphStore(no_match.db_path) as store:
        seed_file(
            store,
            "other/X.aa",
            [node("Class", "X", "\\Other\\X", "other/X.aa")],
            [],
            root=no_match_root,
        )
    assert tool.create(no_match)()["reason"] == REASON_RULE_MATCHED_NO_FILES


def test_ac4_violation_reproducible_via_find_callers(tmp_path: Path) -> None:
    """AC4 — the crossing edge is visible through an existing nav tool at the same index."""
    config = _transitive_repo(tmp_path)
    payload = tool.create(config)()
    via = payload["results"][0]["via_qname"]
    callers = find_callers.create(config)(qname="\\Http\\Front")
    assert any(row["qname"] == "\\Service\\Bridge" for row in callers["results"])
    assert via == "\\Http\\Front"


def test_ac5_identical_index_is_byte_identical(tmp_path: Path) -> None:
    """AC5 — R4.2: same graph → same digest and ordered results."""
    config = _transitive_repo(tmp_path)
    first = tool.create(config)()
    second = tool.create(config)()
    assert first == second
    assert first["digest"] == second["digest"]


def test_evidence_gate_domain_file_does_not_name_http(tmp_path: Path) -> None:
    """Evidence gate: grep over the domain module cannot see the http target."""
    config = _transitive_repo(tmp_path)
    del config
    domain_text = (tmp_path / DOMAIN).read_text(encoding="utf-8")
    assert "Front" not in domain_text
    assert "http" not in domain_text.lower()


# ------------------------------------------------------------------------------------------------
# The rule vocabulary the ticket's Scope 1 names (direction, kinds, transitive). Every case below
# exercises a branch the AC1-AC5 fixture never reaches: it is outgoing, transitive, all-kinds.


def _repo_with_rule(tmp_path: Path, rule: dict, chain: bool = False):
    """One rule, and either a direct domain -> http edge or the transitive chain."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    config = replace(
        db_config(tmp_path),
        architecture_rules=(RULES,),
        root=tmp_path,
        db_path=tmp_path / "graph.db",
    )
    (tmp_path / RULES).write_text(json.dumps({"rules": [rule]}), encoding="utf-8")
    middle = "\\Service\\Bridge" if chain else "\\Http\\Front"
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            DOMAIN,
            [node("Class", "Model", "\\Domain\\Model", DOMAIN)],
            [edge("CALLS", "\\Domain\\Model", middle, DOMAIN, target_qname=middle)],
            root=tmp_path,
        )
        if chain:
            seed_file(
                store,
                SERVICE,
                [node("Class", "Bridge", "\\Service\\Bridge", SERVICE)],
                [
                    edge(
                        "CALLS",
                        "\\Service\\Bridge",
                        "\\Http\\Front",
                        SERVICE,
                        target_qname="\\Http\\Front",
                    )
                ],
                root=tmp_path,
            )
        seed_file(
            store,
            HTTP,
            [node("Class", "Front", "\\Http\\Front", HTTP)],
            [],
            root=tmp_path,
        )
    return config


def _rule(**overrides) -> dict:
    base = {
        "id": "r",
        "sources": ["domain/**"],
        "forbidden": ["http/**"],
        "direction": "outgoing",
        "transitive": True,
    }
    base.update(overrides)
    return base


def test_incoming_direction_honours_the_declared_edge_kinds(tmp_path: Path) -> None:
    """An incoming rule declaring kinds it does not have must not report a violation.

    The only planted edge is CALLS: walking every IMPACT kind regardless of the declaration
    would confirm a violation the rule never described.
    """
    incoming = {"sources": ["http/**"], "forbidden": ["domain/**"], "direction": "incoming"}
    extends_only = _repo_with_rule(
        tmp_path / "extends", _rule(kinds=["EXTENDS"], **incoming)
    )
    assert tool.create(extends_only)()["total_count"] == 0

    calls = _repo_with_rule(tmp_path / "calls", _rule(kinds=["CALLS"], **incoming))
    payload = tool.create(calls)()
    assert payload["total_count"] == 1
    assert payload["results"][0]["source_file"] == HTTP
    assert payload["results"][0]["forbidden_file"] == DOMAIN


def test_non_transitive_rule_sees_the_direct_hop_only(tmp_path: Path) -> None:
    """transitive: false must not close over the chain — that is the whole point of the knob."""
    chained = _repo_with_rule(tmp_path / "chain", _rule(transitive=False), chain=True)
    assert tool.create(chained)()["total_count"] == 0

    direct = _repo_with_rule(tmp_path / "direct", _rule(transitive=False))
    assert tool.create(direct)()["total_count"] == 1


def test_unknown_rule_id_is_not_reported_as_a_clean_pass(tmp_path: Path) -> None:
    """A typo in rule_id asked about nothing; "ok" would read as "your rules hold"."""
    config = _repo_with_rule(tmp_path, _rule())
    payload = tool.create(config)(rule_id="no-such-rule")
    assert payload["reason"] == REASON_NO_MATCHES
    assert payload["total_count"] == 0


def test_a_rule_whose_forbidden_set_matched_nothing_never_reads_as_checked(
    tmp_path: Path,
) -> None:
    """Zero forbidden files proves as little as zero source files (ticket Scope 3)."""
    config = _repo_with_rule(tmp_path, _rule(forbidden=["nowhere/**"]))
    payload = tool.create(config)()
    assert payload["reason"] == REASON_RULE_MATCHED_NO_FILES
    report = payload["rules"][0]
    assert report["status"] == REASON_RULE_MATCHED_NO_FILES
    assert report["sources_matched"] == 1
    assert report["forbidden_matched"] == 0
