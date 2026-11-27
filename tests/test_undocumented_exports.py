"""Task 461 — the other direction: exports under chosen paths that no doc names.

A shared helper is added and the catalogue telling agents to reuse it is never updated, so the next
session writes a second copy. The index holds both sides; the answer is their difference: top-level
symbols under the path globs that no reference in the docs resolves to, less an allowlist.
"""

from __future__ import annotations

import shlex
import sys
from collections.abc import Iterator

import pytest

from code_atlas import doc_refs, query
from code_atlas.config import Config, ConfigError, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import verify_refs
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.test_verify_refs import git, write
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

pytestmark = needs_node

FILES = {
    "lib/errors.py": (
        "def format_error(e):\n    return str(e)\n\n\n"
        "def retry(fn):\n    return fn()\n\n\n"
        "class Dialog:\n    def open(self):\n        return 1\n"
    ),
    "web/src/ui/Button.ts": "export function Button(): number {\n  return 1;\n}\n",
    "web/src/ui/Button.test.ts": "export function setup(): number {\n  return 2;\n}\n",
    "tools/other.py": "def elsewhere():\n    return 1\n",
    "docs/CATALOGUE.md": "- `format_error` · `web/src/ui/Button.ts`\n",
    "allow.txt": "# internal helpers\nlib.errors.Dialog\n",
    ".code-atlas.toml": 'refs_undocumented_allow = "allow.txt"\n',
}
PATHS = ["lib/**", "web/src/**", "!**/*.test.ts"]  # a test file is the caller's to leave out
ENV = {
    "CA_WORKERS": "1",
    "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
    "CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"]),
}


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Config]:
    root = tmp_path_factory.mktemp("undocumented")
    write(root, FILES)
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("home")))
        config = load_config(root, ENV)
        with GraphStore(config.db_path) as store:
            assert full_build(config, store).failed == 0
        yield config


def answer(config: Config, **kwargs: object) -> dict[str, object]:
    with GraphStore(config.db_path) as store:
        return doc_refs.undocumented(config, store, PATHS, docs=["docs/**"], **kwargs)  # type: ignore[arg-type]


def test_only_the_export_no_doc_names_is_a_row(repo: Config) -> None:
    got = answer(repo)
    # format_error: named in a code span · Button: its file is named · Dialog: allowlisted ·
    # Dialog.open: a member, not an export · elsewhere: outside the path globs.
    assert [(r["symbol"], r["kind"], r["file"]) for r in got["rows"]] == [  # type: ignore[union-attr]
        ("lib.errors.retry", "Function", "lib/errors.py")
    ]
    assert (got["candidates"], got["allowlisted"], got["total_count"]) == (4, 1, 1)
    assert got["documented_by_file"] == 1  # Button: unnamed itself, its file is named
    assert got["coverage"] == {"visibility_not_emitted": ["python", "typescript"]}
    assert "rows[].symbol" in got["untrusted_fields"]  # type: ignore[operator]


def test_the_mcp_tool_and_the_shell_answer_it(
    repo: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = verify_refs.create(repo)(undocumented=PATHS, globs=["docs/**"], format="md")
    assert "`lib.errors.retry`" in str(tool["markdown"])
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo.root))
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    argv = ["--undocumented", *PATHS, "--docs", "docs/**", "--format", "jsonl"]
    assert query.main([*argv, "--fail-on", "any"]) == query.NOT_HELD
    assert query.main(["--undocumented", "tools/nothing/**", "--fail-on", "any"]) == query.OK


def test_an_exclusion_glob_leaves_its_files_out(repo: Config) -> None:
    with GraphStore(repo.db_path) as store:
        got = doc_refs.undocumented(repo, store, PATHS[:-1], docs=["docs/**"])
    assert "web/src/ui/Button.test.ts::setup" in [r["symbol"] for r in got["rows"]]  # type: ignore[union-attr]
    with GraphStore(repo.db_path) as store, pytest.raises(ValueError, match="not an exclusion"):
        doc_refs.undocumented(repo, store, ["!**/*.ts"])


def test_no_doc_read_is_its_own_reason(repo: Config) -> None:
    with GraphStore(repo.db_path) as store:
        got = doc_refs.undocumented(repo, store, PATHS, docs=["nowhere/**"])
    assert (got["reason"], got["docs_read"]) == ("no_docs_read", 0)


def test_a_caller_glob_is_bounded(repo: Config) -> None:
    with GraphStore(repo.db_path) as store, pytest.raises(ValueError, match="at most"):
        doc_refs.undocumented(repo, store, ["**/" + "*a" * 20 + "*b"])
    with pytest.raises(ValueError, match="patch"):
        verify_refs.create(repo)(undocumented=PATHS, format="patch")


def test_an_allowlist_that_cannot_be_read_is_a_config_error(repo: Config) -> None:
    missing = load_config(repo.root, {**ENV, "CA_REFS_UNDOCUMENTED_ALLOW": "nope.txt"})
    with pytest.raises(ConfigError, match="refs_undocumented_allow"):
        answer(missing)
