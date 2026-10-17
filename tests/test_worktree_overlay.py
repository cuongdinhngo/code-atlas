"""Task 389 — an agent in a worktree reads that worktree's spans and symbols, without a build."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas import overlay as overlay_module
from code_atlas.adapter import ParseResult
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.overlay import OVERLAY_PARSE_CAP, Overlay
from code_atlas.store import GraphStore
from code_atlas.tools import file_outline, find_callers, read_symbol, search_symbol
from code_atlas.tools.nav_result import REASON_OK, REASON_WORKTREE_OVERLAY

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

PAD = "    // padding\n"
SERVICE = "<?php\nnamespace App;\nclass Service {\nPAD    public function run() { return 1; }\n}\n"
CALLER = "<?php\nnamespace App;\nclass Caller { public function go(Service $s) { $s->run(); } }\n"
OVERLAY_KEYS = ("overlay", "overlay_root", "overlay_truncated")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _commit(root: Path, message: str = "edit") -> None:
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", message)


def _write(root: Path, rel: str, body: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(body, encoding="utf-8")


def _env(caller_root: Path | None = None) -> dict[str, str]:
    env = {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
    }
    if caller_root is not None:
        env["CA_CALLER_ROOT"] = str(caller_root)
    return env


def _main_and_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Main built at A; a linked worktree on its own branch, where `run` sits 90 lines lower."""
    main, worktree = tmp_path / "main", tmp_path / "wt"
    _write(main, "src/Service.php", SERVICE.replace("PAD", ""))
    _write(main, "src/Caller.php", CALLER)
    _git(main, "init", "-q")
    _commit(main, "init")
    config = load_config(main, _env())
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    _git(main, "worktree", "add", "-q", "-b", "feature", str(worktree))
    _write(worktree, "src/Service.php", SERVICE.replace("PAD", PAD * 90))
    _commit(worktree)
    return main, worktree


def _in(main: Path, worktree: Path | None) -> Config:
    return load_config(main, _env(worktree))


@needs_php
def test_ac1_read_symbol_returns_the_worktrees_span_and_body(tmp_path: Path) -> None:
    main, worktree = _main_and_worktree(tmp_path)

    built = read_symbol.create(_in(main, None))("\\App\\Service::run", detail_level="minimal")
    moved = read_symbol.create(_in(main, worktree))("\\App\\Service::run", detail_level="minimal")
    assert moved["line_start"] == built["line_start"] + 90, (built, moved)
    assert "return 1" in str(moved["source"])
    assert moved["overlay"] == "worktree"
    assert moved["overlay_root"] == str(worktree.resolve())


@needs_php
def test_ac2_a_new_worktree_file_is_found_without_a_build(tmp_path: Path) -> None:
    main, worktree = _main_and_worktree(tmp_path)
    _write(
        worktree,
        "src/Fresh.php",
        "<?php\nnamespace App;\nclass Fresh { public function brandNew() {} }\n",
    )

    found = search_symbol.create(_in(main, worktree))(query="brandNew", detail_level="minimal")
    assert found["reason"] == REASON_OK
    assert [row["qname"] for row in found["results"]] == ["\\App\\Fresh::brandNew"]
    assert found["overlay"] == "worktree"
    outline = file_outline.create(_in(main, worktree))("src/Fresh.php", detail_level="minimal")
    assert "\\App\\Fresh::brandNew" in [row["qname"] for row in outline["results"]]


@needs_php
def test_ac3_switching_main_leaves_the_worktrees_answers_alone(tmp_path: Path) -> None:
    main, worktree = _main_and_worktree(tmp_path)
    before = read_symbol.create(_in(main, worktree))("\\App\\Service::run", detail_level="minimal")

    _git(main, "checkout", "-q", "-b", "elsewhere")
    _write(main, "src/Service.php", SERVICE.replace("PAD", PAD * 7))
    _commit(main)
    after = read_symbol.create(_in(main, worktree))("\\App\\Service::run", detail_level="minimal")
    assert after == before


@needs_php
def test_scope3_inbound_answers_add_the_worktrees_edges_at_heuristic(tmp_path: Path) -> None:
    main, worktree = _main_and_worktree(tmp_path)
    _write(
        worktree,
        "src/Extra.php",
        "<?php\nnamespace App;\nclass Extra { public function also(Service $s, $u) "
        "{ $s->run(); $u->run(); } }\n",
    )

    answer = find_callers.create(_in(main, worktree))("\\App\\Service::run", detail_level="minimal")
    assert answer["reason"] == REASON_WORKTREE_OVERLAY
    tiers = {str(row["qname"]): row["confidence_tier"] for row in answer["results"]}
    assert tiers["\\App\\Extra::also"] == "HEURISTIC"
    assert "\\App\\Caller::go" in tiers  # the unchanged file answers from the built graph
    assert answer["overlay_unlinked_same_name"] == 1  # `$u->run()` names no class
    # The built partitions no longer describe these rows, so they are not reported (R5.5).
    assert not {"production_count", "test_count", "tier_census"} & set(answer)


@needs_php
def test_ac4_no_caller_root_is_byte_identical(tmp_path: Path) -> None:
    main, _ = _main_and_worktree(tmp_path)
    for tool, subject in (
        (read_symbol, "\\App\\Service::run"),
        (find_callers, "\\App\\Service::run"),
        (file_outline, "src/Service.php"),
    ):
        plain = tool.create(_in(main, None))(subject, detail_level="minimal")
        same_root = tool.create(_in(main, main))(subject, detail_level="minimal")
        assert plain == same_root
        assert not set(OVERLAY_KEYS) & set(plain)


