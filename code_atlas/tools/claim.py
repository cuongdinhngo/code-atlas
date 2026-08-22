"""Claim signing — render one answer as a quotable, re-runnable line (task 100).

An attestation that never reaches the artifact where the claim is made has, for practical purposes,
not been produced. This module is a **pure formatter**: it receives a payload the tool already
computed and a staleness dict the tool already read, and returns the payload with one added key.
It never opens a store, never spawns git, and never branches on language (R1.1 / R1.4 / R4.1).

Key order is fixed so the same inputs render the same bytes (R4.2). Every caveat owns its own key
rather than living inside prose, so a degrading answer cannot quietly drop it (task 100 W1).

Grammar: ``<schema> key=value …``, space-separated. A value is double-quoted when it is empty or
holds a space, comma, ``=`` or ``"``; an inner ``"`` is **doubled**. There is no escape character,
so a backslash is always literal — a qualified name that uses one survives the round trip.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from code_atlas.build_info import server_identity
from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.tools.nav_result import REASON_OK
from code_atlas.tools.staleness import BEHIND

CLAIM_SCHEMA = "code-atlas/1"
CLAIM_KEY = "claim"

# Name at most this many subject items before collapsing the rest to "+N" (061).
SUBJECT_ITEMS = 3
REV_CHARS = 7

# A value needs quoting when it would otherwise break the key=value split.
_QUOTE_TRIGGERS = ' ,="'


def subject(parts: Sequence[str]) -> str:
    """Name the subject in at most ``SUBJECT_ITEMS`` items, then ``+N`` for the remainder."""
    kept = [part for part in parts[:SUBJECT_ITEMS] if part]
    rest = len([part for part in parts if part]) - len(kept)
    if rest > 0:
        kept.append(f"+{rest}")
    return ",".join(kept)


def weakest_tier(results: Sequence[Mapping[str, object]]) -> str | None:
    """The weakest tier present, or None when there are no hits to tier.

    Never claim the stronger tier (R5.2): one HEURISTIC hit makes the whole answer HEURISTIC.
    """
    present = {
        str(hit["confidence_tier"]) for hit in results if hit.get("confidence_tier") is not None
    }
    for tier in reversed(CONFIDENCE_TIERS):
        if tier in present:
            return tier
    return None


def revision_fields(staleness: Mapping[str, object]) -> list[tuple[str, object]]:
    """``rev`` / ``ref`` / ``index`` — what tree this answer describes (071 / 077).

    ``rev`` and ``ref`` name the revision the INDEX holds, not git HEAD: that is the tree the
    answer actually describes. ``index`` then discloses whether HEAD has moved past it.
    """
    fields: list[tuple[str, object]] = []
    commit = staleness.get("last_commit")
    if commit:
        fields.append(("rev", str(commit)[:REV_CHARS]))
    ref = staleness.get("last_ref")
    if ref:
        fields.append(("ref", ref))
    state = staleness.get("staleness")
    if state:
        fields.append(("index", state))
    dirty = staleness.get("dirty_indexed_files")
    if state == BEHIND and dirty:
        fields.append(("dirty_indexed", dirty))
    return fields


def server_fields() -> list[tuple[str, object]]:
    """Which server build produced this answer — orthogonal to index revision (125)."""
    ident = server_identity()
    return [("server", ident["version"]), ("build", ident["build"])]


def render(fields: Sequence[tuple[str, object]]) -> str:
    """Join ``key=value`` pairs in the order given — never dict order (R4.2)."""
    return " ".join(f"{key}={_value(value)}" for key, value in fields)


def _value(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    text = str(value)
    if not text or any(char in text for char in _QUOTE_TRIGGERS):
        # An inner quote is DOUBLED, never backslash-escaped: the grammar has no escape
        # character, so a separator backslash stays literal and the value round-trips.
        return '"' + text.replace('"', '""') + '"'
    return text


def _answer(payload: Mapping[str, object]) -> object:
    """How many — the counted set the claim is about."""
    total = payload.get("total_count")
    if isinstance(total, int):
        return total
    results = payload.get("results")
    return len(results) if isinstance(results, list) else 0


def sign(
    payload: dict[str, object],
    *,
    tool: str,
    question: str,
    subject_parts: Sequence[str],
    staleness: Mapping[str, object],
    answer: object | None = None,
    carry: Sequence[str] = (),
    extra: Sequence[tuple[str, object]] = (),
) -> dict[str, object]:
    """Attach the one-line claim under ``CLAIM_KEY``; return the same payload.

    ``carry`` names payload keys that ride the line verbatim — the same spelling as the payload,
    so the line stays re-derivable from it. A named key that is absent is simply omitted.
    ``extra`` carries values the payload does not hold; use it only where the line would otherwise
    state an ambiguous claim (task 100 deviation D2).
    """
    results = payload.get("results")
    rows: Sequence[Mapping[str, object]] = results if isinstance(results, list) else ()
    fields: list[tuple[str, object]] = [
        ("tool", tool),
        ("subject", subject(subject_parts)),
        ("question", question),
        ("answer", _answer(payload) if answer is None else answer),
    ]
    tier = weakest_tier(rows)
    if tier is not None:
        fields.append(("tier", tier))
    reason = payload.get("reason")
    if reason is not None and reason != REASON_OK:
        fields.append(("reason", reason))
    fields.extend(extra)
    fields.extend((key, payload[key]) for key in carry if key in payload)
    if payload.get("truncated"):
        fields.append(("truncated", True))
    fields.extend(revision_fields(staleness))
    fields.extend(server_fields())
    payload[CLAIM_KEY] = f"{CLAIM_SCHEMA} {render(fields)}"
    return payload
