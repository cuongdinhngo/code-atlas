"""Task 407 — a record written about code (a ticket, an incident) attached to the symbols it names.

A ``records`` block in the rule file names globs of JSON record files and a field map; the build
resolves each target and the tools list a symbol's records beside its answer. Built through the
real Python and SQL adapters, so the targets are stored qnames. Every id here is invented (R2.4).
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from code_atlas import cli, records
from code_atlas.config import Config, ConfigError, load_config
from code_atlas.enrichment import load_indirection_rules
from code_atlas.indexer import full_build, incremental_update
from code_atlas.store import GraphStore
from code_atlas.tools import (
    build_or_update_index,
    find_references,
    get_index_status,
    impact,
    read_symbol,
)

NODE = shutil.which("node")
REPO = Path(__file__).resolve().parent.parent
PYTHON_ENTRY = REPO / "adapters" / "python" / "index.py"
SQL_ENTRY = REPO / "adapters" / "sql" / "index.js"
pytestmark = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {SQL_ENTRY}")

EDIT = "handlers.orders.Orders::edit"
SAVE = "handlers.repo.save"
TABLE = "dbo.Orders"
SECRET = "SEC-9"

SOURCES = {
    "handlers/__init__.py": "",
    "handlers/orders.py": (
        "from handlers.repo import save\n\n\nclass Orders:\n"
        "    def edit(self):\n        return save('order')\n"
    ),
    "handlers/repo.py": "def save(row):\n    return row\n",
    # One table, two declaring files: a schema file and a later migration (C2).
    "db/schema.sql": "CREATE TABLE dbo.Orders (Id int NOT NULL);\n",
    "db/V002.sql": "CREATE TABLE dbo.Orders (Id int NOT NULL, Note int NULL);\n",
}

RECORD_FILES: dict[str, Any] = {
    # One record per file, the consumer's own shape; the table is spelt in another case.
    "qa/T-1.json": {
        "key": "T-1",
        "summary": "Order edit could not save",
        "link": "https://tracker.example/T-1",
        "code": {"symbols": [EDIT], "tables": ["dbo.orders"]},
    },
    # A consumer-side export: a list of records in one file.
    "qa/export.json": [
        {"key": "T-2", "summary": "Saved row lost its note", "code": {"symbols": [SAVE]}},
        {"key": "T-3", "summary": "Removed handler", "code": {"symbols": ["handlers.gone"]}},
        {"summary": "no id, skipped"},
    ],
    "qa/SEC-9.json": {"key": SECRET, "summary": "open weakness", "code": {"symbols": [SAVE]}},
}

BLOCK: dict[str, object] = {
    "sources": ["qa/*.json"],
    "fields": {
        "id": "key",
        "title": "summary",
        "url": "link",
        "targets": ["code.symbols", "code.tables"],
    },
    "kind": "ticket",
    "exclude": "qa.exclude",
}


def write(root: Path, path: str, text: str) -> None:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text(text, encoding="utf-8")


def make_repo(root: Path, *, block: dict[str, object] | None = BLOCK) -> Config:
    """The fixture repo with its record files and, when ``block`` is given, the rule file."""
    for path, text in SOURCES.items():
        write(root, path, text)
    for path, body in RECORD_FILES.items():
        write(root, path, json.dumps(body))
    write(root, "qa/broken.json", "{not json")
    write(root, "qa.exclude", f"# kept off every answer\n{SECRET}\n")
    # The export and the exclusion list are regenerated, never committed (Scope 1, AC6).
    write(root, ".gitignore", "qa/export.json\nqa.exclude\n")
    env = {
        "CA_WORKERS": "1",
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
        "CA_PYTHON_CMD": shlex.join([sys.executable, str(PYTHON_ENTRY), "--server"]),
        "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
    }
    if block is not None:
        write(root, "rules.json", json.dumps({"records": block}))
        env["CA_INDIRECTION_RULES"] = "rules.json"
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    return load_config(root, env)


def built(root: Path, *, block: dict[str, object] | None = BLOCK) -> Config:
    config = make_repo(root, block=block)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return config


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return built(tmp_path_factory.mktemp("records") / "repo")


def status_of(config: Config) -> Callable[..., dict[str, object]]:
    return get_index_status.create(config, (get_index_status.NAME,))


def rows(answer: dict[str, object]) -> list[dict[str, Any]]:
    found: Any = answer.get("records", [])
    return list(found)


def block_of(answer: dict[str, object]) -> dict[str, Any]:
    found: Any = answer["records"]
    return dict(found)


def ids(answer: dict[str, object]) -> list[str]:
    return [str(row["id"]) for row in rows(answer)]


def test_find_references_lists_a_targets_records_labelled_declared(repo: Config) -> None:
    """AC1a: the record is listed on its target, HEURISTIC and rule-derived."""
    answer = find_references.create(repo)(qname=SAVE)
    assert answer["records"] == [
        {
            "id": "T-2",
            "title": "Saved row lost its note",
            "kind": "ticket",
            "tier": "HEURISTIC",
            "rule": True,
        }
    ]


def test_read_symbol_lists_the_symbols_records(repo: Config) -> None:
    answer = read_symbol.create(repo)(qname=EDIT)
    assert ids(answer) == ["T-1"]
    assert rows(answer)[0]["url"] == "https://tracker.example/T-1"


def test_impact_lists_records_across_the_radius_with_the_carrying_node(repo: Config) -> None:
    """AC2: the seed's record under the seed, the caller's record under the caller."""
    answer = impact.create(repo)(qnames=[SAVE])
    assert {(row["id"], row["via"]) for row in rows(answer)} == {
        ("T-2", SAVE),
        ("T-1", EDIT),
    }
    assert answer["records_total"] == 2


def test_a_table_declared_in_two_files_carries_its_record(repo: Config) -> None:
    """C2: attachment is by qname, so every definition carries it — even where impact refuses
    to walk an ambiguous seed, and with the record spelling the table in another case."""
    assert ids(find_references.create(repo)(qname=TABLE)) == ["T-1"]
    answer = impact.create(repo)(qnames=[TABLE])
    assert answer["reason"] == "subject_ambiguous"
    assert [(row["id"], row["via"]) for row in rows(answer)] == [
        ("T-1", TABLE)
    ]


def test_a_dangling_target_is_reported_never_attached(repo: Config) -> None:
    """AC3: the build result and the status name the pair; no answer carries the record."""
    build = build_or_update_index.create(repo)(detail_level="minimal")
    status = status_of(repo)()
    for block in (block_of(build), block_of(status)):
        assert block["dangling"] == 1
        assert block["dangling_first"] == [
            {"id": "T-3", "target": "handlers.gone"}
        ]
        assert block["attached"] == 2 and block["skipped"] == 2
    for answer in (
        find_references.create(repo)(qname=SAVE),
        impact.create(repo)(qnames=[SAVE]),
    ):
        assert "T-3" not in ids(answer)


def test_an_excluded_record_is_in_no_answer_and_only_counted(
    repo: Config, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4: the five surfaces and the CLI never spell the id; status counts it."""
    answers = [
        find_references.create(repo)(qname=SAVE),
        read_symbol.create(repo)(qname=SAVE),
        impact.create(repo)(qnames=[SAVE]),
        status_of(repo)(detail_level="verbose"),
        build_or_update_index.create(repo)(full=True, allow_full_rebuild=True),
    ]
    for answer in answers:
        assert SECRET not in json.dumps(answer, default=str)
    assert block_of(answers[3])["excluded"] == 1
    for name, value in (
        ("CA_WORKERS", "1"),
        ("CA_INDIRECTION_RULES", "rules.json"),
        ("CA_PYTHON_CMD", shlex.join([sys.executable, str(PYTHON_ENTRY), "--server"])),
        ("CA_SQL_CMD", shlex.join([str(NODE), str(SQL_ENTRY), "--server"])),
        ("CA_DB_PATH", str(repo.db_path)),
    ):
        monkeypatch.setenv(name, value)
    assert cli.build(repo.root, full=True) == cli.OK
    printed = capsys.readouterr()
    assert "code-atlas build:" in printed.err  # the CLI ran and spoke
    assert SECRET not in printed.out + printed.err
    with GraphStore(repo.db_path) as store:
        stored = [store.get_meta(key) for key in records_keys()]
    assert all(SECRET not in (raw or "") for raw in stored)


