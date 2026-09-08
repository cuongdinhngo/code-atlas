"""Zero-answer language-coverage note (160), reusing 159's shipped-adapter source of truth.

A miss on an index that covers only some languages reads as absence unless the answer says what the
index does not cover. The note names the shipped-but-unwired adapters (159) — never the subject's
own language (160, out of scope). It rides a low-confidence answer only, so a confident answer is
byte-identical (061 / AC3).
"""

from __future__ import annotations

from collections.abc import Sequence

from code_atlas.adapter import unconfigured_adapters
from code_atlas.config import Config
from code_atlas.store import COVERED_LANGUAGES_KEY, GraphStore
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_SUBSTRING_MATCH,
)

COVERAGE_KEY = "unconfigured_adapters"
# The second half of the same gap (task 173). 159/160 asked whether the adapter is LAUNCHABLE;
# flipping the switch emptied the note while the graph still held zero files of that language, so
# the zero went back to reading as absence. This key asks whether the graph HOLDS the language.
UNINDEXED_KEY = "unindexed_languages"


def relation_unmodelled_for_language(
    store: GraphStore, *, file_path: str, kinds: Sequence[str]
) -> bool:
    """Is this file's language silent on EVERY edge kind the caller reads (task 186)?

    160 wrote its own carve-out down — the coverage note never names *the subject's own language*.
    On one language that costs nothing; on two it turns an unread relation into a confident zero.
    The verdict is a data question the core may ask without knowing what a language is (R1.1): has
    this language ever emitted any of these kinds in this index? ``False`` whenever the index cannot
    say — no stamp, unindexed file, unnamed language — because silence is not evidence (R5.6).
    """
    language = store.language_of_file(file_path)
    if language is None:
        return False
    return store.language_emits_none_of(language, kinds) is True


def relation_carried_by(store: GraphStore, *, file_path: str, kinds: Sequence[str]) -> bool:
    """Does this file's language emit at least ONE of ``kinds`` in this index (task 188)?

    Not the negation of the function above: that one answers ``False`` where the index cannot say,
    which is right for withholding a confident zero and wrong for naming a route. Both silences
    answer ``False`` here, so a route is named only on positive evidence (R5.4 clause c / R5.6).
    """
    language = store.language_of_file(file_path)
    if language is None:
        return False
    return store.language_emits_none_of(language, kinds) is False


def coverage_gap(config: Config) -> list[dict[str, str]]:
    """The shipped adapters with no launch command — the index's language-coverage gap (159/160)."""
    return unconfigured_adapters(config.adapter_cmds)


def covered_languages(store: GraphStore) -> str | None:
    """The per-build coverage stamp, read once while the store is open (task 173)."""
    return store.get_meta(COVERED_LANGUAGES_KEY)


def cross_language_relation_unmodelled(
    store: GraphStore, *, file_path: str
) -> dict[str, object] | None:
    """The cross-language census when a zero into this file's language is unmeasured (task 221).

    186 asks whether the subject's OWN language emits a kind; a stored proc needs the inverse — does
    the index model any linked edge from ANOTHER language into this one? Returns the census block
    (the low-confidence note) only then. ``None`` — a plain ``no_matches`` — whenever the index
    cannot say: no stamp (R5.6), a single-language graph (no crossing is possible, so a genuine zero
    stays honest — AC2), or a modelled ``*->L`` pair already exists.
    """
    language = store.language_of_file(file_path)
    if language is None:
        return None
    census = store.stamped_cross_language_edges()
    if census is None:
        return None
    stamped = covered_languages(store)
    covered = {name for name in (stamped or "").split(",") if name}
    if not any(name != language for name in covered):
        return None
    pairs = census.get("pairs", {})
    if isinstance(pairs, dict) and any(str(key).endswith(f"->{language}") for key in pairs):
        return None
    return census


def unindexed_languages(config: Config, stamped: str | None) -> list[dict[str, str]]:
    """Configured languages the graph holds no files for — the switch is on, the build is missing.

    Reads the per-build stamp, never a scan (task 173). An index written before that stamp existed
    says nothing rather than guessing every configured language is missing (R5.6).
    """
    if stamped is None:
        return []
    covered = {name.lower() for name in stamped.split(",") if name}
    return [
        {"language": name, "rebuild": "build_or_update_index(full=true)"}
        for name in sorted({name.lower() for name in config.adapter_cmds})
        if name not in covered
    ]


def attach_coverage_gap(
    payload: dict[str, object],
    config: Config,
    covered: str | None = None,
    *,
    detail_level: str = "standard",
) -> dict[str, object]:
    """Attach the coverage gap when one exists — the caller has already judged the answer a zero.

    Omit-when-empty (061): a fully-wired, fully-indexed server adds nothing. Used by
    ``attach_coverage_note`` for a single answer, and directly on the batch envelope when a swept
    subject came back empty. ``minimal`` omits the note — ask ``standard``/``verbose`` (223).
    """
    if detail_level == "minimal":
        return payload
    gap = coverage_gap(config)
    if gap:
        payload[COVERAGE_KEY] = gap
    missing = unindexed_languages(config, covered)
    if missing:
        payload[UNINDEXED_KEY] = missing
    return payload


def attach_coverage_note(
    payload: dict[str, object],
    config: Config,
    covered: str | None = None,
    *,
    detail_level: str = "standard",
) -> dict[str, object]:
    """Name the coverage gap on an indexed *genuine-absence* answer, or a substring near-miss (167).

    Self-gating and idempotent, so it is safe to call at every return point: never on a not-indexed,
    stale, under-qualified or untracked answer. A relationship-not-modelled zero is a different kind
    (it already routes), and is left alone.

    **A PARTIAL answer needs the note as much as an empty one (task 192).** 160 exempted every
    answer carrying results, and field retro 8-A measured what that costs: ``search_symbol``
    answered **one hit** with ``reason: ok`` for a symbol with **281 real sites** in a language the
    index does not hold — *"a false negative wearing a modelled zero's clothes"*. Round 12 saw the
    same shape on a second language. The gap is a property of the INDEX, not of how many rows came
    back, so the only question is whether one exists.

    Omit-when-empty (061) keeps this from becoming noise: a fully-wired, fully-indexed server is
    still byte-identical, which is the no-false-alarm property AC2 pins. ``minimal`` demotes the
    note to a ``detail_level`` that asks for it (223) — identity stays on ``get_index_status``.
    """
    if detail_level == "minimal":
        return payload
    if not payload.get("indexed"):
        return payload
    reason = payload.get("reason")
    if reason == REASON_SUBSTRING_MATCH or payload.get("results"):
        return attach_coverage_gap(payload, config, covered, detail_level=detail_level)
    if reason not in (REASON_NO_MATCHES, REASON_NO_SUCH_SYMBOL):
        return payload
    return attach_coverage_gap(payload, config, covered, detail_level=detail_level)
