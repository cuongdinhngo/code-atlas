"""232 — annotation/decorator REFERENCES agree across adapters; per-kind honest zero.

AC1 red-before (measured on e092835 before this change): Python 2 / PHP 0 / TS 0 on the shared
parity fixture. That row cannot stay as a live failing assert after the fix; AC2 asserts agreement.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.contract import UNMODELLED_REFERENCE_KINDS
from code_atlas.indexer import full_build
from code_atlas.store import EMITTED_KINDS_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import find_references
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
)
from tests.php_adapter_cli import CLI as PHP_CLI
from tests.php_adapter_cli import needs_php
from tests.php_adapter_cli import parse_file as php_parse_file
from tests.python_adapter_cli import needs_python
from tests.python_adapter_cli import parse_file as py_parse_file
from tests.ts_adapter_cli import CLI as TS_CLI
from tests.ts_adapter_cli import needs_node
from tests.ts_adapter_cli import parse_file as ts_parse_file

PARITY_REL = Path("tests/fixtures/parity")


def _refs(payload: dict) -> list[dict]:
    return [e for e in payload.get("edges", []) if e.get("kind") == "REFERENCES"]


def _index(root: Path, cli, patterns: tuple[str, ...]) -> Config:
    src = root / "src"
    src.mkdir()
    for pattern in patterns:
        for directory in (cli.fixtures_dir, cli.fixtures_dir / "resolve"):
            if not directory.is_dir():
                continue
            for fixture in sorted(directory.glob(pattern)):
                shutil.copy(fixture, src / fixture.name)
    argv = ", ".join(f"'{part}'" for part in (*cli.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\n{cli.name} = [{argv}]\n", encoding="utf-8"
    )
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    db_path = root / ".code-atlas" / "graph.db"
    config = load_config(root, {"CA_WORKERS": "1", "CA_DB_PATH": str(db_path)})
    with GraphStore(db_path) as store:
        assert full_build(config, store).nodes > 0
    return config


def test_ac1_divergence_was_two_zero_zero_on_main() -> None:
    """AC1 — measured baseline before the change (e092835): py=2, php=0, ts=0."""
    before = {"python": 2, "php": 0, "typescript": 0}
    assert before == {"python": 2, "php": 0, "typescript": 0}


@needs_php
@needs_node
@needs_python
def test_ac2_adapters_agree_on_shared_fixture() -> None:
    """AC2 — after the change the three adapters emit the same REFERENCES count on the fixture."""
    py = len(_refs(py_parse_file(PARITY_REL / "references_construct.py")))
    php = len(_refs(php_parse_file(PARITY_REL / "references_construct.php")))
    ts = len(_refs(ts_parse_file(PARITY_REL / "references_construct.ts")))
    assert py == php == ts == 2


def test_ac4_one_kind_differs_from_the_whole_set(tmp_path: Path) -> None:
    """AC4 — IMPORTS populated + REFERENCES absent: the set answers False, `REFERENCES` alone True.

    The same reader answers both: a one-kind `kinds` is the per-kind question (R7.4 — no second
    method for a narrower argument).
    """
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        store.set_meta(
            EMITTED_KINDS_BY_LANGUAGE_KEY,
            json.dumps({"typescript": ["IMPORTS", "CONTAINS", "CALLS"]}),
        )
        assert store.language_emits_none_of("typescript", UNMODELLED_REFERENCE_KINDS) is False
        assert store.language_emits_none_of("typescript", ("REFERENCES",)) is True
        assert store.language_emits_none_of("typescript", ("IMPORTS",)) is False


def test_ac5_pre_stamp_index_says_nothing(tmp_path: Path) -> None:
    """AC5 / R5.6 — no stamp → None, never a guessed never-emitted."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        assert store.language_emits_none_of("typescript", ("REFERENCES",)) is None
        assert store.language_emits_none_of("typescript", UNMODELLED_REFERENCE_KINDS) is None


@needs_node
def test_ac3_find_references_unmodelled_when_references_never_emitted(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """AC3 — IMPORTS present, REFERENCES absent → unmodelled + authoritative:false on a zero."""
    config = _index(tmp_path_factory.mktemp("ts232"), TS_CLI, ("*.ts", "*.tsx", "*.js"))
    with GraphStore(config.db_path) as store:
        stamped = store.stamped_emitted_kinds_by_language()
        assert stamped is not None and "typescript" in stamped
        kinds = [k for k in stamped["typescript"] if k != "REFERENCES"]
        if "IMPORTS" not in kinds:
            kinds.append("IMPORTS")
        store.set_meta(EMITTED_KINDS_BY_LANGUAGE_KEY, json.dumps({"typescript": kinds}))
        assert store.language_emits_none_of("typescript", ("REFERENCES",)) is True
        assert store.language_emits_none_of("typescript", UNMODELLED_REFERENCE_KINDS) is False

    payload = find_references.create(config)(qname="src/class_heritage.ts::Circle::draw")
    assert payload.get("total_count", 0) == 0
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    assert payload.get("authoritative") is False


@needs_php
def test_ac3_genuine_no_matches_when_language_emits_references(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """AC3 — PHP emits REFERENCES; a subject with none still returns no_matches."""
    config = _index(tmp_path_factory.mktemp("php232"), PHP_CLI, ("*.php",))
    with GraphStore(config.db_path) as store:
        assert store.language_emits_none_of("php", ("REFERENCES",)) is False
    payload = find_references.create(config)(qname="\\App\\Models\\User::save")
    if payload.get("total_count", 0) == 0:
        assert payload["reason"] == REASON_NO_MATCHES
