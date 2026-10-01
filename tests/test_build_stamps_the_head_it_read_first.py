"""Task 360: a build stamps the HEAD it read before the tree, never the one it reads at the end.

The field run: a `git pull` landed while a session-start build held the lock, and the build then
stamped the pulled SHA over a graph parsed from the old tree — `current`, wrong, and unrepairable
by read-through or an incremental. Each test commits from inside the build's `parse` tick, through
the tool's own progress sink, so the HEAD move is a real one and no production hook is added.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools import build_or_update_index, file_outline
from code_atlas.tools.build_or_update_index import create
from code_atlas.tools.staleness import BEHIND
from tests.test_incremental import committed, config_for, git, write
from tests.test_staleness_scope import status

ADDED = "src/Added.aa"


def _during_parse(monkeypatch: pytest.MonkeyPatch, act: Callable[[], None]) -> list[bool]:
    """Run ``act`` once, on the build's first ``parse`` tick (the tree and the diff are taken)."""
    real = build_or_update_index._progress_sink
    fired: list[bool] = []

    def sink(config: object) -> Callable[[str, int, int], None]:
        publish = real(config)  # type: ignore[arg-type]

        def progress(phase: str, done: int, total: int) -> None:
            if phase == "parse" and not fired:
                fired.append(True)
                act()
            publish(phase, done, total)

        return progress

    monkeypatch.setattr(build_or_update_index, "_progress_sink", sink)
    return fired


def _last_commit(config: object) -> str | None:
    with GraphStore(config.db_path) as store:  # type: ignore[attr-defined]
        return store.get_meta(LAST_COMMIT_KEY)


def _indexed(config: object, path: str) -> bool:
    with GraphStore(config.db_path) as store:  # type: ignore[attr-defined]
        return path in set(store.file_paths())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    committed(tmp_path, {"src/Widget.aa": "class Widget {}\n"})
    return tmp_path


def test_a_head_move_mid_full_build_stamps_the_pre_move_sha(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1 (proving test): pre-move stamp, `behind`, and the next incremental parses the file."""
    config = config_for(repo)
    before = git(repo, "rev-parse", "HEAD")
    fired = _during_parse(
        monkeypatch, lambda: committed(repo, {ADDED: "class Added {}\n"}, message="pull")
    )

    first = create(config)()

    assert fired and first["mode"] == "full"
    assert git(repo, "rev-parse", "HEAD") != before
    assert _last_commit(config) == before
    assert not _indexed(config, ADDED)
    assert status(repo, config.db_path)["staleness"] == BEHIND

    monkeypatch.undo()
    second = create(config)()

    assert second["mode"] == "incremental"
    assert _indexed(config, ADDED)
    assert _last_commit(config) == git(repo, "rev-parse", "HEAD")


def test_a_head_move_mid_incremental_stamps_the_sha_it_diffed_from(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2: the incremental's diff and its stamp name the same commit."""
    config = config_for(repo)
    create(config)()
    diffed = committed(repo, {"src/Widget.aa": "class Widget { }\n"}, message="edit")
    _during_parse(monkeypatch, lambda: committed(repo, {ADDED: "class Added {}\n"}, message="pull"))

    moved = create(config)()

    assert moved["mode"] == "incremental"
    assert _last_commit(config) == diffed
    assert not _indexed(config, ADDED)

    monkeypatch.undo()
    create(config)()

    assert _indexed(config, ADDED)


def test_read_through_repairs_the_file_the_move_added(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4: 035's read-through diffs from the honest stamp, so the added file is found."""
    config = config_for(repo)
    _during_parse(monkeypatch, lambda: committed(repo, {ADDED: "class Added {}\n"}, message="pull"))
    create(config)()
    monkeypatch.undo()

    outline = file_outline.create(config)(ADDED, detail_level="minimal")

    assert outline["found"] is True


def test_an_uncommitted_edit_during_the_build_reaches_the_next_incremental(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5: the single `git diff <since>` keeps the working-tree half of the old union."""
    config = config_for(repo)
    _during_parse(monkeypatch, lambda: write(repo, ADDED, "class Added {}\n"))
    create(config)()
    git(repo, "add", ADDED)  # tracked, not committed: `collect` indexes tracked files only
    monkeypatch.undo()

    create(config)()

    assert _indexed(config, ADDED)
    assert _last_commit(config) == git(repo, "rev-parse", "HEAD")


def test_a_never_indexed_path_in_a_clean_repo_still_answers_not_found(repo: Path) -> None:
    """The AC4 read-through repairs only a changed path; an unknown one answers as before."""
    config = config_for(repo)
    create(config)()

    outline = file_outline.create(config)("src/Missing.aa", detail_level="minimal")

    assert outline["found"] is False
    assert outline["results"] == []
