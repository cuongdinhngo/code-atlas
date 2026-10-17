"""Task 396 — an index built under other rules says so, and an incremental applies a rule edit.

A real Python-adapter build with a ``view_data`` rule and a ``routes`` TSV. Editing either file and
nothing else must turn ``rules_stale`` on in the status and on a rule-fed answer; the next
incremental re-applies the rules without parsing a file.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from code_atlas import contract, indexer, routes
from code_atlas.config import Config, load_config
from code_atlas.enrichment import RULES_DIGEST_KEY
from code_atlas.gitutil import changed_paths
from code_atlas.indexer import BuildReport, full_build, incremental_update
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools import find_callers, find_view_data, get_index_status, trace_capability
from code_atlas.tools.nav_result import REASON_OK, REASON_RULES_STALE
from tests.python_adapter_cli import CLI

HANDLER = "handler.Handler::index"
OTHER = "handler.Handler::other"
URL = "index.php?module=orders&action=edit"
SOURCE = (
    "class Bag:\n"
    "    def set(self, key, value):\n        pass\n\n"
    "    def put(self, key, value):\n        pass\n\n\n"
    "def helper():\n    return 1\n\n\n"
    "class Handler:\n"
    "    def index(self):\n"
    "        bag = Bag()\n"
    "        bag.set('items', helper())\n"
    "        bag.put('extra', 2)\n\n"
    "    def other(self):\n        return helper()\n"
)
SET_RULE = {"setter": "set", "key_arg": 1, "key_from": "string"}
PUT_RULE = {"setter": "put", "key_arg": 1, "key_from": "string"}


def _rules(*view_data: dict[str, object]) -> str:
    return json.dumps(
        {
            "view_data": list(view_data),
            "routes": {
                "significant": ["module", "action"],
                "tsv": "routes.tsv",
                "columns": {"key": "url", "target": "handler"},
            },
        }
    )


def _git(root: Path, *argv: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *argv],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _config(root: Path, *, rules: bool = True) -> Config:
    argv = ", ".join(json.dumps(part) for part in (*CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(f"[adapter_cmd]\npython = [{argv}]\n", encoding="utf-8")
    env = {
        "CA_TRUST_PROJECT_FILE": "1",
        "CA_WORKERS": "1",
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
    }
    if rules:
        env["CA_INDIRECTION_RULES"] = "rules.json"
    return load_config(root, env)


@pytest.fixture
def repo(tmp_path: Path) -> Config:
    """One committed repo, built in full under the ``set`` rule and a one-row route table."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "handler.py").write_text(SOURCE, encoding="utf-8")
    (root / "rules.json").write_text(_rules(SET_RULE), encoding="utf-8")
    (root / "routes.tsv").write_text(f"url\thandler\n{URL}\t{HANDLER}\n", encoding="utf-8")
    config = _config(root)
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return config


def _incremental(config: Config) -> BuildReport:
    with GraphStore(config.db_path) as store:
        last = store.get_meta(LAST_COMMIT_KEY)
        changed = changed_paths(config.root, last)
        assert changed is not None
        return incremental_update(config, store, changed)


def _keys(answer: dict[str, Any]) -> set[str]:
    return {str(hit.get("key")) for hit in answer["results"]}


def _status(config: Config, level: str = "standard") -> dict[str, Any]:
    return get_index_status.create(config, (get_index_status.NAME,))(detail_level=level)


def test_ac1_a_rule_edit_turns_rules_stale_on(repo: Config) -> None:
    """AC1 (proving test): the status names both digests; the rule-fed answer keeps its rows."""
    (repo.root / "rules.json").write_text(_rules(SET_RULE, PUT_RULE), encoding="utf-8")

    status = _status(repo)
    minimal = _status(repo, "minimal")
    answer = find_view_data.create(repo)(HANDLER)

    assert status["rules_stale"] is True and minimal["rules_stale"] is True
    digests = status["rules_digest"]
    assert digests["built"] and digests["current"] and digests["built"] != digests["current"]
    assert "rules changed" in status["summary"] and "build_or_update_index" in status["summary"]
    assert answer["reason"] == REASON_RULES_STALE
    assert answer["rules_stale"] is True
    assert _keys(answer) == {"items"}  # the old rules' rows, kept


def test_ac1_an_answer_that_reads_no_rule_edge_is_unchanged(repo: Config) -> None:
    before = find_callers.create(repo)("handler.helper")
    (repo.root / "rules.json").write_text(_rules(SET_RULE, PUT_RULE), encoding="utf-8")
    after = find_callers.create(repo)("handler.helper")

    assert before == after and after["reason"] == REASON_OK


