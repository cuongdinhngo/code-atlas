"""Task 123 AC2: ``total_count`` means the true total, not the page length, on every emitter."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import Config, load_config
from code_atlas.store import GraphStore
from code_atlas.tools import (
    architecture_overview,
    file_outline,
    find_callers,
    find_implementations,
    find_references,
    find_view_data,
    guided_tour,
    search_symbol,
)
from tests.test_nav_tools import edge, node

CEILING = 2
PATH = "app/w.php"


def _config(tmp_path: Path) -> Config:
    return replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        root=tmp_path,
        max_results=CEILING,
        impact_max_nodes=50,
    )


def _seed(tmp_path: Path) -> None:
    """Enough rows that every tool truncates at ``CEILING``."""
    on_disk = tmp_path / PATH
    on_disk.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    on_disk.write_bytes(body)
    nodes = [node("Function", f"Widget{i}", f"\\Widget{i}", PATH) for i in range(6)]
    for i, row in enumerate(nodes):
        row["line_start"] = i + 1
    edges: list[dict[str, object]] = []
    for i in range(6):
        edges.append(
            edge(
                "CALLS",
                f"\\Widget{i}",
                "call",
                PATH,
                target_qname="\\T::put",
                tier="RESOLVED",
            )
        )
        edges.append(
            edge(
                "EXTENDS",
                f"\\Sub{i}",
                "ext",
                PATH,
                target_qname="\\Base",
                tier="RESOLVED",
            )
        )
        edges.append(
            edge(
                contract.PROVIDES_VIEW_DATA,
                "\\H",
                f"viewdata:k{i}",
                PATH,
                tier="HEURISTIC",
            )
        )
    extra_files = [
        (f"mod/layer{i}/file.php", f"\\L{i}\\File", i + 10)
        for i in range(6)
    ]
    with GraphStore(tmp_path / "graph.db") as store:
        store.upsert_file(PATH, hashlib.sha256(body).hexdigest(), "php")
        store.replace_file_rows(PATH, nodes, edges)
        for fpath, qname, line in extra_files:
            target = tmp_path / fpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            store.upsert_file(fpath, hashlib.sha256(body).hexdigest(), "php")
            store.replace_file_rows(
                fpath,
                [node("Class", "File", qname, fpath)],
                [
                    edge(
                        "CALLS",
                        f"{qname}::m",
                        "\\T::put",
                        fpath,
                        target_qname="\\T::put",
                        tier="RESOLVED",
                        line=line,
                    )
                ],
            )


def _call(name: str, config: Config) -> dict[str, object]:
    if name == "file_outline":
        return file_outline.create(config)(PATH, detail_level="minimal")
    if name == "search_symbol":
        return search_symbol.create(config)("Widget", detail_level="minimal")
    if name == "find_callers":
        return find_callers.create(config)("\\T::put", detail_level="minimal")
    if name == "find_references":
        return find_references.create(config)("\\T::put", detail_level="minimal")
    if name == "find_implementations":
        return find_implementations.create(config)("\\Base", detail_level="minimal")
    if name == "find_view_data":
        return find_view_data.create(config)("\\H", detail_level="minimal")
    if name == "guided_tour":
        return guided_tour.create(config)(detail_level="minimal")
    if name == "architecture_overview":
        return architecture_overview.create(config)(detail_level="minimal")
    raise AssertionError(name)


# Hand-kept, but guarded below by a source scan so emitter N+1 cannot drift in (R6.7 / 123 AC2).
TOTAL_COUNT_TOOLS = [
    "file_outline",
    "search_symbol",
    "find_callers",
    "find_references",
    "find_implementations",
    "find_view_data",
    "guided_tour",
    "architecture_overview",
]


@pytest.mark.parametrize("tool", TOTAL_COUNT_TOOLS)
def test_truncated_payload_reports_true_total_not_page_length(
    tmp_path: Path, tool: str
) -> None:
    """When ``truncated`` is true, ``total_count`` must exceed ``len(results)``."""
    _seed(tmp_path)
    result = _call(tool, _config(tmp_path))
    # The fixture seeds > CEILING rows for every arm, so a false ``truncated`` here means the
    # seed stopped covering that tool — the assertion below must never go vacuous.
    assert result["truncated"] is True, result
    assert int(result["total_count"]) > len(result["results"])


# Helpers, not emitters: ``nav_result``/``claim`` shape or read the field for other tools,
# ``get_index_status`` names it in prose only, and ``generate_onboarding`` reports a write count
# that is never paged — so none of the four is a paged emitter this invariant can assert against.
NOT_PAGED_EMITTERS = {"nav_result", "claim", "get_index_status", "generate_onboarding"}


def test_total_count_denominator_is_guarded_by_a_source_scan() -> None:
    """R6.7 — a new ``total_count`` emitter cannot ship without an arm in ``TOTAL_COUNT_TOOLS``.

    Source-scan (no import), same shape as the 066 clamp guard: the hand-kept list above is only
    safe while this equality holds, and it is what drifts silently when tool N+1 arrives.
    """
    tools_dir = Path(__file__).resolve().parent.parent / "code_atlas" / "tools"
    emitters = sorted(
        module.stem
        for module in tools_dir.glob("*.py")
        if module.stem not in NOT_PAGED_EMITTERS
        and "total_count" in module.read_text(encoding="utf-8")
    )
    assert emitters, "the total_count scan emptied itself"
    assert emitters == sorted(TOTAL_COUNT_TOOLS)
