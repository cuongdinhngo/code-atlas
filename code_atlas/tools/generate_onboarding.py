"""``generate_onboarding`` — write committable onboarding docs from the graph (task 088/089, M11).

Presentation + IO. Enrichment is ``onboarding.artifact`` composing 083–087; this module reads the
store, writes markdown, manifest, and a self-contained ``index.html`` under ``docs/onboarding/``,
and a regenerable cache under ``.code-atlas/onboarding/``. No SQL, no LLM, no language branch.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Literal

from code_atlas.config import Config
from code_atlas.onboarding.artifact import (
    CACHE_DIR,
    CACHE_NAME,
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
    render_module,
    render_overview,
    render_tour,
)
from code_atlas.onboarding.layers import LayerRefiner
from code_atlas.onboarding.summary import StructuralSummarizer, Summarizer
from code_atlas.onboarding.viewer import render_viewer
from code_atlas.store import GraphStore
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
) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo and the 085/091 seams (deterministic defaults when unset)."""
    seam: Summarizer = StructuralSummarizer() if summarizer is None else summarizer

    def generate_onboarding(detail_level: DetailLevel = "standard") -> dict[str, object]:
        """Write committable onboarding docs for this repo — overview, tour, and per-module pages.

        Reads the index and writes markdown plus a ``manifest.json`` under ``docs/onboarding/``
        so a human (or the 089 viewer) can review the map in git. Also writes ``index.html`` —
        one self-contained page that embeds the same facts, so it opens offline with no
        server and no fetch. Regenerating rewrites this
        tool's own files and removes only the module pages its last ``manifest.json`` recorded —
        a hand-authored file in that tree is left alone, and a tree holding these names without
        that manifest is refused rather than overwritten. A regenerable cache of the
        same structure lands under ``.code-atlas/onboarding/`` (gitignored). Deterministic given
        the summarizer: no timestamps. The walk that sizes the tour and per-module pages is the
        same node-budgeted subgraph ``guided_tour`` uses (``CA_IMPACT_MAX_NODES``); ``truncated``
        is true when that budget left an indexed file out. ``results`` lists the committed
        relative paths, capped at ``CA_MAX_RESULTS``. ``minimal`` omits the cache path.
        """
        if not config.db_path.is_file():
            return _unbuilt(config)
        with GraphStore(config.db_path) as store:
            nodes = store.node_universe()
            edges = store.dependency_edges()
            subgraph = store.tour_subgraph(max_nodes=config.impact_max_nodes)
        artifact = build_artifact(
            nodes,
            edges,
            subgraph.files,
            subgraph.edges,
            subgraph.entry_points,
            subgraph.truncated,
            seam,
            layer_refiner,
        )
        if artifact is None:
            return _empty(config)
        written = _write(Path(config.root), artifact)
        return _payload(config, artifact, written, detail_level)

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
    remove, so the previous ``shutil.rmtree`` is gone.
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


def _write(root: Path, artifact: OnboardingArtifact) -> tuple[str, ...]:
    """Rewrite this tool's own onboarding files and the cache. Paths are POSIX."""
    out = root / OUTPUT_DIR
    _refuse_foreign_tree(out)
    _remove_recorded_pages(out)
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    files = {
        OVERVIEW_NAME: render_overview(artifact),
        TOUR_NAME: render_tour(artifact),
        MANIFEST_NAME: manifest_json(artifact),
        VIEWER_NAME: render_viewer(artifact),
    }
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8", newline="\n")
        written.append(f"{OUTPUT_DIR}/{name}")
    for page in artifact.pages:
        dest = out / Path(*PurePosixPath(page.relpath).parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render_module(page), encoding="utf-8", newline="\n")
        written.append(f"{OUTPUT_DIR}/{page.relpath}")
    cache = root / CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    (cache / CACHE_NAME).write_text(cache_json(artifact), encoding="utf-8", newline="\n")
    return tuple(sorted(written))


def _payload(
    config: Config,
    artifact: OnboardingArtifact,
    written: tuple[str, ...],
    detail_level: DetailLevel,
) -> dict[str, object]:
    """``results`` is the committed path list, capped; ``truncated`` covers walk and page."""
    limit = config.max_results
    page = written[:limit]
    payload: dict[str, object] = {
        "indexed": True,
        "results": list(page),
        "truncated": artifact.truncated or len(written) > limit,
        "reason": REASON_OK,
        "total_count": len(written),
        "index_root": config.index_root,
        "output_dir": OUTPUT_DIR,
    }
    if detail_level == "standard":
        payload["cache"] = f"{CACHE_DIR}/{CACHE_NAME}"
    return payload
