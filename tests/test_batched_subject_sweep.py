"""Task 101: a ten-name sweep is one call, and every subject keeps its own answer.

The defect was granularity, not cost — the graph took one subject per call, so an agent with ten
names to check reached for a shell loop. These tests pin the batched shape, the fan-out bound and
its disclosure, and that the single-subject payload did not move.

Every guard here ships with a positive control (R6.5 / `prove-the-guard-fails`): the assertion that
would still pass if the guard were removed is paired with one that would not.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from code_atlas.build_info import server_provenance
from code_atlas.config import ConfigError, clamp_subjects
from code_atlas.main import TOOL_NAMES, build_server
from code_atlas.store import GraphStore
from code_atlas.tokens import estimate_tokens
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
)
from tests.test_mcp_server import committed_repo, served_config
from tests.test_nav_tools import db_config, node, seed_file

REPO = Path(__file__).resolve().parent.parent
# The verdict table moved to the tool reference when the README became a decision page.
SURFACE = REPO / "docs" / "TOOLS.md"

UNBATCHED_HEADING = "#### Tools that take one subject at a time"

# The tools that accept a list of subjects (ticket 101 Scope bullet 1). The denominator they are
# checked against is derived from ``TOOL_NAMES``, never listed here (R6.7).
BATCHING = frozenset({search_symbol.NAME})

# The field sweep that lost to `grep -rn`: ten helper names checked before writing the port.
TEN_NAMES = (
    "getState",
    "setState",
    "resetState",
    "mergeState",
    "cloneState",
    "readConfig",
    "writeConfig",
    "flushCache",
    "warmCache",
    "dropCache",
)
TAKEN = ("getState", "flushCache")


@pytest.fixture
def indexed(tmp_path: Path):
    """An index where two of the ten candidate names are already taken."""
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        for index, name in enumerate(TAKEN):
            path = f"src/{name}.aa"
            seed_file(
                store,
                path,
                [node("Function", name, f"\\Lib\\{name}", path)],
                [],
                root=tmp_path,
            )
            del index
    return config


def sweep(config, **kwargs: Any) -> dict[str, Any]:
    return search_symbol.create(config)(**kwargs)


def schemas(server: Any) -> dict[str, Any]:
    async def once() -> dict[str, Any]:
        async with Client(server) as client:
            return {tool.name: tool.inputSchema for tool in await client.list_tools()}

    return asyncio.run(once())


def unbatched_section(text: str) -> str:
    _, _, rest = text.partition(UNBATCHED_HEADING)
    section, _, _ = rest.partition("\n## ")
    return section


# --- AC1 — N subjects, N addressable answers -------------------------------


def test_ten_subjects_return_ten_addressable_answers_in_caller_order(indexed) -> None:
    """PROVING TEST — the whole ticket: one call answers the sweep that drove a shell loop.

    Ten names, one call, ten entries in the order asked, each with its own verdict.
    """
    payload = sweep(indexed, queries=list(TEN_NAMES))

    subjects = payload["subjects"]
    assert [entry["query"] for entry in subjects] == list(TEN_NAMES)
    assert payload["subject_count"] == 10
    taken = {entry["query"] for entry in subjects if entry["reason"] == REASON_OK}
    assert taken == set(TAKEN)
    # Positive control: a collision really is reported, so the equality above is not vacuous.
    assert subjects[0]["total_count"] == 1
    assert subjects[0]["results"][0]["qname"] == "\\Lib\\getState"


def test_the_whole_batched_payload_is_pinned(indexed) -> None:
    """AC1 — the payload is pinned, not just its counts, so a silent field change fails here."""
    payload = sweep(indexed, queries=["getState", "nosuchname"], detail_level="minimal")

    assert payload == {
        "indexed": True,
        "subject_count": 2,
        "subjects": [
            {
                "query": "getState",
                "results": [
                    {
                        "qname": "\\Lib\\getState",
                        "kind": "Function",
                        "file": "src/getState.aa",
                        "line": 1,
                    }
                ],
                "truncated": False,
                "reason": REASON_OK,
                "total_count": 1,
            },
            {
                "query": "nosuchname",
                "results": [],
                "truncated": False,
                "reason": REASON_NO_MATCHES,
                "total_count": 0,
            },
        ],
        "index_root": str(Path(indexed.root).resolve()),
        # 223: minimal demotes the coverage note; identity still rides the batch envelope.
        **server_provenance(),
    }


def test_a_repeated_subject_is_answered_once_per_position(indexed) -> None:
    """AC1 — no dedupe: answer *i* answers subject *i*, or positional addressing breaks."""
    payload = sweep(indexed, queries=["getState", "getState"])

    assert payload["subject_count"] == 2
    assert [entry["query"] for entry in payload["subjects"]] == ["getState", "getState"]


def test_subject_order_follows_the_caller_not_the_store(indexed) -> None:
    """C1 / R4.2 — the reversed request comes back reversed, not re-ranked."""
    forward = sweep(indexed, queries=list(TEN_NAMES))
    reverse = sweep(indexed, queries=list(reversed(TEN_NAMES)))

    assert [entry["query"] for entry in reverse["subjects"]] == list(reversed(TEN_NAMES))
    assert [entry["query"] for entry in forward["subjects"]] != [
        entry["query"] for entry in reverse["subjects"]
    ]  # positive control: the two orders are genuinely different


# --- R4 / AC1 — one miss must not colour the rest --------------------------


def test_one_miss_in_a_batch_of_ten_does_not_colour_the_other_nine(indexed) -> None:
    """R4 (065 element-wise) — each subject's reason is computed from its own query."""
    payload = sweep(indexed, queries=["nosuchname", *TAKEN])

    reasons = [entry["reason"] for entry in payload["subjects"]]
    assert reasons == [REASON_NO_MATCHES, REASON_OK, REASON_OK]
    # Positive control: the batch does not carry a reason of its own to leak downward.
    assert "reason" not in payload


