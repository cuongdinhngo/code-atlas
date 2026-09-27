"""Task 334 — one qname declared in two files is one candidate, and a partial caller list says so.

Proves at the consumers (R6.9): ``find_callers`` for a bare EXEC and ``find_references`` for an
unqualified INSERT. Two *different* qnames stay ambiguous (214); one qname in two files does not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.resolver import resolve_edges
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from code_atlas.tools.nav_result import CAVEAT_UNLINKED_SAME_NAME_SITES, REASON_OK
from tests.sql_adapter_cli import CLI, needs_node

pytestmark = needs_node

_PROC = "CREATE OR ALTER PROCEDURE {name}\nAS\nBEGIN\n    {body}\nEND\nGO\n"


def _index(root: Path, files: dict[str, str]) -> Config:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    argv = ", ".join(f"'{part}'" for part in (*CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\nsql = [{argv}]\n", encoding="utf-8"
    )
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    db_path = root / ".code-atlas" / "graph.db"
    config = load_config(
        root, {"CA_TRUST_PROJECT_FILE": "1", "CA_WORKERS": "1", "CA_DB_PATH": str(db_path)}
    )
    with GraphStore(db_path) as store:
        assert full_build(config, store).nodes > 0
    return config


def _callers(config: Config, qname: str) -> dict[str, object]:
    return find_callers.create(config)(qname, detail_level="minimal")


def _names(payload: dict[str, object]) -> set[str]:
    results = payload["results"]
    assert isinstance(results, list)
    return {str(hit["qname"]) for hit in results}


def test_bare_exec_links_to_a_proc_declared_in_two_files(tmp_path: Path) -> None:
    """AC1 — a snapshot and a migration both declare dbo.Gen; the bare EXEC still links."""
    config = _index(
        tmp_path,
        {
            "db/snapshot/Gen.sql": _PROC.format(name="dbo.Gen", body="SELECT 1;"),
            "db/change/V1__gen.sql": _PROC.format(name="dbo.Gen", body="SELECT 2;"),
            "db/change/V2__callers.sql": _PROC.format(name="dbo.Caller", body="EXEC Gen;")
            + _PROC.format(name="dbo.Caller2", body="EXEC dbo.Gen;"),
        },
    )
    payload = _callers(config, "dbo.Gen")
    assert payload["reason"] == REASON_OK
    assert _names(payload) == {"dbo.Caller", "dbo.Caller2"}
    assert "unlinked_same_name_sites" not in payload


def test_two_different_qnames_stay_ambiguous(tmp_path: Path) -> None:
    """AC2 — dbo.Gen twice plus sales.Gen: the bare EXEC names two qnames and links to neither.

    Three nodes, so a node-count limit of two would see only the two dbo rows.
    """
    config = _index(
        tmp_path,
        {
            "db/a/Gen.sql": _PROC.format(name="dbo.Gen", body="SELECT 1;"),
            "db/b/Gen.sql": _PROC.format(name="dbo.Gen", body="SELECT 2;"),
            "db/c/Gen.sql": _PROC.format(name="sales.Gen", body="SELECT 3;"),
            "db/d/Caller.sql": _PROC.format(name="dbo.Caller", body="EXEC Gen;"),
        },
    )
    for qname in ("dbo.Gen", "sales.Gen"):
        assert _callers(config, qname)["total_count"] == 0, f"{qname} picked a twin"


def test_unqualified_insert_links_to_a_table_altered_in_another_file(tmp_path: Path) -> None:
    """AC3 — CREATE TABLE in one file, ALTER TABLE in another: INSERT INTO T still links."""
    config = _index(
        tmp_path,
        {
            "db/T.sql": "CREATE TABLE dbo.T (a INT)\nGO\n",
            "db/T_alter.sql": "ALTER TABLE dbo.T ADD b INT\nGO\n",
            "db/W.sql": _PROC.format(name="dbo.W", body="INSERT INTO T (a) VALUES (1);"),
        },
    )
    with GraphStore(config.db_path) as store:
        assert len(store.nodes_by_qualified_name("dbo.T", kind="Table", limit=5)) == 2
    payload = find_references.create(config)("dbo.T", detail_level="minimal")
    assert "dbo.W" in _names(payload)


def test_a_linked_caller_beside_an_unlinked_site_is_not_authoritative(tmp_path: Path) -> None:
    """AC4 — one caller links, a bare EXEC stays ambiguous: the answer counts the unlinked site."""
    config = _index(
        tmp_path,
        {
            "db/Gen.sql": _PROC.format(name="dbo.Gen", body="SELECT 1;")
            + _PROC.format(name="audit.Gen", body="SELECT 2;"),
            "db/Callers.sql": _PROC.format(name="dbo.Caller", body="EXEC Gen;")
            + _PROC.format(name="dbo.Caller2", body="EXEC dbo.Gen;"),
        },
    )
    payload = _callers(config, "dbo.Gen")
    assert _names(payload) == {"dbo.Caller2"}
    assert payload["unlinked_same_name_sites"] == 1
    assert payload["authoritative"] is False
    caveats = payload["authoritative_caveats"]
    assert isinstance(caveats, list)
    assert CAVEAT_UNLINKED_SAME_NAME_SITES in caveats


def _node(kind: str, name: str, qname: str, path: str) -> dict[str, object]:
    return {"kind": kind, "name": name, "qualified_name": qname, "file_path": path, "line_start": 1}


def _edge(kind: str, source: str, raw: str, *, tier: str | None = None) -> dict[str, object]:
    row: dict[str, object] = {
        "kind": kind,
        "source_qname": source,
        "target_raw": raw,
        "file_path": "w.x",
        "line": 3,
    }
    if tier is not None:
        row["confidence_tier"] = tier
    return row


def test_every_unique_candidate_site_counts_qnames(tmp_path: Path) -> None:
    """R1 inventory — casefold passes, both column lookups and the Method fallback, one store.

    Every target is declared in two files under one qname; before 334 each read as two candidates.
    """
    twins = [
        _node("Table", "T", "dbo.T", "{p}"),
        _node("Column", "c", "dbo.T::c", "{p}"),
        _node("Method", "put", "\\Ns\\Repo::put", "{p}"),
    ]
    edges = [
        _edge("WRITES", "dbo.W", "DBO.T"),  # casefold pass 1
        _edge("WRITES", "dbo.W", "T::c"),  # pass 2 → column exact
        _edge("WRITES", "dbo.W", "T::C"),  # pass 2 → column casefold
        _edge("CALLS", "dbo.W", "put", tier="HEURISTIC"),  # bare-name Method fallback
    ]
    with GraphStore(tmp_path / "graph.db") as store:
        for path in ("a.x", "b.x"):
            store.upsert_file(path, "h", "lang")
            rows = [{**row, "file_path": path} for row in twins]
            store.replace_file_rows(path, rows, [])
        store.upsert_file("w.x", "h", "lang")
        store.replace_file_rows("w.x", [_node("Function", "W", "dbo.W", "w.x")], edges)
        resolve_edges(store, max_candidates=50)
        linked = {
            (str(row["target_raw"]), row["target_qname"])
            for row in store.edges_by_source("dbo.W", limit=10)
        }
    assert linked == {
        ("DBO.T", "dbo.T"),
        ("T::c", "dbo.T::c"),
        ("T::C", "dbo.T::c"),
        ("put", "\\Ns\\Repo::put"),
    }


def test_distinct_lookup_ranks_qnames_not_rows(tmp_path: Path) -> None:
    """HOW1 — two dbo.Gen rows plus sales.Gen at limit 2: distinct mode still sees both qnames."""
    with GraphStore(tmp_path / "graph.db") as store:
        for path, qname in (("a.x", "dbo.Gen"), ("b.x", "dbo.Gen"), ("c.x", "sales.Gen")):
            store.upsert_file(path, "h", "lang")
            store.replace_file_rows(path, [_node("Function", "Gen", qname, path)], [])
        plain = store.nodes_by_names(["Gen"], kind="Function", limit=2)["Gen"]
        distinct = store.nodes_by_names(["Gen"], kind="Function", limit=2, distinct_qnames=True)
        folded = store.nodes_by_names_casefold(["gen"], limit=2, distinct_qnames=True)
        by_qname = store.nodes_by_qualified_names_casefold(
            ["DBO.GEN"], limit=2, distinct_qnames=True
        )
    assert [row["qualified_name"] for row in plain] == ["dbo.Gen", "dbo.Gen"]  # 061: unchanged
    assert [row["qualified_name"] for row in distinct["Gen"]] == ["dbo.Gen", "sales.Gen"]
    assert [row["qualified_name"] for row in folded["gen"]] == ["dbo.Gen", "sales.Gen"]
    assert [row["qualified_name"] for row in by_qname["DBO.GEN"]] == ["dbo.Gen"]
