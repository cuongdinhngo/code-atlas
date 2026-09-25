"""022 AC3 / G2: tier 2's three new contract words are opt-in, proven rather than asserted.

The evidence gate's premise is that a general server must not spend contract vocabulary *every user
inherits*. `Table`, `Column` and `WRITES` are only genuinely opt-in if no existing consumer picks
them up, so this file sweeps every named subset in `contract` and asserts the three join none of
them — a repo with no `.sql` therefore gets identical rows from every tool. The sweep is DERIVED
from the module (R6.7): a subset added later is covered without editing a list here.
"""

from __future__ import annotations

import re
from pathlib import Path

from code_atlas import contract

TIER2_WORDS = frozenset({"Table", "Column", "WRITES"})
# The collections the new words legitimately join: the vocabulary itself, the resolver's opt-in for
# the one FQN-linked edge, and 255's evidence set — EDGE_KINDS less the containment spine, so it
# inherits EDGE_KINDS' membership and a repo with no WRITES rows still answers identically.
# Everything else must stay clear of them.
JOINED_BY_DESIGN = frozenset(
    {
        "NODE_KINDS",
        "EDGE_KINDS",
        "FQN_EDGE_KINDS",
        "UNLINKED_EVIDENCE_KINDS",
        "INBOUND_KINDS_BY_SUBJECT",
    }
)
CONVENTION = Path(contract.__file__).resolve().parents[1] / "docs" / "CONVENTION.md"


def named_subsets() -> dict[str, frozenset[str]]:
    """Every kind collection `contract` exports, minus the three joined by design."""
    out: dict[str, frozenset[str]] = {}
    for name in dir(contract):
        if name in JOINED_BY_DESIGN or not name.isupper():
            continue
        value = getattr(contract, name)
        if isinstance(value, (tuple, frozenset, set, list)) and all(
            isinstance(item, str) for item in value
        ):
            out[name] = frozenset(value)
        elif isinstance(value, dict) and all(isinstance(key, str) for key in value):
            out[name] = frozenset(value)
    return out


def test_the_sweep_has_something_to_check() -> None:
    """R6.5 guard-the-guard: an empty sweep would read as "nothing picked them up"."""
    subsets = named_subsets()
    assert len(subsets) >= 10, sorted(subsets)
    # The sweep must actually reach the subsets whose membership would change a tool's answer.
    assert {"TYPE_KINDS", "CALLABLE_KINDS", "IMPACT_KIND_WEIGHTS", "CALLER_KINDS"} <= set(subsets)


def test_the_new_kinds_join_no_existing_named_subset() -> None:
    """The spend is opt-in: no existing consumer's set grew, so no existing answer moves."""
    joined = {
        name: sorted(TIER2_WORDS & members)
        for name, members in named_subsets().items()
        if TIER2_WORDS & members
    }
    assert joined == {}, f"tier-2 vocabulary leaked into: {joined}"


def test_the_new_words_are_in_the_vocabulary_they_were_bumped_for() -> None:
    """Positive control: the sweep above would also pass if the words were never added at all."""
    assert {"Table", "Column"} <= set(contract.NODE_KINDS)
    assert "WRITES" in contract.EDGE_KINDS
    assert "WRITES" in contract.FQN_EDGE_KINDS
    assert contract.CONTRACT_VERSION == 12


def _listed(label: str) -> tuple[str, ...]:
    """The kind spelling CONVENTION §3 publishes under `label`, read out of the doc."""
    line = next(
        row for row in CONVENTION.read_text(encoding="utf-8").splitlines()
        if row.startswith(f"- **{label}:**")
    )
    body = re.search(r"`([^`]+)`", line)
    assert body is not None, line
    return tuple(body.group(1).split())


def test_convention_publishes_the_contract_vocabulary_not_a_stale_copy() -> None:
    """R6.7: the doc re-lists both tuples by hand, so a bump must be caught here, not in review."""
    assert _listed("Node kinds") == contract.NODE_KINDS
    assert _listed("Edge kinds") == contract.EDGE_KINDS
