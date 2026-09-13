"""``generate_onboarding`` — write committable onboarding docs from the graph (task 088/089, M11).

Presentation + IO. Enrichment is ``onboarding.artifact`` composing 083–087; this module reads the
store, writes markdown, manifest, and a self-contained ``index.html`` under ``docs/onboarding/``,
and a versioned ``artifact.json`` under ``.code-atlas/onboarding/``. No SQL, no LLM, no language
branch.

205 removed the per-module page tree: at most five files are written, not 505 — and 210 lets an
audience contract fewer. The recorded-page removal
stays as the migration path — the first write after 205 deletes exactly the pages a pre-205
manifest recorded, and nothing else (R5.7).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
from typing import Literal

from code_atlas.config import Config, as_working_roots
from code_atlas.contract import split_qname
from code_atlas.onboarding.artifact import (
    CACHE_DIR,
    CACHE_NAME,
    FLOWS_NAME,
    MANIFEST_NAME,
    OUTPUT_DIR,
    OVERVIEW_NAME,
    PAGES_DIR,
    TOUR_NAME,
    VIEWER_NAME,
    OnboardingArtifact,
    build_artifact,
    cache_json,
    manifest_json,
    recorded_pages,
    render_flows,
    render_overview,
    render_tour,
)
from code_atlas.onboarding.audience import FLOWS_DOC, TOUR_DOC, VIEWER_DOC, contract_for
from code_atlas.onboarding.dataset import OnboardingDataset, build_dataset
from code_atlas.onboarding.er_diagram import DEFAULT_TABLE_CAP, project_er
from code_atlas.onboarding.flows import FLOW_KINDS
from code_atlas.onboarding.layers import IdentityLayerRefiner, LayerRefiner
from code_atlas.onboarding.orientation import read_orientation
from code_atlas.onboarding.prose import ProseRun, ProseWriter
from code_atlas.onboarding.provenance import Provenance, implementation_name
from code_atlas.onboarding.scope import scoped_paths
from code_atlas.onboarding.summary import StructuralSummarizer, Summarizer
from code_atlas.onboarding.viewer import render_viewer
from code_atlas.store import LAST_COMMIT_KEY, LAST_REF_KEY, GraphStore
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
    NavReason,
)

NAME = "generate_onboarding"

DetailLevel = Literal["minimal", "standard"]

__all__ = ["NAME", "create"]


def create(
    config: Config,
    summarizer: Summarizer | None = None,
    layer_refiner: LayerRefiner | None = None,
    prose_writer: ProseWriter | None = None,
) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo and the 085/091/117 seams (deterministic defaults when unset)."""
    # Both defaults resolve HERE, not inside the builders, so 209's stamp can name the object that
    # actually ran rather than the argument that was passed (LESSONS 201-C2).
    seam: Summarizer = StructuralSummarizer() if summarizer is None else summarizer
    refiner: LayerRefiner = IdentityLayerRefiner() if layer_refiner is None else layer_refiner

    def generate_onboarding(
        detail_level: DetailLevel = "standard",
        audience: str | None = None,
        working_roots: list[str] | None = None,
    ) -> dict[str, object]:
        """Write committable onboarding docs for this repo — overview, guided tour and flows.

        Reads the index and writes **up to five files** under ``docs/onboarding/``: ``overview.md``,
        ``tour.md``, ``flows.md``, ``manifest.json``, and ``index.html`` — one self-contained page
        that embeds the same facts, so it opens offline with no server and no fetch. There is **no
        per-module page tree**: 500 sub-kilobyte pages, one per node-budget slot, were emitted on
        every repo and carried nothing a reader could not read off the path (205).
        Regenerating rewrites this tool's own files, and removes the module pages a **pre-205**
        ``manifest.json`` recorded — a hand-authored file in that tree is left alone, and a tree
        holding these names without that manifest is refused rather than overwritten. A versioned
        dump of the same structure lands under ``.code-atlas/onboarding/artifact.json``
        (gitignored, ``ARTIFACT_VERSION``). Deterministic given the summarizer: no timestamps.
        The walk that sizes the tour is the same node-budgeted subgraph ``guided_tour`` uses
        (``CA_IMPACT_MAX_NODES``) — roots ranked by out-degree, capped at a quarter of the budget
        so the tour describes files the walk actually reached (106); ``truncated`` is true when
        that budget left an indexed file out.

        Three independent axes (210 / 216):

        - ``detail_level`` — how much of the *response* to return (same meaning on 24 tools); the
          response is discarded, so it does not reshape the committed tree.
        - ``audience`` — which *sections* the written tree holds (``full`` / ``newcomer`` /
          ``maintainer``); unset takes ``CA_AUDIENCE``.
        - ``working_roots`` — which *population* those sections draw from: restricts the tour,
          flow seeds and busiest-file pick to those trees (206). Omitted inherits
          ``CA_WORKING_ROOTS`` / config; a list wins over the environment; ``[]`` forces the
          whole index even when the environment scopes it.

        ``results`` lists the committed relative paths, capped at ``CA_MAX_RESULTS``.
        ``minimal`` omits the path to the ``artifact.json`` dump.
        """
        if not config.db_path.is_file():
            return _unbuilt(config)
        # Explicit argument wins over env/config; None keeps today's CA_WORKING_ROOTS default (216).
        roots = (
            config.working_roots
            if working_roots is None
            else as_working_roots("working_roots", list(working_roots))
        )
        # One budget for the whole write: the artifact and the dataset build the same layer table,
        # so a shared run pays for each layer description once and caps the build as a whole (117).
        wants = contract_for(audience if audience is not None else config.audience)
        prose = ProseRun(prose_writer)
        with GraphStore(config.db_path) as store:
            nodes = store.node_universe()
            edge_tiers = store.dependency_edges_with_tier()
            flow_edge_rows = store.flow_edges(FLOW_KINDS)
            edges = [(source, target) for source, target, _tier in edge_tiers]
            file_paths = store.file_paths()
            scoped = scoped_paths(file_paths, roots) if roots else None
            subgraph = store.tour_subgraph(
                max_nodes=config.impact_max_nodes, files=scoped
            )
            counts = store.counts()
            node_kinds = store.node_kind_counts()
            edge_kinds = store.edge_kind_counts()
            confidence = store.edge_health()["by_tier"]
            # 196 — the stamp beside the blend it attributes, never a second fold (183/195, P7).
            confidence_by_language = store.stamped_edge_health_by_language()
            hubs = store.module_hubs(limit=config.page_limit)
            classes = store.largest_classes(limit=config.page_limit)
            file_syms = store.file_symbol_counts()
            file_classes = store.file_class_counts()
            file_kinds = store.file_kind_counts()
            commit = store.get_meta(LAST_COMMIT_KEY) or ""
            last_ref = store.get_meta(LAST_REF_KEY) or commit
            tour_files = subgraph.files
            file_nodes = {
                path: store.nodes_by_file_all(path)
                for path in tour_files
            }
            er_table_rows = store.nodes_by_kind("Table", limit=10_000)
            er_columns: dict[str, list] = {
                str(row["qualified_name"]): [] for row in er_table_rows
            }
            for col in store.nodes_by_kind("Column", limit=50_000):
                container, _ = split_qname(str(col["qualified_name"]))
                if container is not None and container in er_columns:
                    er_columns[container].append(col)
            er_ref_edges = store.edges_matching_kind("REFERENCES", limit=10_000)
            er_tables, er_refs = project_er(er_table_rows, er_columns, er_ref_edges)
        artifact = build_artifact(
            nodes,
            edges,
            tour_files,
            subgraph.edges,
            subgraph.entry_points,
            subgraph.truncated,
            seam,
            refiner,
            max_results=config.page_limit,
            declared_entry_points=config.entry_points,
            declared_stub_roots=config.stub_roots,
            working_roots=roots,
            file_paths=file_paths,
            file_class_counts=file_classes,
            prose=prose,
            root=Path(config.root),
            file_nodes=file_nodes,
            edge_tiers=edge_tiers,
        )
        if artifact is None:
            return _empty(config)
        # An IDENTITY, never a count: 117's AC2 forbids a dataset number that moves when the
        # seam turns on, and `prose_calls` stays in the discarded payload for that reason.
        orientation = read_orientation(
            Path(config.root), config.project_files, max_facts=config.page_limit
        )
        provenance = Provenance(
            summarizer=implementation_name(seam),
            prose=implementation_name(prose.writer),
            layers=implementation_name(refiner),
        )
        dataset = build_dataset(
            nodes,
            edges,
            files=counts["files"],
            parsed=counts["parsed"],
            node_kind_counts=node_kinds,
            edge_kind_counts=edge_kinds,
            confidence=confidence,  # type: ignore[arg-type]
            hubs=hubs,
            classes=classes,
            file_symbol_counts=file_syms,
            file_paths=file_paths,
            path_index_max=config.path_index_max,
            layer_refiner=refiner,
            declared_entry_points=config.entry_points,
            declared_stub_roots=config.stub_roots,
            working_roots=roots,
            reachability_sample_max=config.page_limit,
            file_class_counts=file_classes,
            module_max=config.page_limit,
            mirror_sample_max=config.page_limit,
            file_kind_counts=file_kinds,
            commit=commit,
            prose=prose,
            flow_edges=flow_edge_rows,
            flow_max=config.page_limit,
            flow_max_nodes=config.impact_max_nodes,
            confidence_by_language=confidence_by_language,
            provenance=provenance,
            orientation=orientation,
            audience=wants.audience,
        )
        written = _write(
            Path(config.root),
            artifact,
            dataset,
            config.page_limit,
            file_paths=file_paths,
            working_roots=roots,
            index_root=config.index_root,
            last_ref=last_ref,
            audience=wants.audience,
            er_tables=er_tables,
            er_refs=er_refs,
        )
        return _payload(
            config, artifact, written, detail_level, prose, wants.audience, roots
        )

    return generate_onboarding


