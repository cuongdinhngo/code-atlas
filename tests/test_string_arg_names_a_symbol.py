"""Task 352: a call whose string argument names a class links to it through a ``keyed_calls`` rule.

222 already emits a HEURISTIC ``CALLS`` edge from a string argument through ``target_template``,
and its own test proves the proc-by-string shape (PHP ``querySP('x')`` → a SQL proc). This file
pins the class-by-string shape and the one thing 222 did not count: a literal that names nothing.

The fixture's ``make`` has two rules — the widget namespace and a fully-qualified literal — so a
literal that links under either is resolved, and only one that links under neither is counted.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import load_config
from code_atlas.enrichment import INDIRECTION_FILE, _call_argument
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from tests.php_adapter_cli import ENTRY, PHP, needs_php

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "string_arg_symbol"
RENDER = "\\App\\Widgets\\SaveButton::render"
# page.php: a short literal, a fully-qualified one, a name nothing declares, a variable, a concat,
# and a receiver whose own call holds a literal before `make(` does.
SHORT, QUALIFIED, NOWHERE, VARIABLE, CONCAT, RECEIVER = 10, 11, 12, 13, 14, 15


@pytest.fixture
def built(tmp_path: Path) -> Iterator[tuple[object, GraphStore, object]]:
    (tmp_path / "src").mkdir()
    for name in ("widgets.php", "page.php"):
        shutil.copy(FIXTURES / name, tmp_path / "src" / name)
    (tmp_path / "rules").mkdir()
    shutil.copy(FIXTURES / "rules.json", tmp_path / "rules" / "rules.json")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"]),
            "CA_INDIRECTION_RULES": "rules/rules.json",
            "CA_DB_PATH": str(tmp_path / ".code-atlas" / "graph.db"),
        },
    )
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        yield config, store, report


def rule_lines(store: GraphStore, *, linked: bool) -> set[int]:
    rows = store.calls_by_target_raw(RENDER) + store.calls_by_target_raw("\\Nowhere::render")
    rows += store.calls_by_target_raw("\\App\\Widgets\\Nowhere::render")
    return {
        int(str(row["line"]))
        for row in rows
        if row.get("file_path") == INDIRECTION_FILE and bool(row.get("target_qname")) == linked
    }


@needs_php
def test_a_class_named_by_a_string_reaches_its_method_callers(built: tuple) -> None:
    """AC1: both literal spellings reach ``find_callers`` at HEURISTIC, rule-flagged — 222's
    mechanism, already green before 352; pinned so the class shape cannot regress."""
    config, store, _ = built

    assert rule_lines(store, linked=True) == {SHORT, QUALIFIED, RECEIVER}
    payload = find_callers.create(config)(RENDER)
    assert payload["reason"] == "ok", payload
    hits = payload["results"]
    assert hits and all(hit.get(contract.RULE_FLAG) is True for hit in hits), hits
    assert all(hit.get("confidence_tier") == "HEURISTIC" for hit in hits), hits


@needs_php
def test_a_literal_naming_nothing_links_nothing_and_is_counted(built: tuple) -> None:
    """AC3 (proving test): ``Nowhere`` links under no rule and is the one site counted; a site
    that linked under one of its two rules is not counted for the other's miss."""
    _, store, report = built

    assert NOWHERE not in rule_lines(store, linked=True)
    assert report.rule_keys_unresolved == 1, report


@needs_php
def test_a_non_literal_argument_contributes_nothing(built: tuple) -> None:
    """AC4: a variable and a concatenation emit no rule edge at all."""
    _, store, _ = built

    emitted = rule_lines(store, linked=True) | rule_lines(store, linked=False)
    assert VARIABLE not in emitted and CONCAT not in emitted
    assert emitted == {SHORT, QUALIFIED, NOWHERE, RECEIVER}


def test_the_key_is_read_from_its_own_argument_never_a_neighbouring_literal() -> None:
    """AC4: the argument is split out of ``<callee>(`` at top-level commas, so a literal in the
    receiver or inside an earlier argument is never taken for the key (the challenger's D2)."""
    make = "\\App\\Widgets\\Widget::make"
    assert _call_argument("$c->get('db')->make('X');", make, 1) == "'X'"
    assert _call_argument("make('Save' . $dyn, 'Other');", make, 1) == "'Save' . $dyn"
    assert _call_argument("make('Save' . $dyn, 'Other');", make, 2) == "'Other'"
    assert _call_argument("make(f('a, b'), [1, 2], 'K')", make, 3) == "'K'"
    assert _call_argument("make('a'); make('b');", make, 1) is None
    assert _call_argument("remake('a');", make, 1) is None
    assert _call_argument("make('a',", make, 1) is None
