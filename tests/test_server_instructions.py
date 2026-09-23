"""Task 300 — routing reaches the model through MCP ``instructions``, not only tool descriptions.

Three held-out mechanism questions on the anchor, with 24 tools registered, connected, permitted
and a brief in session context, drew 0/19, 2/43 and 0/13 code-atlas calls. Descriptions and a
consumer-repo brief were the only channels 081 left; this is the one it did not test, and it is the
only one that needs nothing installed in the consumer repo.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

from code_atlas import instructions
from code_atlas.config import load_config
from code_atlas.tools import prompts
from code_atlas.tools.build_or_update_index import create as build_tool

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
ALL_TOOLS = tuple(tool for _q, tool, _n in prompts.RECOGNITION_MAP)


def config_for(root: Path, **extra: str):
    return load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
            **extra,
        },
    )


def test_an_unindexed_repo_says_so_and_names_the_one_tool_that_fixes_it(tmp_path: Path) -> None:
    """The first move has to know the state of this repo — a map alone does not establish it.

    Since 319 the lead sentence is get_index_status's own `summary`; the unbuilt summary says
    `not indexed` and carries the one tool that fixes it (AC3: the CTA is preserved).
    """
    text = instructions.render(config_for(tmp_path), ALL_TOOLS)
    assert text.startswith("unknown ")
    assert "not indexed — run build_or_update_index" in text


def test_an_indexed_repo_carries_its_own_counts(tmp_path: Path) -> None:
    """`current … N files` is the claim grep cannot make (the summary leads since 319)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.aa").write_text("# symbol: alpha\n", encoding="utf-8")
    for command in (
        ("init", "-q"),
        ("config", "user.email", "t@example.com"),
        ("config", "user.name", "t"),
        ("add", "-A"),
        ("commit", "-qm", "seed"),
    ):
        subprocess.run(["git", *command], cwd=tmp_path, check=True, capture_output=True)
    config = config_for(tmp_path)
    build_tool(config)(full=True)

    text = instructions.render(config, ALL_TOOLS)
    assert text.startswith("current")
    assert "1 files" in text


def test_the_map_is_cut_to_the_tools_actually_registered(tmp_path: Path) -> None:
    """`CA_TOOLS` can shrink the surface (268); instructions that name absent tools are a lie."""
    text = instructions.render(config_for(tmp_path), ("get_index_status", "search_symbol"))
    assert "-> search_symbol." in text
    assert "trace_capability" not in text


def test_the_map_has_one_definition_site(tmp_path: Path) -> None:
    """R6.7: `which_tool` and the instructions render the same lines or they drift apart."""
    text = instructions.render(config_for(tmp_path), ALL_TOOLS)
    for line in prompts.recognition_lines():
        assert line in text


def test_the_instructions_tell_the_session_to_keep_going(tmp_path: Path) -> None:
    """Held-out H4: the index was called once at call 3, then abandoned for 29 grep/read calls."""
    text = instructions.render(config_for(tmp_path), ALL_TOOLS)
    assert "more than one call" in text


def test_the_instructions_name_the_load_step_the_deferred_surface_requires(tmp_path: Path) -> None:
    """Verified 2026-09-19: the tools arrive as deferred names; a map alone names the uncallable."""
    text = instructions.render(config_for(tmp_path), ALL_TOOLS)
    assert "deferred names" in text and "ToolSearch" in text


def test_the_instructions_name_the_boundary_and_the_coverage_fields(tmp_path: Path) -> None:
    """The field retros' standing verdict: who/what/where yes, "is something missing" never.

    A session that asks the graph an absence question gets a confident wrong answer, and the
    coverage fields are the only signal that a zero means *this index never looked*.
    """
    text = instructions.render(config_for(tmp_path), ALL_TOOLS)
    assert "ABSENCE" in text and "Grep for the absence" in text
    for field in ("unconfigured_adapters", "unindexed_languages", "unindexed_same_basename"):
        assert field in text


def test_state_single_sources_on_the_index_status_summary(tmp_path, monkeypatch) -> None:
    """319/AC2: the lead sentence is get_index_status's `summary`, lifted — not a second recompose.

    A sentinel the recompose path could never produce must appear verbatim, and must TRACK when the
    field changes — proof of one composition site (R6.7), not two that can drift.
    """
    summary = "SENTINEL current @ deadbee · 7 files · 9 symbols · healthy"
    payload: dict[str, object] = {
        "indexed": True,
        "files": 7,
        "nodes": 9,
        "staleness": "current",
        "summary": summary,
    }
    monkeypatch.setattr(
        instructions.get_index_status, "create", lambda config, names: (lambda: payload)
    )
    text = instructions.render(config_for(tmp_path), ALL_TOOLS)
    assert text.startswith(summary)

    moved = "behind @ deadbee · 7 files · 9 symbols — run build_or_update_index"
    payload["summary"] = moved
    tracked = instructions.render(config_for(tmp_path), ALL_TOOLS)
    assert tracked.startswith(moved)
    assert "SENTINEL" not in tracked
