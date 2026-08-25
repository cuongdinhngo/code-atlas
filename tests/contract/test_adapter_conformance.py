"""R3.4 live-adapter conformance: every registered adapter passes the same schema + count harness.

Task 012 owns this matrix; task 147 made it a per-adapter matrix. The cases, histograms and named
inventory live as **data** in ``adapter_registry.py`` — adding an adapter is a row there plus its
fixtures, never an edit to this module's body (AC2). Construct-level correctness stays in each
adapter's grammar tests; excluded fixtures (PHP's ``grammar.php``) are declared in the registry.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

from code_atlas import contract
from tests.contract.adapter_registry import REGISTRY


def kind_histogram(rows: list[dict[str, Any]], field: str = "kind") -> dict[str, int]:
    return dict(sorted(Counter(row[field] for row in rows).items()))


def edge_shapes(edges: list[dict[str, Any]]) -> list[tuple[str, Any, Any]]:
    # None tiers sort before named ones when kind+raw collide (e.g. self:: vs static::).
    return sorted(
        ((e["kind"], e.get("target_raw"), e.get("confidence_tier")) for e in edges),
        key=lambda t: (t[0], str(t[1]), t[2] is not None, str(t[2] or "")),
    )


def _conformance_params() -> list[Any]:
    params: list[Any] = []
    for name in sorted(REGISTRY):
        adapter = REGISTRY[name]
        for case in sorted(adapter.cases):
            params.append(
                pytest.param(name, case, id=f"{name}:{case}", marks=adapter.cli.availability)
            )
    return params


def test_the_registry_is_non_empty() -> None:
    # R6.5 guard-the-guard: an empty matrix must FAIL, never read as "every adapter conforms".
    assert REGISTRY, "no adapters registered — the conformance matrix would be vacuously green"


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_the_conformance_inventory_is_the_named_set(name: str) -> None:
    adapter = REGISTRY[name]
    assert set(adapter.cases) == adapter.named_inventory
    filenames = {spec.filename for spec in adapter.cases.values()}
    assert filenames.isdisjoint(adapter.excluded_fixtures)
    for spec in adapter.cases.values():
        assert (adapter.cli.fixtures_dir / spec.filename).is_file(), spec.filename


@pytest.mark.parametrize("name, case", _conformance_params())
def test_adapter_conforms(name: str, case: str) -> None:
    adapter = REGISTRY[name]
    spec = adapter.cases[case]
    relative = (adapter.cli.fixtures_dir / spec.filename).relative_to(adapter.cli.root)

    if spec.nodes is None:
        result = adapter.cli.parse_file(relative)  # syntax-error shape emits one line too
        assert result["ok"] is False
        assert "error" in result and result["error"]
        assert "nodes" not in result and "edges" not in result
        return

    result = adapter.cli.parse_file(relative)
    assert result["ok"] is True
    assert contract.validate(result) == []
    nodes = result["nodes"]
    edges = result["edges"]
    assert isinstance(nodes, list) and isinstance(edges, list)
    assert kind_histogram(nodes) == spec.nodes
    assert kind_histogram(edges) == spec.edges

    if spec.exact_edge_shapes is not None:
        assert edge_shapes(edges) == spec.exact_edge_shapes
