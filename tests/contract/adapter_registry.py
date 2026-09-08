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
from tests.python_adapter_cli import CLI as PY_CLI
from tests.sql_adapter_cli import CLI as SQL_CLI
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
        "jsdoc-types",
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
# jsdoc-types: a `.js` file typed in JSDoc (task 154). `@typedef Point` is an Interface; `@param
# {Service}` types the receiver so `svc.handle()` resolves to Service::handle, like a `.ts` file.
_F_JSDOC = "jsdoc_types.js"
_TS_JSDOC_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", _tsq(_F_JSDOC, "run"), _tsq(_F_JSDOC, "Service::handle"), None),
    ("CONTAINS", _tsq(_F_JSDOC), _tsq(_F_JSDOC, "Point"), None),
    ("CONTAINS", _tsq(_F_JSDOC), _tsq(_F_JSDOC, "Service"), None),
    ("CONTAINS", _tsq(_F_JSDOC, "Service"), _tsq(_F_JSDOC, "Service::handle"), None),
    ("CONTAINS", _tsq(_F_JSDOC), _tsq(_F_JSDOC, "run"), None),
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
    "jsdoc-types": Case(
        "jsdoc_types.js",
        {"File": 1, "Class": 1, "Interface": 1, "Method": 1, "Function": 1},
        {"CONTAINS": 4, "CALLS": 1},
        _TS_JSDOC_EDGE_SHAPES,
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


# ── SQL (T-SQL, tier 1a) ─────────────────────────────────────────────────────────────────────────
# R6.2 named inventory (docs/ENGINEERING_RULES.md) — keys must match this set exactly. Three of the
# pairs are two spellings of ONE construct and both are cases, never one (claim 019-C2). There is no
# syntax-error case: a streaming scanner has no parse phase to fail.
SQL_R62_CASES = frozenset(
    {
        "create-procedure",
        "create-proc-abbrev",
        "create-or-alter",
        "create-function-scalar",
        "create-function-table-valued",
        "exec-call",
        "execute-spelling",
        "exec-with-params",
        "exec-dynamic",
        "batch-separator",
        "delimited-identifier",
        "string-literal-keyword",
        "comment-forms",
        # tier 2 (022) — table/column facts and the write sites over them. Four of the ten are a
        # second spelling of a construct already listed and are their own case, never folded in.
        "create-table",
        "table-constraint-not-a-column",
        "column-default-inline",
        "column-default-named-constraint",
        "alter-table-add-column",
        "insert-with-column-list",
        "insert-without-into",
        "insert-without-column-list",
        "update-set-list",
        "create-trigger",
    }
)

_F_BATCH = "tests/fixtures/sql/batch_separator.sql"
_F_DELIM = "tests/fixtures/sql/delimited_identifier.sql"
_F_DYN = "tests/fixtures/sql/exec_dynamic.sql"
_F_STRING = "tests/fixtures/sql/string_literal_keyword.sql"
_F_COMMENT = "tests/fixtures/sql/comment_forms.sql"
_F_NAMED_DEFAULT = "tests/fixtures/sql/column_default_named_constraint.sql"
_F_NO_COLS = "tests/fixtures/sql/insert_without_column_list.sql"
_F_TRIGGER = "tests/fixtures/sql/create_trigger.sql"

# A SQL object's qname is schema-qualified and file-independent — the database, not the file, is its
# container — which is what lets an EXEC in one file link to a proc declared in another.
_SQL_BATCH_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", "dbo.SecondBatch", "dbo.FirstBatch", "RESOLVED"),
    ("CONTAINS", _F_BATCH, "dbo.FirstBatch", "RESOLVED"),
    ("CONTAINS", _F_BATCH, "dbo.SecondBatch", "RESOLVED"),
]
_SQL_DELIM_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", "dbo.Spaced Name", "dbo.Other Name", "RESOLVED"),
    ("CALLS", "dbo.Spaced Name", "dbo.Quoted Name", "RESOLVED"),
    ("CONTAINS", _F_DELIM, "dbo.Spaced Name", "RESOLVED"),
]
# Every dynamic arm is emitted and none is RESOLVED (AC7): `EXEC (@sql)`, `sp_executesql`,
# `EXEC @var`.
_SQL_DYNAMIC_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", "dbo.DynamicCaller", "(dynamic)", "DYNAMIC"),
    ("CALLS", "dbo.DynamicCaller", "(dynamic)", "DYNAMIC"),
    ("CALLS", "dbo.DynamicCaller", "(dynamic)", "DYNAMIC"),
    ("CONTAINS", _F_DYN, "dbo.DynamicCaller", "RESOLVED"),
]
# The two cases that pin what must NOT become an edge: a keyword inside a string literal, and one
# inside every comment form. Both shipped red before the scanner dropped literal bodies (R6.5).
_SQL_STRING_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _F_STRING, "dbo.QuotesOnly", "RESOLVED"),
]
_SQL_COMMENT_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _F_COMMENT, "dbo.Commented", "RESOLVED"),
]

