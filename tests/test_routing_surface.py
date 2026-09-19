"""Task 081: routing guidance belongs on the surface an agent sees (tools), not in prompts.

An agent's client exposes only the 14 tools to the model; MCP prompts surface as human-invoked
entries, so across four field rounds no prompt was called and the evaluator could not reach
``which_tool``. Design 3: keep the prompts as labelled operator recipes, route agents via tool
descriptions (069). These tests pin the reconciliation:

- `docs/TOOLS.md` documents every prompt and labels the section operator-facing (the category fix);
- the ``which_tool`` recognition map stays current with the tool surface;
- 069's ``capability_not_configured`` branch still fires on an index with no view_data rule.

300 adds the channel 081 did not test: the server's MCP ``instructions``, which do reach the model.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import Client

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.main import TOOL_NAMES, build_server
from code_atlas.store import GraphStore
from code_atlas.tools import find_view_data, prompts
from code_atlas.tools.nav_result import REASON_CAPABILITY_NOT_CONFIGURED
from tests.test_incremental import committed, fake_env

REPO = Path(__file__).resolve().parent.parent


def test_the_tool_reference_documents_all_prompts_as_operator_facing() -> None:
    """Proving test: every registered prompt is documented and the section is operator-facing.

    Fails pre-081: the docs omit ``which_tool`` and carry no operator-facing label. The section
    lived in `README.md` until the README became a 60-second decision page; the assertion is the
    same one, pointed at the tool reference that now carries the surface.
    """
    surface = (REPO / "docs" / "TOOLS.md").read_text(encoding="utf-8")
    for name in prompts.PROMPT_NAMES:
        assert f"`{name}`" in surface, f"docs/TOOLS.md does not document prompt {name}"
    assert "Operator prompts" in surface
    assert "human-invoked" in surface
    # The plan carries the same operator-facing framing (AC3: README *and* the plan), and since
    # 300 it also names the channel that is agent-facing: the server's own `instructions`.
    plan = (REPO / "docs" / "PLAN.md").read_text(encoding="utf-8")
    assert "Operator prompts are not agent routing" in plan
    assert "reach the model's system prompt" in plan


def _which_tool_text(config_root: Path) -> str:
    config = load_config(config_root, {})

    async def render() -> str:
        async with Client(build_server(config)) as client:
            result = await client.get_prompt(prompts.WHICH_TOOL, {"question": ""})
            return result.messages[0].content.text

    return asyncio.run(render())


def test_which_tool_map_covers_every_tool(tmp_path: Path) -> None:
    """The recognition map must name every tool on the surface, else it omits a route (069)."""
    text = _which_tool_text(tmp_path)
    for name in TOOL_NAMES:
        assert name in text, f"which_tool map omits {name}"


def test_find_view_data_reports_capability_not_configured_without_rules(tmp_path: Path) -> None:
    """069 re-verified live: an indexed subject with no view_data rule is inert, not empty.

    With no ``CA_INDIRECTION_RULES``, ``find_view_data`` on a found symbol returns
    ``capability_not_configured`` (the tool cannot answer on this index), not ``no_matches``.
    """
    committed(tmp_path, {"src/a.aa": "class Thing {}\n"})
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(workers=1), "CA_DB_PATH": str(db)})
    assert config.indirection_rules is None
    with GraphStore(config.db_path) as store:
        full_build(config, store)

    result = find_view_data.create(config)("src/a.aa::Thing", detail_level="minimal")
    assert result["reason"] == REASON_CAPABILITY_NOT_CONFIGURED
