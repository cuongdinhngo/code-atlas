"""Task 094 — a ``Foo::class`` mention is a DYNAMIC REFERENCES edge, not a refusal.

The field's routing table named classes as array values and dispatched through a variable
method. ``find_references`` answered ``relationship_not_modelled``; the method stayed
``no_matches``. The mention is now an edge; the dispatch is still unmodelled.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools.find_callers import create as create_find_callers
from code_atlas.tools.find_references import create as create_find_references
from tests.php_adapter_cli import ENTRY, FIXTURES, PHP, ROOT, needs_php, parse_file
from tests.test_nav_tools import edge, node, seed_file

FIXTURE = FIXTURES.relative_to(ROOT) / "class_const_mention.php"


def _php_index(tmp_path: Path) -> Config:
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(FIXTURES / "class_const_mention.php", src / "router.php")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"]),
        },
    )
    with GraphStore(db_path) as store:
        assert full_build(config, store).failed == 0
    return config


@needs_php
def test_array_of_class_constants_emits_dynamic_references() -> None:
    """Proving (AC1): parse-level edges for both array values, DYNAMIC, kind REFERENCES."""
    result = parse_file(FIXTURE)
    mentions = [
        e
        for e in result["edges"]
        if isinstance(e, dict) and e.get("kind") == "REFERENCES"
    ]
    pairs = {(e["target_raw"], e.get("confidence_tier")) for e in mentions}
    assert ("\\App\\Wire\\Foo", "DYNAMIC") in pairs
    assert ("\\App\\Wire\\Bar", "DYNAMIC") in pairs
    assert all(e.get("source_qname") == "\\App\\Wire\\Router::dispatch" for e in mentions)
    # Bare assignment is the same language construct (R2), not a follow-up.
    foo_hits = [e for e in mentions if e["target_raw"] == "\\App\\Wire\\Foo"]
    assert len(foo_hits) == 2


@needs_php
def test_special_class_names_resolve_to_the_enclosing_class_like() -> None:
    """``self``/``static``/``parent``::class are the same construct — never a ``\\self`` target."""
    result = parse_file(FIXTURE)
    mentions = [
        e
        for e in result["edges"]
        if isinstance(e, dict) and e.get("kind") == "REFERENCES"
    ]
    targets = [e["target_raw"] for e in mentions]
    assert not [t for t in targets if t in {"\\self", "\\static", "\\parent"}]
    # self:: and static:: name Router itself; parent:: names its extends clause.
    assert targets.count("\\App\\Wire\\Router") == 2
    assert "\\App\\Wire\\BaseRouter" in targets


@needs_php
def test_find_references_returns_the_mention_as_a_candidate_list(
    tmp_path: Path,
) -> None:
    """AC2: linked hit carries DYNAMIC; all-DYNAMIC payload is not authoritative."""
    config = _php_index(tmp_path)
    with GraphStore(config.db_path) as store:
        foo_edges = store.edges_by_target("\\App\\Wire\\Foo", limit=50)
        bar_edges = store.edges_by_target("\\App\\Wire\\Bar", limit=50)
    assert foo_edges and bar_edges
    assert all(e["kind"] == "REFERENCES" and e["confidence_tier"] == "DYNAMIC" for e in foo_edges)
    assert all(e["kind"] == "REFERENCES" and e["confidence_tier"] == "DYNAMIC" for e in bar_edges)

    refs = create_find_references(config)("\\App\\Wire\\Foo", detail_level="minimal")
    assert refs["reason"] == "ok"
    assert refs["total_count"] >= 1
    assert refs["authoritative"] is False
    assert all(hit["confidence_tier"] == "DYNAMIC" for hit in refs["results"])
    assert all(hit["kind"] == "REFERENCES" for hit in refs["results"])


@needs_php
def test_variable_method_dispatch_stays_unmodelled(tmp_path: Path) -> None:
    """AC4: ``$this->$action()`` does not become a caller of Foo::run."""
    config = _php_index(tmp_path)
    callers = create_find_callers(config)("\\App\\Wire\\Foo::run", detail_level="minimal")
    assert callers["reason"] == "no_matches"
    assert callers["results"] == []
    assert callers["total_count"] == 0


def test_skip_dynamic_still_yields_reference_mentions(tmp_path: Path) -> None:
    """Resolver skip_dynamic must not drop linkable DYNAMIC REFERENCES (094)."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        seed_file(
            store,
            "a.php",
            [node("Class", "Foo", "\\Foo", "a.php")],
            [
                edge("REFERENCES", "\\Router::dispatch", "\\Foo", "a.php", tier="DYNAMIC"),
                edge("CALLS", "\\Router::dispatch", "(dynamic)", "a.php", tier="DYNAMIC"),
            ],
            root=tmp_path,
        )
        skipped = [
            row
            for batch in store.iter_unresolved_edges(batch_size=10, skip_dynamic=True)
            for row in batch
        ]
    kinds = {row["kind"] for row in skipped}
    assert "REFERENCES" in kinds
    assert all(
        row["kind"] != "CALLS" or row["confidence_tier"] != "DYNAMIC" for row in skipped
    )
