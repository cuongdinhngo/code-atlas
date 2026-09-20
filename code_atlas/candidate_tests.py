"""Changed-code → candidate test files report (task 308).

Composes existing inbound edges and test-role classification. Never selective execution,
never a skip list, never a failing gate — candidates only; the full suite stays authoritative.
"""

from __future__ import annotations

import json
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

__all__ = [
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
) -> CandidateTestReport:
    """Seed production symbols from changed paths; collect inbound test evidence."""
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
        # Drop test-classified symbols that happen to live on a production path.
        seeds: list[str] = []
        for qname in qnames:
            rows = store.nodes_by_qualified_name(qname, limit=1)
            if not rows:
                continue
            if _as_int_flag(rows[0].get("is_test")):
                continue
            seeds.append(qname)

        evidence: list[CandidateEvidence] = []
        truncated = False
        # Page through the full inbound set; ``max_edges`` (default impact_max_nodes) is the
        # walk ceiling that forces an honest truncated_page unmeasured reason.
        walk_budget = (
            max_edges if max_edges is not None else max(config.impact_max_nodes, cap)
        )
        for seed in seeds:
            offset = 0
            seen_for_seed = 0
            while True:
                page = store.edges_by_target(
                    seed,
                    kinds=_RELATION_KINDS,
                    limit=cap,
                    offset=offset,
                    distinct_sources=False,
                )
                if not page:
                    break
                for edge in page:
                    item = _evidence_from_edge(store, edge, seed)
                    if item is not None:
                        evidence.append(item)
                seen_for_seed += len(page)
                offset += len(page)
                if len(page) < cap:
                    break
                if seen_for_seed >= walk_budget:
                    truncated = True
                    break

            if _has_unlinked_same_name(store, seed):
                unmeasured.append(UNMEASURED_UNLINKED)

        if truncated:
            unmeasured.append(UNMEASURED_TRUNCATED)

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
            f"from {row.source_qname} ({row.test_role_source}) targeting {row.target_qname}"
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


def _evidence_from_edge(
    store: GraphStore, edge: Mapping[str, Any], target_qname: str
) -> CandidateEvidence | None:
    source_qname = str(edge.get("source_qname") or "")
    source_file = str(edge.get("file_path") or "")
    if not source_qname and not source_file:
        return None
    nodes = store.nodes_by_qualified_name(source_qname, limit=1) if source_qname else []
    is_test = _as_int_flag(nodes[0].get("is_test")) if nodes else 0
    file_path = str(nodes[0].get("file_path") or source_file) if nodes else source_file
    path_test = path_indicates_test(file_path)
    if not is_test and not path_test:
        return None
    if is_test:
        role = stored_test_source(is_test, file_path) or "adapter"
    else:
        role = "path_convention"
    tier = str(edge.get("confidence_tier") or "HEURISTIC")
    kind = str(edge.get("kind") or "")
    return CandidateEvidence(
        test_path=file_path,
        edge_kind=kind,
        confidence_tier=tier,
        source_qname=source_qname,
        source_file=file_path,
        target_qname=target_qname,
        test_role_source=role,
    )


def _rank_key(row: CandidateEvidence) -> tuple[object, ...]:
    tier_rank = 0 if row.confidence_tier == "RESOLVED" else 1
    kind_rank = _KIND_RANK.get(row.edge_kind, 9)
    return (tier_rank, kind_rank, row.test_path, row.source_qname, row.target_qname, row.edge_kind)


def _has_unlinked_same_name(store: GraphStore, qname: str) -> bool:
    """True when unresolved inbound edges share the bare name (honest unmeasured)."""
    bare = qname.rsplit("\\", 1)[-1].rsplit(".", 1)[-1]
    if not bare:
        return False
    return store.count_unlinked_by_target_raw([bare], kinds=list(CALLER_KINDS)) > 0
