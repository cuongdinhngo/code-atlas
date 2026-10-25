"""Task 413 — a record's declared attributes ride on every row; ``records_filter`` selects on them.

A records block declares ``attributes``: the build keeps each value that is a string, number,
boolean or a list of them, and every tool that lists records carries them. A filter on a declared
attribute keeps the matching records before any count; one on an undeclared name is refused.
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
from code_atlas.tools import find_references, impact, read_symbol
from tests.python_adapter_cli import CLI

SAVE = "handlers.repo.save"
SOURCES = {
    "handlers/__init__.py": "",
    "handlers/repo.py": "def save(row):\n    return row\n",
    "handlers/orders.py": "from handlers.repo import save\n\n\ndef edit():\n    return save(1)\n",
}
RECORDS = [
    {
        "key": "R-A", "summary": "verified", "targets": [SAVE],
        "tier": "A", "region": "X", "status": ["open", "triage"], "meta": {"x": 1},
    },
    {"key": "R-B", "summary": "unverified", "targets": [SAVE], "tier": "B", "flag": True},
    {"key": "R-N", "summary": "no tier", "targets": [SAVE], "flag": 1},
]
DECLARED = ["tier", "region", "status", "meta", "flag"]


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
    return build(tmp_path_factory.mktemp("attrs") / "repo", attributes=DECLARED)


def by_id(answer: dict[str, object]) -> dict[str, dict[str, Any]]:
    found: Any = answer.get("records", [])
    return {str(row["id"]): row for row in found}


def answers(config: Config, **kwargs: Any) -> list[dict[str, object]]:
    return [
        read_symbol.create(config)(qname=SAVE, **kwargs),
        find_references.create(config)(qname=SAVE, **kwargs),
        impact.create(config)(qnames=[SAVE], **kwargs),
    ]


def test_ac1_every_tool_carries_the_declared_attributes(repo: Config) -> None:
    """AC1 (proving test): ``tier`` and ``region`` on the row in all three tools; an object
    value (``meta``) is not kept, a list of strings is."""
    for answer in answers(repo):
        rows = by_id(answer)
        assert rows["R-A"]["attributes"] == {
            "tier": "A", "region": "X", "status": ["open", "triage"]
        }, answer
        assert rows["R-B"]["attributes"] == {"tier": "B", "flag": True}
        assert rows["R-A"]["tier"] == "HEURISTIC"  # the row's own tier is untouched


def test_ac2_a_filter_keeps_what_matches_and_the_total_counts_it(repo: Config) -> None:
    for answer in answers(repo, records_filter={"tier": ["A"]}):
        assert set(by_id(answer)) == {"R-A"}
    for answer in answers(repo, records_filter={"tier": ["C"]}):
        assert "records" not in answer
    kept = impact.create(repo)(qnames=[SAVE], records_filter={"tier": ["A", "B"]})
    assert kept["records_total"] == 2
    triage = read_symbol.create(repo)(qname=SAVE, records_filter={"status": "triage"})
    assert set(by_id(triage)) == {"R-A"}


def test_a_boolean_matches_only_a_boolean(repo: Config) -> None:
    """JSON's ``true`` is not ``1``: R-N's ``flag: 1`` never answers ``flag: true``."""
    answer = find_references.create(repo)(qname=SAVE, records_filter={"flag": True})
    assert set(by_id(answer)) == {"R-B"}


@pytest.mark.parametrize("wanted", [{"owner": "me"}, {"tier": "A", "summary": "x"}])
def test_a_filter_on_an_undeclared_name_is_refused(repo: Config, wanted: dict[str, object]) -> None:
    for call in (
        lambda: read_symbol.create(repo)(qname=SAVE, records_filter=wanted),
        lambda: find_references.create(repo)(qname=SAVE, records_filter=wanted),
        lambda: impact.create(repo)(qnames=[SAVE], records_filter=wanted),
    ):
        with pytest.raises(ValueError, match="no records block declares"):
            call()


def test_a_bad_filter_is_refused_on_every_path(repo: Config, tmp_path: Path) -> None:
    """Review F1: refused before any early return — an unknown subject, no index — and a value
    no attribute can hold (an object, a null, an empty list) is malformed."""
    with pytest.raises(ValueError, match="no records block declares"):
        read_symbol.create(repo)(qname="handlers.gone", records_filter={"owner": "me"})
    bare = load_config(tmp_path, {"CA_DB_PATH": str(tmp_path / "none.db")})
    with pytest.raises(ValueError, match="no records block declares"):
        impact.create(bare)(qnames=[SAVE], records_filter={"tier": "A"})
    for value in ({"a": 1}, None, [], [["A"]]):
        with pytest.raises(ValueError, match="must be a string"):
            find_references.create(repo)(qname=SAVE, records_filter={"tier": value})


def test_ac3_a_block_without_attributes_answers_as_before(tmp_path: Path) -> None:
    """AC3: no ``attributes`` key on any row, and any filter is refused — nothing is declared."""
    config = build(tmp_path / "repo")
    for answer in answers(config):
        assert all("attributes" not in row for row in by_id(answer).values())
    with pytest.raises(ValueError, match="no records block declares"):
        impact.create(config)(qnames=[SAVE], records_filter={"tier": "A"})


def test_only_scalars_and_lists_of_scalars_are_kept() -> None:
    kept = [records._attribute(value) for value in ("a", 0, 1.5, False, [1, "b"])]
    dropped = [
        records._attribute(value)
        for value in (
            None, {"a": 1}, [], [[1]], [{"a": 1}], float("nan"), [float("inf")],
            "x" * (records.TITLE_MAX + 1), list(range(records.ATTRIBUTE_LIST_MAX + 1)),
        )
    ]
    assert kept == ["a", 0, 1.5, False, [1, "b"]] and dropped == [None] * 9
    with pytest.raises(ValueError, match="must be a string"):
        records.check_filter({"tier": float("nan")}, ["tier"])


@pytest.mark.parametrize("bad", ["tier", [1], [""], [" "], None])
def test_a_malformed_attributes_list_fails_the_build_loud(tmp_path: Path, bad: object) -> None:
    item = {"sources": ["qa.json"], "fields": {"id": "key", "title": "summary"}, "attributes": bad}
    with pytest.raises(ConfigError, match="attributes must be a list of field paths"):
        records.read_blocks(item, "rules.json", tmp_path, lambda _d: None)