# The second DEFAULT spelling fills the column the CREATE already declared — one Column node with a
# default, never a second node for the same column (022 AC5).
_SQL_NAMED_DEFAULT_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _F_NAMED_DEFAULT, "dbo.Stamped", "RESOLVED"),
    ("CONTAINS", "dbo.Stamped", "dbo.Stamped::CreatedAt", "RESOLVED"),
]
# A writer that names no columns writes the TABLE, not a column of it. Silence here would read as
# "writes nothing", which is the answer R5.6 forbids (022 AC6).
_SQL_NO_COLS_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _F_NO_COLS, "dbo.CopyLedger", "RESOLVED"),
    ("WRITES", "dbo.CopyLedger", "dbo.Ledger", "RESOLVED"),
]
# A trigger is a writer, so it is a Function whose body emits WRITES like any other (022 AC4).
_SQL_TRIGGER_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _F_TRIGGER, "dbo.TR_Ledger", "RESOLVED"),
    ("WRITES", "dbo.TR_Ledger", "dbo.Ledger::ChangeUser", "RESOLVED"),
]

SQL_CASES: dict[str, Case] = {
    "create-procedure": Case("create_procedure.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1}),
    "create-proc-abbrev": Case(
        "create_proc_abbrev.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1}
    ),
    "create-or-alter": Case("create_or_alter.sql", {"File": 1, "Function": 2}, {"CONTAINS": 2}),
    "create-function-scalar": Case(
        "create_function_scalar.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1}
    ),
    "create-function-table-valued": Case(
        "create_function_table_valued.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1}
    ),
    "exec-call": Case("exec_call.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1, "CALLS": 1}),
    "execute-spelling": Case(
        "execute_spelling.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1, "CALLS": 1}
    ),
    "exec-with-params": Case(
        "exec_with_params.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1, "CALLS": 1}
    ),
    "exec-dynamic": Case(
        "exec_dynamic.sql",
        {"File": 1, "Function": 1},
        {"CONTAINS": 1, "CALLS": 3},
        _SQL_DYNAMIC_EDGE_SHAPES,
    ),
    "batch-separator": Case(
        "batch_separator.sql",
        {"File": 1, "Function": 2},
        {"CONTAINS": 2, "CALLS": 1},
        _SQL_BATCH_EDGE_SHAPES,
    ),
    "delimited-identifier": Case(
        "delimited_identifier.sql",
        {"File": 1, "Function": 1},
        {"CONTAINS": 1, "CALLS": 2},
        _SQL_DELIM_EDGE_SHAPES,
    ),
    "string-literal-keyword": Case(
        "string_literal_keyword.sql",
        {"File": 1, "Function": 1},
        {"CONTAINS": 1},
        _SQL_STRING_EDGE_SHAPES,
    ),
    "comment-forms": Case(
        "comment_forms.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1}, _SQL_COMMENT_EDGE_SHAPES
    ),
    "create-table": Case(
        "create_table.sql", {"File": 1, "Table": 1, "Column": 2}, {"CONTAINS": 3}
    ),
    "table-constraint-not-a-column": Case(
        "table_constraint_not_a_column.sql", {"File": 1, "Table": 1, "Column": 1}, {"CONTAINS": 2}
    ),
    "column-default-inline": Case(
        "column_default_inline.sql", {"File": 1, "Table": 1, "Column": 1}, {"CONTAINS": 2}
    ),
    "column-default-named-constraint": Case(
        "column_default_named_constraint.sql",
        {"File": 1, "Table": 1, "Column": 1},
        {"CONTAINS": 2},
        _SQL_NAMED_DEFAULT_EDGE_SHAPES,
    ),
    "alter-table-add-column": Case(
        "alter_table_add_column.sql", {"File": 1, "Table": 1, "Column": 1}, {"CONTAINS": 2}
    ),
    "insert-with-column-list": Case(
        "insert_with_column_list.sql",
        {"File": 1, "Function": 1},
        {"CONTAINS": 1, "WRITES": 2},
    ),
    "insert-without-into": Case(
        "insert_without_into.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1, "WRITES": 1}
    ),
    "insert-without-column-list": Case(
        "insert_without_column_list.sql",
        {"File": 1, "Function": 1},
        {"CONTAINS": 1, "WRITES": 1},
        _SQL_NO_COLS_EDGE_SHAPES,
    ),
    "update-set-list": Case(
        "update_set_list.sql", {"File": 1, "Function": 1}, {"CONTAINS": 1, "WRITES": 2}
    ),
    "create-trigger": Case(
        "create_trigger.sql",
        {"File": 1, "Function": 1},
        {"CONTAINS": 1, "WRITES": 1},
        _SQL_TRIGGER_EDGE_SHAPES,
    ),
}

SQL_CONFORMANCE = AdapterConformance(
    cli=SQL_CLI,
    named_inventory=SQL_R62_CASES,
    excluded_fixtures=frozenset(),
    cases=SQL_CASES,
)


# ── Python (task 020 tier 1a) ────────────────────────────────────────────────────────────────────
# N=16 construct inventory ratified at Gate 1.
# Zero new contract vocabulary; CONTRACT_VERSION stays 9.
PY_R62_CASES = frozenset(
    {
        "module",
        "package-init",
        "class-inheritance",
        "class-multiple-inheritance",
        "method-kinds",
        "async-def",
        "nested-function",
        "import-plain",
        "import-from",
        "import-alias",
        "import-relative",
        "call-function",
        "call-method",
        "instantiation",
        "module-const",
        "syntax-error",
        "protocol-abc",
        "enum-class",
        "decorator-references",
        "annotation-references",
    }
)


def _pyq(fixture: str) -> str:
    """Repo-relative path of a Python fixture (File qname)."""
    return f"tests/fixtures/python/{fixture}"


def _pymod(fixture: str) -> str:
    """Dotted module name for a fixture path under ``tests/fixtures/python/``."""
    base = f"tests/fixtures/python/{fixture}"
    if base.endswith("/__init__.py"):
        return base[: -len("/__init__.py")].replace("/", ".")
    if base.endswith(".py"):
        return base[: -len(".py")].replace("/", ".")
    return base.replace("/", ".")


_PY_MODULE_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", f"{_pymod('module.py')}.make_greeter", f"{_pymod('module.py')}.Greeter", None),
    ("CONTAINS", _pyq("module.py"), f"{_pymod('module.py')}.Greeter", None),
    ("CONTAINS", f"{_pymod('module.py')}.Greeter", f"{_pymod('module.py')}.Greeter::greet", None),
    ("CONTAINS", _pyq("module.py"), f"{_pymod('module.py')}.make_greeter", None),
    (
        "REFERENCES",
        f"{_pymod('module.py')}.make_greeter",
        f"{_pymod('module.py')}.Greeter",
        None,
    ),
]
_PY_PACKAGE_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _pyq("pkg/__init__.py"), _pymod("pkg/__init__.py"), None),
]
_PY_INHERIT_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _pyq("class_inheritance.py"), f"{_pymod('class_inheritance.py')}.Animal", None),
    (
        "CONTAINS",
        f"{_pymod('class_inheritance.py')}.Animal",
        f"{_pymod('class_inheritance.py')}.Animal::speak",
        None,
    ),
    ("CONTAINS", _pyq("class_inheritance.py"), f"{_pymod('class_inheritance.py')}.Dog", None),
    (
        "CONTAINS",
        f"{_pymod('class_inheritance.py')}.Dog",
        f"{_pymod('class_inheritance.py')}.Dog::speak",
        None,
    ),
    (
        "EXTENDS",
        f"{_pymod('class_inheritance.py')}.Dog",
        f"{_pymod('class_inheritance.py')}.Animal",
        None,
    ),
]
_M = "class_multiple_inheritance.py"
_PY_MULTI_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _pyq(_M), f"{_pymod(_M)}.ReadWriter", None),
    ("CONTAINS", f"{_pymod(_M)}.ReadWriter", f"{_pymod(_M)}.ReadWriter::flush", None),
    ("CONTAINS", _pyq(_M), f"{_pymod(_M)}.Readable", None),
    ("CONTAINS", f"{_pymod(_M)}.Readable", f"{_pymod(_M)}.Readable::read", None),
    ("CONTAINS", _pyq(_M), f"{_pymod(_M)}.Writable", None),
    ("CONTAINS", f"{_pymod(_M)}.Writable", f"{_pymod(_M)}.Writable::write", None),
    ("EXTENDS", f"{_pymod(_M)}.ReadWriter", f"{_pymod(_M)}.Readable", None),
    ("EXTENDS", f"{_pymod(_M)}.ReadWriter", f"{_pymod(_M)}.Writable", None),
]
_PY_IMPORT_ALIAS_EDGE_SHAPES: list[EdgeShape] = [
    (
        "ALIASES",
        f"{_pymod('import_alias.py')}.tm",
        _pymod("resolve/target_mod.py"),
        None,
    ),
    (
        "ALIASES",
        f"{_pymod('import_alias.py')}.help_fn",
        f"{_pymod('resolve/target_mod.py')}.helper",
        None,
    ),
    ("IMPORTS", _pyq("import_alias.py"), _pyq("resolve/target_mod.py"), None),
    ("IMPORTS", _pyq("import_alias.py"), _pyq("resolve/target_mod.py"), None),
]
_PY_IMPORT_REL_EDGE_SHAPES: list[EdgeShape] = [
    (
        "IMPORTS",
        _pyq("nest/deep/import_relative.py"),
        _pyq("nest/deep/x.py"),
        None,
    ),
    (
        "IMPORTS",
        _pyq("nest/deep/import_relative.py"),
        _pyq("nest/pkg/__init__.py"),
        None,
    ),
]
_PY_CALL_METHOD_EDGE_SHAPES: list[EdgeShape] = [
    (
        "CALLS",
        f"{_pymod('call_method.py')}.Child::hook",
        f"{_pymod('call_method.py')}.Base::hook",
        None,
    ),
    (
        "CALLS",
        f"{_pymod('call_method.py')}.Child::run",
        f"{_pymod('call_method.py')}.Child::hook",
        None,
    ),
    # 227: annotated receiver ``obj: Child`` promotes ``obj.hook()`` off HEURISTIC.
    (
        "CALLS",
        f"{_pymod('call_method.py')}.call_on",
        f"{_pymod('call_method.py')}.Child::hook",
        None,
    ),
    ("CONTAINS", _pyq("call_method.py"), f"{_pymod('call_method.py')}.Base", None),
    (
        "CONTAINS",
        f"{_pymod('call_method.py')}.Base",
        f"{_pymod('call_method.py')}.Base::hook",
        None,
    ),
    ("CONTAINS", _pyq("call_method.py"), f"{_pymod('call_method.py')}.Child", None),
    (
        "CONTAINS",
        f"{_pymod('call_method.py')}.Child",
        f"{_pymod('call_method.py')}.Child::hook",
        None,
    ),
    (
        "CONTAINS",
        f"{_pymod('call_method.py')}.Child",
        f"{_pymod('call_method.py')}.Child::run",
        None,
    ),
    ("CONTAINS", _pyq("call_method.py"), f"{_pymod('call_method.py')}.call_on", None),
    (
        "EXTENDS",
        f"{_pymod('call_method.py')}.Child",
        f"{_pymod('call_method.py')}.Base",
        None,
    ),
    (
        "REFERENCES",
        f"{_pymod('call_method.py')}.call_on",
        f"{_pymod('call_method.py')}.Child",
        None,
    ),
]
_P = "protocol_abc.py"
_PY_PROTOCOL_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _pyq(_P), f"{_pymod(_P)}.Circle", None),
    ("CONTAINS", f"{_pymod(_P)}.Circle", f"{_pymod(_P)}.Circle::draw", None),
    ("CONTAINS", _pyq(_P), f"{_pymod(_P)}.Drawable", None),
    ("CONTAINS", f"{_pymod(_P)}.Drawable", f"{_pymod(_P)}.Drawable::draw", None),
    ("CONTAINS", _pyq(_P), f"{_pymod(_P)}.Shape", None),
    ("CONTAINS", f"{_pymod(_P)}.Shape", f"{_pymod(_P)}.Shape::area", None),
    ("CONTAINS", _pyq(_P), f"{_pymod(_P)}.Square", None),
    ("CONTAINS", f"{_pymod(_P)}.Square", f"{_pymod(_P)}.Square::area", None),
    ("IMPLEMENTS", f"{_pymod(_P)}.Shape", "ABC", None),
    ("IMPLEMENTS", f"{_pymod(_P)}.Drawable", "Protocol", None),
    ("IMPLEMENTS", f"{_pymod(_P)}.Circle", f"{_pymod(_P)}.Drawable", None),
    ("IMPLEMENTS", f"{_pymod(_P)}.Square", f"{_pymod(_P)}.Shape", None),
    ("IMPORTS", _pyq(_P), "abc", None),
    ("IMPORTS", _pyq(_P), "typing", None),
    ("REFERENCES", f"{_pymod(_P)}.Shape::area", "abstractmethod", None),
]
_E = "enum_class.py"
_PY_ENUM_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _pyq(_E), f"{_pymod(_E)}.Color", None),
    ("CONTAINS", f"{_pymod(_E)}.Color", f"{_pymod(_E)}.Color::BLUE", None),
    ("CONTAINS", f"{_pymod(_E)}.Color", f"{_pymod(_E)}.Color::RED", None),
    ("EXTENDS", f"{_pymod(_E)}.Color", "Enum", None),
    ("IMPORTS", _pyq(_E), "enum", None),
]
_D = "decorator_references.py"
_PY_DECORATOR_EDGE_SHAPES: list[EdgeShape] = [
    ("CONTAINS", _pyq(_D), f"{_pymod(_D)}.Service", None),
    ("CONTAINS", f"{_pymod(_D)}.Service", f"{_pymod(_D)}.Service::run", None),
    ("CONTAINS", f"{_pymod(_D)}.Service", f"{_pymod(_D)}.Service::util", None),
    ("CONTAINS", _pyq(_D), f"{_pymod(_D)}.audit", None),
    ("CONTAINS", f"{_pymod(_D)}.audit", f"{_pymod(_D)}.audit::wrap", None),
    ("CONTAINS", _pyq(_D), f"{_pymod(_D)}.audited", None),
    ("CONTAINS", _pyq(_D), f"{_pymod(_D)}.guard", None),
    ("CONTAINS", _pyq(_D), f"{_pymod(_D)}.handler", None),
    ("REFERENCES", f"{_pymod(_D)}.audited", f"{_pymod(_D)}.audit", None),
    ("REFERENCES", f"{_pymod(_D)}.Service::run", f"{_pymod(_D)}.guard", None),
    ("REFERENCES", f"{_pymod(_D)}.handler", f"{_pymod(_D)}.guard", None),
]
_A = "annotation_references.py"
_PY_ANNOTATION_EDGE_SHAPES: list[EdgeShape] = [
    ("CALLS", f"{_pymod(_A)}.Repo::get", f"{_pymod(_A)}.User", None),
    ("CONTAINS", _pyq(_A), f"{_pymod(_A)}.Repo", None),
    ("CONTAINS", f"{_pymod(_A)}.Repo", f"{_pymod(_A)}.Repo::find", None),
    ("CONTAINS", f"{_pymod(_A)}.Repo", f"{_pymod(_A)}.Repo::get", None),
    ("CONTAINS", f"{_pymod(_A)}.Repo", f"{_pymod(_A)}.Repo::merge", None),
    ("CONTAINS", f"{_pymod(_A)}.Repo", f"{_pymod(_A)}.Repo::owner", None),
    ("CONTAINS", f"{_pymod(_A)}.Repo", f"{_pymod(_A)}.Repo::tag", None),
    ("CONTAINS", _pyq(_A), f"{_pymod(_A)}.User", None),
    ("IMPORTS", _pyq(_A), "typing", None),
    ("REFERENCES", f"{_pymod(_A)}.Repo::merge", f"{_pymod(_A)}.Repo", None),
    ("REFERENCES", f"{_pymod(_A)}.Repo::find", f"{_pymod(_A)}.User", None),
    ("REFERENCES", f"{_pymod(_A)}.Repo::get", f"{_pymod(_A)}.User", None),
    ("REFERENCES", f"{_pymod(_A)}.Repo::merge", f"{_pymod(_A)}.User", None),
    ("REFERENCES", f"{_pymod(_A)}.Repo::merge", f"{_pymod(_A)}.User", None),
    ("REFERENCES", f"{_pymod(_A)}.Repo::merge", f"{_pymod(_A)}.User", None),
    ("REFERENCES", f"{_pymod(_A)}.Repo::owner", f"{_pymod(_A)}.User", None),
]

