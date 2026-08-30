"""The cross-language tool-parity matrix, as data (task 185).

One layer above `adapter_registry.py`: 147 proved that every registered adapter *emits* the same
contract; this proves that every one of `main.py`'s `TOOL_NAMES` has a **declared, checked** answer
over each adapter's own graph. Adding a language is a row in `PARITY` plus its fixtures — never an
edit to `test_tool_parity.py`'s body (147 AC2 is the precedent).

Parity is **the declared state matching**, never byte equality: two languages legitimately answer
differently, and the point is that the difference is written down and verified rather than assumed.

A test may name a language — tests are not the core (R1.1). The `code_atlas/` grep-gate is unmoved.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from code_atlas.config import Config
from code_atlas.tools import (
    architecture_overview,
    build_or_update_index,
    check_architecture_rules,
    check_column_defaults,
    class_diagram,
    diff_architecture,
    explain_path,
    file_outline,
    find_callers,
    find_implementations,
    find_orphans,
    find_references,
    find_view_data,
    generate_onboarding,
    get_index_status,
    guided_tour,
    impact,
    impact_modules,
    include_graph,
    reachable_from,
    read_symbol,
    search_symbol,
    subtree_dependencies,
)
from tests.adapter_cli import AdapterCli
from tests.php_adapter_cli import CLI as PHP_CLI
from tests.sql_adapter_cli import CLI as SQL_CLI
from tests.ts_adapter_cli import CLI as TS_CLI

# ── the state vocabulary, one definition site (R6.7) ────────────────────────────────────────────
# Five states, because "empty" has four distinguishable causes and today's payload collapses them.
# 186 owns turning EMPTY_RELATION_NOT_MODELLED into something the payload itself can say.
ANSWERS = "answers"
ANSWERS_WITHOUT = "answers_without"
EMPTY_RELATION_NOT_MODELLED = "empty_relation_not_modelled"
NOT_APPLICABLE_BY_LANGUAGE = "not_applicable_by_language"
EMPTY_CAPABILITY_NOT_CONFIGURED = "empty_capability_not_configured"

STATES: frozenset[str] = frozenset(
    {
        ANSWERS,
        ANSWERS_WITHOUT,
        EMPTY_RELATION_NOT_MODELLED,
        NOT_APPLICABLE_BY_LANGUAGE,
        EMPTY_CAPABILITY_NOT_CONFIGURED,
    }
)
# States whose obligation is an EMPTY principal collection.
EMPTY_STATES: frozenset[str] = frozenset(
    {EMPTY_RELATION_NOT_MODELLED, NOT_APPLICABLE_BY_LANGUAGE, EMPTY_CAPABILITY_NOT_CONFIGURED}
)


@dataclass(frozen=True)
class Expect:
    """One (adapter, tool) cell. Every field carries a checkable obligation, not a comment.

    ``kinds`` — edge kinds this tool reads that must be ABSENT from this language's graph
    (asserted for ``empty_relation_not_modelled`` and for ``answers_without``).
    ``because`` — required for ``not_applicable_by_language``: the language feature that does not
    exist. ``reason`` — the payload's own word for why it is empty; **required** for
    ``empty_capability_not_configured`` and for ``empty_relation_not_modelled`` (186 gave the latter
    one), so neither cell can be confused with the other or with a genuine zero.
    """

    state: str
    kinds: tuple[str, ...] = ()
    because: str = ""
    reason: str = ""


@dataclass(frozen=True)
class Invoker:
    """How to call one tool, and which payload key answering means. Language-independent."""

    call: Callable[[Config, Mapping[str, Any], tuple[str, ...]], dict[str, object]]
    answer_key: str


@dataclass(frozen=True)
class ToolParity:
    """One language's column: how to reach its graph, what to ask, and what each tool must do."""

    cli: AdapterCli
    globs: tuple[str, ...]
    adapter_cmd: tuple[str, ...]
    entry_points: str
    subjects: dict[str, str]
    tools: dict[str, Expect] = field(default_factory=dict)


