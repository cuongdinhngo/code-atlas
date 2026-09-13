"""Task 183 — `edge_health` splits by the language of the edge's own file.

Round 12 was the first two-language round in the field, and the question the round existed to answer
could not be asked: *"HEURISTIC share for the JS/TS slice?"* — *"no per-language breakdown exists in
any payload."* Every whole-graph number is a blend, so neither language's health is recoverable
and a +9.6 pp HEURISTIC move cannot be attributed to the adapter that caused it.

Spec-driven throughout (R6.2/R2): the two languages are the fixture adapter's arbitrary tokens
`fake` and `second`, never a real language name.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from time import perf_counter

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.store import EDGE_HEALTH_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import get_index_status
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.get_index_status import EDGE_HEALTH_BY_LANGUAGE_FIELD

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
FIELD = EDGE_HEALTH_BY_LANGUAGE_FIELD


def fake_cmd(mode: str = "ok") -> str:
    return shlex.join([sys.executable, str(FAKE), mode])


ONE_ADAPTER = {"CA_WORKERS": "1", "CA_FAKE_CMD": fake_cmd()}
TWO_ADAPTERS = {**ONE_ADAPTER, "CA_SECOND_CMD": fake_cmd("second")}


@pytest.fixture(autouse=True)
def only_these_adapters_ship(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ship exactly the two fixture adapters, so 159's unwired note cannot muddy this."""
    root = tmp_path / "shipped"
    for name in ("fake", "second"):
        (root / name / "src").mkdir(parents=True)
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", root)


def write(root: Path, path: str, body: str = "x\n") -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def config_for(root: Path, env: dict[str, str]):
    return load_config(root, {**env, "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")})


def seed_two_languages(root: Path) -> None:
    """Both languages carry edges, and one edge crosses the boundary.

    `dep/*` calls `lib/core.aa::Thing` at HEURISTIC and `dep/extends_*` EXTENDS `\\Dup` at RESOLVED,
    so each language holds two tiers. `dep/cross.cc` is declared in a `second` file and targets a
    `fake` file — the cross-language edge AC4 is about.
    """
    write(root, "lib/core.aa")
    write(root, "dup/d.aa")
    write(root, "dep/a.aa")
    write(root, "dep/extends_a.aa")
    write(root, "dep/cross.cc")
    write(root, "dep/extends_b.cc")


def build(root: Path, env: dict[str, str]):
    config = config_for(root, env)
    build_tool(config)(full=True)
    return config


def verbose(config) -> dict[str, object]:
    return get_index_status.create(config, (get_index_status.NAME,))(detail_level="verbose")


def total_by_tier(block: dict[str, object]) -> dict[str, int]:
    """Sum every bucket's `by_tier` — the identity an outsider checks (082)."""
    buckets = [*dict(block["by_language"]).values()]  # type: ignore[arg-type]
    if "unattributed" in block:
        buckets.append(block["unattributed"])
    summed: dict[str, int] = {}
    for bucket in buckets:
        for tier, count in dict(bucket["by_tier"]).items():  # type: ignore[index]
            summed[tier] = summed.get(tier, 0) + int(count)
    return summed


def test_a_two_language_index_reports_a_mix_that_sums_to_the_whole_graph(tmp_path: Path) -> None:
    """AC1: both languages appear, and the split reconciles against `edge_health` in the payload."""
    seed_two_languages(tmp_path)
    payload = verbose(build(tmp_path, TWO_ADAPTERS))

    block = payload[FIELD]
    by_language = dict(block["by_language"])  # type: ignore[index]
    assert sorted(by_language) == ["fake", "second"]
    assert total_by_tier(block) == payload["edge_health"]["by_tier"]  # type: ignore[index]

    whole = payload["edge_health"]
    linked = sum(int(b["linked"]) for b in by_language.values())  # type: ignore[index]
    unlinked = sum(int(b["unlinked"]) for b in by_language.values())  # type: ignore[index]
    assert linked == whole["linked"]  # type: ignore[index]
    assert unlinked == whole["unlinked"]  # type: ignore[index]

    # The blend the field exists to break apart: each language has its own HEURISTIC share.
    assert by_language["fake"]["by_tier"]["HEURISTIC"] > 0  # type: ignore[index]
    assert by_language["second"]["by_tier"]["HEURISTIC"] > 0  # type: ignore[index]


