"""Task 266 — five-occasion agent brief written into the indexed repo's AGENTS.md."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gen_skill  # noqa: E402


def test_fixture_repo_gets_five_occasion_brief_from_which_tool(tmp_path: Path) -> None:
    """AC1: generator writes the brief; drift guard compares bytes to render_agent_brief()."""
    path = gen_skill.write_agent_brief(tmp_path)
    text = path.read_text(encoding="utf-8")
    assert gen_skill.BRIEF_BEGIN in text and gen_skill.BRIEF_END in text
    assert "Before renaming a symbol" in text
    assert "After editing indexed code" in text
    assert "First session on this repo" in text
    assert "A name that exists in two languages" in text
    assert "Writing the PR claim" in text
    assert "Explaining how a request moves through the system" in text
    assert "trace_capability" in text
    # Every occasion tool line comes from which_tool / recognition_map.
    map_lines = set(gen_skill.recognition_map())
    for line in text.splitlines():
        if line.startswith("- ") and "->" in line:
            assert line in map_lines
    # Drift guard: committed golden equals the generator (same shape as skill drift).
    assert gen_skill.AGENT_BRIEF_PATH.read_text(encoding="utf-8") == gen_skill.render_agent_brief()


def test_existing_agents_md_preserved_and_rerun_idempotent(tmp_path: Path) -> None:
    """AC2: prior AGENTS.md prose survives; second write does not duplicate the section."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\nKeep this paragraph.\n", encoding="utf-8")
    gen_skill.write_agent_brief(tmp_path)
    gen_skill.write_agent_brief(tmp_path)
    text = agents.read_text(encoding="utf-8")
    assert text.count(gen_skill.BRIEF_BEGIN) == 1
    assert text.count(gen_skill.BRIEF_END) == 1
    assert "Keep this paragraph." in text
    assert text.index("Keep this paragraph.") < text.index(gen_skill.BRIEF_BEGIN)


def test_offered_hook_snippet_covers_every_shipped_adapter_suffix() -> None:
    """AC4: hook filter suffixes are derived from shipped_adapters declarations."""
    declared = gen_skill.declared_extensions()
    assert set(declared) == set(gen_skill.shipped_adapters())
    snippet = gen_skill.render_claude_code_snippet()
    for name, suffixes in declared.items():
        assert suffixes, f"{name} must declare at least one suffix"
        for suffix in suffixes:
            assert f"*{suffix}" in snippet, f"{name} suffix {suffix} missing from hook offer"


def test_occasions_name_only_tools_on_the_recognition_map() -> None:
    """R6.7: OCCASIONS cannot invent a tool the which_tool map does not carry."""
    map_tools = set(gen_skill.recognition_lines_by_tool())
    for title, tools in gen_skill.OCCASIONS:
        for tool in tools:
            assert tool in map_tools, f"{title}: {tool} not in which_tool"
