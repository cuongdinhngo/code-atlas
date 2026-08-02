"""Efficiency prompts — status → search/outline → read only what is needed (§12)."""

from __future__ import annotations

from fastmcp import FastMCP

EXPLORE_AREA = "explore_area"
FIND_USAGES = "find_usages"
IMPACT_OF_CHANGE = "impact_of_change"

PROMPT_NAMES: tuple[str, ...] = (EXPLORE_AREA, FIND_USAGES, IMPACT_OF_CHANGE)


def register(server: FastMCP) -> None:
    """Attach the §12 recipe prompts to ``server``."""

    def explore_area(area: str = "") -> str:
        """Efficiently explore a code area without dumping whole files."""
        focus = f" Focus on: {area}." if area.strip() else ""
        return (
            "Explore this codebase cheaply."
            + focus
            + " Call get_index_status first. If the index is missing or stale, call "
            "build_or_update_index. Then use search_symbol and/or file_outline to locate "
            "symbols, and read_symbol only for the few qnames you actually need — never "
            "read whole files when a symbol slice will do."
        )

    def find_usages(symbol: str = "") -> str:
        """Find where a symbol is used, preferring graph tools over raw search."""
        target = f" Symbol: {symbol}." if symbol.strip() else ""
        return (
            "Find usages efficiently."
            + target
            + " Call get_index_status first (build_or_update_index if needed). Prefer "
            "find_references / find_callers / find_implementations on the exact qname. "
            "If you only have a short name, search_symbol first, then navigate. Use "
            "read_symbol only to confirm a hit — do not open entire files."
        )

    def impact_of_change(change: str = "") -> str:
        """Compute blast radius of a change without reading the whole repo."""
        focus = f" Change: {change}." if change.strip() else ""
        return (
            "Assess the blast radius of a change cheaply."
            + focus
            + " Call get_index_status first (build_or_update_index if needed). Then call "
            "impact with the changed paths and/or qnames. Use read_symbol only for the "
            "highest-score hits you must inspect — do not open entire files."
        )

    server.prompt(name=EXPLORE_AREA)(explore_area)
    server.prompt(name=FIND_USAGES)(find_usages)
    server.prompt(name=IMPACT_OF_CHANGE)(impact_of_change)
