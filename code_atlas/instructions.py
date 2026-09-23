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

# The field retros' standing verdict: the index answers who/what/where, never "is something
# missing". Stating the boundary here is cheaper than the confident wrong answer it prevents.
LIMITS = (
    "Two things to read on every answer: a `reason` other than ok, and the coverage fields "
    "(unconfigured_adapters / unindexed_languages / unindexed_same_basename) that mean this index "
    "never looked rather than looked and found nothing. The graph cannot answer an ABSENCE — "
    "whether some call site forgets a check, whether anything still uses an old constant — so ask "
    "the positive form here and use Grep for the absence."
)


def _state(config: Config) -> str:
    """One sentence of ground truth — the summary get_index_status already single-sources (316/319).

    Lifted, never recomposed: one composition site (R6.7), and the CTA for each state (not
    indexed / behind / current) rides the summary rather than a second sentence here.
    """
    return str(get_index_status.create(config, ())()["summary"])


def render(config: Config, names: tuple[str, ...]) -> str:
    """Server instructions for the tools actually registered (``CA_TOOLS`` may cut the surface)."""
    lines = prompts.recognition_lines(frozenset(names))
    return "\n".join([_state(config), "", WHY, "", LOAD, "", *lines, "", KEEP_GOING, "", LIMITS])