# ── how each tool is called, once, for every language (adding a LANGUAGE never touches this) ─────
INVOKERS: dict[str, Invoker] = {
    get_index_status.NAME: Invoker(
        lambda c, s, n: get_index_status.create(c, n)(detail_level="verbose"), "edge_health"
    ),
    build_or_update_index.NAME: Invoker(
        lambda c, s, n: build_or_update_index.create(c)(), "graph"
    ),
    search_symbol.NAME: Invoker(
        lambda c, s, n: search_symbol.create(c)(query=s["query"]), "results"
    ),
    check_column_defaults.NAME: Invoker(
        lambda c, s, n: check_column_defaults.create(c)(table=s["table"]), "results"
    ),
    file_outline.NAME: Invoker(lambda c, s, n: file_outline.create(c)(path=s["path"]), "results"),
    read_symbol.NAME: Invoker(lambda c, s, n: read_symbol.create(c)(qname=s["method"]), "source"),
    find_callers.NAME: Invoker(
        lambda c, s, n: find_callers.create(c)(qname=s["callee"]), "results"
    ),
    find_references.NAME: Invoker(
        lambda c, s, n: find_references.create(c)(qname=s["class"]), "results"
    ),
    find_implementations.NAME: Invoker(
        lambda c, s, n: find_implementations.create(c)(qname=s["interface"]), "results"
    ),
    find_view_data.NAME: Invoker(
        lambda c, s, n: find_view_data.create(c)(qname=s["method"]), "results"
    ),
    include_graph.NAME: Invoker(
        lambda c, s, n: include_graph.create(c)(path=s["path"]), "results"
    ),
    impact.NAME: Invoker(lambda c, s, n: impact.create(c)(qnames=[s["class"]]), "results"),
    impact_modules.NAME: Invoker(
        lambda c, s, n: impact_modules.create(c)(qnames=[s["class"]]), "results"
    ),
    subtree_dependencies.NAME: Invoker(
        lambda c, s, n: subtree_dependencies.create(c)(subtree=s["subtree"]), "outbound"
    ),
    reachable_from.NAME: Invoker(lambda c, s, n: reachable_from.create(c)(), "results"),
    find_orphans.NAME: Invoker(lambda c, s, n: find_orphans.create(c)(), "results"),
    explain_path.NAME: Invoker(
        lambda c, s, n: explain_path.create(c)(from_qname=s["caller"], to_qname=s["callee"]),
        "path",
    ),
    architecture_overview.NAME: Invoker(
        lambda c, s, n: architecture_overview.create(c)(), "results"
    ),
    guided_tour.NAME: Invoker(lambda c, s, n: guided_tour.create(c)(), "results"),
    generate_onboarding.NAME: Invoker(
        lambda c, s, n: generate_onboarding.create(c)(), "results"
    ),
    check_architecture_rules.NAME: Invoker(
        lambda c, s, n: check_architecture_rules.create(c)(), "results"
    ),
    diff_architecture.NAME: Invoker(
        lambda c, s, n: diff_architecture.create(c)(before=s["subtree"], after=s["subtree"]),
        "results",
    ),
    class_diagram.NAME: Invoker(
        lambda c, s, n: class_diagram.create(c)(qname=s["class"]), "results"
    ),
}

# ── the three cells that are the same for every language, so they are written once ───────────────
# Each names the payload's OWN word for the missing configuration. These are NOT language gaps:
# no adapter can make them answer, and flipping a config switch makes every language answer.
_VIEW_DATA = Expect(
    EMPTY_CAPABILITY_NOT_CONFIGURED,
    reason="capability_not_configured",
    because="PROVIDES_VIEW_DATA is produced by enrichment rules, never by any adapter",
)
_ARCH_RULES = Expect(
    EMPTY_CAPABILITY_NOT_CONFIGURED,
    reason="capability_not_configured",
    because="needs an architecture-rules file; language-independent",
)
# A language with no table declarations has no subject for this tool at all — which is a different
# fact from a relation the adapter could emit and does not (022 spends `Table`/`Column`/`WRITES`,
# and only a SQL layer produces them).
_COLUMN_DEFAULTS_ABSENT = Expect(
    NOT_APPLICABLE_BY_LANGUAGE,
    kinds=("WRITES",),
    because="the language declares no tables or columns, so no subject of this tool exists in it",
)
_DIFF_ARCH = Expect(
    EMPTY_CAPABILITY_NOT_CONFIGURED,
    reason="snapshot_not_found",
    because="needs two committed snapshots; language-independent",
)


