"""Task 415 — one URL a front controller serves through several handlers, each under a condition.

A census declares ``/x.php?action=x`` twice: ``XA::save`` when ``region=A``, ``XB::save`` when
``region=B``, each with the ``file:line`` that dispatches it. The route is conditional, not a 411
collision: a trace answers one flow per handler, each carrying its label, and nothing evaluates it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from code_atlas import routes
from code_atlas.config import Config, ConfigError, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status, impact, trace_capability
from tests.python_adapter_cli import CLI

XA, XB = "handlers.xa.XA::save", "handlers.xb.XB::save"
URL = "/x.php?action=x"
SOURCES = {
    "handlers/__init__.py": "",
    "handlers/repo.py": "def save(row):\n    return row\n",
    "handlers/xa.py": (
        "from handlers.repo import save\n\n\n"
        "class XA:\n    def save(self):\n        return save(1)\n"
    ),
    "handlers/xb.py": (
        "from handlers.repo import save\n\n\n"
        "class XB:\n    def save(self):\n        return save(2)\n"
    ),
}
CENSUS = (
    "url\thandler\tcondition\tat\n"
    f"{URL}\t{XA}\tregion=A\tx.php:12\n"
    f"{URL}\t{XB}\tregion=B\tx.php:12\n"
    f"/x.php?action=y\t{XA}\t\t\n"  # a single-handler route, unlabelled
)
BLOCK = {
    "significant": ["action"],
    "tsv": "routes.tsv",
    "columns": {"key": "url", "target": "handler", "when": "condition", "source": "at"},
}


def build(root: Path, census: str = CENSUS, block: dict[str, object] = BLOCK) -> Config:
    root.mkdir(parents=True)
    for path, text in SOURCES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    (root / "routes.tsv").write_text(census, encoding="utf-8")
    (root / "rules.json").write_text(json.dumps({"routes": block}), encoding="utf-8")
    argv = ", ".join(json.dumps(part) for part in (*CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(f"[adapter_cmd]\npython = [{argv}]\n", encoding="utf-8")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    config = load_config(
        root,
        {
            "CA_TRUST_PROJECT_FILE": "1",
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
            "CA_INDIRECTION_RULES": "rules.json",
        },
    )
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return config


def test_ac1_one_flow_per_handler_each_with_its_condition(tmp_path: Path) -> None:
    """AC1 (proving test): two flows, each labelled and sourced; ``impact`` seeds both."""
    config = build(tmp_path / "repo")
    answer = trace_capability.create(config)(route=URL)
    reached = impact.create(config)(routes=[URL])

    assert answer["reason"] == "ok", answer
    labelled = {
        (flow["seed"], flow["route"]["when"], flow["route"]["source"]) for flow in answer["results"]
    }
    assert labelled == {(XA, "region=A", "x.php:12"), (XB, "region=B", "x.php:12")}
    assert "ambiguity" not in answer and routes.CANDIDATES_FIELD not in answer
    assert {(row["target"], row.get("when")) for row in reached["routes"]} >= {
        (XA, "region=A"),
        (XB, "region=B"),
    }
    assert reached["seeds_dropped"] == 0 and "ambiguity" not in reached


def test_status_counts_a_conditional_route_apart_from_collisions(tmp_path: Path) -> None:
    census = get_index_status.create(build(tmp_path / "repo"), (get_index_status.NAME,))()["routes"]
    assert isinstance(census, dict)
    assert (census["conditional"], census["collisions"], census["stored"]) == (1, 0, 3)


def test_ac2_a_single_handler_route_answers_as_before(tmp_path: Path) -> None:
    """AC2: an unlabelled row's route carries no ``when``/``source`` key."""
    answer = trace_capability.create(build(tmp_path / "repo"))(route="/x.php?action=y")
    [flow] = answer["results"]
    assert set(flow["route"]) == {"route", "target", "file", "tier", "rule"}


def test_a_labelled_and_an_unlabelled_handler_still_collide() -> None:
    """Scope 2: nothing tells the unlabelled row apart, so the key is a 411 collision."""
    table, _ = routes.resolve(
        [routes.RouteBlock(None, (routes.Handler("k", "A", "region=A"), ("k", "B")))],
        lambda _t: "f.py",
    )
    same, _ = routes.resolve(
        [routes.RouteBlock(None, (routes.Handler("k", "A", "on"), routes.Handler("k", "B", "on")))],
        lambda _t: "f.py",
    )
    assert routes.collision_fields([table])["ambiguity"] == routes.ROUTE_COLLISION
    assert routes.collision_fields([same])["ambiguity"] == routes.ROUTE_COLLISION


