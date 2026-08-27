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
# exact_edge_shapes pins meaning (kind, source_qname, target_raw, confidence_tier), not cardinality.
EdgeShape = tuple[str, Any, Any, Any]


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

# Meaning-frozen edge shapes (kind, source_qname, target_raw, confidence_tier) — not cardinality.
_INCLUDE_EDGE_SHAPES: list[EdgeShape] = [
    ("INCLUDES", "tests/fixtures/php/include_require.php", "Legacy/Registry.php", None),
    ("INCLUDES", "tests/fixtures/php/include_require.php", "helpers.php", None),
]
_STATIC_VS_INSTANCE_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", "\\App\\Calls\\Service::run", "\\App\\Calls\\Service::make", None),
    ("CALLS", "\\App\\Calls\\Service::run", "\\App\\Calls\\Service::make", None),
    # static:: late binding
    ("CALLS", "\\App\\Calls\\Service::run", "\\App\\Calls\\Service::make", "HEURISTIC"),
    ("CALLS", "\\App\\Calls\\Service::run", "\\App\\Calls\\Service::run", None),
    # `$other = new Service()` (137)
    ("CALLS", "\\App\\Calls\\Service::run", "\\App\\Calls\\Service::run", None),
    ("CONTAINS", "tests/fixtures/php/static_vs_instance.php", "\\App\\Calls", None),
    ("CONTAINS", "\\App\\Calls", "\\App\\Calls\\Service", None),
    ("CONTAINS", "\\App\\Calls\\Service", "\\App\\Calls\\Service::make", None),
    ("CONTAINS", "\\App\\Calls\\Service", "\\App\\Calls\\Service::run", None),
    ("NEW", "\\App\\Calls\\Service::run", "\\App\\Calls\\Service", None),
    ("NEW", "\\App\\Calls\\Service::make", "\\self", None),
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


# ── TypeScript/JavaScript (task 128 spike, task 019 adapter) ────────────────────────────────────
# 149's full 13-construct named inventory. module-cjs and re-export-barrel resolve their specifiers
# to a real file, so their target_raw names the defining module (the core links it RESOLVED).
TS_R62_CASES = frozenset(
    {
        "module-esm",
        "module-cjs",
        "namespace-declare",
        "class-heritage",
        "interface-type-alias",
        "enum-const-enum",
        "generics",
        "decorators",
        "arrow-closure",
        "default-export",
        "default-export-named",
        "re-export-barrel",
        "jsx",
        "syntax-error",
    }
)


def _tsq(fixture: str, suffix: str = "") -> str:
    """A TS fixture's file qname or a `::`-joined member qname — keeps frozen shapes typo-proof."""
    base = f"tests/fixtures/typescript/{fixture}"
    return f"{base}::{suffix}" if suffix else base


