"""342 — a symlink committed in the indexed repo cannot reach outside it, on read or on write.

The repo is untrusted content and git stores symlinks. Each test plants a link out of `root` into
a sibling `outside/` directory and checks the read or write stays home. In-root links still work.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from code_atlas.architecture_rules import load_architecture_rules
from code_atlas.config import ConfigError, load_config
from code_atlas.containment import resolves_inside
from code_atlas.enrichment import load_indirection_rules
from code_atlas.ignore import ATLAS_IGNORE_FILE, load_ignore
from code_atlas.indexer import _collect_with_census, _walk, collect, full_build, indexable
from code_atlas.onboarding.artifact import MANIFEST_NAME, OUTPUT_DIR, OVERVIEW_NAME
from code_atlas.onboarding.metrics import NodeMetric
from code_atlas.onboarding.module_facts import module_facts
from code_atlas.source_slice import comment_block, declaration_slice
from code_atlas.store import GraphStore
from code_atlas.tools import diff_architecture, generate_onboarding, read_symbol
from code_atlas.tools.nav_result import REASON_PATH_OUTSIDE_ROOT, REASON_SNAPSHOT_NOT_FOUND
from tests.python_adapter_cli import ENTRY, needs_python
from tests.test_guided_tour import _cycle_repo
from tests.test_nav_tools import db_config, node

SECRET = "def secret():\n    return 'outside the repo'\n"
REAL = "def real():\n    return 1\n"


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    """``root`` (a git repo) and ``outside`` beside it, holding a file no index may read."""
    root, outside = tmp_path / "root", tmp_path / "outside"
    (root / "src").mkdir(parents=True)
    outside.mkdir()
    (outside / "secret.py").write_text(SECRET, encoding="utf-8")
    (root / "src" / "real.py").write_text(REAL, encoding="utf-8")
    (root / "src" / "leak.py").symlink_to(outside / "secret.py")
    (root / "src" / "alias.py").symlink_to(root / "src" / "real.py")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    return root, outside


def test_a_link_out_of_the_repo_is_not_collected_and_is_counted(tmp_path: Path) -> None:
    """AC1 + AC6 — red before 342: `src/leak.py` was collected and its target parsed."""
    root, _ = _repo(tmp_path)
    kept, census, *_ = _collect_with_census(root, [".py"])
    assert kept == ("src/alias.py", "src/real.py")
    assert census.skipped_escape == 1
    assert census.collected - census.skipped_suffix - census.skipped_ignore - 1 == census.kept
    assert collect(root, [".py"]) == kept
    assert indexable(["src/leak.py", "src/real.py"], root, [".py"]) == ("src/real.py",)


@needs_python
def test_a_built_index_holds_no_row_from_outside(tmp_path: Path) -> None:
    """AC1 end to end: the build never hands the escaping path to an adapter."""
    root, _ = _repo(tmp_path)
    db_path = root / ".code-atlas" / "graph.db"
    cmd = shlex.join([sys.executable, str(ENTRY), "--server"])
    env = {"CA_WORKERS": "1", "CA_DB_PATH": str(db_path), "CA_PYTHON_CMD": cmd}
    config = load_config(root, env)
    with GraphStore(db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        indexed = set(store.file_paths())
        names = {row["name"] for row in store.search_nodes("secret", limit=10)}
    assert "src/leak.py" not in indexed and "src/real.py" in indexed
    assert "secret" not in names


def test_a_symlinked_onboarding_dir_is_refused_and_nothing_lands_outside(tmp_path: Path) -> None:
    """AC2 — red before 342: the tree was written into the link's target."""
    config = _cycle_repo(tmp_path / "root")
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "root" / "docs").mkdir()
    (tmp_path / "root" / OUTPUT_DIR).symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink or resolves outside"):
        generate_onboarding.create(config)()
    assert list(outside.iterdir()) == []


def test_a_symlinked_page_beside_our_manifest_is_refused(tmp_path: Path) -> None:
    """AC3 — our manifest passes 050's foreign-tree check; the linked page must still be refused."""
    root = tmp_path / "root"
    config = _cycle_repo(root)
    generate_onboarding.create(config)()
    victim = tmp_path / "victim.txt"
    victim.write_text("keep me\n", encoding="utf-8")
    page = root / OUTPUT_DIR / OVERVIEW_NAME
    page.unlink()
    page.symlink_to(victim)
    assert (root / OUTPUT_DIR / MANIFEST_NAME).is_file()
    with pytest.raises(ValueError, match="symlink or resolves outside"):
        generate_onboarding.create(config)()
    assert victim.read_text(encoding="utf-8") == "keep me\n"


def test_diff_architecture_reads_nothing_outside_the_tree(tmp_path: Path) -> None:
    """AC4 — an absolute or `..` path is refused; an in-tree path reaches the next check."""
    config = db_config(tmp_path / "root")
    outside = tmp_path / "snap.json"
    outside.write_text("{}", encoding="utf-8")
    tool = diff_architecture.create(config)
    for before in (str(outside), "../snap.json"):
        refused = tool(before=before, after="docs/onboarding/manifest.json")
        assert refused["reason"] == REASON_PATH_OUTSIDE_ROOT
        assert "before" in str(refused["message"])
    missing = tool(before="a.json", after="b.json")
    assert missing["reason"] == REASON_SNAPSHOT_NOT_FOUND


