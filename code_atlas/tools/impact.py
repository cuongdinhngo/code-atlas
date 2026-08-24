"""``impact`` — bounded best-score blast radius (§12 / M6)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal, NamedTuple

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools import claim
from code_atlas.tools.nav_result import (
    REASON_NO_SUCH_SYMBOL,
    SubjectResolution,
    classify_missing_subject,
    empty_nav,
    nav_result,
    shape_exact_miss,
)
from code_atlas.tools.staleness import compute_staleness

NAME = "impact"

# ``subject_parts`` / ``resolve_seeds`` / ``explain_lost_subject`` / ``SeedSet`` are public so the
# module rollup (140) answers about the same seeds this tool does. One definition, two answers.

DetailLevel = Literal["minimal", "standard"]

QUESTION = "blast-radius"
# The two counts that make an empty answer a MODELLED zero rather than a failed query (065).
CLAIM_CARRY = ("seeds_dropped", "frontier_skipped_non_resolved")


class SeedSet(NamedTuple):
    """Resolved seeds, plus one resolution per requested subject that produced none (task 102)."""

    seeds: list[str]
    dropped: tuple[SubjectResolution, ...]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def impact(
        paths: list[str] | None = None,
        qnames: list[str] | None = None,
        depth: int | None = None,
        detail_level: DetailLevel = "standard",
        sign: bool = False,
    ) -> dict[str, object]:
        """What could break if I change this file or symbol — the blast radius?

        Bounded best-score over changed paths and/or qnames. Seeds are the union of every indexed
        node on ``paths`` and the explicit ``qnames``.
        ``depth`` defaults to ``CA_IMPACT_DEPTH``; the node budget is ``CA_IMPACT_MAX_NODES``.
        HEURISTIC/DYNAMIC neighbors are returned with their tier but do not expand the
        frontier. Missing seeds and a missing database yield an empty successful result.

        Walks resolver-linked IMPACT kinds only — an empty answer is a modelled zero for those
        kinds, not ``relationship_not_modelled`` (task 065; see ``find_references``).

        ``seeds_dropped`` counts every requested subject that produced no seed — a qname that is
        absent or resolves to many, a path with no indexed node — plus any seed the node budget
        pruned. ``results: []`` with ``seeds_dropped: 0`` therefore means a modelled zero and
        nothing else (task 102). When every named subject was lost the answer also carries
        ``reason`` (``no_such_symbol`` / ``name_not_qualified`` / ``not_indexed``, with
        ``candidate_count`` / ``try_instead`` where the classifier has them).

        ``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
        ``key=value`` line naming subject, question, answer and the revision the index describes,
        with ``seeds`` beside ``answer`` (``answer == seeds`` is the modelled zero: nothing beyond
        the seeds depends on them) and ``seeds_dropped`` / ``frontier_skipped_non_resolved``.
        No line is emitted when there is no index, or when no seed resolved — a question nothing
        answered would be signed ``answer=0``, and a claim that cannot be re-run is decoration.
        """
        hops = config.impact_depth if depth is None else depth
        if hops < 0:
            raise ValueError(f"depth must be >= 0, got {hops}")
        parts = subject_parts(paths, qnames)
        subject = ",".join(parts)
        if not config.db_path.is_file():
            return empty_nav(subject, detail_level=detail_level, db_path=str(config.db_path),
            index_root=config.index_root,
        )
        with GraphStore(config.db_path) as store:
            seed_set = resolve_seeds(
                store, paths=paths or [], qnames=qnames or [], max_results=config.max_results
            )
            outcome = store.impact_radius(
                seed_set.seeds, depth=hops, max_nodes=config.impact_max_nodes + 1
            )
            staleness = compute_staleness(store, config, include_dirty_count=True) if sign else {}
        truncated = len(outcome.rows) > config.impact_max_nodes
        results = outcome.rows[: config.impact_max_nodes]
        result = nav_result(
            subject,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=truncated,
            depth=hops,
            frontier_skipped_non_resolved=outcome.frontier_skipped_non_resolved,
            seeds_dropped=outcome.seeds_dropped + len(seed_set.dropped),
        )
        if seed_set.dropped and not seed_set.seeds:
            explain_lost_subject(result, seed_set.dropped)
        # A question no seed answered gets no line: it would be signed ``answer=0`` for a subject
        # the index never held. The payload names the loss in ``seeds_dropped`` (tasks 100, 102).
        if not sign or not seed_set.seeds:
            return result
        return claim.sign(
            result,
            tool=NAME,
            question=QUESTION,
            subject_parts=parts,
            staleness=staleness,
            carry=CLAIM_CARRY,
            extra=(("seeds", len(seed_set.seeds)),),
        )

    return impact


def subject_parts(paths: list[str] | None, qnames: list[str] | None) -> list[str]:
    """Subject items in stable order (qnames then paths) — joined for the payload, capped in the
    claim line."""
    bits: list[str] = []
    if qnames:
        bits.extend(qnames)
    if paths:
        bits.extend(paths)
    return bits


def resolve_seeds(
    store: GraphStore, *, paths: Sequence[str], qnames: Sequence[str], max_results: int
) -> SeedSet:
    """Union path-file nodes with explicit qnames (stable order: qnames then path nodes).

    A requested subject that resolves to nothing is kept as its resolution rather than forgotten,
    so the caller can count the loss and say why it happened (task 102). A subject whose nodes were
    all seen already is a duplicate, not a drop.
    """
    found: list[str] = []
    seen: set[str] = set()
    dropped: list[SubjectResolution] = []

    def take(resolution: SubjectResolution) -> None:
        # One rule for both subject slots: a subject that resolved is a seed, whichever argument
        # it arrived in. Counting a resolvable subject as lost is the bug 102 exists to remove.
        if resolution.status != "resolved_unique":
            dropped.append(resolution)
        elif resolution.qname not in seen:
            seen.add(resolution.qname)
            found.append(resolution.qname)

    for qname in qnames:
        if not qname:
            continue
        take(_resolve_seed(store, qname, max_results))
    for path in paths:
        if not path:
            continue
        rows = store.nodes_by_file_all(path)
        if not rows:
            take(classify_missing_subject(store, path, limit=max_results))
            continue
        for row in rows:
            qname = str(row["qualified_name"])
            if qname not in seen:
                seen.add(qname)
                found.append(qname)
    return SeedSet(found, tuple(dropped))


def _resolve_seed(store: GraphStore, qname: str, max_results: int) -> SubjectResolution:
    """A seed's stored qname: exact, or a uniquely-resolvable under-anchored form (075/076).

    An exact hit short-circuits before the classifier, so the hit path pays no extra query (R4).
    An absent or ambiguous seed comes back carrying the classification that says why (task 102).
    """
    if store.nodes_by_qualified_name(qname, limit=1):
        return SubjectResolution("resolved_unique", qname, 1)
    return classify_missing_subject(store, qname, limit=max_results)


def explain_lost_subject(
    result: dict[str, object], dropped: tuple[SubjectResolution, ...]
) -> dict[str, object]:
    """Say why the answer is empty when every named subject was lost (065/075/076; task 102).

    One subject carries its own classification and route. A merged multi-subject radius carries
    only the base class it can prove for every one of them — it has no per-subject channel (100).
    """
    if len(dropped) == 1:
        return shape_exact_miss(result, dropped[0])
    result["reason"] = REASON_NO_SUCH_SYMBOL
    return result
