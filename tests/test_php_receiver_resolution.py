"""Task 029: lexical $this / self / static / parent CALLS receivers in the PHP adapter."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from tests.php_adapter_cli import ENTRY, FIXTURES, PHP, ROOT, needs_php, parse_file

PHP_ENTRY = ENTRY


def _calls(result: dict[str, object]) -> list[dict[str, object]]:
    edges = result.get("edges")
    assert isinstance(edges, list)
    return [e for e in edges if isinstance(e, dict) and e.get("kind") == "CALLS"]


@needs_php
def test_static_vs_instance_rewrites_lexical_receivers() -> None:
    """Hand-count: self/static/$this leave HEURISTIC; $other-> stays HEURISTIC (AC3)."""
    result = parse_file(FIXTURES.relative_to(ROOT) / "static_vs_instance.php")
    calls = _calls(result)
    by_raw = Counter(
        (str(e.get("target_raw")), e.get("confidence_tier")) for e in calls
    )
    # 3× Service::make (Service::, self::, static::) + 1× Service::run ($this) + 1× run HEURISTIC
    assert by_raw[("\\App\\Calls\\Service::make", None)] == 3
    assert by_raw[("\\App\\Calls\\Service::run", None)] == 1
    assert by_raw[("run", "HEURISTIC")] == 1
    assert sum(1 for e in calls if e.get("confidence_tier") == "HEURISTIC") == 1


@needs_php
def test_receiver_fixture_shapes_and_trait_does_not_fabricate_host() -> None:
    result = parse_file(FIXTURES.relative_to(ROOT) / "receiver_resolution.php")
    calls = _calls(result)
    shapes = sorted(
        (str(e.get("target_raw")), e.get("confidence_tier")) for e in calls
    )
    assert ("\\App\\Recv\\Base::fromBase", None) in shapes  # parent::
    assert ("\\App\\Recv\\Child::go", None) in shapes  # $this / self / static (≥1)
    assert shapes.count(("\\App\\Recv\\Child::go", None)) == 3
    assert ("\\App\\Recv\\HasHook::hook", None) in shapes  # trait $this → trait FQN
    assert ("go", "HEURISTIC") in shapes  # $x->go
    # $x->$m has no Identifier name → still no CALLS edge (unchanged).
    assert all(e.get("target_raw") != "$m" for e in calls)


@needs_php
def test_lexical_receivers_resolve_to_enclosing_class_fqn(
    tmp_path: Path,
) -> None:
    """Proving test: after full_build, parent:: and $this link RESOLVED to the right methods."""
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(FIXTURES / "receiver_resolution.php", src / "receiver_resolution.php")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)

    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        },
    )
    with GraphStore(db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0

        parent_calls = [
            row
            for row in store.edges_by_source(
                "\\App\\Recv\\Child::go", kinds=("CALLS",), limit=20
            )
            if row["target_raw"] == "\\App\\Recv\\Base::fromBase"
        ]
        assert len(parent_calls) == 1
        assert parent_calls[0]["target_qname"] == "\\App\\Recv\\Base::fromBase"
        assert parent_calls[0]["confidence_tier"] == "RESOLVED"

        this_calls = [
            row
            for row in store.edges_by_source(
                "\\App\\Recv\\Child::go", kinds=("CALLS",), limit=20
            )
            if row["target_raw"] == "\\App\\Recv\\Child::go"
            and row.get("confidence_tier") != "HEURISTIC"
        ]
        assert len(this_calls) >= 1
        assert all(row["target_qname"] == "\\App\\Recv\\Child::go" for row in this_calls)
        assert all(row["confidence_tier"] == "RESOLVED" for row in this_calls)

        heuristic = [
            row
            for row in store.edges_by_source(
                "\\App\\Recv\\Child::go", kinds=("CALLS",), limit=20
            )
            if row["confidence_tier"] == "HEURISTIC"
        ]
        assert len(heuristic) == 1
        assert heuristic[0]["target_raw"] == "go"
