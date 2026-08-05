"""Task 037: compound nav responses — the call-site line rides along, opt-in and capped.

Integration layer on purpose: the value claim is "one call answers who *and* show me", which only
holds if a real store, a real edge row, and real bytes on disk line up.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from code_atlas.tools import call_site, find_callers, find_references
from tests.test_nav_tools import db_config, edge, node

_CALL_LINE = 7
_SITE = "user.php"  # where the call is made — the file 037 quotes
_TARGET_FILE = "repo.php"  # where the called symbol lives — the file 035 refreshes
_CALL = "$this->repo->put($k);"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _plant(
    tmp_path: Path, store: GraphStore, rel: str, body: bytes, nodes: list, edges: list
) -> None:
    (tmp_path / rel).write_bytes(body)
    store.upsert_file(rel, hashlib.sha256(body).hexdigest(), "php")
    store.replace_file_rows(rel, nodes, edges)


def _seed(tmp_path: Path, store: GraphStore, *, call_text: str = _CALL) -> None:
    """Caller and callee in **separate** files, as in any real repo.

    Keeping them apart is what lets a test drift the *call-site* file (037/C4) without tripping
    035's subject-file guard, which refreshes the file the queried symbol lives in.
    """
    _plant(
        tmp_path,
        store,
        _TARGET_FILE,
        b"<?php\nclass Repo {\n    public function put($k) {}\n}\n",
        [
            node("Class", "Repo", "\\App\\Repo", _TARGET_FILE),
            node("Method", "put", "\\App\\Repo::put", _TARGET_FILE),
        ],
        [],
    )
    lines = ["<?php", "class User {", "    public function save($k)", "    {", "", ""]
    lines += [f"        {call_text}", "    }", "}"]
    _plant(
        tmp_path,
        store,
        _SITE,
        ("\n".join(lines) + "\n").encode("utf-8"),
        [
            node("Class", "User", "\\App\\User", _SITE),
            node("Method", "save", "\\App\\User::save", _SITE),
        ],
        [
            edge(
                "CALLS",
                "\\App\\User::save",
                "\\App\\Repo::put",
                _SITE,
                target_qname="\\App\\Repo::put",
                line=_CALL_LINE,
            )
        ],
    )


def test_find_callers_include_source_quotes_the_call_line(
    tmp_path: Path, store: GraphStore
) -> None:
    """The proving test: one call returns both the caller and the line it calls from."""
    _seed(tmp_path, store)
    result = find_callers.create(db_config(tmp_path))(
        "\\App\\Repo::put", detail_level="minimal", include_source=True
    )
    hits = result["results"]
    assert isinstance(hits, list) and len(hits) == 1
    assert hits[0]["qname"] == "\\App\\User::save"
    assert hits[0]["line"] == _CALL_LINE
    assert hits[0]["source"] == _CALL  # stripped, one line, no context
    assert "source_stale" not in hits[0]


def test_default_call_is_byte_identical_to_the_pre_flag_payload(
    tmp_path: Path, store: GraphStore
) -> None:
    """C1/W1: opt-in means the common case pays nothing — not one extra key."""
    _seed(tmp_path, store)
    tool = find_callers.create(db_config(tmp_path))
    default = tool("\\App\\Repo::put", detail_level="minimal")
    explicit_off = tool("\\App\\Repo::put", detail_level="minimal", include_source=False)
    assert default == explicit_off
    hits = default["results"]
    assert isinstance(hits, list)
    for hit in hits:
        assert "source" not in hit and "source_stale" not in hit


def test_drifted_site_file_is_never_quoted(tmp_path: Path, store: GraphStore) -> None:
    """C4: bytes changed since indexing ⇒ mark it stale rather than quote the wrong line.

    The edit keeps the file the **same length** and line ``_CALL_LINE`` **populated**, so only the
    hash check can catch it. A shorter file would pass this test via the missing-line path and
    prove nothing about freshness (mutation-checked: deleting the `file_is_current` call turns
    this red).
    """
    _seed(tmp_path, store)
    drifted = (tmp_path / _SITE).read_text(encoding="utf-8").splitlines()
    drifted[_CALL_LINE - 1] = "        $this->repo->DELETE($k);  // moved on since indexing"
    (tmp_path / _SITE).write_text("\n".join(drifted) + "\n", encoding="utf-8")
    result = find_callers.create(db_config(tmp_path))(
        "\\App\\Repo::put", detail_level="minimal", include_source=True
    )
    hits = result["results"]
    assert isinstance(hits, list)
    assert hits[0]["source_stale"] is True
    assert "source" not in hits[0]


def test_missing_site_file_is_never_quoted(tmp_path: Path, store: GraphStore) -> None:
    _seed(tmp_path, store)
    (tmp_path / _SITE).unlink()
    result = find_callers.create(db_config(tmp_path))(
        "\\App\\Repo::put", detail_level="minimal", include_source=True
    )
    hits = result["results"]
    assert isinstance(hits, list)
    assert hits[0]["source_stale"] is True
    assert "source" not in hits[0]


def test_long_call_line_is_truncated_at_the_cap(tmp_path: Path, store: GraphStore) -> None:
    """A minified or generated line must not blow up a compound response."""
    _seed(tmp_path, store, call_text="$x->put(" + "a" * 400 + ");")
    result = find_callers.create(db_config(tmp_path))(
        "\\App\\Repo::put", detail_level="minimal", include_source=True
    )
    hits = result["results"]
    assert isinstance(hits, list)
    source = hits[0]["source"]
    assert isinstance(source, str)
    assert len(source) == call_site.SITE_MAX_CHARS + 1  # + the ellipsis
    assert source.endswith("…")


def test_find_references_takes_the_same_flag(tmp_path: Path, store: GraphStore) -> None:
    _seed(tmp_path, store)
    tool = find_references.create(db_config(tmp_path))
    with_source = tool("\\App\\Repo::put", detail_level="minimal", include_source=True)
    without = tool("\\App\\Repo::put", detail_level="minimal")
    assert isinstance(with_source["results"], list) and isinstance(without["results"], list)
    assert with_source["results"][0]["source"] == _CALL
    assert "source" not in without["results"][0]


def test_file_reads_do_not_scale_with_the_number_of_sites(
    tmp_path: Path, store: GraphStore
) -> None:
    """Grouping by file is the cost story: 4 sites in one file cost the same reads as 1."""
    _seed(tmp_path, store)
    opens: list[str] = []
    real_open = Path.open

    def counting_open(self: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if self.name == _SITE:
            opens.append(str(self))
        return real_open(self, *args, **kwargs)  # type: ignore[arg-type]

    def annotate(count: int) -> int:
        opens.clear()
        hits: list[dict[str, object]] = [
            {"qname": f"c{i}", "file": _SITE, "line": _CALL_LINE} for i in range(count)
        ]
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(Path, "open", counting_open)
            call_site.annotate(tmp_path, store, hits)
        assert all(hit["source"] == _CALL for hit in hits)
        return len(opens)

    assert annotate(4) == annotate(1)


def test_annotate_rejects_a_nonsense_cap(tmp_path: Path, store: GraphStore) -> None:
    _seed(tmp_path, store)
    with pytest.raises(ValueError, match="max_chars must be >= 1"):
        call_site.annotate(tmp_path, store, [], max_chars=0)


def test_hit_without_a_usable_line_is_marked_not_guessed(
    tmp_path: Path, store: GraphStore
) -> None:
    _seed(tmp_path, store)
    hits: list[dict[str, object]] = [
        {"qname": "a", "file": _SITE, "line": None},
        {"qname": "b", "file": "", "line": 3},
        {"qname": "c", "file": _SITE, "line": 9999},
    ]
    snapshot = copy.deepcopy(hits)
    call_site.annotate(tmp_path, store, hits)
    for hit, before in zip(hits, snapshot, strict=True):
        assert hit["source_stale"] is True
        assert "source" not in hit
        assert hit["qname"] == before["qname"]
