"""Operator-facing efficiency recipes — status → search/outline → read only what is needed (§12).

These are **human-invoked MCP prompts, not agent-facing capability**. An agent's client surfaces the
21 tools to the model, but MCP prompts surface as human-invoked entries the model never sees — so
across four field rounds no prompt was ever called (task 081). Agent routing lives in the tool
descriptions (069, field-verified); these prompts stay as operator recipes. `which_tool` is the
recognition map a human can open, not a routing tool the agent scans.
"""

from __future__ import annotations

from fastmcp import FastMCP

EXPLORE_AREA = "explore_area"
FIND_USAGES = "find_usages"
IMPACT_OF_CHANGE = "impact_of_change"
WHICH_TOOL = "which_tool"

PROMPT_NAMES: tuple[str, ...] = (EXPLORE_AREA, FIND_USAGES, IMPACT_OF_CHANGE, WHICH_TOOL)


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

    def which_tool(question: str = "") -> str:
        """Which code-atlas tool answers a given question? A recognition map for all 21 tools."""
        asked = f" You asked: {question}." if question.strip() else ""
        return (
            "Pick the code-atlas tool whose answer matches your question." + asked + " Map:\n"
            "- Is the index built/fresh/healthy, what next? -> get_index_status (call first).\n"
            "- Build or refresh the index -> build_or_update_index.\n"
            "- Find a symbol by partial name/text -> search_symbol.\n"
            "- What does a file define, and where -> file_outline.\n"
            "- Read one symbol's source -> read_symbol.\n"
            "- Who calls this function/method -> find_callers.\n"
            "- Where is this symbol used -> find_references.\n"
            "- Which types extend/implement this -> find_implementations.\n"
            "- What variables a handler passes to its template -> find_view_data.\n"
            "- What a file includes / what includes it -> include_graph.\n"
            "- What breaks if I change this -> impact.\n"
        "- Which modules does that change reach, and where to start -> impact_modules.\n"
            "- Can this directory subtree be deleted — what crosses into/out of it "
            "-> subtree_dependencies.\n"
            "- What is reachable from entry points / what is dead -> reachable_from.\n"
            "- Which symbols look unused -> find_orphans.\n"
            "- How does one symbol reach another -> explain_path.\n"
            "- What are this codebase's layers, and how do they depend on each other "
            "-> architecture_overview.\n"
            "- What should I read first, in dependency order -> guided_tour.\n"
            "- Write committable onboarding docs (overview, tour, per-module, manifest) "
            "-> generate_onboarding.\n"
            "- Do the declared architecture dependency rules still hold "
            "-> check_architecture_rules.\n"
            "- What did the agent change about the architecture between two revisions "
            "-> diff_architecture.\n"
            "- Render a class diagram for one type (plus ancestry) or one file "
            "-> class_diagram.\n"
            "- Which writers of this table omit a column that has a DEFAULT "
            "-> check_column_defaults.\n"
            "Then call get_index_status first if unsure the index is current."
        )

    server.prompt(name=EXPLORE_AREA)(explore_area)
    server.prompt(name=FIND_USAGES)(find_usages)
    server.prompt(name=IMPACT_OF_CHANGE)(impact_of_change)
    server.prompt(name=WHICH_TOOL)(which_tool)