@needs_php
def test_a_file_the_worktree_cannot_parse_is_never_read_as_an_absence(tmp_path: Path) -> None:
    """Exposure #5 — an unreadable worktree file is ``index_stale``; a deleted one, a miss."""
    main, worktree = _main_and_worktree(tmp_path)
    _write(worktree, "src/Service.php", "<?php\nclass Service { public function run( \n")
    broken = read_symbol.create(_in(main, worktree))("\\App\\Service::run", detail_level="minimal")
    assert broken["reason"] == "index_stale", broken
    assert broken["overlay"] == "worktree"

    (worktree / "src" / "Service.php").unlink()
    gone = read_symbol.create(_in(main, worktree))("\\App\\Service::run", detail_level="minimal")
    assert gone["reason"] == "no_such_symbol", gone
    hits = search_symbol.create(_in(main, worktree))(query="Service", detail_level="minimal")
    assert all(row["file"] != "src/Service.php" for row in hits["results"])


@needs_php
def test_challenger_renamed_file_hides_the_old_paths_built_rows(tmp_path: Path) -> None:
    """F1 — a rename is a deletion plus an addition, so the old path's built rows never leak."""
    main, worktree = _main_and_worktree(tmp_path)
    _git(worktree, "mv", "src/Caller.php", "src/Renamed.php")
    _commit(worktree)
    hits = search_symbol.create(_in(main, worktree))(query="Caller", detail_level="minimal")
    assert {row["file"] for row in hits["results"]} == {"src/Renamed.php"}, hits


@needs_php
def test_challenger_an_unparseable_file_keeps_its_rows_flagged_in_search(tmp_path: Path) -> None:
    """F2 — search never reads a worktree file it could not parse as an absence."""
    main, worktree = _main_and_worktree(tmp_path)
    _write(worktree, "src/Caller.php", "<?php\nclass Caller { public function go( \n")
    hits = search_symbol.create(_in(main, worktree))(query="Caller", detail_level="minimal")
    rows = [row for row in hits["results"] if row["file"] == "src/Caller.php"]
    assert rows and all(row.get("source_stale") for row in rows), hits


@needs_php
def test_challenger_main_repairing_its_own_drift_does_not_move_the_worktree(
    tmp_path: Path,
) -> None:
    """F5 — main's read-through rewrites a file the worktree never changed; the worktree wins."""
    main, worktree = _main_and_worktree(tmp_path)
    _write(main, "src/Caller.php", "<?php\n\n\n\n" + CALLER.removeprefix("<?php\n"))
    find_callers.create(_in(main, None))("\\App\\Caller::go")  # main repairs its own file
    read = read_symbol.create(_in(main, worktree))("\\App\\Caller::go", detail_level="minimal")
    assert read["line_start"] == 3, read
    assert read["overlay"] == "worktree"


@needs_php
def test_review_worktree_edges_head_only_the_first_page_and_respect_limit(tmp_path: Path) -> None:
    """PR #73 review — a later page never repeats the worktree's edges; no page exceeds limit."""
    main, worktree = _main_and_worktree(tmp_path)
    _write(
        worktree,
        "src/Extra.php",
        "<?php\nnamespace App;\nclass Extra { public function also(Service $s) { $s->run(); } }\n",
    )
    tool = find_callers.create(_in(main, worktree))
    first = tool("\\App\\Service::run", detail_level="minimal", limit=1)
    rows = first["results"]
    assert isinstance(rows, list) and [r["qname"] for r in rows] == ["\\App\\Extra::also"], first
    assert first["truncated"] is True
    later = tool("\\App\\Service::run", detail_level="minimal", limit=1, offset=1)
    rows = later["results"]
    assert isinstance(rows, list) and len(rows) <= 1, later
    assert "\\App\\Extra::also" not in [r["qname"] for r in rows], later


def test_review_one_adapter_start_and_deletions_spend_no_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PR #73 review — changed files parse in one batch; a deleted file is not a parse."""
    calls: list[list[str]] = []

    def fake(_config: Config, paths: list[str]) -> dict[str, tuple[str, ParseResult]]:
        calls.append(list(paths))
        return {p: ("php", ParseResult(path=p, ok=True)) for p in paths}

    monkeypatch.setattr(overlay_module, "parse_files", fake)
    for rel in ("a.php", "b.php"):
        _write(tmp_path, rel, "<?php\n")
    gone = [f"gone{i}.php" for i in range(OVERLAY_PARSE_CAP + 5)]
    seen = Overlay(load_config(tmp_path, {}), frozenset(["a.php", "b.php", *gone]))
    assert all(seen.parsed(rel) == ([], []) for rel in gone)
    assert seen.parsed("b.php") == ([], []) and seen.parsed("a.php") == ([], [])
    assert calls == [["b.php", "a.php"]] and not seen.truncated


def test_review_a_drifted_path_outside_the_worktree_is_never_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PR #73 review — a symlink escaping the worktree never reaches the store or an adapter."""
    root = tmp_path / "wt"
    _write(tmp_path, "outside.php", "<?php\n")
    root.mkdir()
    try:
        (root / "link.php").symlink_to(tmp_path / "outside.php")
    except OSError:
        pytest.skip("this host cannot create symlinks")

    def boom(*_: object) -> None:
        raise AssertionError("the store was opened for a path outside the worktree")

    monkeypatch.setattr(overlay_module, "GraphStore", boom)
    assert not Overlay(load_config(root, {}), frozenset()).changes("link.php")