def _answering(*names: str) -> dict[str, Expect]:
    return {name: Expect(ANSWERS) for name in names}


# ── PHP ─────────────────────────────────────────────────────────────────────────────────────────
PHP_PARITY = ToolParity(
    cli=PHP_CLI,
    globs=("*.php",),
    adapter_cmd=(),  # filled by the harness from the CLI's entry argv
    entry_points="src/static_vs_instance.php",
    subjects={
        "query": "Service",
        "path": "src/include_require.php",
        "class": "\\App\\Calls\\Service",
        "method": "\\App\\Calls\\Service::run",
        "caller": "\\App\\Calls\\Service::run",
        "callee": "\\App\\Calls\\Service::make",
        "interface": "\\App\\Models\\Storable",
        "subtree": "src",
        "table": "\\App\\Calls\\Service",
    },
    tools={
        **_answering(
            get_index_status.NAME,
            build_or_update_index.NAME,
            search_symbol.NAME,
            file_outline.NAME,
            read_symbol.NAME,
            find_callers.NAME,
            find_references.NAME,
            find_implementations.NAME,
            include_graph.NAME,
            impact.NAME,
            impact_modules.NAME,
            subtree_dependencies.NAME,
            reachable_from.NAME,
            find_orphans.NAME,
            explain_path.NAME,
            architecture_overview.NAME,
            guided_tour.NAME,
            generate_onboarding.NAME,
            class_diagram.NAME,
        ),
        find_view_data.NAME: _VIEW_DATA,
        check_architecture_rules.NAME: _ARCH_RULES,
        check_column_defaults.NAME: _COLUMN_DEFAULTS_ABSENT,
        diff_architecture.NAME: _DIFF_ARCH,
    },
)

# ── TypeScript/JavaScript ───────────────────────────────────────────────────────────────────────
TS_PARITY = ToolParity(
    cli=TS_CLI,
    globs=("*.ts", "*.tsx", "*.js"),
    adapter_cmd=(),
    entry_points="src/module_scoped.ts",
    subjects={
        "query": "User",
        "path": "src/module_scoped.ts",
        "class": "src/module_scoped.ts::User",
        "method": "src/module_scoped.ts::User::greet",
        "caller": "src/module_scoped.ts::makeUser",
        "table": "src/module_scoped.ts::User",
        "callee": "src/module_scoped.ts::User::greet",
        "interface": "src/class_heritage.ts::Drawable",
        "subtree": "src",
    },
    tools={
        **_answering(
            get_index_status.NAME,
            build_or_update_index.NAME,
            search_symbol.NAME,
            file_outline.NAME,
            read_symbol.NAME,
            find_callers.NAME,
            impact.NAME,
            impact_modules.NAME,
            reachable_from.NAME,
            find_orphans.NAME,
            explain_path.NAME,
            architecture_overview.NAME,
            guided_tour.NAME,
            generate_onboarding.NAME,
        ),
        # The gap the ticket was filed on, and the only tool that goes EMPTY for a language reason:
        # `include_graph` reads INCLUDES, which TS has no construct for — a module `import` is an
        # IMPORTS edge and a different relation. 186 owns making the payload say this.
        include_graph.NAME: Expect(
            EMPTY_RELATION_NOT_MODELLED,
            kinds=("INCLUDES",),
            because="TS/JS has no textual include; a module specifier is IMPORTS, not INCLUDES",
            # 186 made this state observable in the payload rather than only in this matrix.
            reason="relation_unmodelled_for_language",
        ),
        # Answers, but narrower than PHP's: the relation is missing a kind this adapter never emits.
        find_references.NAME: Expect(
            ANSWERS_WITHOUT,
            kinds=("REFERENCES",),
            because="no `Foo::class`-style bare type mention exists in TS/JS",
        ),
        find_implementations.NAME: Expect(
            ANSWERS_WITHOUT,
            kinds=("USES_TRAIT",),
            because="TypeScript has no traits; heritage is EXTENDS/IMPLEMENTS only",
        ),
        class_diagram.NAME: Expect(
            ANSWERS_WITHOUT,
            kinds=("USES_TRAIT",),
            because="TypeScript has no traits, so no class carries a trait row",
        ),
        subtree_dependencies.NAME: Expect(
            ANSWERS_WITHOUT,
            kinds=("INCLUDES",),
            because="crossings come from IMPORTS/CALLS/NEW; TS emits no INCLUDES to cross on",
        ),
        find_view_data.NAME: _VIEW_DATA,
        check_architecture_rules.NAME: _ARCH_RULES,
        check_column_defaults.NAME: _COLUMN_DEFAULTS_ABSENT,
        diff_architecture.NAME: _DIFF_ARCH,
    },
)


