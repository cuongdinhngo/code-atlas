"""Task 416 — a path seed covers the symbols its own file defines, never its namespace's.

``ns\\A`` in ``a.php`` and ``ns\\B`` in ``b.php`` each carry a record, and so does each file. Every
file in ``ns`` declares the ``\\ns`` Namespace node, so seeding ``a.php`` with it made ``b.php``'s
record ``direct``. Built through the real PHP adapter.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import impact
from tests.php_adapter_cli import CLI, needs_php
from tests.python_adapter_cli import CLI as PY_CLI

pytestmark = needs_php

SOURCES = {
    "a.php": "<?php\nnamespace ns;\nclass A { public function run() { return 1; } }\n",
    "b.php": "<?php\nnamespace ns;\nclass B { public function go() { return 2; } }\n",
}
RECORDS = [
    {"key": "REC-A", "summary": "A", "targets": ["\\ns\\A"]},
    {"key": "REC-B", "summary": "B", "targets": ["\\ns\\B"]},
    {"key": "FILE-A", "summary": "a.php", "targets": ["a.php"]},
    {"key": "FILE-B", "summary": "b.php", "targets": ["b.php"]},
]


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Config:
    root = tmp_path_factory.mktemp("spanning") / "repo"
    root.mkdir()
    for path, text in SOURCES.items():
        (root / path).write_text(text, encoding="utf-8")
    (root / "qa.json").write_text(json.dumps(RECORDS), encoding="utf-8")
    rule = {"sources": ["qa.json"], "fields": {"id": "key", "title": "summary"}}
    (root / "rules.json").write_text(json.dumps({"records": rule}), encoding="utf-8")
    argv = ", ".join(json.dumps(part) for part in (*CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(f"[adapter_cmd]\nphp = [{argv}]\n", encoding="utf-8")
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


def ids(answer: dict[str, object]) -> list[str]:
    found: Any = answer.get("records", [])
    return [str(row["id"]) for row in found]


@pytest.mark.parametrize("records", ["direct", "radius"])
def test_a_path_seed_answers_its_own_files_records_only(repo: Config, records: str) -> None:
    """The proving test: ``b.php``'s records are never ``a.php``'s, whatever the mode."""
    answer = impact.create(repo)(paths=["a.php"], records=records)
    assert ids(answer) == ["REC-A", "FILE-A"]


def test_a_path_seed_and_its_qname_seed_agree(repo: Config) -> None:
    """Seeding the file and seeding the class it defines name the same records."""
    tool = impact.create(repo)
    by_path = tool(paths=["a.php"], records="direct")
    by_qname = tool(qnames=["ns\\A"], records="direct")
    assert sorted(ids(by_path)) == sorted(ids(by_qname)) == ["FILE-A", "REC-A"]


def test_the_namespace_is_no_seed_of_a_path(repo: Config) -> None:
    """No ``\\ns`` seed, so no ``ambiguous_definitions`` across both files and nothing dropped."""
    answer = impact.create(repo)(paths=["a.php"])
    assert "ambiguous_definitions" not in answer
    assert answer["seeds_dropped"] == 0
    assert answer["seed_expansion"] == {"paths": 1, "seeds": 3}


def test_a_namespace_only_its_own_file_declares_stays_a_path_seed(
    tmp_path: Path,
) -> None:
    """A Python package's ``Namespace`` is its ``__init__.py``'s alone, so that path seeds it."""
    root = tmp_path / "repo"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    argv = ", ".join(json.dumps(part) for part in (*PY_CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(f"[adapter_cmd]\npython = [{argv}]\n", encoding="utf-8")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    config = load_config(
        root,
        {
            "CA_TRUST_PROJECT_FILE": "1",
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
        },
    )
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    answer = impact.create(config)(paths=["pkg/__init__.py"])
    assert answer["seed_expansion"] == {"paths": 1, "seeds": 3}
    assert "pkg" in [row["qname"] for row in cast(list[dict[str, Any]], answer["results"])]
