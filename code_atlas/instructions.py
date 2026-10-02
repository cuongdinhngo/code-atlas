"""The text the client puts in front of the model before its first move (task 300).

MCP ``instructions`` ride the initialize result into the session's system prompt. 081 ruled out MCP
*prompts* and moved routing into tool descriptions; this is the channel it never tested, and the
only one that needs nothing installed in the consumer repo.

Claude Code keeps only a prefix of it (343), so the text renders in priority order under
``CLIENT_CAP``: state, LOAD, SCOPE, COVERAGE, KEEP_GOING, then the ``core`` map rows. The full map
stays in ``which_tool`` and the generated skill. COVERAGE is LIMITS' first half, kept here because
the coverage fields are omit-when-empty and no tool result restates what they mean.
"""

from __future__ import annotations

from code_atlas.config import Config
from code_atlas.tools import get_index_status, prompts

# 343: measured 2026-09-29 on Claude Code 2.1.284 — a 2,048-char prefix, then "… [truncated]".
CLIENT_CAP = 2048
# Headroom for the state line, which grows with the sha and the counts.
CAP_MARGIN = 200

SERVER_PREFIX = "mcp__code-atlas__"

# WHY fused with LIMITS' absence clause (343): the boundary is the sentence that must survive a cut.
SCOPE = (
    "The graph resolves names: which definition a call reaches, what overrides what, which modules "
    "a change touches, how a request flows. Ask the index first for who/what/where; keep Grep for "
    "literal text and for an ABSENCE (whether anything still uses an old constant) — the graph "
    "cannot answer one, so use Grep for the absence — unless a `required` architecture rule covers "
    "it."
)

COVERAGE = (
    "On every answer read a `reason` other than ok and the coverage fields "
    "(unconfigured_adapters / unindexed_languages / unindexed_same_basename): they mean the index "
    "never looked, not that it found nothing."
)

# 300's held-out H4: the session called the index once, then answered by hand in 29 grep/read calls.
KEEP_GOING = (
    "Structural questions take more than one call. Follow each answer with the next tool "
    "(search_symbol -> read_symbol, find_callers -> impact) the way you would follow a grep hit."
)


def _state(config: Config) -> str:
    """One sentence of ground truth — the summary get_index_status already single-sources (316/319).

    Lifted, never recomposed: one composition site (R6.7), and the CTA for each state (not
    indexed / behind / current) rides the summary rather than a second sentence here.
    """
    return str(get_index_status.create(config, ())()["summary"])


def _load(names: tuple[str, ...], working_set: tuple[str, ...]) -> str:
    """300: tools arrive as deferred names, so name the working set in one ``select:`` load (343).

    A name the session cannot call is worse than none, so the set is cut to what is registered.
    """
    loadable = [tool for tool in working_set if tool in names] or list(names)
    select = ",".join(SERVER_PREFIX + tool for tool in loadable)
    return (
        "Your client may deliver these as deferred names with no parameter schema. If they are not "
        "directly callable, load them once before the first question — in Claude Code that is "
        f'ToolSearch with "select:{select}" (add the others you need). One load covers the session.'
    )


def render(config: Config, names: tuple[str, ...], working_set: tuple[str, ...]) -> str:
    """Server instructions for the tools actually registered (``CA_TOOLS`` may cut the surface)."""
    lines = prompts.recognition_lines(frozenset(names), core_only=True)
    parts = [_state(config), _load(names, working_set), SCOPE, COVERAGE, KEEP_GOING]
    if lines:
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
