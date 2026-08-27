"""Zero-answer language-coverage note (160), reusing 159's shipped-adapter source of truth.

A miss on an index that covers only some languages reads as absence unless the answer says what the
index does not cover. The note names the shipped-but-unwired adapters (159) — never the subject's
own language (160, out of scope). It rides a low-confidence answer only, so a confident answer is
byte-identical (061 / AC3).
"""

from __future__ import annotations

from code_atlas.adapter import unconfigured_adapters
from code_atlas.config import Config
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_SUBSTRING_MATCH,
)

COVERAGE_KEY = "unconfigured_adapters"


def coverage_gap(config: Config) -> list[dict[str, str]]:
    """The shipped adapters with no launch command — the index's language-coverage gap (159/160)."""
    return unconfigured_adapters(config.adapter_cmds)


def attach_coverage_gap(payload: dict[str, object], config: Config) -> dict[str, object]:
    """Attach the coverage gap when one exists — the caller has already judged the answer a zero.

    Omit-when-empty (061): a fully-wired server adds nothing. Used by ``attach_coverage_note`` for a
    single answer, and directly on the batch envelope when a swept subject came back empty.
    """
    gap = coverage_gap(config)
    if gap:
        payload[COVERAGE_KEY] = gap
    return payload


def attach_coverage_note(payload: dict[str, object], config: Config) -> dict[str, object]:
    """Name the coverage gap on an indexed *genuine-absence* answer, or a substring near-miss (167).

    Self-gating and idempotent, so it is safe to call at every return point: never on a not-indexed,
    stale, under-qualified, untracked, or confident (exact/prefix) answer. A
    relationship-not-modelled zero is a different kind (it already routes), and is left alone. A
    ``substring_match`` answer is the one carrying results that still needs the note — the requested
    symbol is absent (167).
    """
    if not payload.get("indexed"):
        return payload
    reason = payload.get("reason")
    if reason == REASON_SUBSTRING_MATCH:
        return attach_coverage_gap(payload, config)
    if payload.get("results"):
        return payload
    if reason not in (REASON_NO_MATCHES, REASON_NO_SUCH_SYMBOL):
        return payload
    return attach_coverage_gap(payload, config)
