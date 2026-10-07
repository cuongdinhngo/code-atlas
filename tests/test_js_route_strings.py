"""Task 361 — a route string in JavaScript links to the PHP action it dispatches to, by rule.

``keyed_calls`` read a key only when the argument *is* the key. A route sits inside a URL, or in a
``{module, action}`` object, so the rule now takes a ``key_pattern`` whose named groups fill the
template, and ``key_from: "object"`` reads an object literal's string values. Nothing is hard-coded:
the fixture's ``rules.json`` declares the route grammar.
"""

from __future__ import annotations

import json
import shlex
import shutil
import sqlite3
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import ConfigError, load_config
from code_atlas.enrichment import INDIRECTION_FILE, _literal_fields, load_indirection_rules
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from tests.php_adapter_cli import ENTRY as PHP_ENTRY
from tests.php_adapter_cli import PHP, needs_php
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "js_route_strings"
DELETE = "\\App\\ItemsController::deleteItemAction"
ARCHIVE = "\\App\\ItemsController::archiveItemAction"
JS = "public/js/items.js"


def _build(root: Path, *, rules: bool, rules_text: str | None = None) -> tuple[object, object]:
    (root / "src").mkdir(exist_ok=True)
    (root / "public" / "js").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "ItemsController.php", root / "src" / "ItemsController.php")
    shutil.copy(FIXTURES / "items.js", root / JS)
    env = {
        "CA_WORKERS": "1",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        "CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"]),
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
    }
    if rules:
        (root / "rules").mkdir(exist_ok=True)
        shutil.copy(FIXTURES / "rules.json", root / "rules" / "rules.json")
        if rules_text is not None:
            (root / "rules" / "rules.json").write_text(rules_text, encoding="utf-8")
        env["CA_INDIRECTION_RULES"] = "rules/rules.json"
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    config = load_config(root, env)
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    assert report.failed == 0
    return config, report


@pytest.fixture
def built(tmp_path: Path) -> Iterator[tuple[object, object]]:
    yield _build(tmp_path, rules=True)


@needs_php
@needs_node
def test_a_route_url_reaches_the_action_it_names(built: tuple) -> None:
    """AC1 — `$.post('main.php?module=Items&action=deleteItem')` is a HEURISTIC rule caller."""
    config, _ = built
    payload = find_callers.create(config)(DELETE)
    assert payload["reason"] == "ok", payload
    [hit] = payload["results"]
    assert hit["confidence_tier"] == "HEURISTIC"
    assert hit["rule"] is True
    assert hit["qname"].endswith("::removeItem")


@needs_php
@needs_node
def test_a_module_action_object_reaches_the_action_it_names(built: tuple) -> None:
    """AC2 — `{module: 'Items', action: 'archiveItem'}` resolves the same way."""
    config, _ = built
    payload = find_callers.create(config)(ARCHIVE)
    [hit] = payload["results"]
    assert hit["rule"] is True
    assert hit["confidence_tier"] == "HEURISTIC"
    assert hit["qname"].endswith("::archiveItem")


@needs_php
@needs_node
def test_a_route_naming_no_action_is_counted_and_links_nothing(built: tuple) -> None:
    """AC3 — `action=nope` matches the grammar and names no method: unlinked, counted once.

    `health.php` does not match the grammar at all, so it is no route and not counted.
    """
    config, report = built
    assert report.rule_keys_unresolved == 1
    conn = sqlite3.connect(config.db_path)  # type: ignore[attr-defined]
    rows = conn.execute(
        "SELECT target_raw, target_qname FROM edges WHERE file_path = ?", (INDIRECTION_FILE,)
    ).fetchall()
    conn.close()
    assert ("\\App\\ItemsControllerController::nopeAction", None) not in rows
    unlinked = [raw for raw, linked in rows if linked is None]
    assert unlinked == ["\\App\\ItemsController::nopeAction"]
    assert all("health" not in raw for raw, _ in rows)


@needs_php
@needs_node
def test_without_a_rule_the_graph_has_no_rule_rows(tmp_path: Path) -> None:
    """AC4 — no rule of this kind, no rule edge; the JS call stays a bare `post`."""
    config, report = _build(tmp_path, rules=False)
    conn = sqlite3.connect(config.db_path)  # type: ignore[attr-defined]
    count = conn.execute(
        "SELECT COUNT(*) FROM edges WHERE file_path = ?", (INDIRECTION_FILE,)
    ).fetchone()[0]
    conn.close()
    assert count == 0
    assert report.rule_keys_unresolved == 0


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ({"key_pattern": "action=(\\w+", "target_template": "X::{key}"}, "key_pattern"),
        ({"key_pattern": "a=(?P<a>\\w+)", "target_template": "X::{b}"}, "placeholder"),
        ({"key_from": "object", "target_template": "X::y"}, "placeholder"),
        (
            {"key_from": "object", "key_pattern": "a", "target_template": "X::{a}"},
            "key_pattern",
        ),
    ],
)
def test_a_malformed_route_rule_fails_loud(tmp_path: Path, entry: dict, message: str) -> None:
    """R5.3 — a rule that cannot fill its template is a config error before any parse."""
    rule = {"setter": "post", "key_arg": 1, **entry}
    (tmp_path / "rules.json").write_text(json.dumps({"keyed_calls": [rule]}), encoding="utf-8")
    config = load_config(tmp_path, {"CA_INDIRECTION_RULES": "rules.json"})
    with pytest.raises(ConfigError, match=message):
        load_indirection_rules(config)


@needs_php
@needs_node
def test_one_literal_two_rules_read_differently_is_one_unresolved_site(tmp_path: Path) -> None:
    """A route two patterns both read, linking under neither, is counted once — not per rule."""
    rules = {
        "keyed_calls": [
            {
                "setter": "post",
                "key_arg": 1,
                "key_pattern": "action=(\\w+)",
                "target_template": "\\App\\Nowhere::{key}",
            },
            {
                "setter": "post",
                "key_arg": 1,
                "key_pattern": "module=(?P<module>\\w+)",
                "target_template": "\\App\\{module}Nowhere::run",
            },
        ]
    }
    _, report = _build(tmp_path, rules=True, rules_text=json.dumps(rules))
    # Two literals match either pattern (deleteItem's and nope's routes); each counts once.
    assert report.rule_keys_unresolved == 2


@pytest.mark.parametrize(
    ("argument", "fields"),
    [
        ("{module: 'Items', action: 'x'}", {"module": "Items", "action": "x"}),
        ("['module' => 'M', \"action\" => \"y\"]", {"module": "M", "action": "y"}),
        ("{data: {action: 'inner'}, action: 'outer'}", {"action": "outer"}),
        ("{data: {action: 'inner'}}", {}),
        ("{action: 'a' + b}", {}),
        ("{action: c ? 'a' : 'b'}", {}),
        ("{'ac tion': 'x'}", {}),
        ("{module, action: 'x'}", {"action": "x"}),
        ("{a: 'x, y', b: 'z'}", {"a": "x, y", "b": "z"}),
    ],
)
def test_only_a_whole_top_level_string_field_names_a_value(argument: str, fields: dict) -> None:
    """Challenger F1–F3 — a nested, concatenated or conditional value is never read as the field."""
    assert _literal_fields(argument) == fields
