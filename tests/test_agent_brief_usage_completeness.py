"""Task 313 — agent-brief USAGE_RULES must teach or waive every shipped surface item."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "code_atlas" / "tools"

# Plumbing / already taught elsewhere — each waiver names why it is deliberately untaught.
PARAM_WAIVERS: dict[str, str] = {
    "query": "subject selector; routing line already names the tool",
    "queries": "taught as 'list of queries' under How to spend the calls",
    "qname": "subject selector; recognition map names the question shape",
    "qnames": "subject selector (impact batch)",
    "paths": "subject selector (impact batch)",
    "path": "subject selector (trace_capability)",
    "module": "subject selector (trace_capability)",
    "limit": "paging; total_count/truncated prose covers the page contract",
    "offset": "paging; same as limit",
    "detail_level": "envelope shape; unconfigured_adapters prose covers minimal",
    "depth": "walk depth; reachability prose is tool-local",
    "include_source": "token-frugal default; optional quote of the site line",
    "sign": "optional claim line; Writing the PR claim occasion covers when to sign",
    "serve_behind": "taught under get_index_status / staleness prose",
    "exclude_tests": "taught under production_count / test_count prose",
    "arg_position": "find_callers filter; rare; not a field-retro miss",
    "arg_is": "find_callers filter; rare; not a field-retro miss",
    "arg_name": "find_callers filter, arg_position's keyword twin (372); rare",
    "confidence_tier": "taught under confidence_tier prose",
    "reset_fit_counts": "ops knob on get_index_status; not a how-to-ask rule",
}

CAPABILITY_WAIVERS: dict[str, str] = {}
REFUSAL_WAIVERS: dict[str, str] = {
    "no_roots_configured": "find_orphans empty-config status; ops, not a retro miss",
    "roots_matched_nothing": "find_orphans misconfigured roots; ops",
    "walk_budget_exhausted": "find_orphans CA_ORPHANS_MAX_NODES; ops",
}

_PATH_SCOPE_PARAMS = frozenset({"path", "path_prefix", "working_roots"})


def _occasion_tools() -> frozenset[str]:
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    import gen_skill  # noqa: E402

    return frozenset(t for _title, tools in gen_skill.OCCASIONS for t in tools)


def _tool_def(tool: str) -> ast.FunctionDef:
    src = (TOOLS / f"{tool}.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == tool:
            return node
    raise AssertionError(f"{tool}: nested create() method not found")


def _tool_params(tool: str) -> frozenset[str]:
    node = _tool_def(tool)
    return frozenset(a.arg for a in node.args.args + node.args.kwonlyargs)


def _tool_docstring(tool: str) -> str:
    return ast.get_docstring(_tool_def(tool)) or ""


def _rendered_brief() -> str:
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    import gen_skill  # noqa: E402

    return gen_skill.render_agent_brief()


def _shipped_tool_names() -> frozenset[str]:
    from code_atlas.main import TOOL_NAMES

    return frozenset(TOOL_NAMES)


def _advertised_capabilities() -> frozenset[str]:
    """Discover capability flags from shipped tool signatures + docstrings."""
    caps: set[str] = set()
    # find_references docstring advertises Table/Column WRITES (278).
    doc = _tool_docstring("find_references")
    if "Table" in doc and "Column" in doc and "WRITES" in doc:
        caps.add("table_column_writers")
    # A shipped find_orphans with no path-like param advertises whole-index walk.
    if "find_orphans" in _shipped_tool_names():
        if not (_tool_params("find_orphans") & _PATH_SCOPE_PARAMS):
            caps.add("find_orphans_no_path_scope")
    return frozenset(caps)


def _refusal_reason_codes() -> frozenset[str]:
    """Refusal / stamp tokens — reach statuses plus every strategy in the shipped registry (318)."""
    from code_atlas import contract
    from code_atlas.tools import reach_shared

    return frozenset(
        {
            reach_shared.RESOLUTION_UNMODELLED,
            reach_shared.ROOTS_MATCHED_NOTHING,
            reach_shared.WALK_BUDGET_EXHAUSTED,
            reach_shared.NO_ROOTS,
            *contract.UNMODELLED_RESOLUTION_STRATEGIES,
        }
    )


def _capability_needles(cap: str) -> tuple[str, ...]:
    """Every needle must appear (AND) so a sibling line cannot keep the gate green."""
    if cap == "table_column_writers":
        return ("writers", "Column")
    if cap == "find_orphans_no_path_scope":
        return ("find_orphans", "path scope")
    raise AssertionError(f"unknown capability {cap!r}")


def _refusal_needles(code: str) -> tuple[str, ...]:
    if code == "dynamic_sql":
        return ("dynamic_sql", "EXEC")
    if code == "resolution_unmodelled":
        return ("resolution_unmodelled",)
    # Backticked: a bare `autoload` would match any prose mentioning PSR-4 autoloading (318).
    return (f"`{code}`",)


def _param_needles(param: str) -> tuple[str, ...]:
    if param == "kind":
        return ("kind:",)
    if param == "namespace":
        return ("namespace",)
    return (param,)


def _any_mentioned(brief: str, needles: tuple[str, ...]) -> bool:
    return any(n in brief for n in needles)


def _all_mentioned(brief: str, needles: tuple[str, ...]) -> bool:
    return all(n in brief for n in needles)


def _required_params() -> frozenset[str]:
    """Params on occasion tools that are neither waived nor ubiquitous subject selectors."""
    from code_atlas import contract

    required: set[str] = set()
    for tool in sorted(_occasion_tools()):
        params = _tool_params(tool)
        # kind values come from NODE_KINDS; the brief teaches the filter, not each kind token.
        if "kind" in params:
            assert contract.NODE_KINDS, "kind filter has no NODE_KINDS vocabulary"
        for param in params:
            if param in PARAM_WAIVERS:
                continue
            required.add(param)
    return frozenset(required)


def _missing_surface_items(brief: str) -> list[str]:
    missing: list[str] = []
    for param in sorted(_required_params()):
        if not _any_mentioned(brief, _param_needles(param)):
            missing.append(f"param:{param}")
    for cap in sorted(_advertised_capabilities() - CAPABILITY_WAIVERS.keys()):
        if not _all_mentioned(brief, _capability_needles(cap)):
            missing.append(f"capability:{cap}")
    for code in sorted(_refusal_reason_codes() - REFUSAL_WAIVERS.keys()):
        if not _all_mentioned(brief, _refusal_needles(code)):
            missing.append(f"refusal:{code}")
    return missing


def test_usage_rules_teach_or_waive_every_shipped_surface_item() -> None:
    """AC1: backfilled gaps + every unwaived param/capability/refusal are greppable."""
    missing = _missing_surface_items(_rendered_brief())
    assert not missing, f"untaught and unwaived: {missing}"


def test_deleting_a_backfilled_rule_turns_the_gate_red() -> None:
    """AC1 red arm: drop one backfilled teaching and the gate names it."""
    brief = _rendered_brief()
    no_kind = "\n".join(
        ln for ln in brief.splitlines() if "kind:" not in ln and "`namespace`" not in ln
    )
    assert _missing_surface_items(no_kind) == ["param:kind", "param:namespace"]

    # Path-scope teaching must not stay green via a sibling find_orphans mention.
    no_path_scope = "\n".join(ln for ln in brief.splitlines() if "path scope" not in ln)
    assert "capability:find_orphans_no_path_scope" in _missing_surface_items(no_path_scope)


def test_new_search_symbol_param_without_brief_or_waiver_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC2: a new search_symbol param with no mention and no waiver fails the gate."""
    real = _tool_params

    def _with_extra(tool: str) -> frozenset[str]:
        params = set(real(tool))
        if tool == "search_symbol":
            params.add("brand_new_filter")
        return frozenset(params)

    import tests.test_agent_brief_usage_completeness as mod

    monkeypatch.setattr(mod, "_tool_params", _with_extra)
    brief = _rendered_brief()
    assert "brand_new_filter" not in brief
    assert "brand_new_filter" not in PARAM_WAIVERS
    assert "brand_new_filter" in mod._required_params()
    assert "param:brand_new_filter" in mod._missing_surface_items(brief)


def test_golden_brief_teaches_all_four_measured_gaps() -> None:
    """AC3: contrib/agent-brief.md greppable for the four field-retro teachings."""
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    import gen_skill  # noqa: E402

    golden = gen_skill.AGENT_BRIEF_PATH.read_text(encoding="utf-8")
    assert golden == gen_skill.render_agent_brief()
    assert "kind:" in golden and "namespace" in golden
    assert "writers" in golden and "Column" in golden
    assert "dynamic_sql" in golden and "resolution_unmodelled" in golden
    assert "find_orphans" in golden and "path scope" in golden


def test_param_waivers_are_commented_decisions() -> None:
    """Keep the waiver set honest — every entry carries a non-empty why."""
    assert PARAM_WAIVERS
    for name, why in PARAM_WAIVERS.items():
        assert why.strip(), f"waiver for {name} has no reason"