# Q1 evidence: `::` holds through namespace nesting (Geometry::Circle::area), never TS's `.`.
_F_NS = "namespaced.ts"
_TS_NAMESPACE_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _tsq(_F_NS), _tsq(_F_NS, "Geometry"), None),
    ("CONTAINS", _tsq(_F_NS, "Geometry"), _tsq(_F_NS, "Geometry::Circle"), None),
    ("CONTAINS", _tsq(_F_NS, "Geometry::Circle"), _tsq(_F_NS, "Geometry::Circle::area"), None),
    ("CONTAINS", _tsq(_F_NS, "Geometry::Circle"), _tsq(_F_NS, "Geometry::Circle::radius"), None),
    ("CONTAINS", _tsq(_F_NS, "Geometry"), _tsq(_F_NS, "Geometry::Shape"), None),
    ("CONTAINS", _tsq(_F_NS, "Geometry::Shape"), _tsq(_F_NS, "Geometry::Shape::area"), None),
    ("CONTAINS", _tsq(_F_NS, "Geometry"), _tsq(_F_NS, "Geometry::Square"), None),
    ("CONTAINS", _tsq(_F_NS, "Geometry::Square"), _tsq(_F_NS, "Geometry::Square::area"), None),
    ("EXTENDS", _tsq(_F_NS, "Geometry::Square"), _tsq(_F_NS, "Geometry::Circle"), None),
    ("IMPLEMENTS", _tsq(_F_NS, "Geometry::Circle"), _tsq(_F_NS, "Geometry::Shape"), None),
]
# Q2 evidence: a same-file target earns its full qname (NEW → ::User, CALLS → ::User::describe)
# while an imported one stays bare (NEW → Logger, CALLS → log, IMPORTS → ./logger), so the core
# resolver — not a TS Program — links it. The bare `log` also guards the CALLS-emits-unresolved fix,
# and `created.greet()` guards its member-branch twin: name only, so the adapter claims HEURISTIC.
_F_ESM = "module_scoped.ts"
_TS_MODULE_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", _tsq(_F_ESM, "makeUser"), "log", None),
    ("CALLS", _tsq(_F_ESM, "User::greet"), _tsq(_F_ESM, "User::describe"), None),
    # `const created = new User(); created.greet()` -> User::greet, RESOLVED via the table (153).
    ("CALLS", _tsq(_F_ESM, "makeUser"), _tsq(_F_ESM, "User::greet"), None),
    ("CONTAINS", _tsq(_F_ESM), _tsq(_F_ESM, "Greeter"), None),
    ("CONTAINS", _tsq(_F_ESM, "Greeter"), _tsq(_F_ESM, "Greeter::greet"), None),
    ("CONTAINS", _tsq(_F_ESM), _tsq(_F_ESM, "User"), None),
    ("CONTAINS", _tsq(_F_ESM, "User"), _tsq(_F_ESM, "User::describe"), None),
    ("CONTAINS", _tsq(_F_ESM, "User"), _tsq(_F_ESM, "User::greet"), None),
    ("CONTAINS", _tsq(_F_ESM, "User"), _tsq(_F_ESM, "User::name"), None),
    ("CONTAINS", _tsq(_F_ESM), _tsq(_F_ESM, "makeUser"), None),
    ("IMPLEMENTS", _tsq(_F_ESM, "User"), _tsq(_F_ESM, "Greeter"), None),
    ("IMPORTS", _tsq(_F_ESM), "./logger", None),
    ("NEW", _tsq(_F_ESM, "makeUser"), "Logger", None),
    ("NEW", _tsq(_F_ESM, "makeUser"), _tsq(_F_ESM, "User"), None),
]

