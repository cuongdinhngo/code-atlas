"""Task 411 — declared routes that canonicalise to one key are reported, never kept-first silently.

A census declares ``/x.php?cmd=a`` and ``/x.php?cmd=b`` with ``cmd`` outside the significant keys,
so both rows read as the key ``x.php``. Both handlers are stored; a trace or an impact on either
URL answers both, flagged; status balances every declared row against what was stored.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from code_atlas import routes
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status, impact, trace_capability
from tests.python_adapter_cli import CLI

A = "handlers.alpha.A::a"
B = "handlers.beta.B::b"
URL_A, URL_B = "/x.php?cmd=a", "/x.php?cmd=b"
SOURCES = {
    "handlers/__init__.py": "",
    "handlers/repo.py": "def save(row):\n    return row\n",
    "handlers/alpha.py": (
        "from handlers.repo import save\n\n\nclass A:\n    def a(self):\n        return save(1)\n"
    ),
    "handlers/beta.py": (
        "from handlers.repo import save\n\n\nclass B:\n    def b(self):\n        return save(2)\n"
    ),
}
CENSUS = (
    "url\thandler\n"
    f"{URL_A}\t{A}\n"
    f"{URL_B}\t{B}\n"
    f"{URL_A}&page=2\t{A}\n"  # the same key and target: a duplicate
    "/x.php?cmd=c\thandlers.gone.G::c\n"  # names nothing indexed
    "/x.php?cmd=d\t\n"  # no target
)


def build(root: Path, block: dict[str, object]) -> Config:
    root.mkdir(parents=True)
    for path, text in SOURCES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    (root / "routes.tsv").write_text(CENSUS, encoding="utf-8")
    rule = {"tsv": "routes.tsv", "columns": {"key": "url", "target": "handler"}, **block}
    (root / "rules.json").write_text(json.dumps({"routes": rule}), encoding="utf-8")
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


def _status(config: Config) -> dict[str, object]:
    return get_index_status.create(config, (get_index_status.NAME,))()


def _balanced(census: dict[str, object]) -> bool:
    dropped = census["dropped"]
    assert isinstance(dropped, dict)
    return census["declared"] == census["stored"] + sum(dropped.values())


def test_ac1_a_collision_is_reported_and_traces_every_candidate(tmp_path: Path) -> None:
    """AC1 (proving test): one collision in status; the URL answers both handlers, flagged."""
    config = build(tmp_path / "repo", {"significant": ["module"]})
    census = _status(config)["routes"]
    answer = trace_capability.create(config)(route=URL_B)

    assert isinstance(census, dict) and census["collisions"] == 1
    [example] = census["collision_examples"]
    assert {row["target"] for row in example["routes"]} == {A, B}
    assert answer["reason"] == "ok", answer
    assert {flow["seed"] for flow in answer["results"]} == {A, B}
    assert {flow["route"]["target"] for flow in answer["results"]} == {A, B}
    assert answer["ambiguity"] == routes.ROUTE_COLLISION
    assert [row["target"] for row in answer[routes.CANDIDATES_FIELD]] == [A, B]


def test_ac1_impact_on_a_colliding_url_seeds_every_candidate(tmp_path: Path) -> None:
    config = build(tmp_path / "repo", {"significant": ["module"]})
    answer = impact.create(config)(routes=[URL_B])

    assert answer["ambiguity"] == routes.ROUTE_COLLISION
    assert {row["target"] for row in answer[routes.CANDIDATES_FIELD]} == {A, B}
    assert {A, B} <= {row["target"] for row in answer["routes"]}
    assert answer["seeds_dropped"] == 0


def test_ac2_a_path_with_its_own_significant_keys_routes_each_url_alone(tmp_path: Path) -> None:
    """AC2: ``cmd`` significant for ``/x.php`` — each URL its own handler, no collision."""
    config = build(
        tmp_path / "repo", {"significant": ["module"], "significant_by_path": {"/x.php": ["cmd"]}}
    )
    census = _status(config)["routes"]
    traced = trace_capability.create(config)(route=URL_B)

    assert isinstance(census, dict) and census["collisions"] == 0
    assert "collision_examples" not in census
    assert {flow["seed"] for flow in traced["results"]} == {B}
    assert "ambiguity" not in traced and routes.CANDIDATES_FIELD not in traced
    assert "ambiguity" not in impact.create(config)(routes=[URL_A])


def test_ac3_every_declared_row_is_stored_or_dropped_by_reason(tmp_path: Path) -> None:
    """AC3: declared = stored + Σ dropped, with each reason's rows named."""
    for name, block in (
        ("collide", {"significant": ["module"]}),
        ("by_path", {"significant": ["module"], "significant_by_path": {"x.php": ["cmd"]}}),
    ):
        census = _status(build(tmp_path / name, block))["routes"]
        assert isinstance(census, dict) and _balanced(census), census
        assert census["declared"] == 5 and census["stored"] == 2
        assert census["dropped"] == {"duplicate": 1, "incomplete": 1, "unresolved": 1}
        examples = census["dropped_examples"]
        assert examples["unresolved"] == [
            {"route": "/x.php?cmd=c", "target": "handlers.gone.G::c"}
        ]
        assert examples["duplicate"] == [{"route": f"{URL_A}&page=2", "target": A}]
        assert examples["incomplete"] == [{"route": "/x.php?cmd=d", "target": ""}]


def test_ac3_a_short_name_tie_is_its_own_reason() -> None:
    """A census row whose short class names two classes is dropped as a tie, not unresolved."""
    census = routes.Census()
    block = routes.RouteBlock(None, (("e", "Orders::edit"), ("f", "Orders::edit")), True)
    table, unresolved = routes.resolve(
        [block],
        lambda _target: None,
        lambda _target: [("a.Orders::edit", "a.py"), ("b.Orders::edit", "b.py")],
        census=census,
    )

    assert (table, unresolved) == ([], 2)
    assert census.dropped == {routes.SHORT_NAME_TIE: 2}
    assert census.as_status(table)["declared"] == 2


def test_three_rows_of_one_key_keep_each_distinct_target_once() -> None:
    """A, B, A on one key: two stored (a collision), the repeat a duplicate."""
    census = routes.Census()
    rows = (("k?x=1", "A"), ("k?x=2", "B"), ("k?x=3", "A"))
    table, _ = routes.resolve([routes.RouteBlock((), rows)], lambda _t: "f.py", census=census)

    assert [route.target for route in table] == ["A", "B"]
    assert census.dropped == {routes.DUPLICATE: 1}
    assert routes.matches(table, "k?x=9") == table
    assert routes.collision_fields(table[:1]) == {}
