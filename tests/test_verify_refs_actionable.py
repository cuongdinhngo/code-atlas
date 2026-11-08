"""Task 443 — the actionable set: strong moved/gone rows outside the archive, and only those count.

One repo, two commits: a file renamed, one deleted, a method removed. Instruction, reference,
archive and the host's memory folder all name them, beside weak strings — bare names, a slash
word with no suffix — that stay in the full export and out of every summary.
"""

from __future__ import annotations

import dataclasses
import json
import shlex
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from code_atlas import doc_refs, query
from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools import build_or_update_index, verify_refs
from tests.test_verify_refs import KEPT, PY_ENTRY, build, git, write

FIRST = {
    "lib/a.py": "class Repo:\n    def save(self):\n        return 1\n\n    def vanished(self):\n"
    "        return 0\n",
    "lib/c.py": "class Store:\n    def persist(self):\n        return 1\n",
    "lib/d.py": "class Cache:\n    def persist(self):\n        return 2\n",
    "lib/old.py": KEPT,
    "lib/gone.py": "def bye():\n    return 1\n",
    "CLAUDE.md": "- `lib/old.py` · `lib/gone.py` · `lib.a.Repo.vanished`\n"
    "- `persist()` · `nope/missing` · `lib/a.py`\n",
    "docs/ref.md": "Uses `lib/gone.py` and `persist()`.\n",
    "docs/old/x.md": "Was `lib/gone.py`.\n",
    ".code-atlas.toml": 'refs_archive = ["docs/old/**"]\n',
}
MEMORY = "Remember `lib/old.py` and `lib/gone.py`.\n"


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Config]:
    root = tmp_path_factory.mktemp("actionable")
    write(root, FIRST)
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    git(root, "mv", "lib/old.py", "lib/new.py")
    git(root, "rm", "-q", "lib/gone.py")
    write(root, {"lib/a.py": "class Repo:\n    def save(self):\n        return 1\n"})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "second")
    home = tmp_path_factory.mktemp("claude-home")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CLAUDE_CONFIG_DIR", str(home))
        config = build(root)
        folder = doc_refs.memory_dir(config)
        folder.mkdir(parents=True)
        (folder / "note.md").write_text(MEMORY, encoding="utf-8")
        yield config


@pytest.fixture(scope="module")
def found(repo: Config) -> doc_refs.Scan:
    with GraphStore(repo.db_path) as store:
        return doc_refs.scan(repo, store)


def one(found: doc_refs.Scan, ref: str, file: str = "CLAUDE.md") -> dict[str, Any]:
    hits = [r for r in found.rows if r["ref"] == ref and r["file"] == file]
    assert len(hits) == 1, (ref, file, hits)
    return hits[0]


@pytest.mark.parametrize(
    ("ref", "file", "state", "strength", "actionable"),
    [
        ("lib/old.py", "CLAUDE.md", "moved", "strong", True),
        ("lib/gone.py", "CLAUDE.md", "gone", "strong", True),
        ("lib.a.Repo.vanished", "CLAUDE.md", "gone", "strong", True),
        ("persist()", "CLAUDE.md", "ambiguous", "weak", False),
        ("nope/missing", "CLAUDE.md", "never_existed", "weak", False),
        ("lib/a.py", "CLAUDE.md", "ok", "strong", False),
        ("lib/gone.py", "docs/ref.md", "gone", "strong", True),
        ("lib/gone.py", "docs/old/x.md", "gone", "strong", False),
        ("lib/gone.py", "<claude-memory>/note.md", "gone", "strong", True),
    ],
)
def test_strength_and_actionable(
    found: doc_refs.Scan, ref: str, file: str, state: str, strength: str, actionable: bool
) -> None:
    """A2 (proving test): moved/gone, strong, not archive — never ambiguous or never_existed."""
    row = one(found, ref, file)
    assert (row["state"], row["strength"], row["actionable"]) == (state, strength, actionable)


def test_a_reference_docs_weak_rows_are_counted_only_when_asked(found: doc_refs.Scan) -> None:
    default = doc_refs.summarize(found)
    assert default["weak_rows_not_counted"] >= 1
    assert not [r for r in default["rows"] if r["class"] == "reference" and r["strength"] == "weak"]
    weak = doc_refs.summarize(found, strengths=["weak"])
    assert {r["ref"] for r in weak["rows"] if r["file"] == "docs/ref.md"} == {"persist()"}