PY_CASES: dict[str, Case] = {
    "module": Case(
        "module.py",
        {"Class": 1, "File": 1, "Function": 1, "Method": 1},
        {"CALLS": 1, "CONTAINS": 3, "REFERENCES": 1},
        _PY_MODULE_EDGE_SHAPES,
    ),
    "package-init": Case(
        "pkg/__init__.py",
        {"File": 1, "Namespace": 1},
        {"CONTAINS": 1},
        _PY_PACKAGE_EDGE_SHAPES,
    ),
    "class-inheritance": Case(
        "class_inheritance.py",
        {"Class": 2, "File": 1, "Method": 2},
        {"CONTAINS": 4, "EXTENDS": 1},
        _PY_INHERIT_EDGE_SHAPES,
    ),
    "class-multiple-inheritance": Case(
        "class_multiple_inheritance.py",
        {"Class": 3, "File": 1, "Method": 3},
        {"CONTAINS": 6, "EXTENDS": 2},
        _PY_MULTI_EDGE_SHAPES,
    ),
    "method-kinds": Case(
        "method_kinds.py",
        {"Class": 1, "File": 1, "Method": 4},
        {"CONTAINS": 5},
    ),
    "async-def": Case(
        "async_def.py",
        {"Class": 1, "File": 1, "Function": 1, "Method": 1},
        {"CALLS": 1, "CONTAINS": 3},
    ),
    "nested-function": Case(
        "nested_function.py",
        {"File": 1, "Function": 2},
        {"CALLS": 1, "CONTAINS": 2},
    ),
    "import-plain": Case(
        "import_plain.py",
        {"File": 1},
        {"IMPORTS": 1},
        [
            ("IMPORTS", _pyq("import_plain.py"), _pyq("resolve/target_mod.py"), None),
        ],
    ),
    "import-from": Case(
        "import_from.py",
        {"File": 1},
        {"IMPORTS": 1},
        [
            ("IMPORTS", _pyq("import_from.py"), _pyq("resolve/target_mod.py"), None),
        ],
    ),
    "import-alias": Case(
        "import_alias.py",
        {"File": 1},
        {"ALIASES": 2, "IMPORTS": 2},
        _PY_IMPORT_ALIAS_EDGE_SHAPES,
    ),
    "import-relative": Case(
        "nest/deep/import_relative.py",
        {"File": 1},
        {"IMPORTS": 2},
        _PY_IMPORT_REL_EDGE_SHAPES,
    ),
    "call-function": Case(
        "call_function.py",
        {"File": 1, "Function": 2},
        {"CALLS": 1, "CONTAINS": 2},
    ),
    "call-method": Case(
        "call_method.py",
        {"Class": 2, "File": 1, "Function": 1, "Method": 3},
        {"CALLS": 3, "CONTAINS": 6, "EXTENDS": 1, "REFERENCES": 1},
        _PY_CALL_METHOD_EDGE_SHAPES,
    ),
    "instantiation": Case(
        "instantiation.py",
        {"Class": 1, "File": 1, "Function": 1, "Method": 1},
        {"CALLS": 1, "CONTAINS": 3, "REFERENCES": 1},
        [
            (
                "CALLS",
                f"{_pymod('instantiation.py')}.make",
                f"{_pymod('instantiation.py')}.Box",
                None,
            ),
            ("CONTAINS", _pyq("instantiation.py"), f"{_pymod('instantiation.py')}.Box", None),
            (
                "CONTAINS",
                f"{_pymod('instantiation.py')}.Box",
                f"{_pymod('instantiation.py')}.Box::__init__",
                None,
            ),
            ("CONTAINS", _pyq("instantiation.py"), f"{_pymod('instantiation.py')}.make", None),
            (
                "REFERENCES",
                f"{_pymod('instantiation.py')}.make",
                f"{_pymod('instantiation.py')}.Box",
                None,
            ),
        ],
    ),
    "module-const": Case(
        "module_const.py",
        {"Class": 1, "Const": 1, "File": 1, "Property": 1},
        {"CONTAINS": 3},
    ),
    "syntax-error": Case("syntax_error.py", None, None),
    "protocol-abc": Case(
        "protocol_abc.py",
        {"Class": 2, "File": 1, "Interface": 2, "Method": 4},
        {"CONTAINS": 8, "IMPLEMENTS": 4, "IMPORTS": 2, "REFERENCES": 1},
        _PY_PROTOCOL_EDGE_SHAPES,
    ),
    "enum-class": Case(
        "enum_class.py",
        {"Enum": 1, "File": 1, "Property": 2},
        {"CONTAINS": 3, "EXTENDS": 1, "IMPORTS": 1},
        _PY_ENUM_EDGE_SHAPES,
    ),
    "decorator-references": Case(
        "decorator_references.py",
        {"Class": 1, "File": 1, "Function": 5, "Method": 2},
        {"CONTAINS": 8, "REFERENCES": 3},
        _PY_DECORATOR_EDGE_SHAPES,
    ),
    "annotation-references": Case(
        "annotation_references.py",
        {"Class": 2, "File": 1, "Method": 3, "Property": 2},
        {"CALLS": 1, "CONTAINS": 7, "IMPORTS": 1, "REFERENCES": 7},
        _PY_ANNOTATION_EDGE_SHAPES,
    ),
}

PY_CONFORMANCE = AdapterConformance(
    cli=PY_CLI,
    named_inventory=PY_R62_CASES,
    excluded_fixtures=frozenset(
        {
            "resolve/__init__.py",
            "resolve/target_mod.py",
            "nest/deep/__init__.py",
            "nest/deep/x.py",
            "nest/pkg/__init__.py",
            "nest/pkg/y.py",
        }
    ),
    cases=PY_CASES,
)


# ── registry ─────────────────────────────────────────────────────────────────────────────────────
# Keyed by adapter directory name — a 2nd adapter is a new entry here + its fixtures.
REGISTRY: dict[str, AdapterConformance] = {
    PHP_CONFORMANCE.cli.name: PHP_CONFORMANCE,
    TS_CONFORMANCE.cli.name: TS_CONFORMANCE,
    SQL_CONFORMANCE.cli.name: SQL_CONFORMANCE,
    PY_CONFORMANCE.cli.name: PY_CONFORMANCE,
}
