"""The registered adapters, as data (task 147, AC2/AC3).

Adding an adapter is a **row here plus fixtures** — never an edit to the conformance module body.
Registration is keyed by adapter **directory name**, so nothing branches on a language (R1.1), and
the valid set is derived from this table, never re-listed (R6.7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tests.adapter_cli import AdapterCli
from tests.php_adapter_cli import CLI as PHP_CLI

# filename + frozen kind histograms (None node-hist = syntax-error shape: ok=false, no nodes/edges).
# Optional exact_edge_shapes pins meaning (kind, target_raw, confidence_tier), not just cardinality.
EdgeShape = tuple[str, Any, Any]


@dataclass(frozen=True)
class Case:
    filename: str
    nodes: dict[str, int] | None
    edges: dict[str, int] | None
    exact_edge_shapes: list[EdgeShape] | None = None


@dataclass(frozen=True)
class AdapterConformance:
    cli: AdapterCli
    named_inventory: frozenset[str]  # R6.2 named inventory — case keys must equal this set
    excluded_fixtures: frozenset[str]  # fixtures that must never be a conformance case
    cases: dict[str, Case] = field(default_factory=dict)


# ── PHP ──────────────────────────────────────────────────────────────────────────────────────────
# R6.2 named inventory (docs/ENGINEERING_RULES.md) — keys must match this set exactly.
PHP_R62_CASES = frozenset(
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

# Meaning-frozen edge shapes (kind, target_raw, confidence_tier) — not just cardinality.
_INCLUDE_EDGE_SHAPES: list[EdgeShape] = [
    ("INCLUDES", "Legacy/Registry.php", None),
    ("INCLUDES", "helpers.php", None),
]
_STATIC_VS_INSTANCE_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", "\\App\\Calls\\Service::make", None),
    ("CALLS", "\\App\\Calls\\Service::make", None),
    ("CALLS", "\\App\\Calls\\Service::make", "HEURISTIC"),  # static:: late binding
    ("CALLS", "\\App\\Calls\\Service::run", None),
    ("CALLS", "\\App\\Calls\\Service::run", None),  # `$other = new Service()` (137)
    ("CONTAINS", "\\App\\Calls", None),
    ("CONTAINS", "\\App\\Calls\\Service", None),
    ("CONTAINS", "\\App\\Calls\\Service::make", None),
    ("CONTAINS", "\\App\\Calls\\Service::run", None),
    ("NEW", "\\App\\Calls\\Service", None),
    ("NEW", "\\self", None),
]

PHP_CASES: dict[str, Case] = {
    "namespaced": Case(
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
    "global": Case(
        "global.php",
        {"File": 1, "Class": 1, "Function": 1, "Method": 1},
        {"CONTAINS": 3, "CALLS": 1, "NEW": 1},
    ),
    "underscore-psr0": Case(
        "underscore_psr0.php",
        {"File": 1, "Class": 1, "ClassConst": 1, "Property": 1, "Method": 1, "Function": 1},
        {"CONTAINS": 5, "EXTENDS": 1, "CALLS": 1, "NEW": 1},
    ),
    "trait-conflict": Case(
        "trait_conflict.php",
        {"File": 1, "Namespace": 1, "Trait": 2, "Class": 1, "Method": 2},
        {"CONTAINS": 6, "USES_TRAIT": 2},
    ),
    "enum": Case(
        "enum.php",
        {"File": 1, "Namespace": 1, "Enum": 2, "ClassConst": 3},
        {"CONTAINS": 6},
    ),
    "attributes": Case(
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
    "closures-arrow": Case(
        "closures_arrow.php",
        {"File": 1, "Namespace": 1, "Class": 1, "Method": 1, "Function": 2},
        {"CONTAINS": 5},
    ),
    # 3 CONTAINS only — strlen(...)/$this->bind(...) emit no CALLS today (025 gap). The histogram's
    # absent CALLS key already pins "no CALLS", so no exact_edge_shapes is needed to hold that gap.
    "first-class-callable": Case(
        "first_class_callable.php",
        {"File": 1, "Namespace": 1, "Class": 1, "Method": 1},
        {"CONTAINS": 3},
    ),
    "include": Case(
        "include_require.php",
        {"File": 1},
        {"INCLUDES": 2},
        _INCLUDE_EDGE_SHAPES,
    ),
    "static-vs-instance": Case(
        "static_vs_instance.php",
        {"File": 1, "Namespace": 1, "Class": 1, "Method": 2},
        {"CONTAINS": 4, "CALLS": 5, "NEW": 2},
        _STATIC_VS_INSTANCE_EDGE_SHAPES,
    ),
    "syntax-error": Case("syntax_error.php", None, None),
}

PHP_CONFORMANCE = AdapterConformance(
    cli=PHP_CLI,
    named_inventory=PHP_R62_CASES,
    excluded_fixtures=frozenset({"grammar.php"}),  # 025 owns it; never a conformance case
    cases=PHP_CASES,
)


# ── registry ─────────────────────────────────────────────────────────────────────────────────────
# Keyed by adapter directory name — a 2nd adapter is a new entry here + its fixtures.
REGISTRY: dict[str, AdapterConformance] = {
    PHP_CONFORMANCE.cli.name: PHP_CONFORMANCE,
}
