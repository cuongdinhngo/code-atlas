"""Task 253 — a zero-overlap guess gets labelled token candidates, not a bare no_matches.

Field shape: ``uploadMemberPhoto`` shares no substring with ``UploadPhotoController``.
245/249 routes need overlap or a separator repair; neither fires. Decompose the guess into
name tokens and offer declared symbols that carry them — candidates never enter results.
"""

from __future__ import annotations

from pathlib import Path

from code_atlas import contract
from code_atlas.store import GraphStore
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_OK,
    REASON_TOKEN_CANDIDATES,
    TRY_INSTEAD_HINT_TOKEN_CANDIDATES,
    TRY_INSTEAD_HINT_TOKEN_CANDIDATES_NONE,
    TRY_INSTEAD_SEARCH_SYMBOL,
)
from tests.test_nav_tools import (  # noqa: F401 — store is a fixture
    db_config,
    node,
    seed_file,
    store,
)

UPLOAD_PATH = "src/UploadPhotoController.php"
UPLOAD_QNAME = "\\App\\UploadPhotoController"
OTHER_PATH = "src/Member.php"
OTHER_QNAME = "\\App\\Member"


def _seed_upload(graph: GraphStore, root: Path) -> None:
    seed_file(
        graph,
        UPLOAD_PATH,
        [node("Class", "UploadPhotoController", UPLOAD_QNAME, UPLOAD_PATH)],
        [],
        root=root,
    )
    seed_file(
        graph,
        OTHER_PATH,
        [node("Class", "Member", OTHER_QNAME, OTHER_PATH)],
        [],
        root=root,
    )


def test_name_tokens_split_camel_and_snake() -> None:
    assert contract.name_tokens("uploadMemberPhoto") == (
        "upload",
        "member",
        "photo",
    )
    assert contract.name_tokens("upload_member_photo") == (
        "upload",
        "member",
        "photo",
    )
    assert contract.name_tokens("get") == ()
    assert contract.name_tokens("") == ()


def test_zero_overlap_guess_returns_labelled_token_candidates(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC1: uploadMemberPhoto reaches UploadPhotoController via token candidates."""
    _seed_upload(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))("uploadMemberPhoto")
    assert payload["reason"] == REASON_TOKEN_CANDIDATES
    assert payload["reason"] != REASON_OK
    assert payload["reason"] != REASON_NO_MATCHES
    assert payload["results"] == []
    assert payload["total_count"] == 0
    candidates = payload["candidates"]
    assert isinstance(candidates, list) and candidates
    qnames = {c["qname"] for c in candidates}
    assert UPLOAD_QNAME in qnames
    upload = next(c for c in candidates if c["qname"] == UPLOAD_QNAME)
    assert "photo" in upload["matched_tokens"] or "upload" in upload["matched_tokens"]
    assert payload["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_TOKEN_CANDIDATES


def test_token_search_that_finds_none_is_distinct_from_bare_no_matches(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC2: tokens match nothing → token_candidates with empty candidates (search ran)."""
    seed_file(
        store,
        "src/Foo.php",
        [node("Class", "Foo", "\\App\\Foo", "src/Foo.php")],
        [],
        root=tmp_path,
    )
    payload = search_symbol.create(db_config(tmp_path))("zzzxqyvblarg")
    assert contract.name_tokens("zzzxqyvblarg") == ("zzzxqyvblarg",)
    assert payload["reason"] == REASON_TOKEN_CANDIDATES
    assert payload["candidates"] == []
    assert payload["results"] == []
    assert payload["total_count"] == 0
    assert payload["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_TOKEN_CANDIDATES_NONE


def test_candidates_never_enter_results_or_total_count(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC3: existing no_matches consumers reading results/total_count see emptiness."""
    _seed_upload(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))("uploadMemberPhoto")
    assert payload["results"] == []
    assert payload["total_count"] == 0
    assert "candidates" in payload and payload["candidates"]


def test_token_candidates_are_bounded_and_deterministic(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC4: fixed k; identical payloads across runs."""
    _seed_upload(store, tmp_path)
    tool = search_symbol.create(db_config(tmp_path))
    a = tool("uploadMemberPhoto")
    b = tool("uploadMemberPhoto")
    assert a == b
    assert len(a["candidates"]) <= contract.TOKEN_CANDIDATE_K


def test_answers_with_hits_stay_byte_identical(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC5: a real hit never enters the token arm."""
    _seed_upload(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))("UploadPhotoController")
    assert payload["reason"] == REASON_OK
    assert payload["total_count"] >= 1
    assert "candidates" not in payload
