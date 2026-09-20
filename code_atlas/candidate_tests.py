"""Changed-code → candidate test files report (task 308 / 312).

Composes existing inbound edges and test-role classification. Never selective
execution, never a skip list, never a failing gate — candidates only; the full
suite stays authoritative. 312 widens the walk to a bounded inbound depth.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from code_atlas.config import Config
from code_atlas.contract import CALLER_KINDS
from code_atlas.store import GraphStore
from code_atlas.symbol_role import path_indicates_test, stored_test_source
from code_atlas.tools.staleness import compute_staleness

# Direct resolved callers outrank imports and any HEURISTIC evidence.
_KIND_RANK = {
    "CALLS": 0,
    "NEW": 0,
    "REFERENCES": 1,
    "IMPORTS": 2,
}
_RELATION_KINDS: tuple[str, ...] = (*CALLER_KINDS, "REFERENCES", "IMPORTS")

# Goal "one hop further"; 309's misses all sat at inbound depth 2.
DEFAULT_MAX_DEPTH = 2

FULL_SUITE_STATEMENT = (
    "Candidates only — the project's normal full suite remains authoritative. "
    "Unlisted tests are not safe to skip."
)

# Banned vocabulary that would imply selective execution (AC guard).
_BANNED_PHRASES: tuple[str, ...] = (
    "skip list",
    "skip these",
    "selected-test",
    "selected test",
    "failing gate",
    "pytest -k",
    "phpunit --filter",
)

UNMEASURED_TRUNCATED = "truncated_page"
UNMEASURED_STALE = "stale_index"
UNMEASURED_UNINDEXED = "unindexed_change"
UNMEASURED_UNLINKED = "unlinked_same_name_site"
UNMEASURED_NO_RUNNER = "no_runner_mapping"
UNMEASURED_DEPTH_BOUND = "depth_bound"

__all__ = [
    "DEFAULT_MAX_DEPTH",
    "FULL_SUITE_STATEMENT",
    "CandidateEvidence",
    "CandidateTestReport",
    "assert_no_selective_language",
    "build_candidate_test_report",
    "render_candidate_tests_json",
    "render_candidate_tests_text",
    "report_as_dict",
]


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    """One inbound relationship from a test-classified source to a changed production symbol."""

    test_path: str
    edge_kind: str
    confidence_tier: str
    source_qname: str
    source_file: str
    target_qname: str
    test_role_source: str
    hop_distance: int


@dataclass(frozen=True, slots=True)
class CandidateTestReport:
    """Deterministic candidate-test listing for one change set."""

    candidates: tuple[CandidateEvidence, ...]
    unmeasured: tuple[str, ...]
    statement: str
    changed_production_qnames: tuple[str, ...]


def build_candidate_test_report(
    config: Config,
    *,
    changed_indexed: Sequence[str],
    dirty_unindexed: Sequence[str] = (),
    page_limit: int | None = None,
    max_edges: int | None = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> CandidateTestReport:
    """Seed production symbols from changed paths; collect inbound test evidence."""
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    unmeasured: list[str] = [UNMEASURED_NO_RUNNER]
    if dirty_unindexed:
        unmeasured.append(UNMEASURED_UNINDEXED)
    cap = page_limit if page_limit is not None else max(config.page_limit, 1)

    if not config.db_path.is_file():
        unmeasured.append(UNMEASURED_STALE)
        return CandidateTestReport((), tuple(dict.fromkeys(unmeasured)), FULL_SUITE_STATEMENT, ())

    with GraphStore(config.db_path) as store:
        staleness_fields = compute_staleness(store, config)
        staleness = str(staleness_fields.get("staleness") or "")
        if staleness and staleness != "current":
            unmeasured.append(UNMEASURED_STALE)

        production_paths = [
            path for path in changed_indexed if not path_indicates_test(path)
        ]
        qnames = store.qnames_in_files(production_paths)
        seeds: list[str] = []
        for qname in qnames:
            rows = store.nodes_by_qualified_name(qname, limit=1)
            if not rows:
                continue
            if _as_int_flag(rows[0].get("is_test")):
                continue
            seeds.append(qname)

        walk_budget = (
            max_edges if max_edges is not None else max(config.impact_max_nodes, cap)
        )
        evidence, truncated, hit_bound = _walk_inbound(
            store,
            seeds,
            page_cap=cap,
            walk_budget=walk_budget,
            max_depth=max_depth,
        )
        for seed in seeds:
            if _has_unlinked_same_name(store, seed):
                unmeasured.append(UNMEASURED_UNLINKED)

        if truncated:
            unmeasured.append(UNMEASURED_TRUNCATED)
        if hit_bound:
            unmeasured.append(UNMEASURED_DEPTH_BOUND)

    ranked = tuple(sorted(evidence, key=_rank_key))
    return CandidateTestReport(
        ranked,
        tuple(dict.fromkeys(unmeasured)),
        FULL_SUITE_STATEMENT,
        tuple(seeds),
    )


def render_candidate_tests_text(report: CandidateTestReport) -> str:
    """Human text derived only from ``report`` — never a second computation."""
    lines = [
        "candidate_tests:",
        f"statement: {report.statement}",
        f"seeds: {len(report.changed_production_qnames)}",
        f"candidates: {len(report.candidates)}",
    ]
    for row in report.candidates:
        lines.append(
            f"CANDIDATE {row.test_path} <- {row.edge_kind}/{row.confidence_tier} "
            f"hop={row.hop_distance} from {row.source_qname} ({row.test_role_source}) "
            f"targeting {row.target_qname}"
        )
    for reason in report.unmeasured:
        lines.append(f"unmeasured: {reason}")
    text = "\n".join(lines) + "\n"
    assert_no_selective_language(text)
    return text


def render_candidate_tests_json(report: CandidateTestReport) -> str:
    """Deterministic JSON — sorted keys (R4.2)."""
    payload = {
        "candidates": [asdict(row) for row in report.candidates],
        "changed_production_qnames": list(report.changed_production_qnames),
        "statement": report.statement,
        "unmeasured": list(report.unmeasured),
    }
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    assert_no_selective_language(text)
    return text


def report_as_dict(report: CandidateTestReport) -> dict[str, object]:
    """JSON-ready object for embedding in the 303 check result."""
    return {
        "candidates": [asdict(row) for row in report.candidates],
        "changed_production_qnames": list(report.changed_production_qnames),
        "mode": "report_only",
        "statement": report.statement,
        "unmeasured": list(report.unmeasured),
    }


def assert_no_selective_language(text: str) -> None:
    """AC guard — output must not read as a skip/gate/selected-test instruction."""
    lowered = text.lower()
    for phrase in _BANNED_PHRASES:
        if phrase in lowered:
            raise AssertionError(f"candidate-test output contains banned phrase {phrase!r}")


def _as_int_flag(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return 0


def _walk_inbound(
    store: GraphStore,
    seeds: Sequence[str],
    *,
    page_cap: int,
    walk_budget: int,
    max_depth: int,
) -> tuple[list[CandidateEvidence], bool, bool]:
    """BFS inbound from seeds; collect tests at hop <= max_depth."""
    evidence: list[CandidateEvidence] = []
    truncated = False
    hit_bound = False
    # One budget for the whole BFS, not per seed: exhausting it stops the walk and
    # ships ``truncated_page`` rather than silently deepening the edge scan.
    edges_seen = 0
    # (node_qname, hop_from_seed, changed_seed)
    queue: deque[tuple[str, int, str]] = deque((seed, 0, seed) for seed in seeds)
    expanded: set[tuple[str, str]] = set()  # (node, changed_seed)

    while queue:
        node, hop, seed = queue.popleft()
        key = (node, seed)
        if key in expanded:
            continue
        expanded.add(key)

        offset = 0
        while True:
            page = store.edges_by_target(
                node,
                kinds=_RELATION_KINDS,
                limit=page_cap,
                offset=offset,
                distinct_sources=False,
            )
            if not page:
                break
            for edge in page:
                edges_seen += 1
                if edges_seen > walk_budget:
                    truncated = True
                    break
                next_hop = hop + 1
                classified = _classify_source(store, edge)
                if classified is None:
                    continue
                source_qname, source_file, is_test, role = classified
                if is_test:
                    kind = str(edge.get("kind") or "")
                    tier = str(edge.get("confidence_tier") or "HEURISTIC")
                    evidence.append(
                        CandidateEvidence(
                            test_path=source_file,
                            edge_kind=kind,
                            confidence_tier=tier,
                            source_qname=source_qname,
                            source_file=source_file,
                            target_qname=seed,
                            test_role_source=role,
                            hop_distance=next_hop,
                        )
                    )
                elif source_qname:
                    if next_hop < max_depth:
                        queue.append((source_qname, next_hop, seed))
                    elif _has_any_inbound(store, source_qname, page_cap=page_cap):
                        # On the bound: this node's own callers stay unreached — disclose it.
                        hit_bound = True
            if truncated or len(page) < page_cap:
                break
            offset += len(page)
            if truncated:
                break
        if truncated:
            break

    return evidence, truncated, hit_bound


def _classify_source(
    store: GraphStore, edge: Mapping[str, Any]
) -> tuple[str, str, bool, str] | None:
    """Return (qname, file, is_test, role) or None when the source is unusable."""
    source_qname = str(edge.get("source_qname") or "")
    source_file = str(edge.get("file_path") or "")
    if not source_qname and not source_file:
        return None
    nodes = store.nodes_by_qualified_name(source_qname, limit=1) if source_qname else []
    is_test_flag = _as_int_flag(nodes[0].get("is_test")) if nodes else 0
    file_path = str(nodes[0].get("file_path") or source_file) if nodes else source_file
    path_test = path_indicates_test(file_path)
    if not is_test_flag and not path_test:
        return (source_qname, file_path, False, "")
    if is_test_flag:
        role = stored_test_source(is_test_flag, file_path) or "adapter"
    else:
        role = "path_convention"
    return (source_qname, file_path, True, role)


def _has_any_inbound(store: GraphStore, qname: str, *, page_cap: int) -> bool:
    page = store.edges_by_target(
        qname,
        kinds=_RELATION_KINDS,
        limit=max(page_cap, 1),
        offset=0,
        distinct_sources=False,
    )
    return bool(page)


def _rank_key(row: CandidateEvidence) -> tuple[object, ...]:
    # Hop first so every direct candidate outranks every indirect one (312 Scope 2).
    tier_rank = 0 if row.confidence_tier == "RESOLVED" else 1
    kind_rank = _KIND_RANK.get(row.edge_kind, 9)
    return (
        row.hop_distance,
        tier_rank,
        kind_rank,
        row.test_path,
        row.source_qname,
        row.target_qname,
        row.edge_kind,
    )


def _has_unlinked_same_name(store: GraphStore, qname: str) -> bool:
    """True when unresolved inbound edges share the bare name (honest unmeasured)."""
    bare = qname.rsplit("\\", 1)[-1].rsplit(".", 1)[-1]
    if not bare:
        return False
    return store.count_unlinked_by_target_raw([bare], kinds=list(CALLER_KINDS)) > 0
