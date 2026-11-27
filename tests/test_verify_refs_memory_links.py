"""Task 459 — a link inside host memory resolves against the memory folder first.

Claude Code's `MEMORY.md` links its sibling notes by bare name. They live outside the repo, so
the repo tree answered `never_existed` for a present note and a deleted one alike; the folder they
sit in now answers first, and a link to a note gone from it is the stale case worth reporting.
"""

from __future__ import annotations

import shlex
import sys
from collections.abc import Iterator

import pytest

from code_atlas import doc_refs
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.test_verify_refs import git, write

INDEX = (
    "- [Present](present.md) — a note that is there\n"
    "- [Missing](missing.md) — a note that was deleted\n"
    "- [Nested](topics/deep.md) · [Escape](../../outside.md) · [Code](lib/a.py)\n"
    "- `missing.md` in a code span keeps the repo's rules\n"
)


@pytest.fixture(scope="module")
def found(tmp_path_factory: pytest.TempPathFactory) -> Iterator[doc_refs.Scan]:
    root = tmp_path_factory.mktemp("memory")
    write(root, {"lib/a.py": "def keep():\n    return 1\n"})
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("home")))
        config: Config = load_config(root, {
            "CA_WORKERS": "1",
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
        })
        folder = doc_refs.memory_dir(config)
        (folder / "topics").mkdir(parents=True)
        (folder / "MEMORY.md").write_text(INDEX, encoding="utf-8")
        (folder / "present.md").write_text("A note.\n", encoding="utf-8")
        (folder / "topics" / "deep.md").write_text("Deeper.\n", encoding="utf-8")
        with GraphStore(config.db_path) as store:
            assert full_build(config, store).failed == 0
            yield doc_refs.scan(config, store)


def row(found: doc_refs.Scan, ref: str, origin: str = "link") -> dict[str, object]:
    hits = [r for r in found.rows if r["ref"] == ref and r["origin"] == origin]
    assert len(hits) == 1, (ref, hits)
    return hits[0]


@pytest.mark.parametrize(
    ("ref", "state", "reason", "actionable"),
    [
        ("present.md", "ok", "exists_in_memory", False),
        ("topics/deep.md", "ok", "exists_in_memory", False),
        # In neither the memory folder nor the repo: the stale link the memory class exists for.
        ("missing.md", "gone", "missing_from_memory", True),
        # A link that leaves the memory folder is never looked for there (SEC-IN-03).
        ("../../outside.md", "unknown", "outside_the_repo", False),
        # The memory folder lacks it, the repo holds it: the repo's answer stands.
        ("lib/a.py", "ok", "exists", False),
    ],
)
def test_a_memory_link_resolves_in_the_memory_folder_first(
    found: doc_refs.Scan, ref: str, state: str, reason: str, actionable: bool
) -> None:
    got = row(found, ref)
    assert got["class"] == "memory"
    assert (got["state"], got["reason"], got["actionable"]) == (state, reason, actionable), got


def test_a_code_span_in_memory_keeps_the_repos_rules(found: doc_refs.Scan) -> None:
    spans = [r for r in found.rows if r["ref"] == "missing.md" and r["origin"] == "code_span"]
    assert all(r["reason"] != "missing_from_memory" and not r["actionable"] for r in spans), spans
