"""R3.4 live-adapter conformance: every adapter must pass the same schema + count harness.

Task 012 owns this matrix. Construct-level correctness stays in the PHP grammar tests (task 025);
`grammar.php` is deliberately not on this list (A1).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

from code_atlas import contract
from tests.php_adapter_cli import FIXTURES, needs_php, parse_file

# R6.2 named inventory (docs/ENGINEERING_RULES.md) — keys must match this set exactly.
R62_CASES = frozenset(
    {
        "namespaced",
        "global",
        "underscore-psr0",
        "trait-conflict",
        "enum",
        "attributes",
        "closures-arrow",
        "first-class-callable",
        "include",
        "static-vs-instance",
        "syntax-error",
    }
)

# filename + frozen kind histograms (None = syntax-error shape: ok=false, no nodes/edges keys).
# Histograms catch kind swaps that a bare len() cannot; frozen from a golden `--file` run.
CaseSpec = tuple[str, dict[str, int] | None, dict[str, int] | None]
CASES: dict[str, CaseSpec] = {
    "namespaced": (
        "namespaced.php",
        {
            "File": 1,
            "Namespace": 1,
            "Class": 1,
            "Interface": 1,
            "Trait": 1,
            "Enum": 1,
            "Function": 1,
            "Method": 5,
            "Property": 1,
            "ClassConst": 2,
        },
        {"CONTAINS": 14, "EXTENDS": 1, "IMPLEMENTS": 2, "IMPORTS": 1, "CALLS": 1, "NEW": 1},
    ),
    "global": (
        "global.php",
        {"File": 1, "Class": 1, "Function": 1, "Method": 1},
        {"CONTAINS": 3, "CALLS": 1, "NEW": 1},
    ),
    "underscore-psr0": (
        "underscore_psr0.php",
        {"File": 1, "Class": 1, "ClassConst": 1, "Property": 1, "Method": 1, "Function": 1},
        {"CONTAINS": 5, "EXTENDS": 1, "CALLS": 1, "NEW": 1},
    ),
    "trait-conflict": (
        "trait_conflict.php",
        {"File": 1, "Namespace": 1, "Trait": 2, "Class": 1, "Method": 2},
        {"CONTAINS": 6, "USES_TRAIT": 2},
    ),
    "enum": (
        "enum.php",
        {"File": 1, "Namespace": 1, "Enum": 2, "ClassConst": 3},
        {"CONTAINS": 6},
    ),
    "attributes": (
        "attributes.php",
        {
            "File": 1,
            "Namespace": 1,
            "Class": 2,
            "Enum": 1,
            "Function": 3,
            "Method": 2,
            "Property": 2,
            "ClassConst": 2,
        },
        {"CONTAINS": 13, "NEW": 1},
    ),
    "closures-arrow": (
        "closures_arrow.php",
        {"File": 1, "Namespace": 1, "Class": 1, "Method": 1, "Function": 2},
        {"CONTAINS": 5},
    ),
    # 3 CONTAINS only — strlen(...)/$this->bind(...) emit no CALLS today (025 gap).
    "first-class-callable": (
        "first_class_callable.php",
        {"File": 1, "Namespace": 1, "Class": 1, "Method": 1},
        {"CONTAINS": 3},
    ),
    "include": (
        "include_require.php",
        {"File": 1},
        {"INCLUDES": 2},
    ),
    "static-vs-instance": (
        "static_vs_instance.php",
        {"File": 1, "Namespace": 1, "Class": 1, "Method": 2},
        {"CONTAINS": 4, "CALLS": 5, "NEW": 2},
    ),
    "syntax-error": ("syntax_error.php", None, None),
}

# Meaning-frozen edge shapes (kind, target_raw, confidence_tier) — not just cardinality.
INCLUDE_EDGE_SHAPES = [
    ("INCLUDES", "Legacy/Registry.php", None),
    ("INCLUDES", "helpers.php", None),
]
STATIC_VS_INSTANCE_EDGE_SHAPES = [
    ("CALLS", "\\App\\Calls\\Service::make", None),
    ("CALLS", "\\App\\Calls\\Service::make", None),
    ("CALLS", "\\App\\Calls\\Service::make", None),
    ("CALLS", "\\App\\Calls\\Service::run", None),
    ("CALLS", "run", "HEURISTIC"),
    ("CONTAINS", "\\App\\Calls", None),
    ("CONTAINS", "\\App\\Calls\\Service", None),
    ("CONTAINS", "\\App\\Calls\\Service::make", None),
    ("CONTAINS", "\\App\\Calls\\Service::run", None),
    ("NEW", "\\App\\Calls\\Service", None),
    ("NEW", "\\self", None),
]


def kind_histogram(rows: list[dict[str, Any]], field: str = "kind") -> dict[str, int]:
    return dict(sorted(Counter(row[field] for row in rows).items()))


def edge_shapes(edges: list[dict[str, Any]]) -> list[tuple[str, Any, Any]]:
    return sorted((e["kind"], e.get("target_raw"), e.get("confidence_tier")) for e in edges)


def test_the_conformance_inventory_is_the_named_r62_set() -> None:
    assert set(CASES) == R62_CASES
    assert "grammar.php" not in {filename for filename, _, _ in CASES.values()}
    for filename, _, _ in CASES.values():
        assert (FIXTURES / filename).is_file(), filename


@needs_php
@pytest.mark.parametrize("case", sorted(CASES), ids=sorted(CASES))
def test_php_adapter_conforms(case: str) -> None:
    filename, expected_nodes, expected_edges = CASES[case]
    result = parse_file(f"tests/fixtures/php/{filename}")

    if expected_nodes is None:
        assert result["ok"] is False
        assert "error" in result and result["error"]
        assert "nodes" not in result and "edges" not in result
        return

    assert result["ok"] is True
    assert contract.validate(result) == []
    nodes = result["nodes"]
    edges = result["edges"]
    assert isinstance(nodes, list) and isinstance(edges, list)
    assert kind_histogram(nodes) == expected_nodes
    assert kind_histogram(edges) == expected_edges

    if case == "include":
        assert edge_shapes(edges) == INCLUDE_EDGE_SHAPES
    elif case == "static-vs-instance":
        assert edge_shapes(edges) == STATIC_VS_INSTANCE_EDGE_SHAPES
    elif case == "first-class-callable":
        # Pin the FCC gap: only CONTAINS today — a future CALLS emitter must bump deliberately.
        assert all(edge["kind"] == "CONTAINS" for edge in edges)
        assert not any(edge["kind"] == "CALLS" for edge in edges)