# class-heritage: same-file supertypes resolve to their qname (Q3 — EXTENDS/IMPLEMENTS suffice).
_F_HERITAGE = "class_heritage.ts"
_TS_HERITAGE_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _tsq(_F_HERITAGE), _tsq(_F_HERITAGE, "Circle"), None),
    ("CONTAINS", _tsq(_F_HERITAGE, "Circle"), _tsq(_F_HERITAGE, "Circle::draw"), None),
    ("CONTAINS", _tsq(_F_HERITAGE), _tsq(_F_HERITAGE, "Drawable"), None),
    ("CONTAINS", _tsq(_F_HERITAGE, "Drawable"), _tsq(_F_HERITAGE, "Drawable::draw"), None),
    ("CONTAINS", _tsq(_F_HERITAGE), _tsq(_F_HERITAGE, "Shape"), None),
    ("CONTAINS", _tsq(_F_HERITAGE, "Shape"), _tsq(_F_HERITAGE, "Shape::draw"), None),
    ("EXTENDS", _tsq(_F_HERITAGE, "Circle"), _tsq(_F_HERITAGE, "Shape"), None),
    ("IMPLEMENTS", _tsq(_F_HERITAGE, "Circle"), _tsq(_F_HERITAGE, "Drawable"), None),
    ("IMPLEMENTS", _tsq(_F_HERITAGE, "Shape"), _tsq(_F_HERITAGE, "Drawable"), None),
]
# interface-type-alias: a `type` alias is an Interface node, qnamed like a member (Q3, no new kind).
_F_ALIAS = "interface_type_alias.ts"
_TS_TYPE_ALIAS_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _tsq(_F_ALIAS), _tsq(_F_ALIAS, "Id"), None),
    ("CONTAINS", _tsq(_F_ALIAS), _tsq(_F_ALIAS, "Point"), None),
    ("CONTAINS", _tsq(_F_ALIAS, "Point"), _tsq(_F_ALIAS, "Point::x"), None),
    ("CONTAINS", _tsq(_F_ALIAS, "Point"), _tsq(_F_ALIAS, "Point::y"), None),
    ("CONTAINS", _tsq(_F_ALIAS), _tsq(_F_ALIAS, "Vector"), None),
]
# enum-const-enum: both reuse Enum + ClassConst members; `const enum` differs only in node extra.
_F_ENUM = "enum_const_enum.ts"
_TS_ENUM_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _tsq(_F_ENUM), _tsq(_F_ENUM, "Color"), None),
    ("CONTAINS", _tsq(_F_ENUM, "Color"), _tsq(_F_ENUM, "Color::Blue"), None),
    ("CONTAINS", _tsq(_F_ENUM, "Color"), _tsq(_F_ENUM, "Color::Green"), None),
    ("CONTAINS", _tsq(_F_ENUM, "Color"), _tsq(_F_ENUM, "Color::Red"), None),
    ("CONTAINS", _tsq(_F_ENUM), _tsq(_F_ENUM, "Direction"), None),
    ("CONTAINS", _tsq(_F_ENUM, "Direction"), _tsq(_F_ENUM, "Direction::Down"), None),
    ("CONTAINS", _tsq(_F_ENUM, "Direction"), _tsq(_F_ENUM, "Direction::Up"), None),
]
# generics: a qname carries no type params — `Box`, not `Box<T>` (Q1).
_F_GENERICS = "generics.ts"
_TS_GENERICS_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _tsq(_F_GENERICS), _tsq(_F_GENERICS, "Box"), None),
    ("CONTAINS", _tsq(_F_GENERICS, "Box"), _tsq(_F_GENERICS, "Box::get"), None),
    ("CONTAINS", _tsq(_F_GENERICS, "Box"), _tsq(_F_GENERICS, "Box::value"), None),
    ("CONTAINS", _tsq(_F_GENERICS), _tsq(_F_GENERICS, "identity"), None),
]
# decorators: annotate a declaration → no edge (mirrors PHP attributes); the factory `@log()` is not
# a CALLS. The imported decorator library is the only IMPORTS.
_F_DECO = "decorators.ts"
_TS_DECORATORS_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _tsq(_F_DECO), _tsq(_F_DECO, "Widget"), None),
    ("CONTAINS", _tsq(_F_DECO, "Widget"), _tsq(_F_DECO, "Widget::render"), None),
    ("CONTAINS", _tsq(_F_DECO, "Widget"), _tsq(_F_DECO, "Widget::title"), None),
    ("IMPORTS", _tsq(_F_DECO), "./decorators-lib", None),
]
# arrow-closure: a name-bound arrow/function is a named Function; a field arrow stays a Property; an
# inline callback gets no node (Q1).
_F_ARROW = "arrow_closure.ts"
_TS_ARROW_EDGE_SHAPES: list[EdgeShape] = [
    # `[1, 2].forEach(cb)` is a method call like any other: name known, receiver not (HEURISTIC).
    ("CALLS", _tsq(_F_ARROW, "run"), "forEach", "HEURISTIC"),
    ("CONTAINS", _tsq(_F_ARROW), _tsq(_F_ARROW, "Handlers"), None),
    ("CONTAINS", _tsq(_F_ARROW, "Handlers"), _tsq(_F_ARROW, "Handlers::onClick"), None),
    ("CONTAINS", _tsq(_F_ARROW), _tsq(_F_ARROW, "add"), None),
    ("CONTAINS", _tsq(_F_ARROW), _tsq(_F_ARROW, "greet"), None),
    ("CONTAINS", _tsq(_F_ARROW), _tsq(_F_ARROW, "run"), None),
]
# default-export: an unnamed default is qnamed `::default`; a module-scoped `const` is a Const (Q1).
_F_DEFAULT = "default_export.ts"
_TS_DEFAULT_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _tsq(_F_DEFAULT), _tsq(_F_DEFAULT, "default"), None),
    ("CONTAINS", _tsq(_F_DEFAULT), _tsq(_F_DEFAULT, "helper"), None),
    ("CONTAINS", _tsq(_F_DEFAULT), _tsq(_F_DEFAULT, "version"), None),
]
# module-cjs: a `require("./x")` specifier resolves to the file on disk, so `new Service()` targets
# the defining module's qname — the RESOLVED win, for CommonJS as well as ESM (Q2).
_F_CJS = "module_cjs.ts"
_TS_CJS_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _tsq(_F_CJS), _tsq(_F_CJS, "boot"), None),
    ("IMPORTS", _tsq(_F_CJS), _tsq("cjs_service.js"), None),
    ("NEW", _tsq(_F_CJS, "boot"), _tsq("cjs_service.js", "Service"), None),
]
# default-export-named: `export default class Foo {}` keeps its own name; an ALIASES ::default ->
# ::Foo reaches it so a default-import resolves (019 finding). One default per file -> own fixture.
_F_DEFAULT_NAMED = "default_export_named.ts"
_TS_DEFAULT_NAMED_EDGE_SHAPES: list[EdgeShape] = [
    ("ALIASES", _tsq(_F_DEFAULT_NAMED, "default"), _tsq(_F_DEFAULT_NAMED, "Widget"), None),
    ("CONTAINS", _tsq(_F_DEFAULT_NAMED), _tsq(_F_DEFAULT_NAMED, "Widget"), None),
    ("CONTAINS", _tsq(_F_DEFAULT_NAMED, "Widget"), _tsq(_F_DEFAULT_NAMED, "Widget::render"), None),
    ("CONTAINS", _tsq(_F_DEFAULT_NAMED), _tsq(_F_DEFAULT_NAMED, "helper"), None),
]
# re-export-barrel: a named re-export ALIASES to the *defining* module (Q2, load-bearing). An
# `export *` cannot enumerate names file-at-a-time, so it emits only the module dep (IMPORTS).
_F_BARREL = "reexport_barrel.ts"
_TS_REEXPORT_EDGE_SHAPES: list[EdgeShape] = [
    ("ALIASES", _tsq(_F_BARREL, "Button"), _tsq("widgets.ts", "Button"), None),
    ("ALIASES", _tsq(_F_BARREL, "Dialog"), _tsq("widgets.ts", "Modal"), None),
    ("IMPORTS", _tsq(_F_BARREL), _tsq("more_widgets.ts"), None),
    ("IMPORTS", _tsq(_F_BARREL), _tsq("widgets.ts"), None),
    ("IMPORTS", _tsq(_F_BARREL), _tsq("widgets.ts"), None),
]
# jsx: a JSX element is not a call (no spurious edge); `this.method()` in JSX still resolves (Q3).
_F_JSX = "jsx.tsx"
_TS_JSX_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", _tsq(_F_JSX, "Panel::render"), _tsq(_F_JSX, "Panel::title"), None),
    ("CONTAINS", _tsq(_F_JSX), _tsq(_F_JSX, "App"), None),
    ("CONTAINS", _tsq(_F_JSX), _tsq(_F_JSX, "Panel"), None),
    ("CONTAINS", _tsq(_F_JSX, "Panel"), _tsq(_F_JSX, "Panel::render"), None),
    ("CONTAINS", _tsq(_F_JSX, "Panel"), _tsq(_F_JSX, "Panel::title"), None),
    ("IMPORTS", _tsq(_F_JSX), "./ui", None),
]

