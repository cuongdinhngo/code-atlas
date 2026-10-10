"""Task 378 — a one-letter typo answers with the name it meant, beside empty results.

`fts_term` matches the query as one literal trigram phrase, so a typo has no substring hit, and
253's token route fails when the typo sits inside the distinctive token. An edit-distance pass
over declared names suggests the spelling — in `did_you_mean`, never in `results` (R5.6).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from code_atlas.store import (
    GraphStore,
    edit_distance,
    edit_distance_limit,
    edit_pieces,
    name_tail,
)
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import (
    REASON_OK,
    REASON_TOKEN_CANDIDATES,
    TRY_INSTEAD_HINT_DID_YOU_MEAN,
    TRY_INSTEAD_HINT_TOKEN_CANDIDATES,
)
from tests.test_nav_tools import (  # noqa: F401 — store is a fixture
    db_config,
    node,
    seed_file,
    store,
)

PATH = "src/Users.php"


def _seed(graph: GraphStore, root: Path, *names: str) -> None:
    rows = [node("Method", name, f"\\App\\Users::{name}", PATH) for name in names]
    seed_file(graph, PATH, rows, [], root=root)


def test_a_one_letter_typo_suggests_the_name_at_distance_one(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """378 AC1 — red before 378: `getUserByld` answered no suggestion of `getUserById`."""
    _seed(store, tmp_path, "getUserById", "deleteUser")
    payload = search_symbol.create(db_config(tmp_path))("getUserByld")
    assert payload["reason"] == REASON_TOKEN_CANDIDATES
    assert payload["results"] == [] and payload["total_count"] == 0
    assert payload["did_you_mean"][0] == {
        "qname": "\\App\\Users::getUserById",
        "name": "getUserById",
        "kind": "Method",
        "edit_distance": 1,
    }
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_TOKEN_CANDIDATES


def test_equidistant_names_come_back_in_name_order_every_time(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """378 AC2 — ties break on the casefolded name, then the qname; 50 calls are identical."""
    _seed(store, tmp_path, "parseRows", "parseCols", "ParseRowz")
    tool = search_symbol.create(db_config(tmp_path))
    first = json.dumps(tool("parseRowx"), sort_keys=True)
    payload = json.loads(first)
    assert [(d["name"], d["edit_distance"]) for d in payload["did_you_mean"]] == [
        ("parseRows", 1),
        ("ParseRowz", 1),
    ]  # parseCols is three edits away, past the bound of two
    assert all(json.dumps(tool("parseRowx"), sort_keys=True) == first for _ in range(50))


def test_a_query_with_a_hit_never_takes_the_edit_distance_path(
    tmp_path: Path,
    store,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """378 AC3 — an exact hit answers exactly as it would with the path removed."""
    _seed(store, tmp_path, "getUserById", "getUserByIds")
    tool = search_symbol.create(db_config(tmp_path))
    with_path = tool("getUserById")

    def refuse(*_args: object, **_kwargs: object) -> list[object]:
        raise AssertionError("an exact hit reached the edit-distance pass")

    monkeypatch.setattr(GraphStore, "edit_distance_names", refuse)
    assert tool("getUserById") == with_path
    assert with_path["reason"] == REASON_OK and "did_you_mean" not in with_path
    assert tool(queries=["getUserById", "getUserBy"]) == tool(queries=["getUserById", "getUserBy"])


def test_a_sweep_suggests_per_subject(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """378 Scope 3 — a `queries` sweep carries each subject's own suggestions."""
    _seed(store, tmp_path, "getUserById", "deleteUser")
    sweep = search_symbol.create(db_config(tmp_path))(queries=["getUserByld", "deleteUsr"])
    first, second = sweep["subjects"]
    assert first["did_you_mean"][0]["name"] == "getUserById"
    assert second["did_you_mean"][0]["name"] == "deleteUser"


def test_a_typo_inside_a_short_name_is_suggested_under_its_own_hint(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """378 review — red before: `paxse` shares no trigram with `parse`, so nothing was suggested."""
    _seed(store, tmp_path, "parse", "render")
    tool = search_symbol.create(db_config(tmp_path))
    for query, meant in (("paxse", "parse"), ("rendr", "render")):
        payload = tool(query)
        assert payload["candidates"] == [], "253 finds no shared word, so only the spelling helps"
        assert [d["name"] for d in payload["did_you_mean"]] == [meant]
        assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_DID_YOU_MEAN
    answer = tool(queries=["paxse", "rendr"])["subjects"][1]
    assert answer["try_instead_hint"] == TRY_INSTEAD_HINT_DID_YOU_MEAN


def test_every_name_within_the_bound_keeps_one_piece_whole() -> None:
    """The prefilter's pigeonhole: a true match always contains a piece, so none is dropped."""
    rng = random.Random(378)
    alphabet = "abcde_"
    for _ in range(2000):
        query = "".join(rng.choice(alphabet) for _ in range(rng.randint(3, 16)))
        name = list(query)
        for _ in range(rng.randint(0, edit_distance_limit(query))):
            at = rng.randrange(len(name) + 1)
            op = rng.choice("isd")
            if op == "i":
                name.insert(at, rng.choice(alphabet))
            elif at < len(name) and op == "d":
                del name[at]
            elif at < len(name):
                name[at] = rng.choice(alphabet)
        target = "".join(name)
        bound = edit_distance_limit(query)
        if edit_distance(query, target, bound) <= bound:
            assert any(piece in target for piece in edit_pieces(query, bound)), (query, target)


def test_no_near_name_keeps_todays_token_answer(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """Nothing within the bound adds no field — the 253 payload is unchanged."""
    _seed(store, tmp_path, "getUserById")
    payload = search_symbol.create(db_config(tmp_path))("zzzxqyvblarg")
    assert payload["reason"] == REASON_TOKEN_CANDIDATES
    assert "did_you_mean" not in payload


def test_the_distance_is_bounded_and_read_off_the_name_tail() -> None:
    assert name_tail("indexer.full_biuld") == "full_biuld"
    assert name_tail("App\\Users::getUserByld") == "getUserByld"
    assert [edit_distance_limit("x" * n) for n in (5, 6, 10, 11)] == [1, 2, 2, 3]
    assert edit_distance("full_biuld", "full_build", 2) == 2  # a transposition costs two
    assert edit_distance("GETUSERBYLD", "getUserById", 1) == 1
    assert edit_distance("abc", "abcdefgh", 2) == 3  # beyond the bound reads as bound + 1