def test_ac2_an_incremental_applies_the_edit_without_a_parse(repo: Config) -> None:
    """AC2: the new rule's edge is there, nothing was parsed, and the build says it re-applied."""
    (repo.root / "rules.json").write_text(_rules(SET_RULE, PUT_RULE), encoding="utf-8")

    report = _incremental(repo)
    answer = find_view_data.create(repo)(HANDLER)

    assert (report.files, report.parsed) == (0, 0)
    assert report.rules_reapplied is True and report.edges > 0
    assert answer["reason"] == REASON_OK and "rules_stale" not in answer
    assert _keys(answer) == {"items", "extra"}
    assert "rules_stale" not in _status(repo)


def test_ac2_the_rows_equal_a_full_build_of_the_same_state(repo: Config) -> None:
    """R4.2: the rules-only delta and a fresh full build hold the same rule rows."""
    (repo.root / "rules.json").write_text(_rules(SET_RULE, PUT_RULE), encoding="utf-8")
    _incremental(repo)
    with GraphStore(repo.db_path) as store:
        delta = sorted(
            (str(e["source_qname"]), str(e["target_raw"]), str(e.get("target_qname")))
            for e in store.edges_matching_kind(contract.PROVIDES_VIEW_DATA, limit=50)
        )
        full_build(repo, store)
        rebuilt = sorted(
            (str(e["source_qname"]), str(e["target_raw"]), str(e.get("target_qname")))
            for e in store.edges_matching_kind(contract.PROVIDES_VIEW_DATA, limit=50)
        )
    assert delta == rebuilt and len(delta) == 2


def test_ac3_rules_removed_clear_every_rule_row(repo: Config) -> None:
    """AC3: with the knob off, an incremental drops the rule edges and the route table."""
    bare = _config(repo.root, rules=False)
    assert _status(bare)["rules_stale"] is True  # built under rules, now none

    report = _incremental(bare)

    assert report.parsed == 0 and report.rules_reapplied is True
    with GraphStore(bare.db_path) as store:
        assert store.edges_matching_kind(contract.PROVIDES_VIEW_DATA, limit=5) == []
        assert store.get_meta(routes.ROUTES_META_KEY) is None
        assert store.get_meta(RULES_DIGEST_KEY) == ""
    assert "rules_stale" not in _status(bare)


def test_ac4_a_route_table_edit_is_stale_then_applied(repo: Config) -> None:
    """AC4: the TSV alone moves the digest; the route answers labelled, then from the new row."""
    (repo.root / "routes.tsv").write_text(f"url\thandler\n{URL}\t{OTHER}\n", encoding="utf-8")

    stale = trace_capability.create(repo)(route=URL)
    assert stale["reason"] == REASON_RULES_STALE and stale["rules_stale"] is True
    assert stale["results"][0]["steps"][0]["qname"] == HANDLER  # old row, kept

    report = _incremental(repo)
    fresh = trace_capability.create(repo)(route=URL)

    assert report.parsed == 0 and report.rules_reapplied is True
    assert fresh["reason"] == REASON_OK and "rules_stale" not in fresh
    assert fresh["results"][0]["steps"][0]["qname"] == OTHER


def test_ac5_an_unchanged_digest_keeps_the_noop(
    repo: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5: no late writer runs, the report is zero, and the answers are byte-identical."""
    with GraphStore(repo.db_path) as store:
        assert store.get_meta(RULES_DIGEST_KEY)  # the first build seeded it (374-C1)
    before = (find_view_data.create(repo)(HANDLER), trace_capability.create(repo)(route=URL))
    calls = {"late": 0}
    real = indexer.apply_indirection_rules

    def spy(*args: object, **kwargs: object) -> object:
        calls["late"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(indexer, "apply_indirection_rules", spy)
    report = _incremental(repo)
    after = (find_view_data.create(repo)(HANDLER), trace_capability.create(repo)(route=URL))

    assert calls["late"] == 0
    assert (report.parsed, report.edges, report.rules_reapplied) == (0, 0, False)
    assert json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)


def test_an_index_with_no_stored_digest_is_stale_only_under_rules(repo: Config) -> None:
    """W2: a pre-396 index cannot show it was built under the rules, so it is not attested."""
    with GraphStore(repo.db_path) as store:
        store.delete_meta(RULES_DIGEST_KEY)

    assert _status(repo)["rules_stale"] is True
    assert "rules_stale" not in _status(_config(repo.root, rules=False))


def test_an_unreadable_rule_file_is_reported_not_raised(repo: Config) -> None:
    """H6: the status answers with the error; the build is what fails loud."""
    (repo.root / "rules.json").write_text("{not json", encoding="utf-8")

    status = _status(repo)

    assert status["rules_stale"] is True
    assert status["rules_digest"]["current"] is None and status["rules_error"]