# ── T-SQL (tier 1a) ─────────────────────────────────────────────────────────────────────────────
# The narrowest surface of the three, and deliberately so: tier 1a emits `Function` nodes and
# CONTAINS/CALLS edges and nothing else, so every relation built on a kind it never emits is EMPTY
# here BY DECLARATION rather than by accident. A SQL object's qname is schema-qualified and
# file-independent (`dbo.Caller`), which is why a caller in one file reaches a callee in another.
SQL_PARITY = ToolParity(
    cli=SQL_CLI,
    globs=("*.sql",),
    adapter_cmd=(),
    entry_points="src/exec_call.sql",
    subjects={
        "query": "Caller",
        "path": "src/exec_call.sql",
        "class": "dbo.Caller",
        "method": "dbo.Caller",
        "caller": "dbo.SecondBatch",
        "callee": "dbo.FirstBatch",
        "interface": "dbo.Caller",
        "subtree": "src",
        # The one fixture table that declares a DEFAULT; nothing writes it, which is the
        # `table_has_no_writers` arm answering rather than a modelled zero.
        "table": "dbo.Audit",
    },
    tools={
        **_answering(
            get_index_status.NAME,
            build_or_update_index.NAME,
            search_symbol.NAME,
            file_outline.NAME,
            read_symbol.NAME,
            find_callers.NAME,
            impact.NAME,
            impact_modules.NAME,
            reachable_from.NAME,
            find_orphans.NAME,
            explain_path.NAME,
            architecture_overview.NAME,
            guided_tour.NAME,
            generate_onboarding.NAME,
            check_column_defaults.NAME,
        ),
        include_graph.NAME: Expect(
            EMPTY_RELATION_NOT_MODELLED,
            kinds=("INCLUDES",),
            because="T-SQL has no textual include; a proc reaches another by EXEC, which is CALLS",
            reason="relation_unmodelled_for_language",
        ),
        # Measured, not assumed: 186's per-language census DOES fire here. SQL emits neither of
        # the kinds `find_references` reads, so the payload says so rather than a confident zero.
        find_references.NAME: Expect(
            EMPTY_RELATION_NOT_MODELLED,
            kinds=("REFERENCES", "IMPORTS"),
            because="tier 1a emits neither a bare type mention nor a module dependency",
            reason="relation_unmodelled_for_language",
        ),
        find_implementations.NAME: Expect(
            NOT_APPLICABLE_BY_LANGUAGE,
            kinds=("EXTENDS", "IMPLEMENTS", "USES_TRAIT"),
            because="T-SQL has no inheritance of any kind; there is no heritage relation to answer",
        ),
        class_diagram.NAME: Expect(
            NOT_APPLICABLE_BY_LANGUAGE,
            kinds=("EXTENDS", "IMPLEMENTS", "USES_TRAIT"),
            because="tier 1a emits no Class node, so there is no box to draw",
        ),
        subtree_dependencies.NAME: Expect(
            ANSWERS_WITHOUT,
            kinds=("INCLUDES",),
            because="crossings come from CALLS alone; tier 1a emits no INCLUDES to cross on",
        ),
        find_view_data.NAME: _VIEW_DATA,
        check_architecture_rules.NAME: _ARCH_RULES,
        diff_architecture.NAME: _DIFF_ARCH,
    },
)

# ── the matrix ──────────────────────────────────────────────────────────────────────────────────
# Keyed by adapter directory name, exactly as `adapter_registry.REGISTRY` is.
PARITY: dict[str, ToolParity] = {
    PHP_PARITY.cli.name: PHP_PARITY,
    TS_PARITY.cli.name: TS_PARITY,
    SQL_PARITY.cli.name: SQL_PARITY,
}
