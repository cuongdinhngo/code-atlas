"""Task 458 — a bare word with a file suffix is a path, never a member reference.

`atoms.json` names a data file; it used to be read as the member `json` of whatever `atoms` matched
and come out `gone`. A known suffix — the index's, the doc set's, or one a tracked file carries —
makes the reference a path first; only an `ok` symbol, or an external one, still outranks it.
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

SERIES = "class Series:\n    atoms: int = 0\n    cover: str = ''\n    json: int = 0\n"
SETTINGS = "class Settings:\n    dev: int = 0\n    kept: int = 0\n"
DOC = (
    "- `atoms.json` · `cover.wav` · `keys.ts` · `response.json`\n"
    "- `Series.json` · `Settings.dev`\n"
)


@pytest.fixture(scope="module")
def found(tmp_path_factory: pytest.TempPathFactory) -> Iterator[doc_refs.Scan]:
    root = tmp_path_factory.mktemp("suffix")
    write(root, {
        "lib/series.py": SERIES,
        "web/src/api/keys.ts": "export const KEYS = 1;\n",
        "web/src/api/client.ts": "export const CLIENT = 1;\n",  # no TS adapter: the tree knows `ts`
        "assets/intro.wav": "RIFF",
        "assets/outro.wav": "RIFF",
        "lib/settings.py": SETTINGS,
        "Dockerfile.dev": "FROM scratch\n",
        "CLAUDE.md": DOC,
    })
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    write(root, {"lib/settings.py": SETTINGS.replace("    dev: int = 0\n", "")})
    git(root, "commit", "-qam", "drop Settings.dev")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("home")))
        config: Config = load_config(root, {
            "CA_WORKERS": "1",
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
        })
        with GraphStore(config.db_path) as store:
            assert full_build(config, store).failed == 0
            yield doc_refs.scan(config, store)


def rows(found: doc_refs.Scan, ref: str) -> list[dict[str, object]]:
    return [r for r in found.rows if r["ref"] == ref]


@pytest.mark.parametrize(
    ("ref", "state", "reason"),
    [
        # A data file named beside a class with a member `atoms`: a path no branch held.
        ("atoms.json", "never_existed", "no_branch_ever_held_it"),
        # `.wav` is no adapter's suffix; two tracked files carry it, so the tree knows it.
        ("cover.wav", "never_existed", "no_branch_ever_held_it"),
        # A bare file name with one tracked file of that name.
        ("keys.ts", "ok", "under_a_subproject"),
    ],
)
def test_a_name_with_a_file_suffix_is_a_path(
    found: doc_refs.Scan, ref: str, state: str, reason: str
) -> None:
    (got,) = rows(found, ref)
    assert (got["ref_kind"], got["state"], got["reason"], got["actionable"]) == (
        "path", state, reason, False
    ), got


def test_a_real_symbol_still_outranks_the_suffix(found: doc_refs.Scan) -> None:
    (got,) = rows(found, "Series.json")  # a member that exists is the symbol
    assert (got["ref_kind"], got["state"]) == ("symbol", "ok"), got


def test_a_suffix_one_tracked_file_carries_leaves_a_member_a_member(found: doc_refs.Scan) -> None:
    (got,) = rows(found, "Settings.dev")  # only `Dockerfile.dev` ends so: still a removed member
    assert (got["ref_kind"], got["state"], got["actionable"]) == ("symbol", "gone", True), got


def test_an_external_name_that_reads_like_a_file_stays_silent(found: doc_refs.Scan) -> None:
    assert rows(found, "response.json") == []
