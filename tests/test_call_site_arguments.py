"""Task 049: select call sites by argument shape.

The question this exists for is "of the N callers of this shared helper, which pass a literal
``null`` at position 2" — a decision about where a fix belongs. The answer has to be a *count*
against a denominator, so every test here asserts what was matched **and** what was not judged.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from tests.php_adapter_cli import needs_php, parse_file

TARGET = "\\Db::query"
CALLER_FILE = "callers.php"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def db_config(tmp_path: Path, *, max_results: int = 10) -> Config:
    return replace(
        load_config(tmp_path, {}), db_path=tmp_path / "graph.db", max_results=max_results
    )


def call(source: str, line: int, args: list[str | None] | None) -> dict[str, object]:
    edge: dict[str, object] = {
        "kind": "CALLS",
        "source_qname": source,
        "target_raw": "query",
        "target_qname": TARGET,
        "file_path": CALLER_FILE,
        "line": line,
        "confidence_tier": "RESOLVED",
    }
    if args is not None:
        edge["args"] = args
    return edge


def plant(store: GraphStore, root: Path, edges: list[dict[str, object]]) -> None:
    """One target node plus N call sites, with on-disk bytes so freshness does not intervene."""
    body = b"# planted\n"
    for path in (CALLER_FILE, "db.php"):
        (root / path).write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    store.upsert_file("db.php", digest, "lang")
    store.replace_file_rows(
        "db.php",
        [
            {
                "kind": "Class",
                "name": "Db",
                "qualified_name": "\\Db",
                "file_path": "db.php",
                "line_start": 1,
            },
            {
                "kind": "Method",
                "name": "query",
                "qualified_name": TARGET,
                "file_path": "db.php",
                "line_start": 2,
            },
        ],
        [],
    )
    store.upsert_file(CALLER_FILE, digest, "lang")
    store.replace_file_rows(
        CALLER_FILE,
        [
            {
                "kind": "Function",
                "name": f"c{index}",
                "qualified_name": f"\\c{index}",
                "file_path": CALLER_FILE,
                "line_start": index + 1,
            }
            for index in range(len(edges))
        ],
        edges,
    )


def a_population(store: GraphStore, root: Path) -> None:
    """25 call sites: 3 pass literal null at 2, 4 omit it, 16 pass something else, 2 unrecorded."""
    shapes: list[list[str | None] | None] = (
        [[None, "null"]] * 3 + [[None]] * 4 + [[None, "array"]] * 16 + [None] * 2
    )
    edges = [call(f"\\c{line}", line, args) for line, args in enumerate(shapes, start=1)]
    plant(store, root, edges)


def find(tmp_path: Path, **kwargs: object) -> dict[str, object]:
    return find_callers.create(db_config(tmp_path))(qname=TARGET, **kwargs)


# --- AC1: K of N, with the denominator still visible ----------------------------------------------


def test_a_literal_at_a_position_is_counted_against_the_whole_population(
    store: GraphStore, tmp_path: Path
) -> None:
    a_population(store, tmp_path)

    everything = find(tmp_path)
    matched = find(tmp_path, arg_position=2, arg_is="null")

    assert everything["total_count"] == 25  # N — more than max_results, so truncation is exercised
    assert everything["truncated"] is True
    assert matched["total_count"] == 3  # K
    assert matched["truncated"] is False
    assert len(matched["results"]) == 3  # type: ignore[arg-type]
    assert {str(hit["qname"]) for hit in matched["results"]} == {  # type: ignore[union-attr]
        "\\c1",
        "\\c2",
        "\\c3",
    }


def test_the_unjudgeable_call_sites_are_reported_not_hidden(
    store: GraphStore, tmp_path: Path
) -> None:
    """Unknown is not absent: an unrecorded call site must never be counted either way."""
    a_population(store, tmp_path)

    matched = find(tmp_path, arg_position=2, arg_is="null")
    absent = find(tmp_path, arg_position=2, arg_is="absent")

    assert matched["args_unrecorded"] == 2
    assert absent["args_unrecorded"] == 2
    # 3 null + 4 absent + 16 other + 2 unrecorded = 25; the unrecorded two are in no bucket.
    dynamic = find(tmp_path, arg_position=2, arg_is="dynamic")
    array = find(tmp_path, arg_position=2, arg_is="array")
    assert (matched["total_count"], absent["total_count"]) == (3, 4)
    assert (array["total_count"], dynamic["total_count"]) == (16, 0)


# --- AC2: "omits it" and "passes null" are different questions ------------------------------------


def test_absent_and_null_are_distinguished(store: GraphStore, tmp_path: Path) -> None:
    a_population(store, tmp_path)

    absent = find(tmp_path, arg_position=2, arg_is="absent")

    assert absent["total_count"] == 4
    assert {str(hit["qname"]) for hit in absent["results"]} == {  # type: ignore[union-attr]
        "\\c4",
        "\\c5",
        "\\c6",
        "\\c7",
    }


def test_position_one_is_the_first_argument_not_the_zeroth(
    store: GraphStore, tmp_path: Path
) -> None:
    plant(store, tmp_path, [call("\\c1", 1, ["null", "number"])])

    assert find(tmp_path, arg_position=1, arg_is="null")["total_count"] == 1
    assert find(tmp_path, arg_position=2, arg_is="number")["total_count"] == 1
    assert find(tmp_path, arg_position=1, arg_is="number")["total_count"] == 0


# --- AC3: filtering never changes what a hit claims about itself ----------------------------------


def test_filtering_does_not_change_a_hit_s_confidence_tier(
    store: GraphStore, tmp_path: Path
) -> None:
    edges = [call("\\c1", 1, [None, "null"]), call("\\c2", 2, [None, "null"])]
    edges[1]["confidence_tier"] = "HEURISTIC"
    plant(store, tmp_path, edges)

    matched = find(tmp_path, arg_position=2, arg_is="null")

    tiers = {str(hit["qname"]): hit["confidence_tier"] for hit in matched["results"]}  # type: ignore[union-attr]
    assert tiers == {"\\c1": "RESOLVED", "\\c2": "HEURISTIC"}


# --- AC5: the filter is opt-in, and off it changes nothing ----------------------------------------


def test_an_unfiltered_call_is_unchanged_by_this_feature(
    store: GraphStore, tmp_path: Path
) -> None:
    a_population(store, tmp_path)

    found = find(tmp_path)

    assert "args_unrecorded" not in found
    assert found["total_count"] == 25


def test_an_index_without_recorded_arguments_matches_nothing_and_says_so(
    store: GraphStore, tmp_path: Path
) -> None:
    """A pre-v3 index (or an adapter that records nothing) must report an empty, honest answer."""
    plant(store, tmp_path, [call(f"\\c{n}", n, None) for n in range(1, 4)])

    matched = find(tmp_path, arg_position=2, arg_is="null")

    assert matched["total_count"] == 0
    assert matched["args_unrecorded"] == 3
    assert matched["results"] == []


# --- R5.3: a typo fails loud rather than reading as "no matches" ----------------------------------


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"arg_position": 2}, "set together"),
        ({"arg_is": "null"}, "set together"),
        ({"arg_position": 0, "arg_is": "null"}, "1-based"),
        ({"arg_position": 2, "arg_is": "nul"}, "unknown arg_is"),
        ({"arg_position": 2, "arg_is": "null", "depth": 2}, "depth=1"),
    ],
)
def test_a_malformed_filter_raises(
    store: GraphStore, tmp_path: Path, kwargs: dict[str, object], message: str
) -> None:
    plant(store, tmp_path, [call("\\c1", 1, [None, "null"])])

    with pytest.raises(ValueError, match=message):
        find(tmp_path, **kwargs)


# --- the adapter half: what PHP actually records -------------------------------------------------


@needs_php
def test_the_php_adapter_records_argument_literal_categories(tmp_path: Path) -> None:
    source = tmp_path / "args.php"
    source.write_text(
        "<?php\n"
        "class A {\n"
        "    public function run($db, $rest) {\n"
        "        $db->q($sql, null);\n"
        "        $db->q($sql);\n"
        "        $db->q('s', 1, true, false, []);\n"
        "        $db->q(...$rest);\n"
        "        $db->q(sql: $sql, params: null);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    result = parse_file(source)

    calls = {
        int(str(edge["line"])): edge
        for edge in result["edges"]  # type: ignore[union-attr]
        if edge["kind"] == "CALLS"
    }
    assert calls[4]["args"] == [None, "null"]
    assert calls[5]["args"] == [None]
    assert calls[6]["args"] == ["string", "number", "true", "false", "array"]
    # A spread hides the count and a named argument frees its position — neither is recordable.
    assert "args" not in calls[7]
    assert "args" not in calls[8]


@needs_php
def test_recorded_arguments_survive_the_json_contract(tmp_path: Path) -> None:
    """The adapter writes one JSON line; `args` must arrive as a list, not a string."""
    source = tmp_path / "one.php"
    source.write_text("<?php f($a, null);\n", encoding="utf-8")

    line = json.dumps(parse_file(source))

    assert '"args": [null, "null"]' in line or '"args":[null,"null"]' in line
