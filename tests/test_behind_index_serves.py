"""Task 388 — a behind index with no build running answers, labelled, instead of refusing."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references, get_index_status, search_symbol
from code_atlas.tools.claim import REV_CHARS
from code_atlas.tools.freshness import label_behind
from code_atlas.tools.nav_result import (
    REASON_INDEX_BEHIND,
    REASON_INDEX_BEHIND_SUBJECT_CHANGED,
    REASON_INDEX_BEHIND_SUBJECT_REMOVED,
    REASON_INDEX_STALE,
    REASON_OK,
)

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

STABLE = (
    "<?php\nnamespace App;\nclass Stable { public function hit() {} "
    "public function run() { $this->hit(); } }\n"
)
DRIFT = (
    "<?php\nnamespace App;\nclass Drift { public function gone() {} "
    "public function run(Stable $s) { $s->hit(); } }\n"
)
USER = "<?php\nnamespace App;\nclass User { public function go(Drift $d) { $d->gone(); } }\n"
OTHER = "<?php\nnamespace Lib;\nclass Other{n} {{ public function x() {{ {body} }} }}\n"
# Keys a behind answer adds; a current index must carry none of them (AC5).
BEHIND_KEYS = ("last_commit", "index_revision", "source_stale", "behind_because")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _commit(root: Path) -> None:
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "edit")


def _env(php: str | None = None) -> dict[str, str]:
    return {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": php or shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
    }


def _write(root: Path, rel: str, body: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(body, encoding="utf-8")


def _built(root: Path) -> tuple[Config, str]:
    """Plant, commit and build at revision A; return the config and A."""
    _write(root, "src/stable.php", STABLE)
    _write(root, "src/drift.php", DRIFT)
    _write(root, "src/user.php", USER)
    for n in ("", "2"):
        _write(root, f"lib/other{n}.php", OTHER.format(n=n, body=""))
    _git(root, "init", "-q")
    _commit(root)
    config = load_config(root, _env())
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
        built = store.get_meta("last_commit")
    assert isinstance(built, str) and built
    return config, built


def _status(config: Config) -> dict[str, object]:
    return get_index_status.create(config, (get_index_status.NAME,))(detail_level="standard")


def _keys(payload: object) -> set[str]:
    """Every key anywhere in a payload, nested rows included."""
    if isinstance(payload, dict):
        return set(payload) | {k for v in payload.values() for k in _keys(v)}
    if isinstance(payload, list):
        return {k for v in payload for k in _keys(v)}
    return set()


@needs_php
def test_ac1_unchanged_subject_answers_index_behind_with_the_built_revision(
    tmp_path: Path,
) -> None:
    config, built = _built(tmp_path)
    _write(tmp_path, "lib/other.php", OTHER.format(n="", body="return 1;"))
    _commit(tmp_path)  # HEAD at B; no build holds the lock

    for tool in (find_callers, find_references):
        payload = tool.create(config)("\\App\\Stable::hit", detail_level="minimal")
        assert payload["reason"] == REASON_INDEX_BEHIND, payload
        assert payload["total_count"] == 2
        assert payload["last_commit"] == built
        assert {row["index_revision"] for row in payload["results"]} == {built[:REV_CHARS]}


@needs_php
def test_ac2_changed_subject_refusal_names_the_exact_serve_behind_call(tmp_path: Path) -> None:
    config, built = _built(tmp_path)
    _write(tmp_path, "src/stable.php", STABLE.replace("hit() {}", "hit() { return 1; }"))
    _commit(tmp_path)
    broken = load_config(tmp_path, _env("false"))  # the re-read of the changed file fails

    refused = find_callers.create(broken)("\\App\\Stable::hit", detail_level="minimal")
    assert refused["reason"] == REASON_INDEX_STALE
    call = 'find_callers(qname="\\\\App\\\\Stable::hit", detail_level="minimal", serve_behind=true)'
    assert str(refused["try_instead_hint"]).endswith(call), refused

    served = find_callers.create(broken)(
        "\\App\\Stable::hit", detail_level="minimal", serve_behind=True
    )
    assert served["reason"] == REASON_INDEX_BEHIND_SUBJECT_CHANGED
    assert served["last_commit"] == built
    assert served["total_count"] == 2


@needs_php
def test_ac3_search_on_a_behind_index_never_answers_index_stale(tmp_path: Path) -> None:
    config, _ = _built(tmp_path)
    # Two drifted files against a one-file repair budget, and no file named by the miss.
    for n in ("", "2"):
        _write(tmp_path, f"lib/other{n}.php", OTHER.format(n=n, body="return 2;"))
    search = search_symbol.create(config)

    hits = search(query="Other", detail_level="minimal")
    assert hits["reason"] != REASON_INDEX_STALE
    # One file spent the budget and was re-read; every row of the other says it drifted.
    stale = {str(row["file"]) for row in hits["results"] if row.get("source_stale")}
    assert len(stale) == 1 and stale <= {"lib/other.php", "lib/other2.php"}, hits
    assert all(row.get("source_stale") for row in hits["results"] if row["file"] in stale)

    miss = search(query="Nowhere", detail_level="minimal")
    assert miss["reason"] == REASON_INDEX_BEHIND
    assert miss["other_indexed_files_drifted"] == 2


@needs_php
def test_ac3_a_sweep_names_the_subjects_its_shared_budget_could_not_vouch_for(
    tmp_path: Path,
) -> None:
    config, _ = _built(tmp_path)
    for n in ("", "2"):
        _write(tmp_path, f"lib/other{n}.php", OTHER.format(n=n, body="return 2;"))

    sweep = search_symbol.create(config)(
        queries=["Stable", "Other", "Nowhere"], detail_level="minimal"
    )
    reasons = {str(s["query"]): s["reason"] for s in sweep["subjects"]}
    assert REASON_INDEX_STALE not in reasons.values(), reasons
    assert sweep["index_stale_subjects"] == ["Other", "Nowhere"]


@needs_php
def test_ac4_a_deleted_method_lists_its_built_graph_references(tmp_path: Path) -> None:
    config, built = _built(tmp_path)
    _write(tmp_path, "src/drift.php", DRIFT.replace("public function gone() {} ", ""))

    payload = find_references.create(config)("\\App\\Drift::gone", detail_level="minimal")
    assert payload["reason"] == REASON_INDEX_BEHIND_SUBJECT_REMOVED, payload
    assert [row["qname"] for row in payload["results"]] == ["\\App\\User::go"]
    assert payload["last_commit"] == built


@needs_php
def test_ac4_a_deleted_file_answers_removed_without_a_re_read(tmp_path: Path) -> None:
    config, _ = _built(tmp_path)
    (tmp_path / "src" / "drift.php").unlink()

    payload = find_callers.create(config)("\\App\\Drift::gone", detail_level="minimal")
    assert payload["reason"] == REASON_INDEX_BEHIND_SUBJECT_REMOVED, payload
    assert [row["qname"] for row in payload["results"]] == ["\\App\\User::go"]


@needs_php
def test_f2_status_names_the_paths_that_made_it_behind(tmp_path: Path) -> None:
    config, _ = _built(tmp_path)
    (tmp_path / "lib" / "other2.php").unlink()
    _write(tmp_path, "lib/other.php", OTHER.format(n="", body="return 3;"))

    status = _status(config)
    assert status["behind_because"] == [
        {"path": "lib/other.php", "change": "uncommitted"},
        {"path": "lib/other2.php", "change": "deleted"},
    ]
    assert status["behind_serves"] == [
        "search_symbol",
        "read_symbol",
        "find_callers",
        "find_references",
    ]
    assert "behind_refuses" not in status


@needs_php
def test_ac5_a_current_index_carries_no_behind_label(tmp_path: Path) -> None:
    config, _ = _built(tmp_path)

    answers = [
        find_callers.create(config)("\\App\\Stable::hit"),
        find_references.create(config)("\\App\\Stable::hit"),
        search_symbol.create(config)(query="Stable"),
        search_symbol.create(config)(queries=["Stable", "Nowhere"]),
    ]
    for payload in answers:
        assert not _keys(payload) & set(BEHIND_KEYS), payload
    assert answers[0]["reason"] == REASON_OK
    assert answers[1]["reason"] == REASON_OK
    assert "behind_serves" not in _status(config)


def test_a_removed_subject_keeps_its_label_with_no_revision_to_stamp() -> None:
    """Challenger minor 3 — off git there is no revision, but a removed subject is never ``ok``."""
    payload = label_behind(
        {"reason": REASON_OK, "results": [{"qname": "A::b"}]},
        subject_path=None,
        revision={"staleness": "unknown", "last_commit": None},
        dirty_paths=[],
        subject_removed=True,
    )
    assert payload["reason"] == REASON_INDEX_BEHIND_SUBJECT_REMOVED
    assert "last_commit" not in payload
