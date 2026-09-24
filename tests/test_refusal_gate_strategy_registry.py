"""318 — the brief's refusal gate reads every unmodelled-resolution strategy from one registry.

313's gate listed its refusal codes by hand, so `dynamic_import` and `autoload` — siblings of the
gated `dynamic_sql` under the same `UNMODELLED_RESOLUTION` key — shipped neither taught nor waived.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest

from code_atlas import contract
from tests import test_agent_brief_usage_completeness as gate

FIXTURES = Path(__file__).parent / "fixtures"
# Every adapter's stamp fixtures: the graph side of the registry (what the adapters emit).
ADAPTERS = {
    "php": "tests.php_adapter_cli",
    "python": "tests.python_adapter_cli",
    "sql": "tests.sql_adapter_cli",
    "typescript": "tests.ts_adapter_cli",
}


def test_the_registry_holds_the_three_shipped_strategy_tokens() -> None:
    """Scope 1 — one shipped source, grouped from the tokens that already ship (no bump)."""
    assert contract.UNMODELLED_RESOLUTION_STRATEGIES == (
        contract.RESOLUTION_AUTOLOAD,
        contract.RESOLUTION_DYNAMIC_IMPORT,
        contract.RESOLUTION_DYNAMIC_SQL,
    )
    assert contract.CONTRACT_VERSION == 10


def test_the_gate_derives_its_refusal_set_from_the_registry() -> None:
    """AC1 — every strategy is in the refusal set, and no strategy constant is named by hand."""
    codes = gate._refusal_reason_codes()
    assert set(contract.UNMODELLED_RESOLUTION_STRATEGIES) <= codes
    source = inspect.getsource(gate._refusal_reason_codes)
    named = {
        node.attr for node in ast.walk(ast.parse(source.strip()))
        if isinstance(node, ast.Attribute) and node.attr.startswith("RESOLUTION_")
    }
    assert named == {"RESOLUTION_UNMODELLED"}, named  # reach_shared's status, not a strategy


def test_every_strategy_is_taught_or_waived() -> None:
    """AC2 — `dynamic_import` and `autoload` are greppable in the brief, or carry a waiver."""
    brief = gate._rendered_brief()
    for token in contract.UNMODELLED_RESOLUTION_STRATEGIES:
        taught = gate._all_mentioned(brief, gate._refusal_needles(token))
        assert taught or token in gate.REFUSAL_WAIVERS, token
    assert not [m for m in gate._missing_surface_items(brief) if m.startswith("refusal:")]


def test_a_new_strategy_with_no_teaching_turns_the_gate_red(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC3 — mirrors `brand_new_filter`: a fourth token, untaught and unwaived, is named."""
    extended = (*contract.UNMODELLED_RESOLUTION_STRATEGIES, "brand_new_strategy")
    monkeypatch.setattr(contract, "UNMODELLED_RESOLUTION_STRATEGIES", extended)
    brief = gate._rendered_brief()
    assert "brand_new_strategy" not in brief
    assert "refusal:brand_new_strategy" in gate._missing_surface_items(brief)


@pytest.mark.parametrize("language", sorted(ADAPTERS))
def test_every_stamp_an_adapter_emits_is_in_the_registry(language: str) -> None:
    """Scope 1's graph half — a token outside the registry could never be gated."""
    cli = importlib.import_module(ADAPTERS[language])
    skip = cli.CLI.availability.args[0] if cli.CLI.availability.args else False
    if skip:
        pytest.skip(f"{language} adapter not launchable here")
    fixtures = sorted((FIXTURES / cli.CLI.fixtures_dir.name / "unmodelled_resolution").iterdir())
    stamped: set[str] = set()
    for path in fixtures:
        result = cli.parse_file(path.relative_to(Path(__file__).resolve().parent.parent))
        for node in result.get("nodes") or []:
            if node["kind"] == "File":
                stamped.update((node.get("extra") or {}).get(contract.UNMODELLED_RESOLUTION, []))
    assert stamped, f"{language}: no fixture stamps anything — the check would pass vacuously"
    assert stamped <= set(contract.UNMODELLED_RESOLUTION_STRATEGIES), stamped