def records_keys() -> tuple[str, ...]:
    return (records.RECORDS_META_KEY, records.RECORDS_STATUS_META_KEY)


def test_an_edited_record_file_reaches_the_next_build_with_no_consumer_step(
    tmp_path: Path,
) -> None:
    """AC1b: an incremental after an edit to a record file answers from the edited file."""
    config = built(tmp_path / "repo")
    path = config.root / "qa" / "T-1.json"
    edited = dict(RECORD_FILES["qa/T-1.json"])
    edited.update(summary="Edit saves again", code={"symbols": [SAVE]})
    path.write_text(json.dumps(edited), encoding="utf-8")
    with GraphStore(config.db_path) as store:
        report = incremental_update(config, store, [])
    assert report.rules_reapplied
    assert sorted(ids(find_references.create(config)(qname=SAVE))) == ["T-1", "T-2"]
    assert ids(read_symbol.create(config)(qname=EDIT)) == []


def test_a_removed_target_dangles_after_an_incremental(tmp_path: Path) -> None:
    """AC3 at a later revision: a removed symbol's record is reported, not served."""
    config = built(tmp_path / "repo")
    write(config.root, "handlers/repo.py", "def store(row):\n    return row\n")
    subprocess.run(["git", "add", "-A"], cwd=config.root, check=True, capture_output=True)
    with GraphStore(config.db_path) as store:
        incremental_update(config, store, ["handlers/repo.py"])
    status = block_of(status_of(config)())
    assert {"id": "T-2", "target": SAVE} in status["dangling_first"]
    assert ids(impact.create(config)(qnames=[EDIT])) == ["T-1"]


