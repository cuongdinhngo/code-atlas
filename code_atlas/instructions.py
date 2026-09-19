"""The text the client puts in front of the model before its first move (task 300).

MCP ``instructions`` ride the initialize result into the session's system prompt. 081 ruled out MCP
*prompts* and moved routing into tool descriptions; this is the channel it never tested, and the
only one that needs nothing installed in the consumer repo.
"""

from __future__ import annotations

from code_atlas.config import Config
from code_atlas.tools import get_index_status, prompts

WHY = (
    "The graph resolves names: which definition a call reaches, what overrides what, which modules "
    "a change touches, how a request flows. Grep matches text and cannot answer those. Ask the "
    "index first for structure, callers, impact and control flow; keep Grep for literal text "
    "(strings, comments, config)."
)

# 300: the tools arrive as deferred names without schemas, so using one costs a deliberate extra
# step that Grep does not. A map naming tools the session cannot call is worse than no map.
LOAD = (
    "Your client may deliver these as deferred names with no parameter schema. If they are not "
    "directly callable, load them once before the first question — in Claude Code that is "
    'ToolSearch with "select:mcp__code-atlas__get_index_status,mcp__code-atlas__search_symbol" '
    "(add the others you need). One load covers the session."
)

# 300's held-out H4: the session called the index once, then answered by hand in 29 grep/read calls.
KEEP_GOING = (
    "Structural questions take more than one call. Follow each answer with the next tool "
    "(search_symbol -> read_symbol, find_callers -> impact) the way you would follow a grep hit."
)


def _state(config: Config) -> str:
    """One sentence of ground truth, so the first move knows this repo has an index."""
    status = get_index_status.create(config, ())()
    if not status.get("indexed"):
        return "This repository is not indexed yet — call build_or_update_index before asking."
    files, nodes = status.get("files"), status.get("nodes")
    staleness = status.get("staleness")
    where = f"{files} files, {nodes} symbols"
    if staleness == "current":
        return f"This repository is indexed and current: {where}."
    return f"This repository is indexed ({where}) but {staleness} — call build_or_update_index."


def render(config: Config, names: tuple[str, ...]) -> str:
    """Server instructions for the tools actually registered (``CA_TOOLS`` may cut the surface)."""
    lines = prompts.recognition_lines(frozenset(names))
    return "\n".join([_state(config), "", WHY, "", LOAD, "", *lines, "", KEEP_GOING])