def test_the_fallback_walk_ends_on_a_symlink_loop(tmp_path: Path) -> None:
    """AC5 — without a git index the walk followed directory links; `loop -> .` never ended."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text(REAL, encoding="utf-8")
    (tmp_path / "pkg" / "loop").symlink_to(tmp_path, target_is_directory=True)
    assert _walk(tmp_path, load_ignore(tmp_path), {".py"}) == ["pkg/m.py"]


def test_containment_treats_a_loop_and_an_escape_as_outside(tmp_path: Path) -> None:
    (tmp_path / "a").symlink_to(tmp_path / "b")
    (tmp_path / "b").symlink_to(tmp_path / "a")
    assert not resolves_inside(tmp_path, tmp_path / "a")
    assert not resolves_inside(tmp_path / "sub", tmp_path)
    assert resolves_inside(tmp_path, tmp_path)


@pytest.mark.parametrize(
    ("variable", "loader"),
    [
        ("CA_INDIRECTION_RULES", load_indirection_rules),
        ("CA_ARCHITECTURE_RULES", load_architecture_rules),
    ],
)
def test_a_rules_file_linked_out_of_the_repo_is_a_config_error(
    tmp_path: Path, variable: str, loader: object
) -> None:
    """Challenger round 1: configured rule files were read through a committed link."""
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "rules.json").write_text("[]", encoding="utf-8")
    (root / "rules.json").symlink_to(outside / "rules.json")
    config = load_config(root, {variable: "rules.json"})
    with pytest.raises(ConfigError, match="resolves outside"):
        loader(config)  # type: ignore[operator]


def test_an_ignore_file_or_untracked_path_linked_out_is_not_read(tmp_path: Path) -> None:
    root, outside = _repo(tmp_path)
    (outside / "ignore").write_text("src/real.py\n", encoding="utf-8")
    (root / ATLAS_IGNORE_FILE).symlink_to(outside / "ignore")
    (root / "src" / "late.py").symlink_to(outside / "secret.py")
    kept, _, untracked, *_ = _collect_with_census(root, [".py"])
    assert "src/real.py" in kept, "an ignore file outside the repo must not shape the index"
    assert "src/late.py" not in untracked


DOCUMENTED = "# The real doc.\ndef real():\n    return 1\n"
LEAKY = "# SECRET doc outside the repo.\ndef real():\n    return 'SECRET body outside the repo'\n"


def _built_then_swapped(tmp_path: Path, target: str) -> tuple[Path, object]:
    """Index ``src/real.py`` as a file, then swap it for a link to ``target`` (375)."""
    root, outside = tmp_path / "root", tmp_path / "outside"
    (root / "src").mkdir(parents=True)
    outside.mkdir()
    (root / "src" / "real.py").write_text(DOCUMENTED, encoding="utf-8")
    (root / "src" / "copy.py").write_text(DOCUMENTED, encoding="utf-8")
    (outside / "secret.py").write_text(LEAKY, encoding="utf-8")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    db_path = root / ".code-atlas" / "graph.db"
    cmd = shlex.join([sys.executable, str(ENTRY), "--server"])
    env = {"CA_WORKERS": "1", "CA_DB_PATH": str(db_path), "CA_PYTHON_CMD": cmd}
    config = load_config(root, env)
    with GraphStore(db_path) as store:
        assert full_build(config, store).failed == 0
    (root / "src" / "real.py").unlink()
    (root / "src" / "real.py").symlink_to({"outside": outside / "secret.py",
                                           "inside": root / "src" / "copy.py"}[target])
    return root, read_symbol.create(config)


@needs_python
@pytest.mark.parametrize("detail_level", ["standard", "minimal"])
def test_an_indexed_file_swapped_for_a_link_out_reads_no_outside_text(
    tmp_path: Path, detail_level: str
) -> None:
    """375 AC1 — red before 375: the body and docblock came back from `outside/` with reason ok."""
    _, tool = _built_then_swapped(tmp_path, "outside")
    result = tool("src.real.real", detail_level=detail_level)  # type: ignore[operator]
    assert "SECRET" not in json.dumps(result)
    assert result["reason"] == REASON_PATH_OUTSIDE_ROOT
    assert result["source"] == "" and result["file"] == "src/real.py"


@needs_python
def test_an_indexed_file_swapped_for_a_link_inside_reads_as_before(tmp_path: Path) -> None:
    """375 AC2 — a link that stays in the repo reads its target exactly as a plain file would."""
    _, tool = _built_then_swapped(tmp_path, "inside")
    result = tool("src.real.real")  # type: ignore[operator]
    assert result["reason"] == "ok"
    assert result["source"] == DOCUMENTED


def test_a_docblock_is_not_read_through_a_link_out(tmp_path: Path) -> None:
    """375 AC3 — red before 375: the onboarding docblock came from the link's outside target."""
    root, outside = tmp_path / "root", tmp_path / "outside"
    (root / "src").mkdir(parents=True)
    outside.mkdir()
    (outside / "secret.py").write_text(LEAKY, encoding="utf-8")
    (root / "src" / "leak.py").symlink_to(outside / "secret.py")
    (root / "src" / "real.py").write_text(DOCUMENTED, encoding="utf-8")
    (root / "src" / "hop.py").symlink_to(root / "src" / "real.py")
    (root / "src" / "chain.py").symlink_to(root / "src" / "hop.py")
    metric = NodeMetric("src/leak.py", 0, 0, "isolated")
    row = node("Function", "real", "src.leak.real", "src/leak.py")
    row["line_start"] = 2
    assert module_facts(root, "src/leak.py", metric, [row]).doc == ""
    assert comment_block(root / "src" / "leak.py", 2, root=root) == ""
    assert declaration_slice(root / "src" / "leak.py", 2, 3, root=root) == ""
    # An in-root chain of links still reads (the exposure check's two-hop case).
    assert comment_block(root / "src" / "chain.py", 2, root=root) == "# The real doc.\n"