def test_a_gitignored_source_is_read_and_its_rewrite_reaches_the_next_refresh(
    tmp_path: Path,
) -> None:
    """AC6: the export git ignores is read at build; rewritten with the same ids and new targets,
    answers are flagged `rules_stale` until the next refresh, which moves the records."""
    config = built(tmp_path / "repo")
    listed = subprocess.run(
        ["git", "ls-files", "qa"], cwd=config.root, check=True, capture_output=True, text=True
    ).stdout.split()
    assert "qa/export.json" not in listed and ids(read_symbol.create(config)(qname=SAVE)) == ["T-2"]
    export = list(RECORD_FILES["qa/export.json"])
    export[0] = {**export[0], "code": {"symbols": [EDIT]}}
    (config.root / "qa" / "export.json").write_text(json.dumps(export), encoding="utf-8")
    assert status_of(config)()["rules_stale"] is True
    stale = find_references.create(config)(qname=SAVE)
    assert ids(stale) == ["T-2"] and stale["rules_stale"] is True
    assert stale["reason"] != "rules_stale"  # records are a side-field: flagged, not relabelled
    with GraphStore(config.db_path) as store:
        assert incremental_update(config, store, []).rules_reapplied
    assert "records" not in find_references.create(config)(qname=SAVE)
    assert ids(read_symbol.create(config)(qname=EDIT)) == ["T-1", "T-2"]
    assert "rules_stale" not in status_of(config)()


def test_no_records_block_adds_nothing_to_any_answer(tmp_path: Path) -> None:
    """AC5: with no block, no surface carries a records field and the index holds no key."""
    config = built(tmp_path / "repo", block=None)
    answers = [
        find_references.create(config)(qname=SAVE),
        read_symbol.create(config)(qname=EDIT),
        impact.create(config)(qnames=[SAVE]),
        status_of(config)(detail_level="verbose"),
        build_or_update_index.create(config)(full=True, allow_full_rebuild=True),
    ]
    for answer in answers:
        assert not any(key.startswith("records") for key in answer)
    with GraphStore(config.db_path) as store:
        assert all(store.get_meta(key) is None for key in records_keys())


def test_a_rule_file_without_the_block_answers_as_no_rule_file(tmp_path: Path) -> None:
    """AC5: a block that stops being declared leaves nothing behind."""
    config = built(tmp_path / "repo")
    (config.root / "rules.json").write_text("{}", encoding="utf-8")
    with GraphStore(config.db_path) as store:
        incremental_update(config, store, [])
        assert all(store.get_meta(key) is None for key in records_keys())
    assert "records" not in find_references.create(config)(qname=SAVE)


def test_a_missing_exclude_file_fails_the_build(tmp_path: Path) -> None:
    """W2: serving every record is not the fallback for a missing exclusion list."""
    config = make_repo(tmp_path / "repo")
    (config.root / "qa.exclude").unlink()
    with pytest.raises(ConfigError, match="exclude"):
        load_indirection_rules(config)


@pytest.mark.parametrize(
    "block",
    [
        {"sources": []},
        {"sources": ["../outside/*.json"]},
        {"sources": ["qa/*.json"], "fields": {"targets": []}},
        {"sources": ["qa/*.json"], "kind": 3},
    ],
)
def test_a_bad_block_fails_loud(tmp_path: Path, block: dict[str, object]) -> None:
    config = make_repo(tmp_path / "repo", block=block)
    with pytest.raises(ConfigError, match="records"):
        load_indirection_rules(config)


def test_a_thousand_records_load_quickly(tmp_path: Path) -> None:
    """C4: the anchor's scale (about 1,000 records); the measured time is printed for the ledger."""
    for n in range(1000):
        body = {"key": f"R-{n}", "summary": "x", "code": {"symbols": [SAVE, f"m.f{n}"]}}
        write(tmp_path, f"qa/R-{n}.json", json.dumps(body))
    started = time.monotonic()
    block = {"sources": ["qa/*.json"], "fields": BLOCK["fields"]}
    sets = records.read_blocks(block, "rules.json", tmp_path, lambda _: None)
    stored, counts = records.resolve(sets, lambda target: target if target == SAVE else None)
    elapsed = time.monotonic() - started
    print(f"1000 records read and resolved in {elapsed:.3f}s")
    assert counts["attached"] == 1000 and counts["dangling"] == 1000
    assert elapsed < 5.0
