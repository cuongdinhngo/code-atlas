"""Task 161 — impact refuses a shared qname instead of binding one twin, and dates its answer.

9-A: a seed qname defined in two files was silently walked as one arbitrary twin at tier RESOLVED,
with no signal. The graph links callers by qname, not node identity, so it cannot attribute a caller
to a specific twin — the honest response is subject_ambiguous with the sites (read_symbol parity),
not a confident radius. 8-E: a blast radius acted on destructively now names the revision in-band.
"""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.tools import impact
from code_atlas.tools.nav_result import REASON_SUBJECT_AMBIGUOUS
from tests.test_nav_tools import db_config, edge, node, seed_file, store  # noqa: F401 — fixture


def test_a_shared_qname_seed_is_disclosed_ambiguous_not_walked(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC1/AC2 + 9-A: two definitions of one qname → subject_ambiguous + both sites, not walked."""
    seed_file(store, "a.php", [node("Method", "dup", "\\App\\Dup", "a.php")], [], root=tmp_path)
    seed_file(store, "b.php", [node("Method", "dup", "\\App\\Dup", "b.php")], [], root=tmp_path)
    result = impact.create(db_config(tmp_path))(qnames=["\\App\\Dup"])
    assert result["reason"] == REASON_SUBJECT_AMBIGUOUS
    assert result["results"] == []
    assert result["seeds_dropped"] == 1
    sites = result["ambiguous_definitions"]
    assert {s["file"] for s in sites} == {"a.php", "b.php"}


def test_a_unique_qname_seed_still_walks_its_callers(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """Regression: the ambiguity split must not stop a genuinely unique seed from walking (R4)."""
    seed_file(
        store,
        "a.php",
        [node("Method", "uniq", "\\App\\Uniq", "a.php"),
         node("Method", "caller", "\\App\\Caller", "a.php")],
        [edge("CALLS", "\\App\\Caller", "uniq", "a.php", target_qname="\\App\\Uniq")],
        root=tmp_path,
    )
    result = impact.create(db_config(tmp_path))(qnames=["\\App\\Uniq"])
    assert "ambiguous_definitions" not in result
    assert "\\App\\Caller" in {r["qname"] for r in result["results"]}


def test_default_payload_names_the_revision(tmp_path: Path, store) -> None:  # noqa: F811
    """AC3 / 8-E: the default (sign=false) impact payload carries a freshness signal."""
    seed_file(store, "a.php", [node("Method", "uniq", "\\App\\Uniq", "a.php")], [], root=tmp_path)
    result = impact.create(db_config(tmp_path))(qnames=["\\App\\Uniq"])
    assert "staleness" in result


def test_freshness_byte_cost_on_the_cheap_path_is_small_and_measured(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC3 / 061: measured delta of the freshness fields on ``minimal`` — 24 B (``staleness`` alone,
    no commit) up to ~83 B (``staleness`` + a full 40-char ``last_commit``); bounded, never scaling.
    """
    seed_file(store, "a.php", [node("Method", "uniq", "\\App\\Uniq", "a.php")], [], root=tmp_path)
    result = impact.create(db_config(tmp_path))(qnames=["\\App\\Uniq"], detail_level="minimal")
    without = {k: v for k, v in result.items() if k not in ("staleness", "last_commit")}
    delta = len(json.dumps(result)) - len(json.dumps(without))
    assert 0 < delta <= 90, f"freshness added {delta} bytes; expected the two short fields only"


def test_impact_answer_is_deterministic(tmp_path: Path, store) -> None:  # noqa: F811
    """AC5 / R4.2: same index, same subject, same answer (ambiguity ordering included)."""
    seed_file(store, "a.php", [node("Method", "dup", "\\App\\Dup", "a.php")], [], root=tmp_path)
    seed_file(store, "b.php", [node("Method", "dup", "\\App\\Dup", "b.php")], [], root=tmp_path)
    tool = impact.create(db_config(tmp_path))
    assert tool(qnames=["\\App\\Dup"]) == tool(qnames=["\\App\\Dup"])