def test_one_handler_under_two_conditions_is_kept_twice() -> None:
    """The same target under two labels is two handlers, never a duplicate."""
    census = routes.Census()
    rows = (routes.Handler("k", "A", "region=A"), routes.Handler("k", "A", "region=B"))
    table, _ = routes.resolve([routes.RouteBlock(None, rows)], lambda _t: "f.py", census=census)

    assert [route.when for route in table] == ["region=A", "region=B"]
    assert census.dropped == {}
    assert routes.collision_fields([table]) == {}


def test_inline_and_json_rows_take_when_and_source(tmp_path: Path) -> None:
    (tmp_path / "e.json").write_text(
        json.dumps([{"u": URL, "h": XA, "c": {"when": "flag=ON"}}]), encoding="utf-8"
    )
    blocks = routes.read_blocks(
        {
            "table": [{"key": URL, "target": XB, "when": " region=B ", "source": "x.php:3"}],
            "json": "e.json",
            "columns": {"key": "u", "target": "h", "when": "c.when"},
        },
        "rules.json",
        tmp_path,
        lambda _data: None,
    )
    assert [tuple(entry) for block in blocks for entry in block.entries] == [
        (URL, XB, "region=B", "x.php:3"),
        (URL, XA, "flag=ON", None),
    ]


def test_a_missing_label_column_fails_the_build(tmp_path: Path) -> None:
    """Review M1: a misspelt ``when`` column would read every conditional route as a collision."""
    (tmp_path / "routes.tsv").write_text(CENSUS, encoding="utf-8")
    block = {**BLOCK, "columns": {"key": "url", "target": "handler", "when": "conditon"}}
    with pytest.raises(ConfigError, match="no when column"):
        routes.read_blocks(block, "rules.json", tmp_path, lambda _data: None)


def test_a_collision_example_names_its_labels() -> None:
    """Review M2: the label that failed to tell two rows apart is shown in status."""
    census = routes.Census()
    rows = (routes.Handler("k", "A", "on"), routes.Handler("k", "B", "on"))
    table, _ = routes.resolve([routes.RouteBlock(None, rows)], lambda _t: "f.py", census=census)
    [example] = census.as_status(table)["collision_examples"]  # type: ignore[misc]
    assert [row["when"] for row in example["routes"]] == ["on", "on"]


def test_two_conditional_urls_sharing_labels_are_no_collision_in_impact(tmp_path: Path) -> None:
    """Review: each URL is judged on its own key, never the concatenation of every match."""
    other = "/x.php?action=z"
    census = CENSUS + "".join(
        f"{other}\t{target}\t{when}\t\n" for target, when in ((XA, "region=A"), (XB, "region=B"))
    )
    answer = impact.create(build(tmp_path / "repo", census))(routes=[URL, other, URL])
    assert "ambiguity" not in answer and routes.CANDIDATES_FIELD not in answer


def test_one_target_labelled_and_unlabelled_is_a_duplicate_not_a_collision() -> None:
    census = routes.Census()
    rows = (routes.Handler("k", "A", "region=A"), ("k", "A"))
    table, _ = routes.resolve([routes.RouteBlock(None, rows)], lambda _t: "f.py", census=census)

    assert [route.when for route in table] == ["region=A"]
    assert census.dropped == {routes.DUPLICATE: 1}
    assert census.as_status(table)["collisions"] == 0


def test_one_handler_under_two_conditions_traces_once_under_each(tmp_path: Path) -> None:
    header = "url\thandler\tcondition\tat\n"
    census = header + "".join(f"{URL}\t{XA}\t{when}\t\n" for when in ("region=A", "region=B"))
    answer = trace_capability.create(build(tmp_path / "repo", census))(route=URL)
    assert sorted(flow["route"]["when"] for flow in answer["results"]) == ["region=A", "region=B"]


def test_a_table_stored_before_415_loads_unlabelled() -> None:
    raw = '[{"key":"k","declared":"k","target":"T","file":"f","significant":null}]'
    [route] = routes.load(raw) or []
    assert (route.when, route.source) == (None, None)