def test_a_cross_language_edge_is_attributed_to_the_file_that_declared_it(
    tmp_path: Path,
) -> None:
    """AC4: `dep/cross.cc` targets a `fake` file; the edge is one row of `second`, counted once."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    with GraphStore(config.db_path) as store:
        rows = store._conn.execute(
            "SELECT COUNT(*) FROM edges WHERE file_path = ?", ("dep/cross.cc",)
        ).fetchone()
        assert rows[0] == 1, "the fixture must plant exactly one edge in the crossing file"
        computed = store.edge_health_by_language()

    second = dict(computed["by_language"])["second"]  # type: ignore[index]
    fake = dict(computed["by_language"])["fake"]  # type: ignore[index]
    # Counted under the declaring language, and NOT double-counted under the target's.
    assert int(second["by_tier"]["HEURISTIC"]) == 1  # type: ignore[index]
    assert int(fake["by_tier"]["HEURISTIC"]) == 1  # type: ignore[index]
    assert total_by_tier(computed)["HEURISTIC"] == 2


def test_a_single_language_index_is_byte_identical(tmp_path: Path) -> None:
    """AC2/061: one bucket adds nothing the whole-graph number does not already give."""
    write(tmp_path, "lib/core.aa")
    write(tmp_path, "dep/a.aa")
    payload = verbose(build(tmp_path, ONE_ADAPTER))

    assert FIELD not in payload
    assert payload["edge_health"]["by_tier"]["HEURISTIC"] > 0  # type: ignore[index]


def test_the_breakdown_is_absent_from_minimal(tmp_path: Path) -> None:
    """AC3 (261): absent from minimal; standard = verdict; verbose = full stamp."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    tool = get_index_status.create(config, (get_index_status.NAME,))

    assert FIELD not in tool(detail_level="minimal")
    standard = tool(detail_level="standard")
    assert FIELD in standard
    assert "edge_health" in standard, "the whole-graph number stays where it was"
    assert "pairs" not in json.dumps(standard[FIELD])
    verbose = tool(detail_level="verbose")
    assert FIELD in verbose
    assert "pairs" in verbose[FIELD]["cross_language"]  # type: ignore[index]


def test_a_pre_183_index_says_nothing_rather_than_guessing(tmp_path: Path) -> None:
    """AC6/R5.6: no stamp means the split was never measured — not that there is one language."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    with GraphStore(config.db_path) as store:
        store.delete_meta(EDGE_HEALTH_BY_LANGUAGE_KEY)
        assert store.stamped_edge_health_by_language() is None
        # A stamp that is present but unreadable is the same answer: silence, not a guess.
        store.set_meta(EDGE_HEALTH_BY_LANGUAGE_KEY, "not json at all")
        assert store.stamped_edge_health_by_language() is None

    payload = verbose(config)
    assert FIELD not in payload
    assert "edge_health" in payload, "the whole-graph number is unaffected by the missing stamp"


def test_an_edge_whose_file_has_no_language_row_is_carried_not_dropped(tmp_path: Path) -> None:
    """The bucket is not decorative: `edges.file_path` has no foreign key, so it can fill."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    with GraphStore(config.db_path) as store:
        before = store.edge_health()
        store._conn.execute(
            "INSERT INTO edges (kind, source_qname, target_raw, file_path, line, confidence_tier) "
            "VALUES ('CALLS', 'x', 'y', 'not/in/files.zz', 1, 'DYNAMIC')"
        )
        store._conn.commit()
        after = store.edge_health()
        computed = store.edge_health_by_language()

    assert after["by_tier"]["DYNAMIC"] == before["by_tier"]["DYNAMIC"] + 1  # type: ignore[index]
    assert "unattributed" in computed
    assert int(computed["unattributed"]["by_tier"]["DYNAMIC"]) == 1  # type: ignore[index]
    # Still reconciles — which is the whole point of carrying it rather than dropping it.
    assert total_by_tier(computed) == after["by_tier"]


