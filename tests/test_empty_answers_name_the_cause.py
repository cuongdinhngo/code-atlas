"""Task 354: two empty answers used to name the wrong cause.

1. ``trace_capability`` on an index with no flow seed answered ``no_matches`` for every subject,
   which read as "this route joins no flow". It now says the capability is not configured and
   names the knob that seeds a flow.
2. A qualification miss (``dbo.Orders`` for a table declared ``[Orders]``) on a behind index
   answered ``index_stale``: the freshness guard refused before any name variant was tried. The
   variant's file now names the subject, and the miss names the stored qname as a candidate.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references, read_symbol, trace_capability
from code_atlas.tools.nav_result import (
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
)
from code_atlas.tools.trace_capability import ENTRY_POINTS_ROUTE
from tests.sql_adapter_cli import CLI, needs_node

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root, check=True, capture_output=True,
    )


def fake_config(root: Path, **env: str) -> Config:
    return load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
            "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
            **env,
        },
    )


def write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def build(config: Config) -> None:
    with GraphStore(config.db_path) as store:
        full_build(config, store)


def test_a_trace_with_no_flow_seed_says_not_configured(tmp_path: Path) -> None:
    """AC1 (proving test): no entry point and no seed layout — the answer names the missing
    configuration and its knob, never ``no_matches``."""
    write(tmp_path, "lib/core.aa", "class Thing {}\n")
    config = fake_config(tmp_path)
    build(config)

    answer = trace_capability.create(config)(path="lib/core.aa")

    assert answer["reason"] == REASON_CAPABILITY_NOT_CONFIGURED
    assert answer["results"] == []
    assert answer["try_instead"] == "get_index_status"
    assert answer["try_instead_hint"] == ENTRY_POINTS_ROUTE
    assert "CA_ENTRY_POINTS" in ENTRY_POINTS_ROUTE


def test_a_subject_outside_a_real_flow_still_answers_no_matches(tmp_path: Path) -> None:
    """AC2: with one flow traced, a subject in none of them keeps ``no_matches``."""
    write(tmp_path, "lib/core.aa", "class Thing {}\n")
    write(tmp_path, "dep/a.aa", "class Thing {}\n")
    write(tmp_path, "src/lone.aa", "class Thing {}\n")
    config = fake_config(tmp_path, CA_ENTRY_POINTS="dep/**")
    build(config)
    trace = trace_capability.create(config)

    assert trace(path="dep/a.aa")["reason"] == "ok", "the fixture must trace one real flow"
    outside = trace(path="src/lone.aa")

    assert outside["reason"] == REASON_NO_MATCHES


def sql_repo(root: Path) -> Config:
    """``[Orders]`` is stored as ``Orders``; two other SQL files are then left dirty."""
    write(root, "db/tables.sql", "CREATE TABLE [Orders] (Id int NOT NULL);\n")
    write(root, "db/a.sql", "CREATE TABLE [Alpha] (Id int);\n")
    write(root, "db/b.sql", "CREATE TABLE [Beta] (Id int);\n")
    argv = ", ".join(f"'{part}'" for part in (*CLI.entry_argv, "--server"))
    write(root, ".code-atlas.toml", f"[adapter_cmd]\nsql = [{argv}]\n")
    git(root, "init", "-q", ".")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "one")
    config = load_config(
        root, {"CA_TRUST_PROJECT_FILE": "1", "CA_WORKERS": "1",
               "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")},
    )
    build(config)
    return config


def dirty_two_other_files(root: Path) -> None:
    write(root, "db/a.sql", "CREATE TABLE [Alpha] (Id int, Name int);\n")
    write(root, "db/b.sql", "CREATE TABLE [Beta] (Id int, Name int);\n")


@needs_node
def test_a_qualification_miss_on_a_behind_index_names_the_stored_candidate(
    tmp_path: Path,
) -> None:
    """AC3: ``dbo.Orders`` with two unrelated dirty files answers the ``Orders`` candidate, not
    ``index_stale`` — on read_symbol, find_callers and find_references alike."""
    config = sql_repo(tmp_path)
    dirty_two_other_files(tmp_path)

    answers = {
        "read_symbol": read_symbol.create(config)(qname="dbo.Orders"),
        "find_callers": find_callers.create(config)(qname="dbo.Orders"),
        "find_references": find_references.create(config)(qname="dbo.Orders"),
    }

    for tool, answer in answers.items():
        assert answer["reason"] != REASON_INDEX_STALE, f"{tool} still refused as stale"
        assert answer["candidates"] == ["Orders"], f"{tool}: {answer}"


@needs_node
def test_a_qualification_miss_on_a_current_index_names_the_candidate_too(
    tmp_path: Path,
) -> None:
    """AC3's clean half: with nothing dirty the same miss names the candidate rather than a bare
    ``no_such_symbol``, and never re-points onto it — the extra qualifier may be wrong."""
    config = sql_repo(tmp_path)

    answer = read_symbol.create(config)(qname="dbo.Orders")

    assert answer["found"] is False
    assert answer["candidates"] == ["Orders"]
    assert "resolved_qname" not in answer


@needs_node
def test_a_true_miss_on_a_behind_index_still_answers_index_stale(tmp_path: Path) -> None:
    """AC4: no variant anywhere, several dirty files — 073's refusal is unchanged."""
    config = sql_repo(tmp_path)
    dirty_two_other_files(tmp_path)

    answer = read_symbol.create(config)(qname="dbo.Nowhere")

    assert answer["reason"] == REASON_INDEX_STALE
    assert "candidates" not in answer
