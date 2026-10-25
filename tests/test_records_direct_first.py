"""Task 412 — the subject's own records lead an ``impact`` answer; a hub's cannot drown them.

A front controller file carries 50 records and reaches a leaf handler that carries 2. ``impact``
on the leaf lists the leaf's 2 first, ``direct: true``; a ``stop_at`` glob keeps the hub's out;
``records="direct"`` returns the 2 alone. Built through the real Python adapter.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from code_atlas import records
from code_atlas.config import Config, ConfigError, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import impact
from tests.python_adapter_cli import CLI

HUB, LEAF = "front.py", "handlers/leaf.py"
SAVE = "handlers.leaf.Leaf::save"
SOURCES = {
    "handlers/__init__.py": "",
    LEAF: "class Leaf:\n    def save(self):\n        return 1\n",
    HUB: (
        "from handlers.leaf import Leaf\n\n\n"
        "def dispatch(action):\n    return Leaf().save() if action else None\n"
    ),
}
RECORDS = [
    *({"key": f"HUB-{n:02}", "summary": f"screen {n}", "targets": [HUB]} for n in range(50)),
    {"key": "LEAF-1", "summary": "save lost a row", "targets": [SAVE]},
    {"key": "LEAF-2", "summary": "leaf module", "targets": [LEAF]},
]


def build(root: Path, **block: object) -> Config:
    root.mkdir(parents=True)
    for path, text in SOURCES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    (root / "qa.json").write_text(json.dumps(RECORDS), encoding="utf-8")
    rule = {"sources": ["qa.json"], "fields": {"id": "key", "title": "summary"}, **block}
    (root / "rules.json").write_text(json.dumps({"records": rule}), encoding="utf-8")
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


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return build(tmp_path_factory.mktemp("direct") / "repo")


def rows(answer: dict[str, object]) -> list[dict[str, Any]]:
    found: Any = answer.get("records", [])
    return list(found)


def test_ac1_the_leafs_own_records_lead_each_direct(repo: Config) -> None:
    """AC1 (proving test): the 2 leaf records first, ``direct``, ahead of the hub's 50."""
    answer = impact.create(repo)(paths=[LEAF])
    listed = rows(answer)

    assert [row["id"] for row in listed[:2]] == ["LEAF-1", "LEAF-2"]
    assert [(row["direct"], row["distance"]) for row in listed[:2]] == [(True, 0), (True, 0)]
    assert all(row["direct"] is False and row["distance"] >= 1 for row in listed[2:])
    assert answer["records_total"] == 52


def test_a_record_on_a_member_of_the_seed_is_direct(repo: Config) -> None:
    """A class seed's method record is direct even where the walk never reaches the method."""
    answer = impact.create(repo)(qnames=["handlers.leaf.Leaf"])
    assert {row["id"]: row["direct"] for row in rows(answer)[:2]} == {
        "LEAF-1": True,
        "LEAF-2": True,  # the seed's own file
    }


def test_a_qname_seeds_own_file_is_direct_though_the_walk_never_reaches_it(repo: Config) -> None:
    """W4: the default set gains the subject's records today's carriers missed — the seed's file."""
    answer = impact.create(repo)(qnames=[SAVE])
    assert [(row["id"], row["direct"]) for row in rows(answer)[:2]] == [
        ("LEAF-1", True),
        ("LEAF-2", True),
    ]


def test_ac2_stop_at_keeps_the_hubs_records_out(tmp_path: Path) -> None:
    """AC2: none of the hub's 50 reach the leaf's answer; the hub's own answer keeps them."""
    config = build(tmp_path / "repo", stop_at=["front.*"])
    leaf = impact.create(config)(paths=[LEAF])
    hub = impact.create(config)(paths=[HUB])

    assert [row["id"] for row in rows(leaf)] == ["LEAF-1", "LEAF-2"]
    assert leaf["records_total"] == 2 and leaf["records_stopped"] == 50
    assert sum(row["id"].startswith("HUB-") for row in rows(hub)) == 50
    assert "records_stopped" not in hub


def test_ac3_direct_returns_exactly_the_subjects_records(repo: Config) -> None:
    answer = impact.create(repo)(paths=[LEAF], records="direct")
    assert [row["id"] for row in rows(answer)] == ["LEAF-1", "LEAF-2"]
    assert answer["records_total"] == 2


def test_ac4_the_default_answer_keeps_the_same_set(repo: Config) -> None:
    """AC4: neither parameter — every record counted as before, paged at ``page_limit``;
    ``records_limit`` pages less and is clamped, visibly, at the page (066)."""
    answer = impact.create(repo)(paths=[LEAF])
    two = impact.create(repo)(paths=[LEAF], records_limit=2)
    more = impact.create(repo)(paths=[LEAF], records_limit=repo.page_limit + 1)

    assert len(rows(answer)) == repo.page_limit == 50 and answer["records_total"] == 52
    assert [row["id"] for row in rows(two)] == ["LEAF-1", "LEAF-2"]
    assert more["limit_capped_to"] == repo.page_limit and "limit_capped_to" not in answer


def test_bad_arguments_are_refused(repo: Config, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="records must be"):
        impact.create(repo)(paths=[LEAF], records="all")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="records_limit"):
        impact.create(repo)(paths=[LEAF], records_limit=0)
    with pytest.raises(ConfigError, match="stop_at"):
        records.read_blocks(
            {"sources": ["qa.json"], "stop_at": [""]}, "rules.json", tmp_path, lambda _d: None
        )
