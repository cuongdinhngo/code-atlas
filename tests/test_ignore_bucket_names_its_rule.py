"""Task 095: verbose ``collection`` names which ignore source dropped each skip.

``skipped.ignore`` stays the 082 int. ``skipped.ignore_sources`` is the per-source breakdown,
omitted when empty, and only on ``get_index_status(verbose)`` — not on standard status or the
build payload. Keys are derived from ``load_ignore``'s composition, not a hand-kept list.
"""

from __future__ import annotations

from pathlib import Path

from code_atlas.config import load_config
from code_atlas.ignore import (
    ATLAS_IGNORE_FILE,
    COMPOSED_IGNORE_FILES,
    GITIGNORE_FILE,
    SOURCE_BUILTIN,
    composed_source_names,
    source_name,
)
from code_atlas.main import build_server
from code_atlas.tools import get_index_status
from code_atlas.tools.build_or_update_index import NAME as BUILD
from code_atlas.tools.get_index_status import NAME as STATUS
from tests.test_files_reconciliation import _verbose
from tests.test_incremental import committed, fake_env, git, write
from tests.test_mcp_server import call


def _082_closes(col: dict[str, object]) -> None:
    skipped = col["skipped"]
    assert isinstance(skipped, dict)
    assert col["collected"] - skipped["suffix"] - skipped["ignore"] == col["kept"]
    if "ignore_sources" in skipped:
        sources = skipped["ignore_sources"]
        assert isinstance(sources, dict)
        assert sum(sources.values()) == skipped["ignore"]


def test_two_ignore_sources_report_per_source_counts_that_sum_to_ignore(tmp_path: Path) -> None:
    """Proving test: two sources, ``sum(sources) == ignore``, 082 identities still close.

    Fails pre-095 (no ``ignore_sources``). ``vendor/`` is builtin; ``skip/`` is
    ``.codeatlasignore``. A gitignore-only exclusion often never enters ``collected`` because
    ``git ls-files`` already dropped it — so the second source here is atlas, not gitignore.
    """
    committed(
        tmp_path,
        {
            "src/a.aa": "class A {}\n",
            "vendor/lib.aa": "class V {}\n",
            "skip/hidden.aa": "class H {}\n",
            ".codeatlasignore": "skip/\n",
        },
    )
    db = tmp_path / ".code-atlas" / "graph.db"
    env = {**fake_env(workers=1), "CA_DB_PATH": str(db)}
    status = _verbose(tmp_path, env)
    col = status["collection"]
    atlas = source_name(ATLAS_IGNORE_FILE)
    assert col["skipped"]["ignore"] == 2
    assert col["skipped"]["ignore_sources"] == {SOURCE_BUILTIN: 1, atlas: 1}
    _082_closes(col)
    assert col["kept"] == 1

    config = load_config(tmp_path, env)
    standard = get_index_status.create(config, (STATUS, BUILD))(detail_level="standard")
    assert "collection" not in standard

    built = call(
        build_server(config),
        BUILD,
        {"full": True, "allow_full_rebuild": True, "detail_level": "standard"},
    )
    assert "ignore_sources" not in built["collection"]["skipped"]
    _082_closes(built["collection"])


def test_overlapping_sources_attribute_once_to_the_last_excluding_source(tmp_path: Path) -> None:
    """AC2: builtin ``vendor/`` + ``.codeatlasignore vendor/`` → last source wins."""
    committed(
        tmp_path,
        {
            "src/a.aa": "class A {}\n",
            "vendor/lib.aa": "class V {}\n",
            ".codeatlasignore": "vendor/\n",
        },
    )
    db = tmp_path / ".code-atlas" / "graph.db"
    status = _verbose(tmp_path, {**fake_env(workers=1), "CA_DB_PATH": str(db)})
    sources = status["collection"]["skipped"]["ignore_sources"]
    atlas = source_name(ATLAS_IGNORE_FILE)
    assert sources == {atlas: 1}
    assert SOURCE_BUILTIN not in sources
    _082_closes(status["collection"])


def test_force_added_gitignored_file_counts_under_gitignore(tmp_path: Path) -> None:
    """A tracked-but-gitignored file is the gitignore source ``git ls-files`` still lists."""
    committed(tmp_path, {"src/a.aa": "class A {}\n"})
    write(tmp_path, "hidden.aa", "class Hidden {}\n")
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    (tmp_path / ".gitignore").write_text(gitignore + "hidden.aa\n", encoding="utf-8")
    git(tmp_path, "add", "-f", "hidden.aa", ".gitignore")
    git(tmp_path, "commit", "-qm", "force-add gitignored")
    db = tmp_path / ".code-atlas" / "graph.db"
    status = _verbose(tmp_path, {**fake_env(workers=1), "CA_DB_PATH": str(db)})
    assert status["collection"]["skipped"]["ignore_sources"] == {
        source_name(GITIGNORE_FILE): 1
    }
    _082_closes(status["collection"])


def test_zero_ignore_omits_ignore_sources(tmp_path: Path) -> None:
    """061: no empty object when the ignore bucket is zero."""
    committed(tmp_path, {"src/a.aa": "class A {}\n"})
    db = tmp_path / ".code-atlas" / "graph.db"
    status = _verbose(tmp_path, {**fake_env(workers=1), "CA_DB_PATH": str(db)})
    assert status["collection"]["skipped"]["ignore"] == 0
    assert "ignore_sources" not in status["collection"]["skipped"]


def test_composed_source_names_are_derived_and_exclude_retro_keys() -> None:
    """Source keys come from the composition; retro's vendor/config are not sources.

    The equality is the derivation. ``vendor`` / ``config`` failing to be in the set is the
    guard that can fail: adding them to match the ticket's illustrative list would turn red.
    """
    assert composed_source_names() == frozenset(
        {SOURCE_BUILTIN, *(source_name(name) for name in COMPOSED_IGNORE_FILES)}
    )
    assert COMPOSED_IGNORE_FILES == (GITIGNORE_FILE, ATLAS_IGNORE_FILE)
    assert "vendor" not in composed_source_names()
    assert "config" not in composed_source_names()