# --- AC2 — the bound is disclosed, and names what it dropped ---------------


def test_exceeding_the_bound_names_every_dropped_subject(indexed) -> None:
    """AC2 / 066 — a silently truncated sweep is worse than ten honest calls."""
    config = replace(indexed, max_subjects=4)
    payload = sweep(config, queries=list(TEN_NAMES))

    assert payload["subject_count"] == 4
    assert payload["subjects_capped_to"] == 4
    assert payload["subjects_dropped"] == list(TEN_NAMES[4:])
    assert len(payload["subjects_dropped"]) == 6  # the count is the list's length (061)
    assert [entry["query"] for entry in payload["subjects"]] == list(TEN_NAMES[:4])


def test_a_batch_within_the_bound_says_nothing_about_a_clamp(indexed) -> None:
    """066/061 — the disclosure appears only when it happened; control for the test above."""
    payload = sweep(indexed, queries=list(TEN_NAMES))

    assert "subjects_capped_to" not in payload
    assert "subjects_dropped" not in payload


def test_clamp_subjects_splits_at_the_bound_and_refuses_a_useless_one() -> None:
    """The bound is a config concern; a bound below 1 would accept no subject at all (R5.3)."""
    kept, dropped = clamp_subjects(list("abcde"), 3)
    assert (kept, dropped) == (["a", "b", "c"], ["d", "e"])

    kept, dropped = clamp_subjects(list("ab"), 25)
    assert (kept, dropped) == (["a", "b"], [])

    with pytest.raises(ConfigError, match="CA_MAX_SUBJECTS"):
        clamp_subjects(["a"], 0)


def test_the_default_bound_leaves_the_field_sweep_room(tmp_path: Path) -> None:
    """CL-6 — ten is the measured case; the default must not clamp it."""
    assert db_config(tmp_path).max_subjects >= len(TEN_NAMES)


# --- AC3 — the single-subject answer did not move --------------------------


def test_a_single_subject_payload_is_unchanged(indexed) -> None:
    """AC3 (narrowed by D2) — dict-equal to the pre-101 shape; 223 demotes envelope off minimal.

    Coverage disclosure and ``server_*`` return at ``standard``/``verbose`` (ask for them).
    """
    payload = sweep(indexed, query="getState", detail_level="minimal")

    assert payload == {
        "indexed": True,
        "results": [
            {
                "qname": "\\Lib\\getState",
                "kind": "Function",
                "file": "src/getState.aa",
                "line": 1,
            }
        ],
        "truncated": False,
        "reason": REASON_OK,
        "total_count": 1,
        "index_root": str(Path(indexed.root).resolve()),
    }
    assert "unconfigured_adapters" not in payload
    assert "server_version" not in payload
    # Positive control: the batched keys are absent from a single-subject answer.
    assert "subjects" not in payload
    assert "subject_count" not in payload
    standard = sweep(indexed, query="getState", detail_level="standard")
    assert "unconfigured_adapters" in standard
    assert "server_version" in standard


def test_a_single_subject_call_still_takes_its_query_positionally(indexed) -> None:
    """AC3 — an existing caller passing the query positionally is unaffected."""
    assert sweep(indexed, query="getState") == search_symbol.create(indexed)("getState")


def test_a_missing_index_answers_the_call_not_each_subject(indexed, tmp_path: Path) -> None:
    """061 — N identical empty answers would read as N proofs of absence (schema_guard's rule)."""
    empty = replace(indexed, db_path=tmp_path / "absent" / "graph.db")
    payload = sweep(empty, queries=list(TEN_NAMES))

    assert payload["indexed"] is False
    assert payload["reason"] == REASON_NOT_INDEXED
    assert "subjects" not in payload
    # Positive control: the single-subject not-indexed answer is untouched, results key and all.
    assert sweep(empty, query="getState")["results"] == []