def _base(config: Config, *, indexed: bool, reason: NavReason) -> dict[str, object]:
    """The keys every outcome carries: 071's ``index_root``, 033/065's reason + count."""
    return {
        "indexed": indexed,
        "results": [],
        "truncated": False,
        "reason": reason,
        "total_count": 0,
        "index_root": config.index_root,
    }


def _unbuilt(config: Config) -> dict[str, object]:
    """No database yet — a write must not invent an index to document."""
    return _base(config, indexed=False, reason=REASON_NOT_INDEXED)


def _empty(config: Config) -> dict[str, object]:
    """An index with no module: a genuine zero, distinct from the unbuilt one above (033/065)."""
    return _base(config, indexed=True, reason=REASON_NO_MATCHES)


def _refuse_foreign_tree(out: Path) -> None:
    """Our filenames without our manifest mean somebody else owns this tree (050)."""
    if (out / MANIFEST_NAME).is_file():
        return
    for name in (OVERVIEW_NAME, TOUR_NAME, VIEWER_NAME):
        if (out / name).exists():
            raise ValueError(
                f"refusing to overwrite {OUTPUT_DIR}/{name}: no {MANIFEST_NAME}, so this "
                f"tree was not written by {NAME}"
            )


def _remove_recorded_pages(out: Path) -> None:
    """Delete exactly the pages the last manifest recorded, then directories left empty.

    A page this tool never wrote — a hand-authored file under ``modules/`` — is not ours to
    remove, so the previous ``shutil.rmtree`` is gone. Since 205 nothing writes a page, so this
    runs once against a pre-205 manifest and finds nothing thereafter (R5.7).
    """
    manifest = out / MANIFEST_NAME
    if not manifest.is_file():
        return
    for rel in recorded_pages(manifest.read_text(encoding="utf-8")):
        (out / Path(*PurePosixPath(rel).parts)).unlink(missing_ok=True)
    pages = out / PAGES_DIR
    if not pages.is_dir():
        return
    for path in sorted(pages.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def _write(
    root: Path,
    artifact: OnboardingArtifact,
    dataset: OnboardingDataset,
    max_results: int,
    *,
    file_paths: Sequence[str] = (),
    working_roots: Sequence[str] | None = None,
    index_root: str = "",
    last_ref: str = "",
    audience: str | None = None,
    er_tables: Sequence = (),
    er_refs: Sequence = (),
) -> tuple[str, ...]:
    """Rewrite this tool's own onboarding files and artifact.json. Paths are POSIX.

    A document this audience's contract does not name is not written, and a stale copy of it from a
    previous audience is removed — a tree that still holds one is lying about who it is for (210).
    """
    wants = contract_for(audience)
    out = root / OUTPUT_DIR
    _refuse_foreign_tree(out)
    _remove_recorded_pages(out)
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    files = {
        OVERVIEW_NAME: render_overview(
            artifact,
            node_cap=max_results,
            file_paths=file_paths,
            working_roots=working_roots,
            provenance=dataset.provenance,
            orientation=dataset.orientation,
            audience=wants.audience,
            er_tables=er_tables,
            er_refs=er_refs,
            er_table_cap=DEFAULT_TABLE_CAP,
        ),
        TOUR_NAME: render_tour(
            artifact,
            max_results,
            file_paths=file_paths,
            working_roots=working_roots,
        ),
        FLOWS_NAME: render_flows(dataset, file_paths=file_paths, working_roots=working_roots),
        MANIFEST_NAME: manifest_json(
            artifact, dataset, index_root=index_root, last_ref=last_ref
        ),
        VIEWER_NAME: render_viewer(dataset, max_results),
    }
    contracted = {
        TOUR_NAME: TOUR_DOC,
        FLOWS_NAME: FLOWS_DOC,
        VIEWER_NAME: VIEWER_DOC,
    }
    for name, text in files.items():
        document = contracted.get(name)
        if document is not None and not wants.wants_document(document):
            (out / name).unlink(missing_ok=True)
            continue
        (out / name).write_text(text, encoding="utf-8", newline="\n")
        written.append(f"{OUTPUT_DIR}/{name}")
    cache = root / CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    (cache / CACHE_NAME).write_text(cache_json(artifact), encoding="utf-8", newline="\n")
    return tuple(sorted(written))


def _payload(
    config: Config,
    artifact: OnboardingArtifact,
    written: tuple[str, ...],
    detail_level: DetailLevel,
    prose: ProseRun,
    audience: str,
    working_roots: Sequence[str] | None,
) -> dict[str, object]:
    """``results`` is the committed path list, capped; ``truncated`` covers walk and page."""
    limit = config.page_limit
    wants = contract_for(audience)
    page = written[:limit]
    payload: dict[str, object] = {
        "indexed": True,
        "results": list(page),
        "truncated": artifact.truncated or len(written) > limit,
        "reason": REASON_OK,
        "total_count": len(written),
        "index_root": config.index_root,
        "output_dir": OUTPUT_DIR,
        "working_roots": list(working_roots) if working_roots else None,
        "audience": wants.audience,
    }
    if detail_level == "standard":
        payload["cache"] = f"{CACHE_DIR}/{CACHE_NAME}"
        # What the 117 seam cost this write, and how many slots its ceiling left structural. Not in
        # the dataset on purpose: a number that moved when the seam turned on would break AC2.
        payload["prose_calls"] = prose.calls
        payload["prose_declined"] = prose.declined
    return payload
