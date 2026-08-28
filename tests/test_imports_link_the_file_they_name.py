"""Task 188 — a module ``IMPORTS`` edge is linked to the file it names, so a module graph exists.

155 taught the TS adapter to resolve a specifier through ``tsconfig`` ``baseUrl``/``paths``, and it
works: ``target_raw`` is a repo-relative path that exists in ``files``. The core threw it away —
``resolver.py`` had a path-linking arm for ``INCLUDES`` and only ``INCLUDES``, and ``IMPORTS`` is
in neither that arm nor ``FQN_EDGE_KINDS``, so it fell through both. Measured on the TS fixture
index before this change: **14 ``IMPORTS`` rows, 10 naming an indexed file, 0 linked**;
``find_references`` on an imported file answered ``relationship_not_modelled`` with 0 rows;
``impact`` on it returned 1 row, its own file. Every TS file was an island.

**The discriminator is the graph, never a language name (R1.1):** does ``target_raw`` name an
indexed ``File`` node? A PHP symbol import (``use A\\B\\C``) does not, so it stays bare.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import Config, load_config
from code_atlas.indexer import incremental_update
from code_atlas.resolver import resolve_edges
from code_atlas.store import EMITTED_KINDS_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import find_references, impact, include_graph
from code_atlas.tools.nav_result import (
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    TRY_INSTEAD_FIND_REFERENCES,
    TRY_INSTEAD_HINT_RELATION_CARRIED_BY_ANOTHER_KIND,
    TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE,
)
from tests.php_adapter_cli import CLI as PHP_CLI
from tests.php_adapter_cli import needs_php
from tests.test_relation_unmodelled_for_language import PHP_NOT_INCLUDED, TS_IMPORTED, _index
from tests.ts_adapter_cli import CLI as TS_CLI
from tests.ts_adapter_cli import needs_node


@pytest.fixture(scope="module")
def ts_index(tmp_path_factory: pytest.TempPathFactory) -> Config:
    """Own index, not 186's: two of these tests mutate one, and a shared fixture would carry it."""
    return _index(tmp_path_factory.mktemp("ts188"), TS_CLI, ("*.ts", "*.tsx", "*.js"))