# --- R5.3 — the argument pair fails loud -----------------------------------


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"query": "a", "queries": ["a"]}, "never both"),
        ({}, "one subject"),
        ({"queries": []}, "at least one subject"),
    ],
)
def test_the_subject_arguments_fail_loud(indexed, kwargs, message) -> None:
    """R5.3 — silently preferring one spelling would hide a caller bug behind a real answer."""
    with pytest.raises(ValueError, match=message):
        sweep(indexed, **kwargs)


# --- C5 — one repair budget for the call, disclosed per subject ------------


def test_the_sweep_shares_one_read_through_budget(indexed, monkeypatch) -> None:
    """C5 — one guard for the whole call, and the refusal it causes is disclosed.

    The first subject spends the cap; the second's repair is refused. That refusal must surface as
    ``index_stale``, never silently as ``no_matches`` — a sweep that reports a quieter reason than
    it earned is attesting past its own resolution.

    The planted file is made to *really* drift: ``FreshnessGuard.ensure`` checks ``file_is_current``
    before the cap, so a fixture whose bytes still match their digest never reaches the budget at
    all and this guard would pass however the budget were scoped.
    """
    from code_atlas.tools import freshness

    (indexed.root / "src/getState.aa").write_bytes(b"# drifted\n")

    calls: list[str] = []

    def counted(config, store, path):  # noqa: ANN001 — test double
        calls.append(path)
        return True

    monkeypatch.setattr(freshness, "reparse_file", counted)
    monkeypatch.setattr(
        freshness, "dirty_indexed_paths", lambda store, config: ["src/getState.aa"]
    )
    payload = sweep(indexed, queries=["nosuchname", "alsomissing"])

    # Positive control: the cap really was spent by the first subject, not skipped entirely.
    assert len(calls) == freshness.READ_THROUGH_CAP == 1
    assert payload["subjects"][1]["reason"] == REASON_INDEX_STALE


# --- AC4 — measure the win, and let it be shape rather than a number -------


def test_the_batched_payload_is_no_heavier_than_ten_single_answers(indexed) -> None:
    """AC4 / 061 — the envelope is stated once, so a sweep must not cost more than the calls it
    replaces. Tokens are the deterministic half; wall clock is recorded in the working doc."""
    singles = sum(
        estimate_tokens(json.dumps(sweep(indexed, query=name))) for name in TEN_NAMES
    )
    batched = estimate_tokens(json.dumps(sweep(indexed, queries=list(TEN_NAMES))))

    assert batched < singles
    # Positive control: the comparison is over a real ten-subject payload, not an empty one.
    assert batched > 0


def test_a_sweep_is_one_store_open_not_ten(indexed, monkeypatch) -> None:
    """AC4 — the call-count win is structural: one connection, one guard, N queries."""
    from code_atlas.tools import search_symbol as module

    opens = 0
    real = module.GraphStore

    class Counting(real):  # type: ignore[misc, valid-type]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            nonlocal opens
            opens += 1
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(module, "GraphStore", Counting)
    sweep(indexed, queries=list(TEN_NAMES))

    assert opens == 1


# --- AC5 — a verdict for every tool, derived not listed --------------------


def test_queries_is_published_on_exactly_the_batching_tools(tmp_path: Path) -> None:
    """AC5 — over a live client, so FastMCP's real schema is the judge (R6.7 denominator)."""
    committed_repo(tmp_path, "src/a.aa")
    published = schemas(build_server(served_config(tmp_path)))

    assert set(published) == set(TOOL_NAMES)  # denominator derived, never listed (R6.7)
    batching = {
        name for name, schema in published.items() if "queries" in schema["properties"]
    }
    assert batching == BATCHING
    assert set(TOOL_NAMES) - BATCHING  # positive control: the exclusion set is not empty
    assert "query" in published[search_symbol.NAME]["properties"]  # D2 — still published


def test_every_unbatched_tool_is_recorded_with_the_reason_it_stays_single(tmp_path: Path) -> None:
    """AC5 — the per-tool verdict is a finding the docs carry, not an omission."""
    section = unbatched_section(SURFACE.read_text(encoding="utf-8"))

    assert section, f"docs/TOOLS.md is missing the {UNBATCHED_HEADING!r} section"
    for name in sorted(set(TOOL_NAMES) - BATCHING):
        assert f"`{name}`" in section, name
    for name in sorted(BATCHING):
        assert f"`{name}`" not in section, name  # positive control


def test_the_verdict_table_gives_every_unbatched_tool_a_reason() -> None:
    """AC5 — *"with reasons"*: a name in a table with an empty cell is not a verdict."""
    section = unbatched_section(SURFACE.read_text(encoding="utf-8"))
    rows = re.findall(r"^\| `([a-z_]+)` \| (.+?) \|$", section, re.MULTILINE)

    assert {name for name, _ in rows} == set(TOOL_NAMES) - BATCHING
    for name, reason in rows:
        assert len(reason.strip()) > 20, name
