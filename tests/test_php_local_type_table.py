"""Task 137: the receiver's type decides the target, and the tier follows the evidence.

136 measured local type information behind >=99% of the HEURISTIC share. Two mechanisms settle
it and they are separately measurable: a **hierarchy walk** for a method an ancestor or trait
declares (no type inference at all -- the graph already holds the edges), and a **local type
table** for `$obj->m()`. Both are asserted at the store level, because a target that is precise
but unlinked, or linked at the wrong tier, is the failure this ticket exists to prevent (AC5).
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from tests.php_adapter_cli import ENTRY, FIXTURES, PHP, ROOT, needs_php, parse_file

PHP_ENTRY = ENTRY
FIXTURE_FILES = ("local_types_base.php", "local_types.php")


def _calls(result: dict[str, object]) -> list[dict[str, object]]:
    edges = result.get("edges")
    assert isinstance(edges, list)
    return [e for e in edges if isinstance(e, dict) and e.get("kind") == "CALLS"]


def _shapes(name: str) -> set[tuple[str, object]]:
    result = parse_file(FIXTURES.relative_to(ROOT) / name)
    return {(str(e.get("target_raw")), e.get("confidence_tier")) for e in _calls(result)}


def _indexed(tmp_path: Path) -> GraphStore:
    """Index the fixture pair and hand back an open store (both files, one build)."""
    src = tmp_path / "src"
    src.mkdir()
    for name in FIXTURE_FILES:
        shutil.copy(FIXTURES / name, src / name)
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
    store = GraphStore(db_path)
    report = full_build(config, store)
    assert report.failed == 0 and report.parsed == len(FIXTURE_FILES)
    return store


def _by_raw(store: GraphStore, source: str) -> dict[str, dict[str, object]]:
    rows = store.edges_by_source(source, kinds=("CALLS",), limit=50)
    return {str(row["target_raw"]): dict(row) for row in rows}


@needs_php
def test_ac5_an_inherited_receiver_names_the_class_it_was_called_on() -> None:
    """`$this->m()` with no local declaration is `\\Enclosing::m` -- never a bare name."""
    shapes = _shapes("local_types.php")
    assert ("\\App\\Types\\Engine::boot", None) in shapes
    assert ("\\App\\Types\\Engine::log", None) in shapes
    assert ("\\App\\Types\\Engine::run", None) in shapes
    assert not {raw for raw, _ in shapes} & {"boot", "log", "run"}


@needs_php
def test_ac3_a_receiver_with_no_ancestry_is_not_evidence() -> None:
    """No parent, interface or trait means nothing can declare it -- the guess stays a guess."""
    shapes = _shapes("local_types.php")
    assert ("whatever", "HEURISTIC") in shapes
    assert ("\\App\\Types\\Magic::whatever", None) not in shapes
    # A trait's $this is the using class; naming the trait would fabricate a host (029 AC2).
    assert ("hostMethod", "HEURISTIC") in shapes


@needs_php
def test_ac5_the_walk_links_the_ancestor_that_declares_it_at_resolved(tmp_path: Path) -> None:
    """The proving assertion: target *and* tier, after a real cross-file build."""
    with _indexed(tmp_path) as store:
        rows = _by_raw(store, "\\App\\Types\\Engine::start")
        expected = {
            "\\App\\Types\\Engine::boot": "\\App\\Types\\Machine::boot",
            "\\App\\Types\\Engine::log": "\\App\\Types\\Logs::log",
            "\\App\\Types\\Engine::run": "\\App\\Types\\Runner::run",
        }
        for raw, declared_at in expected.items():
            assert raw in rows, f"{raw} was never emitted"
            assert rows[raw]["target_qname"] == declared_at
            assert rows[raw]["confidence_tier"] == "RESOLVED"


@needs_php
def test_ac3_an_unanswerable_receiver_is_still_linked_by_name_at_heuristic(
    tmp_path: Path,
) -> None:
    """The walk must not cost recall: what it cannot answer keeps the name-match path."""
    with _indexed(tmp_path) as store:
        rows = _by_raw(store, "\\App\\Types\\Magic::go")
        assert rows["whatever"]["confidence_tier"] == "HEURISTIC"


@needs_php
def test_ac1_every_spec_source_of_a_receiver_type_names_the_same_target() -> None:
    """One assertion per source, because each is a separate rule and fails separately."""
    result = parse_file(FIXTURES.relative_to(ROOT) / "local_types.php")
    calls = _calls(result)
    spin = [e for e in calls if str(e.get("target_raw")).endswith("spin")]
    by_line = {int(str(e["line"])): str(e["target_raw"]) for e in spin}
    source = (FIXTURES / "local_types.php").read_text(encoding="utf-8").splitlines()
    named = "\\App\\Types\\Wheel::spin"

    settled = {
        "[new]": named,
        "[param-hint]": named,
        "[promoted]": named,
        "[typed-property]": named,
        "[return-hint]": named,
        "[self-return]": named,
        "[single-class-union]": named,
        "[nullsafe]": named,
        # A hint the code has written past is not evidence about what the variable holds now.
        "[rebound]": "spin",
        # The parameter is a list of Wheel; binding it to Wheel would claim a type PHP never gives.
        "[variadic]": "spin",
    }
    for marker, expected in settled.items():
        lines = [n for n, text in enumerate(source, 1) if marker in text]
        assert len(lines) == 1, f"fixture marker {marker!r} is not unique"
        assert by_line[lines[0]] == expected, marker


@needs_php
def test_ac3_a_catch_declares_the_type_of_what_it_caught() -> None:
    shapes = _shapes("local_types.php")
    assert ("\\RuntimeException::getMessage", None) in shapes


@needs_php
def test_ac1_a_receiver_from_another_file_defers_to_the_graph() -> None:
    """The file names the member, never its type — so the claim names the member (137)."""
    shapes = _shapes("local_types.php")
    assert ("\\App\\Types\\Depot::issue()::boot", None) in shapes
    assert ("\\App\\Types\\Depot::chain()::issue", None) in shapes


@needs_php
def test_ac1_the_graph_reads_the_declared_type_the_file_could_not(tmp_path: Path) -> None:
    """Two rounds: what did that member declare, and who declares the method on it."""
    with _indexed(tmp_path) as store:
        rows = _by_raw(store, "\\App\\Types\\Yard::collect")
        # `issue(): Machine`, and Machine declares boot.
        boot = rows["\\App\\Types\\Depot::issue()::boot"]
        assert boot["target_qname"] == "\\App\\Types\\Machine::boot"
        assert boot["confidence_tier"] == "RESOLVED"
        # `chain(): self` is the class that declared it, so the chain stays on Depot.
        chained = rows["\\App\\Types\\Depot::chain()::issue"]
        assert chained["target_qname"] == "\\App\\Types\\Depot::issue"
        assert chained["confidence_tier"] == "RESOLVED"
        # Two steps, neither answerable in the calling file: Depot -> Depot -> Machine.
        walked = rows["\\App\\Types\\Depot::chain()::issue()::boot"]
        assert walked["target_qname"] == "\\App\\Types\\Machine::boot"
        assert walked["confidence_tier"] == "RESOLVED"


@needs_php
def test_ac3_a_known_receiver_that_lacks_the_member_stays_a_precise_unlinked_claim(
    tmp_path: Path,
) -> None:
    """The walk answered the receiver: Machine. Machine has no spin(), and some other class's
    spin() is not a better answer than saying so — that is the vendor cap 136 measured, and
    trading a precise unlinked claim for an imprecise linked one is how it gets hidden."""
    with _indexed(tmp_path) as store:
        row = _by_raw(store, "\\App\\Types\\Yard::collect")[
            "\\App\\Types\\Depot::issue()::spin"
        ]
        assert row["target_qname"] is None
        assert row["confidence_tier"] == "RESOLVED"


@needs_php
def test_ac3_a_chain_with_no_declared_type_falls_back_to_the_name(tmp_path: Path) -> None:
    """`untyped()` declares nothing, so there is no receiver at all — only then does the
    name-match path run, and what it finds is a guess (R5.2)."""
    with _indexed(tmp_path) as store:
        row = _by_raw(store, "\\App\\Types\\Yard::collect")[
            "\\App\\Types\\Depot::untyped()::spin"
        ]
        assert row["target_qname"] == "\\App\\Types\\Wheel::spin"
        assert row["confidence_tier"] == "HEURISTIC"


@needs_php
def test_ac3_a_member_only_subtypes_declare_is_a_guess_among_them(tmp_path: Path) -> None:
    """The receiver is certain and the target is not, so the tier grades the target (R5.2)."""
    with _indexed(tmp_path) as store:
        rows = store.edges_by_source("\\App\\Types\\Surveyor::measure", kinds=("CALLS",), limit=20)
        area = [row for row in rows if str(row["target_raw"]) == "\\App\\Types\\Shape::area"]
        assert {str(row["target_qname"]) for row in area} == {
            "\\App\\Types\\Circle::area",
            "\\App\\Types\\Square::area",
        }
        assert {str(row["confidence_tier"]) for row in area} == {"HEURISTIC"}


@needs_php
def test_ac3_a_declared_type_the_graph_holds_no_node_for_is_not_a_receiver(
    tmp_path: Path,
) -> None:
    """`?Depot` reads as one name and names nothing, so the chain broke — it must fall back
    rather than block on a receiver that was never resolved."""
    with _indexed(tmp_path) as store:
        row = _by_raw(store, "\\App\\Types\\Yard::collect")[
            "\\App\\Types\\Depot::maybe()::issue"
        ]
        assert row["target_qname"] == "\\App\\Types\\Depot::issue"
        assert row["confidence_tier"] == "HEURISTIC"
