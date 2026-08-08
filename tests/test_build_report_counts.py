"""Task 051: a build report must count every row the build wrote, not just the adapters' share.

``_parse_all`` tallies while writing adapter output, and two later steps insert more rows —
enrichment's synthetic ALIASES/CALLS and the resolver's sibling candidates. A report built from the
parse tally alone described a graph smaller than the one just created; on the anchor repo, 949,808
against 1,775,812 stored, while ``get_index_status`` reported the larger figure for the same graph.

The definition these tests pin is **"what this run wrote"**: a full build therefore agrees with the
table, and an incremental run still reports its own delta rather than the whole graph.
"""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas import gitutil
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build, incremental_update
from code_atlas.main import build_server
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools.build_or_update_index import NAME as BUILD
from code_atlas.tools.get_index_status import NAME as STATUS
from tests.test_incremental import committed, fake_env
from tests.test_mcp_server import call

# twin/* declare the same method name twice, dep/name_* calls it bare — one call site, two
# candidates, so the resolver inserts exactly one sibling row per caller. lib/ + dep/plain are
# untouched by an edit to twin/a, which is what makes an incremental delta smaller than the whole.
MULTI_CANDIDATE = {
    "twin/a.aa": "run a\n",
    "twin/b.aa": "run b\n",
    "dep/name_caller.aa": "calls run\n",
    "dep/name_other.aa": "calls run too\n",
    "lib/core.aa": "the core\n",
    "dep/plain.aa": "calls core\n",
}

RULES = {
    "aliases": [{"from": "\\Facade", "to": "\\Real"}],
    "calls": [{"source": "\\Facade::get", "target": "\\Real::get", "line": 7}],
}


def config_for(root: Path, **extra: str) -> Config:
    db = root / ".code-atlas" / "graph.db"
    return load_config(root, {**fake_env(), "CA_DB_PATH": str(db), **extra})


def with_rules(root: Path) -> Config:
    (root / "rules").mkdir(exist_ok=True)
    (root / "rules" / "rules.json").write_text(json.dumps(RULES), encoding="utf-8")
    return config_for(root, CA_INDIRECTION_RULES="rules/rules.json")


def sibling_rows(store: GraphStore) -> int:
    """Rows sharing a call site with another — what the parse tally could not have counted."""
    stored, distinct = store._conn.execute(
        "SELECT (SELECT COUNT(*) FROM edges),"
        " (SELECT COUNT(*) FROM (SELECT DISTINCT source_qname, kind, target_raw, file_path, line"
        " FROM edges))"
    ).fetchone()
    return int(stored) - int(distinct)


def test_the_fixture_really_produces_siblings(tmp_path: Path) -> None:
    """Guards the guard: with no sibling rows, every agreement test below passes vacuously."""
    committed(tmp_path, MULTI_CANDIDATE)
    config = config_for(tmp_path)

    with GraphStore(config.db_path) as store:
        full_build(config, store)

        assert sibling_rows(store) == 2


def test_a_full_build_reports_the_edges_the_table_holds(tmp_path: Path) -> None:
    committed(tmp_path, MULTI_CANDIDATE)
    config = config_for(tmp_path)

    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        counted = store.counts()

        assert report.edges == counted["edges"]
        assert report.nodes == counted["nodes"]


def test_the_build_tool_and_the_status_tool_agree(tmp_path: Path) -> None:
    """The two numbers an agent sees, one after the other, with no build in between."""
    committed(tmp_path, MULTI_CANDIDATE)
    config = config_for(tmp_path)
    server = build_server(config)

    built = call(server, BUILD, {})
    status = call(server, STATUS, {})

    assert built["wrote"]["edges"] == status["edges"]
    assert built["wrote"]["nodes"] == status["nodes"]
    assert built["graph"]["edges"] == status["edges"]
    assert built["graph"]["nodes"] == status["nodes"]


def test_a_second_full_build_reports_the_same_totals(tmp_path: Path) -> None:
    """Rebuilding in place replaces every row, so "what this run wrote" is unchanged (R4.2)."""
    committed(tmp_path, MULTI_CANDIDATE)
    config = config_for(tmp_path)

    with GraphStore(config.db_path) as store:
        first = full_build(config, store)
        second = full_build(config, store)

        assert (second.nodes, second.edges) == (first.nodes, first.edges)
        assert second.edges == store.counts()["edges"]


def test_enrichment_rows_are_counted_too(tmp_path: Path) -> None:
    """The rules insert a File node and two edges after the tally; all three were missing."""
    committed(tmp_path, MULTI_CANDIDATE)
    plain = config_for(tmp_path)
    enriched = with_rules(tmp_path)

    with GraphStore(plain.db_path) as store:
        bare = full_build(plain, store)
    with GraphStore(enriched.db_path) as store:
        ruled = full_build(enriched, store)
        counted = store.counts()

    assert ruled.nodes == bare.nodes + 1
    assert ruled.edges == bare.edges + len(RULES["aliases"]) + len(RULES["calls"])
    assert (ruled.nodes, ruled.edges) == (counted["nodes"], counted["edges"])


def test_the_rules_bookmark_is_the_one_known_disagreement(tmp_path: Path) -> None:
    """`files`/`parsed` still differ by the synthetic rules path — pinned so it cannot drift."""
    committed(tmp_path, MULTI_CANDIDATE)
    config = with_rules(tmp_path)

    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        counted = store.counts()

    assert counted["files"] == report.files + 1
    assert counted["parsed"] == report.parsed + 1


def test_an_incremental_run_reports_its_delta_not_the_graph(tmp_path: Path) -> None:
    """The other definition — "rows in the graph now" — would fail here, and should."""
    committed(tmp_path, MULTI_CANDIDATE)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        whole = full_build(config, store)
        last = store.get_meta(LAST_COMMIT_KEY)
    assert last is not None

    committed(tmp_path, {"twin/a.aa": "run a v2\n"}, message="edit twin a")
    changed = gitutil.changed_paths(tmp_path, last)
    assert changed == ("twin/a.aa",)

    with GraphStore(config.db_path) as store:
        delta = incremental_update(config, store, changed)
        counted = store.counts()

    assert delta.edges < whole.edges
    assert counted["edges"] == whole.edges
