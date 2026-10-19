"""Task 404 — a property's bare name finds it as an exact match.

The PHP adapter stores a property as ``$name`` (``\\App\\C::$name``, CONVENTION §3), so on ``main``
``search_symbol "name"`` was neither an exact nor a prefix match of it, and ``$`` was no separator
in the qname suffix check: the property sank below substring near-misses. The stored name stays.
"""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore, is_direct_match
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import REASON_OK
from tests.php_adapter_cli import needs_php
from tests.test_nav_tools import (  # noqa: F401 — store is a fixture
    db_config,
    node,
    seed_file,
    store,
)

BARE = "isInRespite"
PROPERTY = f"\\App\\Care\\Stay::${BARE}"
# Each holds the bare name as a substring, in a short file, so it leads under BM25 (180's shape).
NEAR = ("wasIsInRespite", "thisIsInRespiteFlag")


def _seed(graph: GraphStore, root: Path) -> None:
    for i, name in enumerate(NEAR):
        path = f"n{i}.php"
        seed_file(graph, path, [node("Function", name, name, path)], [], root=root)
    path = "src/app/care/models/long/path/Stay.php"
    seed_file(graph, path, [node("Property", f"${BARE}", PROPERTY, path)], [], root=root)


def _first(payload: dict[str, object]) -> str:
    return str(payload["results"][0]["qname"])  # type: ignore[index]


def test_ac1_the_bare_name_ranks_the_property_first_as_exact(
    tmp_path: Path, store  # noqa: F811
) -> None:
    _seed(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))(BARE)

    assert _first(payload) == PROPERTY, payload
    assert payload["reason"] == REASON_OK


def test_ac2_the_sigil_spelling_is_unchanged(tmp_path: Path, store) -> None:  # noqa: F811
    _seed(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))(f"${BARE}")

    assert _first(payload) == PROPERTY and payload["reason"] == REASON_OK
    assert is_direct_match(f"${BARE}", f"${BARE}", PROPERTY)


def test_a_short_bare_name_finds_its_property(tmp_path: Path, store) -> None:  # noqa: F811
    """The challenger's finding 1: under three characters search takes the LIKE path, not FTS."""
    path = "src/Row.php"
    qname = "\\App\\Row::$id"
    seed_file(store, path, [node("Property", "$id", qname, path)], [], root=tmp_path)
    payload = search_symbol.create(db_config(tmp_path))("id")

    assert [hit["qname"] for hit in payload["results"]] == [qname], payload
    assert payload["total_count"] == 1, "the page and its count read one clause"


def test_the_sigil_is_never_a_wildcard() -> None:
    """Only a leading sigil reads through: a query naming another member still misses."""
    assert not is_direct_match("InRespite", f"${BARE}", PROPERTY)
    assert not is_direct_match(f"${BARE}x", f"${BARE}", PROPERTY)


@needs_php
def test_the_php_adapter_property_is_found_by_its_bare_name(tmp_path: Path) -> None:
    """The field case end to end: `public bool $isInRespite` through the real adapter."""
    import shlex
    import subprocess

    from code_atlas.config import load_config
    from code_atlas.indexer import full_build
    from tests.php_adapter_cli import ENTRY, PHP

    src = tmp_path / "src"
    src.mkdir()
    (src / "Stay.php").write_text(
        f"<?php\nnamespace App\\Care;\nclass Stay {{\n    public bool ${BARE} = false;\n}}\n"
        "function wasIsInRespite() {}\n",
        encoding="utf-8",
    )
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
    config = load_config(
        tmp_path,
        {"CA_WORKERS": "1", "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"])},
    )
    with GraphStore(config.db_path) as graph:
        assert full_build(config, graph).failed == 0
    payload = search_symbol.create(config)(BARE)

    assert _first(payload) == PROPERTY and payload["reason"] == REASON_OK, payload
