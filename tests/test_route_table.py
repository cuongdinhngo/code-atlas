"""Task 385 — a URL a tester reports is a subject: a declared route table read as data.

A fixture front controller dispatches on request input, so the graph holds no edge to the handler.
A ``routes`` block in the rule file names the handler per URL from a TSV census, and the tools
answer about the URL. Built through the real Python adapter, so the targets are stored qnames.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from code_atlas import contract, routes
from code_atlas.config import Config, load_config
from code_atlas.indexer import BuildReport, full_build
from code_atlas.store import GraphStore
from code_atlas.tools import impact, search_symbol, trace_capability
from tests.python_adapter_cli import CLI

HANDLER = "handlers/orders.py"
EDIT = "handlers.orders.Orders::edit"
LISTING = "handlers.orders.Orders::listing"
EDIT_URL = "index.php?module=orders&action=edit"

SOURCES = {
    "app.py": (
        "import sys\n\nfrom handlers.orders import Orders\n\n\n"
        "def dispatch(action):\n    return getattr(Orders(), action)()\n\n\n"
        "dispatch(sys.argv[1])\n"
    ),
    HANDLER: (
        "from handlers.repo import save\n\n\nclass Orders:\n"
        "    def edit(self):\n        return save('order')\n\n"
        "    def listing(self):\n        return []\n"
    ),
    "handlers/repo.py": "def save(row):\n    return row\n",
    "handlers/__init__.py": "",
}

# A measured census, used as is: its own column names and a noise column.
CENSUS = (
    "url\thandler\thits\n"
    f"/{EDIT_URL}\t{EDIT}\t12\n"
    "index.php?action=listing&module=orders\t" + LISTING + "\t40\n"
)
MISSING_ROW = "index.php?module=orders&action=gone\thandlers.orders.Orders::gone\t1\n"

RULES = {
    "routes": {
        "significant": ["module", "action"],
        "tsv": "routes.tsv",
        "columns": {"key": "url", "target": "handler"},
    }
}


def build(root: Path, *, census: str | None = CENSUS) -> tuple[Config, BuildReport]:
    """The fixture repo, its rule file when a census is given, and one full build."""
    root.mkdir(parents=True, exist_ok=True)
    for path, text in SOURCES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    argv = ", ".join(json.dumps(part) for part in (*CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(f"[adapter_cmd]\npython = [{argv}]\n", encoding="utf-8")
    env = {
        "CA_TRUST_PROJECT_FILE": "1",
        "CA_WORKERS": "1",
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
    }
    if census is not None:
        (root / "routes.tsv").write_text(census, encoding="utf-8")
        (root / "rules.json").write_text(json.dumps(RULES), encoding="utf-8")
        env["CA_INDIRECTION_RULES"] = "rules.json"
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    config = load_config(root, env)
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    return config, report


@pytest.fixture
def repo(tmp_path: Path) -> Config:
    return build(tmp_path / "repo")[0]


def test_a_route_traces_from_its_declared_target(repo: Config) -> None:
    """AC1 (proving test): the path starts at the target; the hop into it is HEURISTIC, rule."""
    noisy = "index.php?page=3&action=edit&module=orders"  # key order and a noise key
    answer = trace_capability.create(repo)(route=noisy)

    assert answer["reason"] == "ok", answer
    flow: dict[str, Any] = answer["results"][0]
    first = flow["steps"][0]
    assert first["qname"] == EDIT
    assert (first["tier"], first["rule"]) == (routes.ROUTE_TIER, True)
    assert flow["route"]["target"] == EDIT and flow["route"][contract.RULE_FLAG] is True
    assert any(step["qname"] == "handlers.repo.save" for step in flow["steps"][1:])


def test_impact_on_the_targets_file_lists_the_route(repo: Config) -> None:
    """AC2: "which routes does this change reach" — the radius names the routes into it."""
    answer = impact.create(repo)(paths=[HANDLER])
    by_route = impact.create(repo)(routes=[EDIT_URL])

    assert {row["target"] for row in answer["routes"]} == {EDIT, LISTING}
    assert all(row["tier"] == routes.ROUTE_TIER for row in answer["routes"])
    assert EDIT in {row["target"] for row in by_route["routes"]}
    assert by_route["seeds_dropped"] == 0
    plain = impact.create(repo)(qnames=["handlers.repo.save"])
    assert {row["target"] for row in plain["routes"]} == {EDIT}  # reached through the radius


def test_a_route_to_a_missing_target_is_counted_and_links_nothing(tmp_path: Path) -> None:
    """AC3: ``routes_unresolved`` counts it; the URL then answers like any undeclared one."""
    config, report = build(tmp_path / "repo", census=CENSUS + MISSING_ROW)
    _, clean = build(tmp_path / "clean")

    assert (report.routes_unresolved, clean.routes_unresolved) == (1, 0)
    gone = trace_capability.create(config)(route="index.php?module=orders&action=gone")
    assert gone["reason"] == "no_such_symbol"
    assert "results" in gone and gone["results"] == []


def test_with_no_routes_rule_a_route_is_not_configured(tmp_path: Path) -> None:
    """AC4: an inert capability, not an empty result."""
    config, _ = build(tmp_path / "bare", census=None)
    answer = trace_capability.create(config)(route=EDIT_URL)

    assert answer["reason"] == "capability_not_configured"
    assert "try_instead_hint" in answer and "try_instead" not in answer
    assert "routes" not in impact.create(config)(paths=[HANDLER])


def test_an_unmatched_url_names_the_nearest_declared_routes(repo: Config) -> None:
    answer = trace_capability.create(repo)(route="index.php?module=orders&action=edti")

    assert answer["reason"] == "no_such_symbol"
    assert answer["nearest_routes"][0] == f"/{EDIT_URL}"


def test_search_symbol_finds_a_route_by_its_key(repo: Config) -> None:
    hits = search_symbol.create(repo)(query="action=edit")

    assert [row["target"] for row in hits["routes"]] == [EDIT]
    assert "routes" not in search_symbol.create(repo)(query="dispatch")  # no route key holds it


def test_a_route_adds_no_vocabulary() -> None:
    """Deviation from Scope 2 (P3): a lookup in front of existing subjects, so no new kinds."""
    assert "Entry" not in contract.NODE_KINDS
    assert "ROUTES_TO" not in contract.EDGE_KINDS


def test_a_route_to_a_file_traces_from_the_file(tmp_path: Path) -> None:
    """Scope 1: a target may be a File; its flow starts at the file's own node."""
    config, report = build(tmp_path / "repo", census="url\thandler\nreport.php\tapp.py\n")
    answer = trace_capability.create(config)(route="/report.php?x=1")

    assert report.routes_unresolved == 0
    assert answer["reason"] == "ok", answer
    assert answer["results"][0]["steps"][0]["qname"] == "app.py"
    assert {row["target"] for row in impact.create(config)(paths=["app.py"])["routes"]} == {
        "app.py"
    }


def test_a_wildcard_value_matches_any_action() -> None:
    table, unresolved = routes.resolve(
        [routes.RouteBlock(("module", "action"), (("i.php?module=a&action=*", "T"),))],
        lambda target: "f.py",
    )

    assert unresolved == 0
    assert routes.match(table, "i.php?action=zz&module=a") is table[0]
    assert routes.match(table, "i.php?action=zz&module=b") is None
