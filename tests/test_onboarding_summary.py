"""Task 085 — the summarizer seam: deterministic default + a proof of the split.

The summarizer logic is pure, so the fixtures are plain Python — no database, no LLM (R4/R4.1). The
split proof (R3/AC2) injects a **fake** ``Summarizer`` whose output *diverges* from the structural
default, then asserts presentation reflects the seam's output — and would flip red if presentation
read the graph directly (093-C3 `prove-the-guard-fails`). Determinism (AC1, R4.2) is proven by
summarizing twice over shuffled input and byte-comparing the JSON.
"""

import inspect
from typing import Protocol

from code_atlas.onboarding import summary as summary_module
from code_atlas.onboarding.metrics import DIRECTION_LABELS, NodeMetric
from code_atlas.onboarding.summary import (
    ROLE_LABELS,
    NodeFacts,
    StructuralSummarizer,
    Summarizer,
    Summary,
    summaries_as_dict,
    summarize_modules,
)

# One fact per direction label, so every role mapping is exercised. ``doc`` carries a blank first
# line to prove the docline is the first NON-empty line, not merely line 0.
FIXTURE_FACTS = [
    NodeFacts("fn entry()", "\n  Kicks off the run.\n more", NodeMetric("z_entry", 0, 2, "source")),
    NodeFacts("fn leaf()", "A shared helper.", NodeMetric("a_leaf", 3, 0, "sink")),
    NodeFacts("fn hub()", "Sits between layers.", NodeMetric("m_hub", 2, 2, "mixed")),
    NodeFacts("fn alone()", "No edges.", NodeMetric("q_alone", 0, 0, "isolated")),
]


class _FakeSummarizer:
    """A ticket-blind stand-in for the LLM impl (090): it ignores the facts entirely and returns a
    sentinel that DISAGREES with the structural default, so the split proof can tell them apart."""

    SENTINEL_DOCLINE = "FAKE-DOCLINE"
    SENTINEL_ROLE = "fake-role"

    def summarize(self, facts: NodeFacts) -> Summary:
        return Summary(facts.metric.key, "FAKE-SIG", self.SENTINEL_DOCLINE, self.SENTINEL_ROLE)


# --------------------------------------------------------------------------- the structural default


def test_structural_default_derives_docline_and_role():
    """The default takes the signature verbatim, the first non-empty docblock line, and the role
    from 083's direction label."""
    summaries = summarize_modules(FIXTURE_FACTS, StructuralSummarizer())
    by_key = {s.key: s for s in summaries}
    assert by_key["z_entry"].docline == "Kicks off the run."  # first NON-empty line
    assert by_key["z_entry"].signature == "fn entry()"
    assert by_key["z_entry"].role == "entry-point"
    assert by_key["a_leaf"].role == "foundation"
    assert by_key["m_hub"].role == "connector"
    assert by_key["q_alone"].role == "standalone"


def test_empty_docblock_yields_empty_docline():
    facts = [NodeFacts("fn x()", "\n   \n", NodeMetric("x", 1, 0, "sink"))]
    assert summarize_modules(facts, StructuralSummarizer())[0].docline == ""


def test_default_is_deterministic_and_byte_stable():
    """Same facts in any order → byte-identical JSON (AC1, R4.2)."""
    forward = summarize_modules(FIXTURE_FACTS, StructuralSummarizer())
    reverse = summarize_modules(list(reversed(FIXTURE_FACTS)), StructuralSummarizer())
    assert summaries_as_dict(forward) == summaries_as_dict(reverse)
    assert [s.to_json() for s in forward] == [s.to_json() for s in reverse]


# --------------------------------------------- the split: graph → enrichment → presentation


def test_presentation_reflects_the_seam_not_the_graph():
    """R3/AC2 — the proving test for the seam. Enrichment routes through the INJECTED summarizer:
    presentation carries the fake's output, so if ``summarize_modules`` bypassed the seam and
    hardcoded ``StructuralSummarizer`` this assertion flips red (093-C3 — recorded sabotage run in
    the 085 working doc). The other half of AC2 — presentation cannot reach the graph — is proven
    structurally by ``test_presentation_signature_cannot_reach_the_graph``."""
    fake = _FakeSummarizer()
    rendered = summaries_as_dict(summarize_modules(FIXTURE_FACTS, fake))
    roles = {row["role"] for row in rendered["summaries"]}
    doclines = {row["docline"] for row in rendered["summaries"]}

    # Presentation carries the seam's output ...
    assert roles == {fake.SENTINEL_ROLE}
    assert doclines == {fake.SENTINEL_DOCLINE}

    # ... and the structural default WOULD have produced different values, so reading the graph
    # directly would flip the two assertions above (the guard is proven falsifiable, not vacuous).
    structural = summaries_as_dict(summarize_modules(FIXTURE_FACTS, StructuralSummarizer()))
    structural_roles = {row["role"] for row in structural["summaries"]}
    assert fake.SENTINEL_ROLE not in structural_roles
    assert structural_roles == {"entry-point", "foundation", "connector", "standalone"}


def test_presentation_signature_cannot_reach_the_graph():
    """AC2, the structural half — presentation's only input is the summaries iterable; it has no
    parameter through which a NodeFacts or NodeMetric could reach it, so it *structurally* cannot
    read the graph directly (the failure mode AC2 names)."""
    assert list(inspect.signature(summaries_as_dict).parameters) == ["summaries"]


# ------------------------------------------------------- seam shape / no dead abstraction


def test_role_map_covers_every_direction_label():
    """R6.7 derived-not-listed: the role map's keys equal 083's DIRECTION_LABELS, so a new metrics
    label cannot ship unmapped, and ROLE_LABELS is derived from that map (never a re-typed copy)."""
    assert set(summary_module._ROLE_BY_DIRECTION) == set(DIRECTION_LABELS)
    assert ROLE_LABELS == tuple(summary_module._ROLE_BY_DIRECTION[d] for d in DIRECTION_LABELS)


def _defined_here(obj: object) -> bool:
    """True when *obj* is a class DEFINED in the summary module (not an imported symbol)."""
    return isinstance(obj, type) and getattr(obj, "__module__", "") == summary_module.__name__


def test_exactly_one_protocol_and_one_default_impl():
    """R7.4 / AC3 — one seam, one default, no registry/factory (R1.2)."""
    local = {name: obj for name, obj in vars(summary_module).items() if _defined_here(obj)}
    protocols = [name for name, obj in local.items() if Protocol in getattr(obj, "__bases__", ())]
    assert protocols == ["Summarizer"]
    impls = [
        name for name, obj in local.items() if obj is not Summarizer and hasattr(obj, "summarize")
    ]
    assert impls == ["StructuralSummarizer"]
    # No registry/factory symbol crept in (YAGNI until a second summarizer exists).
    assert not [n for n in vars(summary_module) if "regist" in n.lower() or "factory" in n.lower()]
