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
    """Hand-count: self/$this default; static:: FQN at HEURISTIC; `new`-bound $other resolved."""
    result = parse_file(FIXTURES.relative_to(ROOT) / "static_vs_instance.php")
    calls = _calls(result)
    by_raw = Counter(
        (str(e.get("target_raw")), e.get("confidence_tier")) for e in calls
    )
    # Service:: + self:: at default; static:: at HEURISTIC; $this and `$other = new Service()`
    # both name Service::run — the second because the local type table read the `new` (137).
    assert by_raw[("\\App\\Calls\\Service::make", None)] == 2
    assert by_raw[("\\App\\Calls\\Service::make", "HEURISTIC")] == 1
    assert by_raw[("\\App\\Calls\\Service::run", None)] == 2
    assert by_raw[("run", "HEURISTIC")] == 0
    # Only static:: is left: late binding is the one cause no receiver type settles (136).
    assert sum(1 for e in calls if e.get("confidence_tier") == "HEURISTIC") == 1


@needs_php
def test_receiver_fixture_shapes_and_trait_does_not_fabricate_host() -> None:
    result = parse_file(FIXTURES.relative_to(ROOT) / "receiver_resolution.php")
    calls = _calls(result)
    shapes = sorted(
        ((str(e.get("target_raw")), e.get("confidence_tier")) for e in calls),
        key=lambda t: (str(t[0]), t[1] is not None, str(t[1] or "")),
    )
    assert ("\\App\\Recv\\Base::fromBase", None) in shapes  # parent::
    # $this / self / $this? at default; static:: at HEURISTIC (late binding)
    assert shapes.count(("\\App\\Recv\\Child::go", None)) == 3
    assert ("\\App\\Recv\\Child::go", "HEURISTIC") in shapes
    assert ("\\App\\Recv\\HasHook::hook", None) in shapes  # trait $this → trait FQN
    # Inherited / trait-mixin through $this name Child — the class the call was made on (137).
    assert ("\\App\\Recv\\Child::fromBase", None) in shapes
    assert ("\\App\\Recv\\Child::hook", None) in shapes
    assert not {raw for raw, _ in shapes} & {"fromBase", "hook"}
    assert ("go", "HEURISTIC") in shapes  # $x->go
    assert ("(dynamic)", "DYNAMIC") in shapes  # $x->$m (task 030)
    # Nested anonymous with no extends: parent:: left as today (\parent::…).
    assert ("\\parent::fromBase", None) in shapes
    # Variable method name is DYNAMIC, not a bare "$m" target.
    assert all(e.get("target_raw") != "$m" for e in calls)


@needs_php
def test_lexical_receivers_resolve_to_enclosing_class_fqn(
    tmp_path: Path,
) -> None:
    """Proving test: cross-file parent:: and local $this link; inherited stay linked."""
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(FIXTURES / "receiver_base.php", src / "receiver_base.php")
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
        assert report.parsed == 2

        child_calls = list(
            store.edges_by_source(
                "\\App\\Recv\\Child::go", kinds=("CALLS",), limit=20
            )
        )
        # Recall invariant: linkable CALLS from Child::go are never left unlinked (finding 1/3).
        linkable = [row for row in child_calls if row["confidence_tier"] != "DYNAMIC"]
        assert linkable
        assert all(row["target_qname"] is not None for row in linkable)

        parent_calls = [
            row
            for row in child_calls
            if row["target_raw"] == "\\App\\Recv\\Base::fromBase"
        ]
        assert len(parent_calls) == 1
        assert parent_calls[0]["target_qname"] == "\\App\\Recv\\Base::fromBase"
        assert parent_calls[0]["confidence_tier"] == "RESOLVED"

        this_calls = [
            row
            for row in child_calls
            if row["target_raw"] == "\\App\\Recv\\Child::go"
            and row.get("confidence_tier") != "HEURISTIC"
        ]
        assert len(this_calls) >= 1
        assert all(row["target_qname"] == "\\App\\Recv\\Child::go" for row in this_calls)
        assert all(row["confidence_tier"] == "RESOLVED" for row in this_calls)

        # Inherited $this->fromBase and trait-mixin $this->hook reach the declaring ancestor
        # through the hierarchy walk, so the guess they used to need is gone (137).
        by_raw = {row["target_raw"]: row for row in child_calls}
        inherited = {
            "\\App\\Recv\\Child::fromBase": "\\App\\Recv\\Base::fromBase",
            "\\App\\Recv\\Child::hook": "\\App\\Recv\\HasHook::hook",
        }
        for raw, declared_at in inherited.items():
            assert by_raw[raw]["target_qname"] == declared_at
            assert by_raw[raw]["confidence_tier"] == "RESOLVED"

        heuristic = [row for row in child_calls if row["confidence_tier"] == "HEURISTIC"]
        # What is left is what no receiver type can settle: $x->go (untyped) + static:: (late).
        assert len(heuristic) == 2
        assert {row["target_raw"] for row in heuristic} == {
            "go",
            "\\App\\Recv\\Child::go",
        }