def test_the_stamp_is_read_from_meta_and_the_answer_path_adds_no_group_by(
    tmp_path: Path,
) -> None:
    """AC5: the split is stamped once; a verbose answer is a meta read plus a JSON parse."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)

    with GraphStore(config.db_path) as store:
        raw = store.get_meta(EDGE_HEALTH_BY_LANGUAGE_KEY)
        assert raw is not None
        assert json.loads(raw) == store.edge_health_by_language()

        traced: list[str] = []
        store._conn.set_trace_callback(traced.append)
        store.stamped_edge_health_by_language()
        store._conn.set_trace_callback(None)
    assert len(traced) == 1, traced
    assert "GROUP BY" not in traced[0]

    tool = get_index_status.create(config, (get_index_status.NAME,))
    started = perf_counter()
    for _ in range(50):
        tool(detail_level="verbose")
    per_call_ms = (perf_counter() - started) / 50 * 1000
    assert per_call_ms < 50.0, f"{per_call_ms:.3f} ms per verbose answer"


def test_the_stamp_is_bounded_on_a_large_edge_table(tmp_path: Path) -> None:
    """AC5: the one build-time statement, timed on a corpus big enough for the shape to matter."""
    with GraphStore(tmp_path / "big.db") as store:
        for path, language in (("a.aa", "fake"), ("b.cc", "second")):
            store.upsert_file(path, "d", language)
        store._conn.commit()
        rows = [
            (
                "CALLS",
                f"s{i}",
                None,
                "t",
                "a.aa" if i % 2 else "b.cc",
                1,
                "HEURISTIC" if i % 3 else "RESOLVED",
            )
            for i in range(200_000)
        ]
        store._conn.executemany(
            "INSERT INTO edges (kind, source_qname, target_qname, target_raw, file_path, line, "
            "confidence_tier) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        store._conn.commit()

        started = perf_counter()
        computed = store.edge_health_by_language()
        elapsed_ms = (perf_counter() - started) * 1000

    assert sorted(dict(computed["by_language"])) == ["fake", "second"]  # type: ignore[arg-type]
    assert total_by_tier(computed) == {"RESOLVED": 66_667, "HEURISTIC": 133_333, "DYNAMIC": 0}
    assert elapsed_ms < 4_000, f"{elapsed_ms:.0f} ms over 200k edges"


def test_the_split_is_deterministic_and_key_ordered(tmp_path: Path) -> None:
    """AC7/R4.2: identical input, identical bytes — including key order, since it is stamped."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    with GraphStore(config.db_path) as store:
        first = store.edge_health_by_language()
        second = store.edge_health_by_language()
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert list(dict(first["by_language"])) == sorted(dict(first["by_language"]))  # type: ignore[arg-type]


def cross_language(block: dict[str, object]) -> dict[str, object]:
    return dict(block["cross_language"])  # type: ignore[arg-type]


def test_the_cross_language_row_counts_the_boundary_183_cannot_see(tmp_path: Path) -> None:
    """204 AC4: two `second` files reach a `fake` one, and 183's rows call both healthy `second`.

    The row names the boundary as well as the tier, so a non-zero value says WHICH pair to look at
    — a bare total would leave the reader with the same unattributable blend 183 broke apart. It
    counts every crossing, not only the guessed ones: `dep/extends_b.cc` EXTENDS a qname another
    language declares and resolves at **RESOLVED**, which is a crossing on real evidence. That is
    the row's job — report the boundary; 204 removes only the BARE-NAME guesses across it.
    """
    seed_two_languages(tmp_path)
    payload = verbose(build(tmp_path, TWO_ADAPTERS))

    row = cross_language(dict(payload[FIELD]))  # type: ignore[arg-type]
    assert row["linked"] == 2
    assert row["unlinked"] == 0
    assert dict(row["by_tier"]) == {"RESOLVED": 1, "HEURISTIC": 1, "DYNAMIC": 0}
    assert row["pairs"] == {"second->fake": 2}
    # 183's own rows are unchanged and still count both under the DECLARING language only.
    by_language = dict(dict(payload[FIELD])["by_language"])  # type: ignore[index]
    assert int(by_language["second"]["by_tier"]["HEURISTIC"]) == 1  # type: ignore[index]
    assert int(by_language["second"]["by_tier"]["RESOLVED"]) == 1  # type: ignore[index]


def test_a_single_language_index_measures_the_row_as_zero(tmp_path: Path) -> None:
    """A measured 0 is a different claim from an unmeasured one (R5.6) — the key is always there."""
    write(tmp_path, "lib/core.aa")
    write(tmp_path, "dep/a.aa")
    config = build(tmp_path, ONE_ADAPTER)

    with GraphStore(config.db_path) as store:
        row = cross_language(store.edge_health_by_language())
    assert row["linked"] == 0
    assert row["pairs"] == {}


def test_a_pre_204_stamp_reports_no_row_rather_than_a_zero(tmp_path: Path) -> None:
    """P7: an index stamped before this ticket never measured the boundary; it must not read 0."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)

    with GraphStore(config.db_path) as store:
        stamped = store.stamped_edge_health_by_language()
        assert stamped is not None
        del stamped["cross_language"]
        store.set_meta(EDGE_HEALTH_BY_LANGUAGE_KEY, json.dumps(stamped, sort_keys=True))

    payload = verbose(config)
    assert "cross_language" not in dict(payload[FIELD])
    assert "by_language" in dict(payload[FIELD]), "183's rows are unaffected"
