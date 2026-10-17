"""Task 397 — a routes block reads the consumer's JSON census, and a short class resolves.

The census names each handler as ``Class::method()`` by its short class. The build resolves it
against the stored qnames, a ``prefer`` list breaks a tie between same-named classes, and the
file is digested like a TSV, so editing it turns 396's ``rules_stale`` on.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from code_atlas.config import Config, ConfigError, load_config
from code_atlas.gitutil import changed_paths
from code_atlas.indexer import BuildReport, full_build, incremental_update
from code_atlas.routes import read_blocks
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools import get_index_status, trace_capability
from code_atlas.tools.nav_result import REASON_OK, REASON_RULES_STALE
from tests.python_adapter_cli import CLI

ORDERS = "handlers/orders.py"
SOURCES = {
    ORDERS: (
        "class Orders:\n"
        "    def edit(self):\n        return 1\n\n"
        "    def listing(self):\n        return []\n\n"
        "    def remove(self):\n        return 0\n"
    ),
    "handlers/__init__.py": "",
}
TWIN = {
    "legacy/orders.py": "class Orders:\n    def edit(self):\n        return 2\n",
    "legacy/__init__.py": "",
}
URLS = (
    "index.php?module=orders&action=edit",
    "index.php?module=orders&action=listing",
    "index.php?module=orders&action=remove",
)
CENSUS = {
    "generated": "2026-10-17",
    "endpoints": [
        {"url": f"/{URLS[0]}", "handler": {"name": "Orders::edit()"}},
        {"url": URLS[1], "handler": {"name": "Orders::listing"}},
        {"url": URLS[2], "handler": {"name": "Orders::remove()"}},
    ],
}


def _block(**extra: object) -> dict[str, object]:
    return {
        "significant": ["module", "action"],
        "json": "endpoints.json",
        "rows": "endpoints",
        "columns": {"key": "url", "target": "handler.name"},
        **extra,
    }


def _git(root: Path, *argv: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *argv],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _build(
    root: Path,
    block: dict[str, object],
    *,
    sources: dict[str, str] = SOURCES,
    census: dict[str, Any] = CENSUS,
    extra: dict[str, str] | None = None,
) -> tuple[Config, BuildReport]:
    root.mkdir(parents=True)
    for path, text in {**sources, **(extra or {})}.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    (root / "endpoints.json").write_text(json.dumps(census), encoding="utf-8")
    (root / "rules.json").write_text(json.dumps({"routes": block}), encoding="utf-8")
    argv = ", ".join(json.dumps(part) for part in (*CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(f"[adapter_cmd]\npython = [{argv}]\n", encoding="utf-8")
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    env = {
        "CA_TRUST_PROJECT_FILE": "1",
        "CA_WORKERS": "1",
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
        "CA_INDIRECTION_RULES": "rules.json",
    }
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    config = load_config(root, env)
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    return config, report


def _portable(answer: dict[str, Any]) -> dict[str, Any]:
    """An answer without the fields that name the repo it came from."""
    return {k: v for k, v in answer.items() if k not in ("index_root", "db_path")}


def _first_hop(config: Config, url: str) -> dict[str, Any]:
    return trace_capability.create(config)(route=url)


def test_ac1_three_short_class_handlers_link(tmp_path: Path) -> None:
    """AC1 (proving test): every census row links, and answers as the equivalent TSV does."""
    config, report = _build(tmp_path / "json", _block())
    answers = [_first_hop(config, url) for url in URLS]

    assert report.routes_unresolved == 0
    assert [a["reason"] for a in answers] == [REASON_OK] * 3
    assert [a["results"][0]["steps"][0]["qname"] for a in answers] == [
        "handlers.orders.Orders::edit",
        "handlers.orders.Orders::listing",
        "handlers.orders.Orders::remove",
    ]
    rows = "".join(
        f"{row['url']}\thandlers.orders.{row['handler']['name'].removesuffix('()')}\n"
        for row in CENSUS["endpoints"]
    )
    block = {"significant": ["module", "action"], "tsv": "routes.tsv",
             "columns": {"key": "url", "target": "handler"}}
    twin, _ = _build(tmp_path / "tsv", block, extra={"routes.tsv": "url\thandler\n" + rows})
    same = [_first_hop(twin, url) for url in URLS]
    assert [_portable(a) for a in answers] == [_portable(a) for a in same]  # field for field


def test_ac2_two_classes_of_one_short_name_are_named_not_guessed(tmp_path: Path) -> None:
    """AC2: no `prefer` — unresolved, and the status names both candidates."""
    config, report = _build(tmp_path / "r", _block(), sources={**SOURCES, **TWIN})
    status = get_index_status.create(config, (get_index_status.NAME,))()

    assert report.routes_unresolved == 1  # the edit row; listing and remove have one class each
    assert status["routes_ambiguous_count"] == 1
    [row] = status["routes_ambiguous"]
    assert row["candidates"] == ["handlers.orders.Orders::edit", "legacy.orders.Orders::edit"]
    assert _first_hop(config, URLS[0])["reason"] == "no_such_symbol"


def test_ac2_prefer_picks_the_preferred_class(tmp_path: Path) -> None:
    config, report = _build(
        tmp_path / "r", _block(prefer=["legacy", "handlers"]), sources={**SOURCES, **TWIN}
    )

    assert report.routes_unresolved == 0
    assert _first_hop(config, URLS[0])["results"][0]["steps"][0]["qname"] == (
        "legacy.orders.Orders::edit"
    )
    assert "routes_ambiguous" not in get_index_status.create(config, (get_index_status.NAME,))()


def test_ac3_editing_the_census_turns_rules_stale_on_then_applies(tmp_path: Path) -> None:
    """AC3: the census alone moves the digest; the next incremental applies it."""
    config, _ = _build(tmp_path / "r", _block())
    edited = {**CENSUS, "endpoints": [{"url": URLS[0], "handler": {"name": "Orders::remove"}}]}
    (config.root / "endpoints.json").write_text(json.dumps(edited), encoding="utf-8")

    stale = _first_hop(config, URLS[0])
    with GraphStore(config.db_path) as store:
        changed = changed_paths(config.root, store.get_meta(LAST_COMMIT_KEY))
        assert changed is not None
        report = incremental_update(config, store, changed)
    fresh = _first_hop(config, URLS[0])

    assert stale["reason"] == REASON_RULES_STALE
    assert report.parsed == 0 and report.rules_reapplied is True
    assert fresh["reason"] == REASON_OK
    assert fresh["results"][0]["steps"][0]["qname"] == "handlers.orders.Orders::remove"


def test_a_short_class_matches_a_whole_component_only(tmp_path: Path) -> None:
    """`Orders` never names `BigOrders` (R5.2)."""
    sources = {**SOURCES, "big.py": "class BigOrders:\n    def edit(self):\n        return 3\n"}
    config, report = _build(tmp_path / "r", _block(), sources=sources)

    assert report.routes_unresolved == 0
    assert _first_hop(config, URLS[0])["results"][0]["steps"][0]["qname"] == (
        "handlers.orders.Orders::edit"
    )


def test_a_census_with_no_list_at_rows_is_a_config_error(tmp_path: Path) -> None:
    (tmp_path / "endpoints.json").write_text(json.dumps(CENSUS), encoding="utf-8")
    with pytest.raises(ConfigError, match="no list"):
        read_blocks(_block(rows="generated"), "rules.json", tmp_path, lambda _data: None)
    with pytest.raises(ConfigError, match="needs a json source"):
        read_blocks({"table": [], "prefer": ["x"]}, "rules.json", tmp_path, lambda _data: None)