def test_the_memory_folder_is_read_by_default_and_patched_by_hand(
    repo: Config, found: doc_refs.Scan
) -> None:
    """A2: the host's memory folder is the memory class; its edits carry no diff (outside git)."""
    moved = one(found, "lib/old.py", "<claude-memory>/note.md")
    assert moved["class"] == "memory" and moved["patch_ready"]
    made, _ = doc_refs.patches(repo, found.rows)
    assert all(doc_refs.in_repo(p.file) for p in made) and made
    with GraphStore(repo.db_path) as store:
        narrowed = doc_refs.scan(dataclasses.replace(repo, refs_memory=("notes/*.md",)), store)
    assert not [r for r in narrowed.rows if str(r["file"]).startswith(doc_refs.MEMORY_PREFIX)]


def test_ac4_the_default_answer_is_the_actionable_summary(
    repo: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A4: counts per class and state, compact rows, instruction first; truthful paging."""
    answer = verify_refs.create(repo)()
    assert answer["actionable"] == {
        "instruction": {"moved": 1, "gone": 2},
        "memory": {"moved": 1, "gone": 1},
        "reference": {"moved": 0, "gone": 1},
    }
    assert answer["total_count"] == answer["actionable_total"] == 6
    assert [r["class"] for r in answer["rows"]][:3] == ["instruction"] * 3
    assert "by_class" not in answer and "files" not in answer and "rows[].ref" in (
        answer["untrusted_fields"]
    )
    assert set(answer["rows"][0]) <= set(verify_refs._COMPACT)
    monkeypatch.setattr(doc_refs, "DEFAULT_ROWS", 2)
    paged = verify_refs.create(repo)()
    assert (paged["returned"], paged["truncated"], paged["total_count"]) == (2, True, 6)
    full = verify_refs.create(repo)(state=["never_existed"])
    assert full["total_count"] == 1 and full["rows"][0]["ref"] == "nope/missing"


def test_ac1_the_export_streams_every_row_and_the_diff_counts_actionable_only(
    repo: Config,
    found: doc_refs.Scan,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """A1: every row, uncapped, keyed; the diff helper reads two exports."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo.root))
    monkeypatch.setenv("CA_PYTHON_CMD", shlex.join([sys.executable, str(PY_ENTRY), "--server"]))
    assert query.main(["--verify-refs", "--format", "jsonl"]) == query.OK
    out = capsys.readouterr()
    lines = [json.loads(line) for line in out.out.splitlines()]
    assert len(lines) == len(found.rows) and f"total_count {len(found.rows)}" in out.err
    assert all({"key", "class", "file", "ref", "state", "reason", "strength", "actionable"}
               <= set(line) for line in lines)
    after = [dict(line) for line in lines if line["ref"] != "lib.a.Repo.vanished"]
    after.append({"key": ["reference", "docs/ref.md", "lib/x.py"], "actionable": True})
    old, new = tmp_path / "old.jsonl", tmp_path / "new.jsonl"
    old.write_text("".join(json.dumps(r) + "\n" for r in lines), encoding="utf-8")
    new.write_text("".join(json.dumps(r) + "\n" for r in after), encoding="utf-8")
    assert query.main(["--refs-diff", str(old), str(new)]) == query.OK
    diff = json.loads(capsys.readouterr().out)
    assert diff["by_class"]["instruction"] == {"baseline": 3, "fixed": 1, "new": 0, "unchanged": 2}
    assert diff["total"] == {"baseline": 6, "fixed": 1, "new": 1, "unchanged": 5}
    assert diff["fix_rate"] == round(1 / 6, 4)


def test_fail_on_counts_the_actionable_set(
    repo: Config, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo.root))
    monkeypatch.setenv("CA_PYTHON_CMD", shlex.join([sys.executable, str(PY_ENTRY), "--server"]))
    assert query.main(["--verify-refs", "--fail-on", "actionable"]) == query.NOT_HELD
    assert query.main(["--verify-refs", "docs/old/x.md", "--fail-on", "gone"]) == query.OK
    with pytest.raises(SystemExit):
        query.main(["--verify-refs", "--fail-on", "never_existed"])  # never actionable
    capsys.readouterr()


def test_ac5_a_build_stores_the_summary_only_when_opted_in(repo: Config) -> None:
    with GraphStore(repo.db_path) as store:
        store.set_meta(doc_refs.SUMMARY_KEY, "")
    off = build_or_update_index.create(repo)(full=False)
    assert "refs_summary" not in off
    on = build_or_update_index.create(dataclasses.replace(repo, refs_session_line=True))(full=False)
    assert on["refs_summary"] == "stored"
    with GraphStore(repo.db_path) as store:
        held = doc_refs.stored_summary(store)
    assert held is not None and held["actionable"]["instruction"] == {"moved": 1, "gone": 2}
