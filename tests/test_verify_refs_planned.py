"""Task 460 — a reference marked as planned reports `planned`; one whose target exists says so.

A catalogue row `| lib/errors.ts | ⏳ T30.2 |` names a file a later task creates; `never_existed`
is correct and silent. With `refs_planned_markers` configured it reads `planned`, and a marked row
whose target has since appeared is `ok` (`planned_but_exists`) — a marker to drop. Unconfigured, the
answer is the base's byte for byte (`fixtures/verify_refs/planned_unconfigured.json`, pre-change).
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import get_args

import pytest

from code_atlas import doc_refs, query
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import verify_refs
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.test_verify_refs import git, write

GOLDEN = Path(__file__).parent / "fixtures" / "verify_refs" / "planned_unconfigured.json"
DOC = (
    "| block | file | state |\n|---|---|---|\n"
    "| errors | `lib/errors.py` | ⏳ T30.2 |\n"
    "| retry | `lib/retry.py` | ⏳ T31 |\n"
    "- `lib/later.py` (planned)\n"
    "- `lib/other.py` was never written\n"
    "- `lib/retry.py` is real\n"
)
ENV = {"CA_WORKERS": "1", "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"])}


def make_repo(root: Path, markers: bool) -> Config:
    """One repo: two marked rows (absent, present), one marked list item, two unmarked."""
    write(root, {"lib/retry.py": "def retry():\n    return 1\n", "CLAUDE.md": DOC})
    if markers:
        (root / ".code-atlas.toml").write_text(
            'refs_planned_markers = ["⏳", "(planned)"]\n', encoding="utf-8"
        )
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    config = load_config(root, ENV)
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


def answer(config: Config) -> dict[str, object]:
    """The summary and its markdown, as `--verify-refs` with a filter answers them."""
    with GraphStore(config.db_path) as store:
        found = doc_refs.scan(config, store)
    summary = doc_refs.summarize(found, states=list(doc_refs.STATES))
    return {"summary": summary, "markdown": doc_refs.markdown(summary)}


@pytest.fixture(scope="module")
def configured(tmp_path_factory: pytest.TempPathFactory) -> Config:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("home")))
        return make_repo(tmp_path_factory.mktemp("planned"), markers=True)


def row(config: Config, ref: str) -> dict[str, object]:
    with GraphStore(config.db_path) as store:
        hits = [r for r in doc_refs.scan(config, store).rows if r["ref"] == ref]
    assert len(hits) == 1, (ref, hits)
    return hits[0]


@pytest.mark.parametrize(
    ("ref", "state", "reason"),
    [
        ("lib/errors.py", "planned", "no_branch_ever_held_it"),  # marked, absent
        ("lib/later.py", "planned", "no_branch_ever_held_it"),  # the second marker
        ("lib/other.py", "never_existed", "no_branch_ever_held_it"),  # unmarked: unchanged
    ],
)
def test_a_marked_absent_target_is_planned_and_never_actionable(
    configured: Config, ref: str, state: str, reason: str
) -> None:
    got = row(configured, ref)
    assert (got["state"], got["reason"], got["actionable"]) == (state, reason, False), got


def test_a_marked_target_that_exists_is_a_marker_to_drop(configured: Config) -> None:
    with GraphStore(configured.db_path) as store:
        found = doc_refs.scan(configured, store)
    marked = [r for r in found.rows if r["ref"] == "lib/retry.py"]
    assert sorted((r["state"], r["reason"]) for r in marked) == [
        ("ok", "exists"), ("ok", "planned_but_exists")
    ]
    summary = doc_refs.summarize(found, states=list(doc_refs.STATES))
    assert summary["markers_to_drop"] == 1
    assert "planned_but_exists" in doc_refs.markdown(summary)


def test_the_default_answer_lists_the_markers_to_drop(configured: Config) -> None:
    with GraphStore(configured.db_path) as store:
        found = doc_refs.scan(configured, store)
    summary = doc_refs.summarize(found, actionable=True)  # unfiltered: the page is actionable rows
    assert summary["markers_to_drop"] == 1
    drop = [{"file": "CLAUDE.md", "line": 4, "ref": "lib/retry.py"}]
    assert summary["markers_to_drop_rows"] == drop
    assert "`lib/retry.py`" in doc_refs.markdown(summary)
    assert "markers_to_drop_rows[].ref" in summary["untrusted_fields"]


def test_every_surface_names_the_same_states(
    configured: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert set(get_args(verify_refs.State)) == set(doc_refs.ALL_STATES)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(configured.root))
    monkeypatch.setenv("CA_PYTHON_CMD", ENV["CA_PYTHON_CMD"])
    assert query.main(["--verify-refs", "--state", "planned", "--format", "md"]) == query.OK


def test_fail_on_names_a_marker_to_drop(
    configured: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(configured.root))
    monkeypatch.setenv("CA_PYTHON_CMD", ENV["CA_PYTHON_CMD"])
    assert query.main(["--verify-refs", "--fail-on", "planned_but_exists"]) == query.NOT_HELD
    assert query.main(["--verify-refs", "--fail-on", "gone"]) == query.OK


def test_no_marker_configured_answers_the_base_byte_for_byte(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("home")))
        got = answer(make_repo(tmp_path_factory.mktemp("unconfigured"), markers=False))
    assert json.dumps(got, sort_keys=True, ensure_ascii=False, indent=1) + "\n" == (
        GOLDEN.read_text(encoding="utf-8")
    )
