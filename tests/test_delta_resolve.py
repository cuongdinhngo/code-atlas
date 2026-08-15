"""Task 096 — a delta-scoped resolve must equal a full resolve, row for row.

The cost fix is worthless if it drifts: `resolve` scanned the whole unresolved residue on every
incremental (O(residue), flat across delta size), so an incremental was ~26x a no-op. Scoping it
is only legitimate while the scoped pass links exactly what the full pass links (R4.2), so the
equivalence — not the seconds — is what these tests hold.
"""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas import gitutil
from code_atlas.config import load_config
from code_atlas.indexer import full_build, incremental_update
from code_atlas.resolver import delta_scope, resolve_edges
from code_atlas.store import GraphStore
from tests.test_incremental import committed, config_for, fake_env, git, snapshot
from tests.test_resolver import edge, node, seed_file


def _full_build(root: Path, db_name: str) -> dict[str, list[tuple[object, ...]]]:
    """Build the same tree from scratch — the answer a delta-scoped run has to match."""
    fresh = config_for(root, db_name)
    with GraphStore(fresh.db_path) as store:
        full_build(fresh, store)
        return snapshot(store)


def test_delta_resolve_links_residue_a_new_file_satisfies(tmp_path: Path) -> None:
    """Proving (AC2): the cross-file case a file-scoped resolve gets wrong.

    ``dep/user.aa`` calls ``lib/core.aa::Thing`` before that file exists, so its edge sits in the
    unresolved residue. Adding ``lib/core.aa`` makes the residue edge resolvable — but ``dep`` is
    not a dependent (``file_paths_targeting`` matches ``target_qname``, still NULL), so it is never
    reparsed. A scope keyed only on parsed files would leave the edge unlinked forever.
    """
    committed(tmp_path, {"dep/user.aa": "one\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        unresolved = [
            row
            for batch in store.iter_unresolved_edges()
            for row in batch
            if row["source_qname"] == "dep/user.aa::Thing"
        ]
    assert unresolved, "fixture is inert: dep/user.aa must start with an unresolved edge"

    last = git(tmp_path, "rev-parse", "HEAD").strip()
    committed(tmp_path, {"lib/core.aa": "core\n"}, message="add the target")
    changed = gitutil.changed_paths(tmp_path, last)
    assert changed == ("lib/core.aa",)

    with GraphStore(config.db_path) as store:
        incremental_update(config, store, changed)
        after = snapshot(store)
        linked = store.edges_by_source("dep/user.aa::Thing", kinds=("CALLS",), limit=5)
    assert [row["target_qname"] for row in linked] == ["lib/core.aa::Thing"]
    assert after == _full_build(tmp_path, "fresh.db")


def test_delta_resolve_links_residue_a_new_bare_name_satisfies(tmp_path: Path) -> None:
    """AC2: the unmatched-CALLS second pass resolves by bare name, so keys carry names too."""
    committed(tmp_path, {"dep/name_user.aa": "one\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)

    last = git(tmp_path, "rev-parse", "HEAD").strip()
    committed(tmp_path, {"twin/impl.aa": "impl\n"}, message="declare run")
    changed = gitutil.changed_paths(tmp_path, last)

    with GraphStore(config.db_path) as store:
        incremental_update(config, store, changed)
        after = snapshot(store)
    assert after == _full_build(tmp_path, "fresh.db")


def test_delta_scope_carries_qnames_and_bare_names(tmp_path: Path) -> None:
    """The key set is the whole lookup surface — qnames plus bare method names."""
    committed(tmp_path, {"twin/impl.aa": "impl\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        scope = delta_scope(store, ["twin/impl.aa"])
    assert "twin/impl.aa::run" in scope.keys
    assert "run" in scope.keys
    assert scope.files == ("twin/impl.aa",)
    assert "CALLS" in scope.scoped_kinds and "INCLUDES" not in scope.scoped_kinds


def test_delta_scope_actually_narrows_the_scan(tmp_path: Path) -> None:
    """Prove the guard (093-C3): an inert scope that streamed everything would pass silently."""
    # Every dep/ file calls lib/core.aa::Thing, which is never created — a 41-edge residue.
    files = {f"dep/other{i:03d}.aa": f"body {i}\n" for i in range(40)}
    files["dep/user.aa"] = "user\n"
    committed(tmp_path, files)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        full = [row for batch in store.iter_unresolved_edges(skip_dynamic=True) for row in batch]
        scope = delta_scope(store, ["dep/user.aa"])
        scoped = [
            row
            for batch in store.iter_unresolved_edges(skip_dynamic=True, delta=scope)
            for row in batch
        ]
    assert full, "fixture is inert: there must be an unresolved residue to narrow"
    assert len(scoped) < len(full)
    assert all(row["file_path"] == "dep/user.aa" for row in scoped)


def test_delta_scope_keeps_unscoped_kinds_streaming(tmp_path: Path) -> None:
    """094's `skip-dynamic-means-unlinkable`: the delta filter ANDs with skip_dynamic."""
    committed(tmp_path, {"dep/user.aa": "user\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        store.insert_edges(
            [
                {
                    "kind": "INCLUDES",
                    "source_qname": "dep/user.aa",
                    "target_raw": "../lib/core.aa",
                    "file_path": "dep/user.aa",
                    "line": 1,
                    "confidence_tier": "RESOLVED",
                },
                {
                    "kind": "REFERENCES",
                    "source_qname": "other/far.aa::Thing",
                    "target_raw": "\\Never\\Resolved",
                    "file_path": "other/far.aa",
                    "line": 1,
                    "confidence_tier": "DYNAMIC",
                },
            ]
        )
        scope = delta_scope(store, ["dep/user.aa"])
        kinds = {
            str(row["kind"])
            for batch in store.iter_unresolved_edges(skip_dynamic=True, delta=scope)
            for row in batch
        }
    # INCLUDES resolves by computed path, not target_raw, so a key-based scope must not drop it.
    assert "INCLUDES" in kinds


def test_enrichment_rows_resolve_under_a_delta_scope(tmp_path: Path) -> None:
    """Regression: the bookmark is rewritten after the parse, so no delta lists it.

    ``apply_indirection_rules`` deletes and re-inserts every rule row under a synthetic path on
    each run, always bare. A scope built from the parsed files alone never covers that path, so
    the fresh ``ALIASES`` row stayed unresolved while a full build linked it — caught in review,
    not by the equivalence tests above, because their fixtures had no rules.
    """
    rules = {
        "aliases": [{"from": "\\Facade", "to": "\\Dup"}],
        "calls": [{"source": "dep/user.aa::Thing", "target": "\\Facade::run", "line": 7}],
    }
    committed(tmp_path, {"dep/user.aa": "one\n", "dup/first.aa": "d\n"})
    (tmp_path / "rules").mkdir(exist_ok=True)
    (tmp_path / "rules" / "rules.json").write_text(json.dumps(rules), encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "rules")

    def configured(db_name: str) -> object:
        return load_config(
            tmp_path,
            {
                **fake_env(),
                "CA_DB_PATH": str(tmp_path / ".code-atlas" / db_name),
                "CA_INDIRECTION_RULES": "rules/rules.json",
            },
        )

    config = configured("graph.db")
    with GraphStore(config.db_path) as store:
        full_build(config, store)

    last = git(tmp_path, "rev-parse", "HEAD").strip()
    committed(tmp_path, {"other/touch.aa": "t\n"}, message="unrelated edit")
    with GraphStore(config.db_path) as store:
        incremental_update(config, store, gitutil.changed_paths(tmp_path, last))
        after = snapshot(store)
        aliases = [
            row
            for row in store.edges_by_target("\\Dup", limit=20)
            if row["kind"] == "ALIASES"
        ]
    assert aliases, "the rule ALIASES row must be linked, not left bare"

    fresh = configured("fresh.db")
    with GraphStore(fresh.db_path) as store:
        full_build(fresh, store)
        assert after == snapshot(store)


def _seed_alias_residue(store: GraphStore, raw: str, extra: list[dict[str, object]]) -> None:
    """A residue edge naming ``\\Ns\\Aka``, the alias of a class no file declares yet."""
    seed_file(
        store,
        "a.x",
        [node("Class", "User", "\\Ns\\User", "a.x")],
        [edge("CALLS", "\\Ns\\User", raw, "a.x", tier="RESOLVED")],
    )
    seed_file(
        store,
        "alias.x",
        [],
        [edge("ALIASES", "\\Ns\\Aka", "\\Ns\\Real", "alias.x", tier="RESOLVED")],
    )
    resolve_edges(store, max_candidates=50)
    assert [row["target_qname"] for row in store.edges_by_source(
        "\\Ns\\User", kinds=("CALLS",), limit=5
    )] == [None], "fixture is inert: the alias must start unresolved"
    seed_file(store, "real.x", [node("Class", "Real", "\\Ns\\Real", "real.x")] + extra, [])


def test_delta_scope_covers_an_edge_naming_an_alias(tmp_path: Path) -> None:
    """AC2 via the alias map: ``_lookup_raw`` reaches a delta's key through it, so the scope must.

    ``a.x`` names ``\\Ns\\Aka``; the delta declares ``\\Ns\\Real``. Keyed on raw text alone the
    edge is out of scope in a file no delta lists, and a full build links it while this one
    does not — the alias map being *unchanged* is exactly when the guard hands over to the scope.
    """
    with GraphStore(tmp_path / "graph.db") as store:
        _seed_alias_residue(store, "\\Ns\\Aka", [])
        resolve_edges(store, max_candidates=50, delta=delta_scope(store, ["real.x"]))
        linked = store.edges_by_source("\\Ns\\User", kinds=("CALLS",), limit=5)
    assert [row["target_qname"] for row in linked] == ["\\Ns\\Real"]


def test_delta_scope_covers_an_aliased_container(tmp_path: Path) -> None:
    """Same reach, `_lookup_raw`'s other branch: ``\\Ns\\Aka::run`` → ``\\Ns\\Real::run``."""
    with GraphStore(tmp_path / "graph.db") as store:
        _seed_alias_residue(
            store, "\\Ns\\Aka::run", [node("Method", "run", "\\Ns\\Real::run", "real.x")]
        )
        resolve_edges(store, max_candidates=50, delta=delta_scope(store, ["real.x"]))
        linked = store.edges_by_source("\\Ns\\User", kinds=("CALLS",), limit=5)
    assert [row["target_qname"] for row in linked] == ["\\Ns\\Real::run"]