@pytest.fixture(scope="module")
def php_index(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return _index(tmp_path_factory.mktemp("php188"), PHP_CLI, ("*.php",))


def _imports(store: GraphStore) -> list[tuple[str, str, str | None]]:
    """Every ``IMPORTS`` row as ``(source, target_raw, target_qname)``, id-ordered."""
    return [
        (str(row[0]), str(row[1]), None if row[2] is None else str(row[2]))
        for row in store._conn.execute(
            "SELECT source_qname, target_raw, target_qname FROM edges "
            "WHERE kind = 'IMPORTS' ORDER BY id"
        )
    ]


# ── AC1: the link exists ─────────────────────────────────────────────────────────────────────────


@needs_node
def test_a_ts_imports_edge_naming_an_indexed_file_is_linked(ts_index: Config) -> None:
    """AC1: ``target_qname`` is set to the file's qname — ``None`` on every row before 188."""
    with GraphStore(ts_index.db_path) as store:
        indexed = set(store.file_paths())
        rows = _imports(store)
    nameable = [row for row in rows if row[1] in indexed]
    assert len(nameable) >= 3, f"the fixture must exercise the link, got {nameable}"
    unlinked = [row for row in nameable if row[2] is None]
    assert unlinked == [], f"an IMPORTS naming an indexed file must be linked, bare: {unlinked}"
    assert all(row[2] == row[1] for row in nameable), "the link is the file's own qname"


@needs_node
def test_an_unresolvable_specifier_stays_bare(ts_index: Config) -> None:
    """AC1 boundary: `./logger` names no indexed file, so nothing is invented for it (R5.6).

    This is also what keeps find_references' unlinked-evidence arm supplied: a specifier the
    adapter could not resolve is still real evidence that a relation exists off-graph.
    """
    with GraphStore(ts_index.db_path) as store:
        indexed = set(store.file_paths())
        rows = _imports(store)
    unnameable = [row for row in rows if row[1] not in indexed]
    assert unnameable, "the fixture must also carry an unresolvable specifier"
    assert all(row[2] is None for row in unnameable), f"invented a link: {unnameable}"


# ── AC2: PHP's symbol-shaped IMPORTS is untouched ────────────────────────────────────────────────


@needs_php
def test_a_php_class_fqn_import_is_not_path_linked(php_index: Config) -> None:
    """AC2 / 061: `use App\\Contracts\\Jsonable` is a symbol, not a path — it stays bare.

    Would fail if `IMPORTS` had simply joined the `INCLUDES` arm keyed on the includer's directory:
    `_relative_to('src/x.php', 'App\\Contracts\\Jsonable')` is a string, and a repo that happened to
    hold a matching path would get a silent false link.
    """
    with GraphStore(php_index.db_path) as store:
        rows = _imports(store)
        indexed = set(store.file_paths())
    assert rows, "the PHP fixture must emit IMPORTS for this to bite"
    assert all(row[2] is None for row in rows), f"a class FQN was path-linked: {rows}"
    assert all(row[1] not in indexed for row in rows), "a class FQN must not name an indexed file"


@needs_php
def test_a_php_only_index_keeps_its_answers(php_index: Config) -> None:
    """061: the payload a PHP-only index produces is unchanged — no new field, no new reason."""
    payload = include_graph.create(php_index)(path=PHP_NOT_INCLUDED, direction="imported_by")
    assert payload["results"] == []
    assert payload["reason"] == "no_matches"
    assert "try_instead" not in payload
    assert "try_instead_hint" not in payload


# ── AC3: the tools re-measured, and 186's no-route revisited ─────────────────────────────────────


@needs_node
def test_find_references_now_enumerates_a_ts_files_importers(ts_index: Config) -> None:
    """AC3: 186 measured this as zero rows and recorded *"if this answers, the route becomes the
    honest thing to emit"*. It answers."""
    payload = find_references.create(ts_index)(qname=TS_IMPORTED)
    assert payload["reason"] == "ok"
    assert payload["total_count"] >= 3, payload
    sources = {str(row["qname"]) for row in payload["results"]}
    assert all(name.endswith((".ts", ".js", ".tsx")) for name in sources), sources
    assert TS_IMPORTED not in sources, "an importer is another file, never the subject itself"


@needs_node
def test_include_graph_names_the_route_that_can_now_answer(ts_index: Config) -> None:
    """AC3 / R5.4 clause (c): the reason stays, the no-route becomes a route.

    `include_graph` still reads `INCLUDES` only (069's territory, out of scope here), so the empty
    answer and its `relation_unmodelled_for_language` reason are both correct. What changed is that
    a registered tool can now enumerate the relation, and clause (c) says name it.
    """
    payload = include_graph.create(ts_index)(path=TS_IMPORTED, direction="imported_by")
    assert payload["results"] == []
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    assert payload["try_instead"] == TRY_INSTEAD_FIND_REFERENCES
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_RELATION_CARRIED_BY_ANOTHER_KIND
    # The route must make progress, not loop (093): the subject is a File qname, which is exactly
    # what the named tool takes.
    routed = find_references.create(ts_index)(qname=str(payload["path"]))
    assert routed["total_count"] > 0, "a named route that answers zero is worse than no route"


def test_no_route_where_the_language_carries_neither_kind(tmp_path: Path) -> None:
    """AC3's boundary and 186's original case, kept live: no carrying kind ⇒ hint and NO route.

    Seeded, because it needs a language emitting neither `INCLUDES` nor `IMPORTS` — no shipped
    adapter is that silent. The route is named on positive evidence only, so an index that cannot
    say anything about the language names no tool (R5.6).
    """
    db_path = tmp_path / ".code-atlas" / "graph.db"
    (tmp_path / "src").mkdir(parents=True)
    (tmp_path / "src/subject.zz").write_text("# planted\n", encoding="utf-8")
    with GraphStore(db_path) as store:
        store.upsert_file("src/subject.zz", "d1", "silent")
        store.replace_file_rows(
            "src/subject.zz",
            [{"kind": "File", "name": "subject.zz", "qualified_name": "src/subject.zz",
              "file_path": "src/subject.zz", "line_start": 1}],
            [],
        )
        census = store.edge_language_census()
        store.set_meta(EMITTED_KINDS_BY_LANGUAGE_KEY, json.dumps(census.kinds, sort_keys=True))
        assert store.language_emits_none_of("silent", ("INCLUDES",)) is True
        assert store.language_emits_none_of("silent", ("IMPORTS",)) is True

    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    payload = include_graph.create(config)(path="src/subject.zz", direction="imported_by")
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    assert "try_instead" not in payload
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE


# ── AC4: impact crosses a module boundary ────────────────────────────────────────────────────────


@needs_node
def test_impact_crosses_a_ts_module_boundary(ts_index: Config) -> None:
    """AC4: the user-visible cost of the gap was *every TS file is an island*."""
    payload = impact.create(ts_index)(qnames=[TS_IMPORTED])
    files = {str(row["file"]) for row in payload["results"]}
    assert payload["results"], payload
    assert files - {TS_IMPORTED}, f"impact never left the seed's own file: {files}"
    # Two hops: app.ts imports models.ts, and consumer.ts reaches it through barrel.ts. A one-hop
    # answer would still pass the line above, so the depth is what makes it a module GRAPH.
    assert max(int(row["depth"]) for row in payload["results"]) >= 2, payload["results"]


def test_imports_walks_at_the_same_weight_as_an_include() -> None:
    """AC4: a module dependency is a file-level dependency, so it carries INCLUDES' weight.

    Pinned because the weight is the decision: a lower one would rank a real module edge below a
    same-file call, and a higher one would outrank a direct caller.
    """
    weights = contract.IMPACT_KIND_WEIGHTS
    assert weights["IMPORTS"] == weights["INCLUDES"]
    assert "IMPORTS" in contract.IMPACT_KINDS


# ── AC5: no language branch, deterministic, no contract bump owed ────────────────────────────────


def _seed(tmp_path: Path, *, target_raw: str) -> Path:
    """One indexed file plus one bare ``IMPORTS`` naming ``target_raw`` — no adapter, no language.

    The point of seeding rather than indexing: the graph is the only input to the decision, so the
    test can state the whole input. The language name is one no adapter ships (R2).
    """
    db_path = tmp_path / ".code-atlas" / "graph.db"
    with GraphStore(db_path) as store:
        for path in ("pkg/a.mod", "pkg/b.mod"):
            store.upsert_file(path, f"h-{path}", "martian")
            store.replace_file_rows(
                path,
                [{"kind": "File", "name": path.split("/")[-1], "qualified_name": path,
                  "file_path": path, "line_start": 1}],
                [{"kind": "IMPORTS", "source_qname": path, "target_raw": target_raw,
                  "file_path": path, "line": 1, "confidence_tier": "RESOLVED"}]
                if path == "pkg/a.mod" else [],
            )
    return db_path


def test_the_discriminator_is_whether_the_graph_holds_the_file(tmp_path: Path) -> None:
    """AC5 / R1.1: one seeded graph, an invented language name, and the link follows the file."""
    hit = _seed(tmp_path / "hit", target_raw="pkg/b.mod")
    miss = _seed(tmp_path / "miss", target_raw="pkg/nowhere.mod")
    for db_path, expected in ((hit, "pkg/b.mod"), (miss, None)):
        with GraphStore(db_path) as store:
            resolve_edges(store, max_candidates=8)
            assert _imports(store)[0][2] == expected


def test_two_resolve_passes_produce_the_same_row(tmp_path: Path) -> None:
    """AC5 / R4.2: identical input, identical rows — and a second pass is a no-op."""
    db_path = _seed(tmp_path, target_raw="pkg/b.mod")
    with GraphStore(db_path) as store:
        resolve_edges(store, max_candidates=8)
        first = _imports(store)
        resolve_edges(store, max_candidates=8)
        assert _imports(store) == first


def test_a_path_kind_is_never_also_fqn_resolved() -> None:
    """AC5: the two arms are disjoint by construction, so no edge id is double-linked."""
    assert not (set(contract.PATH_EDGE_KINDS) & contract.FQN_EDGE_KINDS)
    assert set(contract.PATH_EDGE_KINDS) == {"INCLUDES", "IMPORTS"}
    assert set(contract.PATH_TARGET_BASIS) == set(contract.PATH_EDGE_KINDS)


@needs_node
def test_an_incremental_links_imports_from_files_the_delta_never_names(tmp_path: Path) -> None:
    """AC5 / R3: why no ``contract_version`` bump is owed.

    v8's bump fired on 129's *mechanism* trigger: an index built before and updated after would mix
    eras. It does not fire here — ``IMPORTS`` is not in ``FQN_EDGE_KINDS``, so ``delta_scope`` never
    scopes it and every unresolved ``IMPORTS`` streams on any resolve pass. Measured by clearing the
    links, touching **one** file, and updating: the untouched files' imports come back. Uses its own
    index because it mutates one (the module fixture is shared).
    """
    config = _index(tmp_path, TS_CLI, ("*.ts", "*.tsx", "*.js"))
    with GraphStore(config.db_path) as store:
        store._conn.execute("UPDATE edges SET target_qname = NULL WHERE kind = 'IMPORTS'")
        store._conn.commit()
        assert all(row[2] is None for row in _imports(store))
    touched = config.root / "src" / "widgets.ts"
    touched.write_text(touched.read_text(encoding="utf-8") + "\n// touched\n", encoding="utf-8")
    with GraphStore(config.db_path) as store:
        incremental_update(config, store, ("src/widgets.ts",))
        rows = _imports(store)
        indexed = set(store.file_paths())
    from_untouched = [row for row in rows if row[1] in indexed and row[0] != "src/widgets.ts"]
    assert from_untouched, "the measurement needs an import from a file the delta never named"
    assert all(row[2] is not None for row in from_untouched), from_untouched


@pytest.mark.parametrize("kind", ["INCLUDES", "IMPORTS"])
def test_both_path_kinds_declare_how_target_raw_names_the_file(kind: str) -> None:
    """AC5: the contract states the basis, so the resolver reads a declaration, not a hunch."""
    assert contract.PATH_TARGET_BASIS[kind] in ("includer-relative", "repo-relative")