TS_CASES: dict[str, Case] = {
    "module-esm": Case(
        "module_scoped.ts",
        {"File": 1, "Interface": 1, "Class": 1, "Property": 1, "Method": 3, "Function": 1},
        {"IMPORTS": 1, "CONTAINS": 7, "IMPLEMENTS": 1, "CALLS": 3, "NEW": 2},
        _TS_MODULE_EDGE_SHAPES,
    ),
    "namespace-declare": Case(
        "namespaced.ts",
        {"File": 1, "Namespace": 1, "Interface": 1, "Class": 2, "Property": 1, "Method": 3},
        {"CONTAINS": 8, "EXTENDS": 1, "IMPLEMENTS": 1},
        _TS_NAMESPACE_EDGE_SHAPES,
    ),
    "class-heritage": Case(
        "class_heritage.ts",
        {"File": 1, "Interface": 1, "Class": 2, "Method": 3},
        {"CONTAINS": 6, "EXTENDS": 1, "IMPLEMENTS": 2},
        _TS_HERITAGE_EDGE_SHAPES,
    ),
    "interface-type-alias": Case(
        "interface_type_alias.ts",
        {"File": 1, "Interface": 3, "Property": 2},
        {"CONTAINS": 5},
        _TS_TYPE_ALIAS_EDGE_SHAPES,
    ),
    "enum-const-enum": Case(
        "enum_const_enum.ts",
        {"File": 1, "Enum": 2, "ClassConst": 5},
        {"CONTAINS": 7},
        _TS_ENUM_EDGE_SHAPES,
    ),
    "generics": Case(
        "generics.ts",
        {"File": 1, "Class": 1, "Property": 1, "Method": 1, "Function": 1},
        {"CONTAINS": 4},
        _TS_GENERICS_EDGE_SHAPES,
    ),
    "decorators": Case(
        "decorators.ts",
        {"File": 1, "Class": 1, "Property": 1, "Method": 1},
        {"IMPORTS": 1, "CONTAINS": 3},
        _TS_DECORATORS_EDGE_SHAPES,
    ),
    "arrow-closure": Case(
        "arrow_closure.ts",
        {"File": 1, "Function": 3, "Class": 1, "Property": 1},
        {"CONTAINS": 5, "CALLS": 1},
        _TS_ARROW_EDGE_SHAPES,
    ),
    "default-export": Case(
        "default_export.ts",
        {"File": 1, "Const": 1, "Function": 2},
        {"CONTAINS": 3},
        _TS_DEFAULT_EDGE_SHAPES,
    ),
    "default-export-named": Case(
        "default_export_named.ts",
        {"File": 1, "Class": 1, "Method": 1, "Function": 1},
        {"CONTAINS": 3, "ALIASES": 1},
        _TS_DEFAULT_NAMED_EDGE_SHAPES,
    ),
    "jsx": Case(
        "jsx.tsx",
        {"File": 1, "Function": 1, "Class": 1, "Method": 2},
        {"IMPORTS": 1, "CONTAINS": 4, "CALLS": 1},
        _TS_JSX_EDGE_SHAPES,
    ),
    "module-cjs": Case(
        "module_cjs.ts",
        {"File": 1, "Function": 1},
        {"IMPORTS": 1, "CONTAINS": 1, "NEW": 1},
        _TS_CJS_EDGE_SHAPES,
    ),
    "re-export-barrel": Case(
        "reexport_barrel.ts",
        {"File": 1},
        {"IMPORTS": 3, "ALIASES": 2},
        _TS_REEXPORT_EDGE_SHAPES,
    ),
    "syntax-error": Case("syntax_error.ts", None, None),
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
