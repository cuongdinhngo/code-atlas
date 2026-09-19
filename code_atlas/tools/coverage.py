"""Language- and suffix-coverage notes (160/173/192/299), from stamps — never guessed languages.

A miss on a partial-language index reads as absence unless the answer names the gap. The note lists
shipped-but-unwired adapters (159) and configured-but-unheld languages (173). Task 192 widened it
onto partial hit lists; 299 adds a same-stem unindexed-suffix field on non-empty ``search_symbol``
pages so a ``.ts`` hit list cannot hide a twin ``.js`` that was never a candidate (061 omit-empty).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath

from code_atlas import gitutil
from code_atlas.adapter import unconfigured_adapters
from code_atlas.config import Config
from code_atlas.ignore import IgnoreMatcher, load_ignore
from code_atlas.store import (
    COVERED_LANGUAGES_KEY,
    COVERED_SUFFIXES_KEY,
    INDEXED_SUFFIXES_KEY,
    GraphStore,
)
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_SUBJECT_FILE_CHECKED,
    REASON_SUBSTRING_MATCH,
    REASON_TOKEN_CANDIDATES,
)

COVERAGE_KEY = "unconfigured_adapters"
# The second half of the same gap (task 173). 159/160 asked whether the adapter is LAUNCHABLE;
# flipping the switch emptied the note while the graph still held zero files of that language, so
# the zero went back to reading as absence. This key asks whether the graph HOLDS the language.
UNINDEXED_KEY = "unindexed_languages"
# Hit-path twin of the gap: same stem as a hit/query, suffix outside 173's held set (task 299).
SAME_BASENAME_KEY = "unindexed_same_basename"


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
    """The census when this file's language has no modelled inbound crossing (221/238).

    Language-scope, not hit-count: an unmeasured crossing is unmeasured whether this answer
    found in-language hits. ``None`` when the index cannot say — no stamp (R5.6), a
    single-language graph, or a modelled ``*->L`` pair already exists.
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


def cross_language_census_has_edges(census: Mapping[str, object]) -> bool:
    """True when the stamped census counted at least one cross-language edge (276).

    An empty census is a standing repo fact (on ``get_index_status``), not a per-answer
    partition — firing ``authoritative: false`` on every hit then partitions nothing.
    """
    linked = census.get("linked")
    unlinked = census.get("unlinked")
    linked_n = linked if isinstance(linked, int) else 0
    unlinked_n = unlinked if isinstance(unlinked, int) else 0
    return linked_n + unlinked_n > 0


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
    if reason not in (
        REASON_NO_MATCHES,
        REASON_NO_SUCH_SYMBOL,
        REASON_SUBJECT_FILE_CHECKED,
        REASON_TOKEN_CANDIDATES,
    ):
        return payload
    return attach_coverage_gap(payload, config, covered, detail_level=detail_level)


def held_suffixes(store: GraphStore) -> frozenset[str] | None:
    """173's held suffix set — what the graph HOLDS, never what was configured (R5.6 if absent)."""
    covered = store.get_meta(COVERED_SUFFIXES_KEY)
    if covered is not None:
        return frozenset(part for part in covered.split(",") if part)
    claimed = store.get_meta(INDEXED_SUFFIXES_KEY)
    if claimed is None:
        return None
    return frozenset(part for part in claimed.split(",") if part)


def attach_unindexed_same_basename(
    payload: dict[str, object],
    *,
    root: Path,
    indexed_suffixes: frozenset[str] | None,
    results: Sequence[Mapping[str, object]],
    subjects: Sequence[str],
    detail_level: str = "standard",
) -> dict[str, object]:
    """Name unindexed same-stem files beside a non-empty hit page (task 299).

    Omit-when-empty (061). Never guesses a language or a symbol in those files (R5.6).
    ``reason`` is untouched — hits stay ``ok``. ``minimal`` omits the field (223).
    """
    if detail_level == "minimal" or not payload.get("indexed") or not results:
        return payload
    if indexed_suffixes is None:
        return payload
    stems = _stems_for_same_basename(results, subjects)
    if not stems:
        return payload
    suffixes, count = _unindexed_same_stem_census(root, stems, indexed_suffixes)
    if count == 0:
        return payload
    payload[SAME_BASENAME_KEY] = {"suffixes": list(suffixes), "count": count}
    return payload


def _stems_for_same_basename(
    results: Sequence[Mapping[str, object]], subjects: Sequence[str]
) -> frozenset[str]:
    """Hit-file stems plus bare query stems — paths contribute their filename stem only."""
    stems: set[str] = set()
    for row in results:
        file_path = row.get("file")
        if isinstance(file_path, str) and file_path:
            stems.add(PurePosixPath(file_path).stem.casefold())
    for subject in subjects:
        if not subject:
            continue
        if "/" in subject or "\\" in subject:
            stems.add(PurePosixPath(subject.replace("\\", "/")).stem.casefold())
        else:
            stems.add(subject.casefold())
    return frozenset(stems)


def _unindexed_same_stem_census(
    root: Path, stems: frozenset[str], indexed_suffixes: frozenset[str]
) -> tuple[tuple[str, ...], int]:
    """Path-only census: matching stems whose suffix is outside the held set (no body read).

    Suffix and stem are decided on the basename before ``is_ignored``, which walks every rule:
    on a 52k-file tree that ordering is 24 ms instead of 4.8 s, for the same answer.
    """
    matcher = load_ignore(root)
    tracked = gitutil.ls_files(root)
    paths = tracked if tracked is not None else _walk_all_paths(root, matcher)
    found: set[str] = set()
    count = 0
    for path in paths:
        base = path.rsplit("/", 1)[-1]
        dot = base.rfind(".")
        if dot <= 0:
            continue
        suffix = base[dot:].lower()
        if suffix in indexed_suffixes or base[:dot].casefold() not in stems:
            continue
        if matcher.is_ignored(path):
            continue
        found.add(suffix)
        count += 1
    return tuple(sorted(found)), count


def _walk_all_paths(root: Path, matcher: IgnoreMatcher) -> tuple[str, ...]:
    """Non-git fallback: every non-ignored file path under ``root`` (suffix-agnostic)."""
    found: list[str] = []
    stack = [root]
    while stack:
        for entry in sorted(stack.pop().iterdir()):
            relative = entry.relative_to(root).as_posix()
            if entry.is_dir():
                if not matcher.is_ignored(relative, is_dir=True):
                    stack.append(entry)
            elif not matcher.is_ignored(relative):
                found.append(relative)
    return tuple(found)
