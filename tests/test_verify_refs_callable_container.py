"""Task 457 — a dotted word whose head only matches a function or method names no member.

Docs name telemetry events (`run.end`), SQL columns (`jobs.series_id`) and calls on a local. The
head used to match *some* indexed member by its last word, and the tail was judged gone from it. A
callable has no members to lose, and a lowercase word matched only by a member's name is weak.
"""

from __future__ import annotations

import shlex
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from code_atlas import doc_refs
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.sql_adapter_cli import ENTRY as SQL_ENTRY
from tests.sql_adapter_cli import NODE, needs_node
from tests.test_verify_refs import git, write

pytestmark = needs_node

CODE = (
    "class Metrics:\n    batch: int = 0\n    synth: int = 0\n\n\n"
    "class Pipeline:\n    tts: Metrics\n\n    def run(self):\n        return 1\n\n\n"
    "class Repo:\n    def save(self):\n        return 1\n\n"
    "    def vanished(self):\n        return 0\n"
)
DOC = (
    "- `run.end` · `Pipeline.run.end` · `tts.batch` · `Pipeline.tts.batch`\n"
    "- `Repo.vanished` · `Repo.gone` · `jobs.series_id`\n"
)


@pytest.fixture(scope="module")
def found(tmp_path_factory: pytest.TempPathFactory) -> Iterator[doc_refs.Scan]:
    root = tmp_path_factory.mktemp("callable")
    write(root, {
        "lib/pipe.py": CODE,
        "db/schema.sql": "CREATE TABLE jobs (\n    series_id INTEGER\n);\n",
        "CLAUDE.md": DOC,
    })
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    gone = CODE.replace("    batch: int = 0\n", "").replace(
        "\n\n    def vanished(self):\n        return 0\n", "\n"
    )
    write(root, {"lib/pipe.py": gone})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "drop Metrics.batch and Repo.vanished")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("home")))
        config: Config = load_config(root, {
            "CA_WORKERS": "1",
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
            "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
        })
        with GraphStore(config.db_path) as store:
            assert full_build(config, store).failed == 0
            yield doc_refs.scan(config, store)


def row(found: doc_refs.Scan, ref: str) -> dict[str, Any]:
    hits = [r for r in found.rows if r["ref"] == ref]
    assert len(hits) == 1, (ref, hits)
    return hits[0]


@pytest.mark.parametrize(
    ("ref", "state", "reason", "strength", "actionable"),
    [
        # A method has no members: the word after it is not a reference to one.
        ("run.end", "unknown", "container_is_callable", "weak", False),
        ("Pipeline.run.end", "unknown", "container_is_callable", "strong", False),
        # One lowercase word matched only by a member's name: the verdict stands, weakly.
        ("tts.batch", "gone", "missing_on_live_container", "weak", False),
        # The same member reached through its class keeps today's strength.
        ("Pipeline.tts.batch", "gone", "missing_on_live_container", "strong", True),
        ("Repo.vanished", "gone", "missing_on_live_container", "strong", True),
        ("Repo.gone", "unknown", "not_declared_on_container", "strong", False),
        # A SQL `table.column` an adapter indexes resolves as written (Scope 3).
        ("jobs.series_id", "ok", "indexed", "strong", False),
    ],
)
def test_a_callable_or_a_bare_member_word_is_never_an_actionable_member(
    found: doc_refs.Scan, ref: str, state: str, reason: str, strength: str, actionable: bool
) -> None:
    got = row(found, ref)
    assert (got["state"], got["reason"], got["strength"], got["actionable"]) == (
        state, reason, strength, actionable
    ), got
