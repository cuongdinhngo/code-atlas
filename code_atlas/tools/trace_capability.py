"""``trace_capability`` — the flows one subject participates in (task 199).

197 shipped capability flows to the reader's surfaces and deliberately shipped no agent-facing one,
because the surface it tried was measured and rejected: to read one 4-file trace an agent bought
the whole `architecture_overview` payload, and `summary.flows` answered with *every* flow, claiming
six files belonging to other requests. Both defects were properties of the surface. This is the
per-subject surface — the same derivation, filtered, in a nav-sized payload.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.onboarding.flows import FLOW_KINDS, Flow, FlowSet, flows_from_graph
from code_atlas.onboarding.layers import (
    IdentityLayerRefiner,
    assign_layers,
    refine_layers,
)
from code_atlas.onboarding.metrics import compute_metrics
from code_atlas.onboarding.modules import find_business_modules
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import (
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    REASON_OK,
    TRY_INSTEAD_SEARCH_SYMBOL,
)

NAME = "trace_capability"

DetailLevel = Literal["minimal", "standard"]

SUBJECT_QNAME = "qname"
SUBJECT_PATH = "path"
SUBJECT_MODULE = "module"

# A subject that IS indexed but joins no traced flow. `architecture_overview` names the flows that
# exist, so the route makes progress rather than pointing back here (R5.4).
TRY_INSTEAD_OVERVIEW = "architecture_overview"

__all__ = [
    "NAME",
    "SUBJECT_MODULE",
    "SUBJECT_PATH",
    "SUBJECT_QNAME",
    "create",
]


def _participates(flow: Flow, kind: str, subject: str) -> bool:
    """Exact membership — never a prefix or a deepest-wins predicate (130/131/197's lesson).

    A subject is in a flow when it IS one of its steps, not when it merely shares a path segment
    with one: `deepest-wins-is-not-a-membership-test` has cost this repo three tickets.
    """
    if kind == SUBJECT_MODULE:
        return flow.module == subject
    if kind == SUBJECT_PATH:
        return flow.seed_file == subject or any(step.file == subject for step in flow.steps)
    return flow.seed == subject or any(step.qname == subject for step in flow.steps)


def _incomplete(built: FlowSet) -> bool:
    """Is this answer possibly missing a flow the subject is in? (R5.6)

    Three ways, and the third is the one that bites. `build_flows` caps at SEED SELECTION, so a
    subject whose seed was never traced answers `no_matches` while its flow exists — a refusal that
    is confidently wrong, not a true zero. `flows_cut` alone does not see it: the flows were never
    built to be cut.
    """
    return (
        built.walk_truncated
        or built.flows_cut > 0
        or built.seeds_traced < built.seeds_found
    )


def _drop_subsumed(flows: list[Flow]) -> tuple[list[Flow], int]:
    """Drop a flow whose steps are a strict PREFIX of another's — it adds nothing to the answer.

    `build_flows` emits one flow per (seed, sink) pair (197), so a seed reaching two nodes in the
    domain layer yields two paths, the shorter contained in the longer. That is right for the map,
    which ranks flows for a reader; for a question about ONE request it is the same over-answering
    199 exists to remove, one level down. The count is reported, never silently absorbed.
    """
    chains = [tuple(step.qname for step in flow.steps) for flow in flows]
    kept = [
        flow
        for flow, chain in zip(flows, chains, strict=True)
        if not any(other != chain and other[: len(chain)] == chain for other in chains)
    ]
    return kept, len(flows) - len(kept)


def _envelope(
    *,
    config: Config,
    subject: str,
    subject_kind: str,
    indexed: bool,
    reason: str,
    results: list[dict[str, object]] | None = None,
    truncated: bool = False,
) -> dict[str, object]:
    """The whole payload shape. AC2: no aggregate the question did not ask for.

    The tool pages nothing, so every match is returned and ``len(results)`` IS the total; a second
    copy of that number would be the unread field 196 shipped and pruned. Its guard scans tool
    sources as TEXT, so the paging denominator is not named here even to say it is absent — doing
    so would declare this tool an emitter of a field it does not carry (123's guard, R6.7's class).
    """
    return {
        "index_root": config.index_root,
        "indexed": indexed,
        "reason": reason,
        "results": results if results is not None else [],
        "subject": subject,
        "subject_kind": subject_kind,
        "truncated": truncated,
    }


def _flow_row(flow: Flow, detail_level: DetailLevel) -> dict[str, object]:
    """One flow, sized like a nav answer: the trace and how it ended, nothing aggregate."""
    row: dict[str, object] = {
        "seed": flow.seed,
        "seed_file": flow.seed_file,
        "module": flow.module,
        "ended": flow.ended,
        "sink": flow.sink,
        "steps": [
            {
                "qname": step.qname,
                "file": step.file,
                "layer": step.layer,
                "kind": step.kind,
                "tier": step.tier,
            }
            for step in flow.steps
        ],
    }
    if detail_level == "standard":
        row["layers"] = list(flow.layers)
        if flow.walk_truncated:
            row["walk_truncated"] = True
    return row


def _subject_of(qname: str | None, path: str | None, module: str | None) -> tuple[str, str] | None:
    """Exactly one subject, or None when the caller named none or several."""
    named = [
        (SUBJECT_QNAME, qname),
        (SUBJECT_PATH, path),
        (SUBJECT_MODULE, module),
    ]
    given = [(kind, value) for kind, value in named if value]
    return (given[0][0], str(given[0][1])) if len(given) == 1 else None


def _build(store: GraphStore, config: Config) -> FlowSet:
    """The same derivation the map runs, through the one assembly both callers share (199)."""
    nodes = store.node_universe()
    edge_tiers = store.dependency_edges_with_tier()
    edges = [(source, target) for source, target, _tier in edge_tiers]
    metrics = compute_metrics(nodes, edges)
    assignment = refine_layers(assign_layers(metrics), metrics, IdentityLayerRefiner())
    modules = find_business_modules(
        store.file_paths(),
        class_counts=dict(store.file_class_counts()),
        fan_in={metric.key: metric.fan_in for metric in metrics.modules},
        stub_roots=config.stub_roots or (),
        limit=config.page_limit,
    )
    return flows_from_graph(
        nodes,
        store.flow_edges(FLOW_KINDS),
        metrics=metrics,
        assignment=assignment,
        modules=modules,
        declared_entry_points=config.entry_points or (),
        declared_stub_roots=config.stub_roots or (),
        max_flows=config.page_limit,
        max_nodes=config.impact_max_nodes,
    )


def _known(store: GraphStore, kind: str, subject: str, limit: int) -> bool:
    """Is this subject in the index at all? Distinguishes 'no such thing' from 'no flow' (R5.6)."""
    if kind == SUBJECT_QNAME:
        return bool(store.nodes_by_qualified_name(subject, limit=1))
    if kind == SUBJECT_PATH:
        return subject in set(store.file_paths())
    del limit
    return True


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def trace_capability(
        qname: str | None = None,
        path: str | None = None,
        module: str | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """How this codebase routes an incoming request — the capability flows one subject is in.

        Prefer this over Grep/Glob when the question is *"how does a request reach the code that
        produces the response?"* or *"what happens when a user does X?"*. Answers for **one**
        subject: an entry symbol (``qname``), a file (``path``), or a business module (``module``).
        Supply exactly one; naming none or several answers ``reason: name_not_qualified``. Each
        result is one flow — its seed, its ordered ``steps`` (``qname`` · ``file`` · ``layer`` ·
        ``kind`` · ``tier``), how it ``ended`` and its ``sink``. A subject the index does not hold
        answers ``no_such_symbol``; one it holds that joins no traced flow answers ``no_matches``
        and routes to ``architecture_overview`` — never an empty ``results`` presented as an answer.
        Carries no layer table, matrix, hub list or capability table: for the whole picture call
        ``architecture_overview`` instead.
        """
        chosen = _subject_of(qname, path, module)
        if chosen is None:
            return _envelope(
                config=config,
                subject="",
                subject_kind="",
                indexed=config.db_path.is_file(),
                reason=REASON_NAME_NOT_QUALIFIED,
            )
        kind, subject = chosen
        if not config.db_path.is_file():
            return _envelope(
                config=config,
                subject=subject,
                subject_kind=kind,
                indexed=False,
                reason=REASON_NOT_INDEXED,
            )
        with GraphStore(config.db_path) as store:
            if not _known(store, kind, subject, config.page_limit):
                payload = _envelope(
                    config=config,
                    subject=subject,
                    subject_kind=kind,
                    indexed=True,
                    reason=REASON_NO_SUCH_SYMBOL,
                )
                payload["try_instead"] = TRY_INSTEAD_SEARCH_SYMBOL
                return payload
            built = _build(store, config)
        matched = [flow for flow in built.flows if _participates(flow, kind, subject)]
        matched, subsumed = _drop_subsumed(matched)
        if not matched:
            payload = _envelope(
                config=config,
                subject=subject,
                subject_kind=kind,
                indexed=True,
                reason=REASON_NO_MATCHES,
                truncated=_incomplete(built),
            )
            payload["try_instead"] = TRY_INSTEAD_OVERVIEW
            return payload
        payload = _envelope(
            config=config,
            subject=subject,
            subject_kind=kind,
            indexed=True,
            reason=REASON_OK,
            results=[_flow_row(flow, detail_level) for flow in matched],
            truncated=_incomplete(built),
        )
        # A caveat about this answer's own shaping rides on this answer (R5.5), never elsewhere.
        if subsumed:
            payload["subsumed"] = subsumed
        return payload

    return trace_capability
