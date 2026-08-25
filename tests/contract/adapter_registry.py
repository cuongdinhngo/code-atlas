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
from tests.ts_adapter_cli import CLI as TS_CLI

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


# ── TypeScript/JavaScript (task 128 M0 spike) ──────────────────────────────────────────────────
# Two of 149's named inventory — the pair 128 AC1 asks for. The other 11 constructs are 019's.
TS_R62_CASES = frozenset({"module-esm", "namespace-declare"})

# Q1 evidence: `::` holds through namespace nesting (Geometry::Circle::area), never TS's `.`.
_TS_NAMESPACE_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", "tests/fixtures/typescript/namespaced.ts::Geometry", None),
    ("CONTAINS", "tests/fixtures/typescript/namespaced.ts::Geometry::Circle", None),
    ("CONTAINS", "tests/fixtures/typescript/namespaced.ts::Geometry::Circle::area", None),
    ("CONTAINS", "tests/fixtures/typescript/namespaced.ts::Geometry::Circle::radius", None),
    ("CONTAINS", "tests/fixtures/typescript/namespaced.ts::Geometry::Shape", None),
    ("CONTAINS", "tests/fixtures/typescript/namespaced.ts::Geometry::Shape::area", None),
    ("CONTAINS", "tests/fixtures/typescript/namespaced.ts::Geometry::Square", None),
    ("CONTAINS", "tests/fixtures/typescript/namespaced.ts::Geometry::Square::area", None),
    ("EXTENDS", "tests/fixtures/typescript/namespaced.ts::Geometry::Circle", None),
    ("IMPLEMENTS", "tests/fixtures/typescript/namespaced.ts::Geometry::Shape", None),
]
# Q2 evidence: a same-file target earns its full qname (NEW → ::User, CALLS → ::User::describe)
# while an imported one stays bare (NEW → Logger, CALLS → log, IMPORTS → ./logger), so the core
# resolver — not a TS Program — links it. The bare `log` also guards the CALLS-emits-unresolved fix.
_TS_MODULE_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", "log", None),
    ("CALLS", "tests/fixtures/typescript/module_scoped.ts::User::describe", None),
    ("CONTAINS", "tests/fixtures/typescript/module_scoped.ts::Greeter", None),
    ("CONTAINS", "tests/fixtures/typescript/module_scoped.ts::Greeter::greet", None),
    ("CONTAINS", "tests/fixtures/typescript/module_scoped.ts::User", None),
    ("CONTAINS", "tests/fixtures/typescript/module_scoped.ts::User::describe", None),
    ("CONTAINS", "tests/fixtures/typescript/module_scoped.ts::User::greet", None),
    ("CONTAINS", "tests/fixtures/typescript/module_scoped.ts::User::name", None),
    ("CONTAINS", "tests/fixtures/typescript/module_scoped.ts::makeUser", None),
    ("IMPLEMENTS", "tests/fixtures/typescript/module_scoped.ts::Greeter", None),
    ("IMPORTS", "./logger", None),
    ("NEW", "Logger", None),
    ("NEW", "tests/fixtures/typescript/module_scoped.ts::User", None),
]

TS_CASES: dict[str, Case] = {
    "module-esm": Case(
        "module_scoped.ts",
        {"File": 1, "Interface": 1, "Class": 1, "Property": 1, "Method": 3, "Function": 1},
        {"IMPORTS": 1, "CONTAINS": 7, "IMPLEMENTS": 1, "CALLS": 2, "NEW": 2},
        _TS_MODULE_EDGE_SHAPES,
    ),
    "namespace-declare": Case(
        "namespaced.ts",
        {"File": 1, "Namespace": 1, "Interface": 1, "Class": 2, "Property": 1, "Method": 3},
        {"CONTAINS": 8, "EXTENDS": 1, "IMPLEMENTS": 1},
        _TS_NAMESPACE_EDGE_SHAPES,
    ),
}

TS_CONFORMANCE = AdapterConformance(
    cli=TS_CLI,
    named_inventory=TS_R62_CASES,
    excluded_fixtures=frozenset(),
    cases=TS_CASES,
)


# ── registry ─────────────────────────────────────────────────────────────────────────────────────
# Keyed by adapter directory name — a 2nd adapter is a new entry here + its fixtures.
REGISTRY: dict[str, AdapterConformance] = {
    PHP_CONFORMANCE.cli.name: PHP_CONFORMANCE,
    TS_CONFORMANCE.cli.name: TS_CONFORMANCE,
}
