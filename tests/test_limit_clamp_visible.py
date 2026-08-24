"""Task 066: a clamped ``limit`` is reported (``limit_capped_to``), uniformly across tools.

Proving path is integration: seed a store, then call the real tools — the layer where a caller
who asked for 30 and silently got 10 would be misled. A source-scan guard keeps a *new* tool
from taking ``limit`` without the signal.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import Config, clamp_limit, load_config
from code_atlas.store import GraphStore
from code_atlas.tools import (
    file_outline,
    find_callers,
    find_implementations,
    find_orphans,
    find_references,
    find_view_data,
    get_index_status,
    search_symbol,
)

CEILING = 3
NROWS = 10  # > CEILING so every tool truncates and clamps a generous limit
PATH = "app/w.php"
REPO = Path(__file__).resolve().parent.parent


def _config(tmp_path: Path) -> Config:
    return replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        max_results=CEILING,
        entry_points=("entry.php",),
    )


def _seed(tmp_path: Path) -> None:
    """Plant enough nodes/edges that all five tools have > CEILING results for one subject."""
    path = "app/w.php"
    on_disk = tmp_path / path
    on_disk.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    on_disk.write_bytes(body)
    nodes = [
        {
            "kind": "Function",
            "name": f"Widget{i}",
            "qualified_name": f"\\Widget{i}",
            "file_path": path,
            "line_start": i + 1,
        }
        for i in range(NROWS)
    ]
    edges: list[dict[str, object]] = []
    for i in range(NROWS):
        edges.append(_edge("CALLS", f"\\Widget{i}", "call", path, target="\\T"))
        edges.append(_edge("EXTENDS", f"\\Sub{i}", "ext", path, target="\\Base"))
        edges.append(
            _edge(contract.PROVIDES_VIEW_DATA, "\\H", f"viewdata:k{i}", path, tier="HEURISTIC")
        )
    with GraphStore(tmp_path / "graph.db") as store:
        store.upsert_file("entry.php", hashlib.sha256(body).hexdigest(), "php")
        store.replace_file_rows(
            "entry.php",
            [
                {
                    "kind": "Function",
                    "name": "main",
                    "qualified_name": "\\Entry\\main",
                    "file_path": "entry.php",
                    "line_start": 1,
                }
            ],
            [],
        )
        store.upsert_file(path, hashlib.sha256(body).hexdigest(), "php")
        store.replace_file_rows(path, nodes, edges)


def _edge(
    kind: str, source: str, target_raw: str, path: str, *, target: str | None = None,
    tier: str = "RESOLVED",
) -> dict[str, object]:
    row: dict[str, object] = {
        "kind": kind,
        "source_qname": source,
        "target_raw": target_raw,
        "file_path": path,
        "line": 1,
        "confidence_tier": tier,
    }
    if target is not None:
        row["target_qname"] = target
    return row


def _call(name: str, config: Config, limit: int | None) -> dict[str, object]:
    if name == "file_outline":
        return file_outline.create(config)(PATH, limit=limit, detail_level="minimal")
    if name == "find_orphans":
        return find_orphans.create(config)(limit=limit, detail_level="minimal")
    if name == "find_callers":
        return find_callers.create(config)("\\T", limit=limit, detail_level="minimal")
    if name == "find_references":
        return find_references.create(config)("\\T", limit=limit, detail_level="minimal")
    if name == "find_implementations":
        return find_implementations.create(config)("\\Base", limit=limit, detail_level="minimal")
    if name == "find_view_data":
        return find_view_data.create(config)("\\H", limit=limit, detail_level="minimal")
    if name == "search_symbol":
        return search_symbol.create(config)("Widget", limit=limit, detail_level="minimal")
    raise AssertionError(name)


TOOLS = [
    "file_outline",
    "find_orphans",
    "find_callers",
    "find_references",
    "find_implementations",
    "find_view_data",
    "search_symbol",
]


@pytest.mark.parametrize("tool", TOOLS)
def test_clamp_reported_uniformly_across_tools(tmp_path: Path, tool: str) -> None:
    """Proving test: `limit` above the ceiling reports `limit_capped_to` on every tool."""
    _seed(tmp_path)
    result = _call(tool, _config(tmp_path), CEILING + 5)
    assert result["limit_capped_to"] == CEILING
    assert len(result["results"]) == CEILING
    # Deterministic: a second identical call yields the same payload (R4/C1).
    assert _call(tool, _config(tmp_path), CEILING + 5) == result


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("limit", [None, CEILING, CEILING - 1])
def test_no_field_when_request_is_honoured(
    tmp_path: Path, tool: str, limit: int | None
) -> None:
    """AC2 / C2: `limit` at or below the ceiling (or unset) leaves the payload without the field."""
    _seed(tmp_path)
    result = _call(tool, _config(tmp_path), limit)
    assert "limit_capped_to" not in result


def test_status_reports_max_results_and_double_duty(tmp_path: Path) -> None:
    """AC4: the ceiling and its double duty are discoverable from `get_index_status`."""
    _seed(tmp_path)
    status = get_index_status.create(_config(tmp_path), TOOLS)(detail_level="standard")
    assert status["max_results"] == {
        "value": CEILING,
        "governs": ["returned_rows", "resolver_candidate_fanout"],
    }
    minimal = get_index_status.create(_config(tmp_path), TOOLS)(detail_level="minimal")
    assert "max_results" not in minimal  # minimal stays the cheap path


def test_clamp_limit_helper_is_pure() -> None:
    """C1: the clamp is a deterministic function of (limit, ceiling)."""
    assert clamp_limit(None, 10) == (10, False)
    assert clamp_limit(5, 10) == (5, False)
    assert clamp_limit(10, 10) == (10, False)
    assert clamp_limit(30, 10) == (10, True)


def test_no_limit_taking_tool_opts_out_of_the_signal() -> None:
    """AC3: any tool exposing a user `limit` must route through both clamp helpers.

    Source-scan (no import) so a *new* tool with `limit: int | None` cannot ship without the
    signal — the exact "holds for five tools and not the sixth" failure the ticket names.
    """
    offenders: list[str] = []
    covered: list[str] = []
    for module in sorted((REPO / "code_atlas" / "tools").glob("*.py")):
        src = module.read_text(encoding="utf-8")
        if "limit: int | None" not in src:
            continue
        covered.append(module.name)
        if "clamp_limit(" not in src or "attach_limit_capped(" not in src:
            offenders.append(module.name)
    assert not offenders, f"limit-taking tools missing the clamp signal: {offenders}"
    assert len(covered) == 9  # eight prior limit-taking tools + check_architecture_rules (138)
