"""Task 025: each remaining PHP grammar construct emits the expected contract tuple.

Assertions drive the real adapter against a spec-driven fixture (R6.1, R6.2). Task 012 owns the
cross-adapter conformance matrix; this file owns construct correctness for the PHP adapter.
"""

from __future__ import annotations

import re
from pathlib import Path

from code_atlas import contract
from code_atlas.contract import CONTRACT_VERSION, EDGE_FIELDS, EDGE_KINDS, NODE_FIELDS, NODE_KINDS
from tests.php_adapter_cli import needs_php, parse_file

FIXTURE = "tests/fixtures/php/grammar.php"


def parse_grammar() -> dict[str, object]:
    return parse_file(FIXTURE)


def by_qname(result: dict[str, object]) -> dict[str, dict[str, object]]:
    return {node["qualified_name"]: node for node in result["nodes"]}  # type: ignore[index]


def edges_of(result: dict[str, object], kind: str) -> list[dict[str, object]]:
    return [edge for edge in result["edges"] if edge["kind"] == kind]  # type: ignore[index]


@needs_php
def test_grammar_fixture_is_a_valid_non_empty_contract_result() -> None:
    result = parse_grammar()
    assert contract.validate(result) == []
    assert result["ok"] is True
    assert result["nodes"]
    assert result["edges"]


# --- one assertion per inventory row I1-I19 --------------------------------------------


@needs_php
def test_i1_backed_enum_captures_scalar_type() -> None:
    nodes = by_qname(parse_grammar())
    node = nodes["\\App\\Grammar\\Suit"]
    assert node["kind"] == "Enum"
    assert node["extra"]["scalar_type"] == "string"
    # Pure enums omit scalar_type so they stay distinguishable from backed ones.
    assert "scalar_type" not in nodes["\\App\\Grammar\\Pure"].get("extra", {})


@needs_php
def test_i2_anonymous_class_uses_line_anchored_qname() -> None:
    nodes = by_qname(parse_grammar())
    anon = [q for q, n in nodes.items() if n["kind"] == "Class" and n["name"] == "{class}"]
    assert len(anon) == 1
    assert re.fullmatch(r"\\App\\Grammar\\Sample::run::\{class@\d+\}", anon[0])


@needs_php
def test_i3_property_declared_type_is_captured() -> None:
    node = by_qname(parse_grammar())["\\App\\Grammar\\Sample::$typed"]
    assert node["kind"] == "Property"
    assert node["extra"]["type"] == "string"


@needs_php
def test_i4_promoted_constructor_property_is_emitted() -> None:
    node = by_qname(parse_grammar())["\\App\\Grammar\\Sample::$id"]
    assert node["kind"] == "Property"
    assert node["modifiers"] == ["private"]
    assert node["extra"]["type"] == "int"


@needs_php
def test_i5_property_hooks_are_listed_in_extra() -> None:
    node = by_qname(parse_grammar())["\\App\\Grammar\\Sample::$hooked"]
    assert node["extra"]["hooks"] == ["get"]
    assert node["extra"]["type"] == "string"


@needs_php
def test_i6_class_const_modifiers_and_type_are_captured() -> None:
    node = by_qname(parse_grammar())["\\App\\Grammar\\Sample::FLAG"]
    assert node["kind"] == "ClassConst"
    assert node["modifiers"] == ["public", "final"]
    assert node["extra"]["type"] == "string"


@needs_php
def test_i7_enum_case_is_a_class_const_with_enum_flag() -> None:
    node = by_qname(parse_grammar())["\\App\\Grammar\\Suit::Hearts"]
    assert node["kind"] == "ClassConst"
    assert node["extra"]["enum_case"] is True


@needs_php
def test_i2_same_line_anonymous_declarations_get_a_column_suffix(
    tmp_path: Path,
) -> None:
    # C1: second same-line closure keeps its source column — inserting earlier must not rename it.
    line = "class C{public function m(){$a=function(){};$b=function(){};}}"
    fixture = tmp_path / "collide.php"
    fixture.write_text(f"<?php\nnamespace N;\n{line}\n", encoding="utf-8")
    result = parse_file(fixture)
    assert contract.validate(result) == []
    closures = sorted(
        n["qualified_name"] for n in result["nodes"] if n["name"] == "{closure}"
    )
    # Columns from getStartFilePos: first function @32, second @48 on this line.
    assert closures == [
        "\\N\\C::m::{closure@3}",
        "\\N\\C::m::{closure@3}:48",
    ]

    padded = tmp_path / "collide_pad.php"
    padded.write_text(
        f"<?php\nnamespace N;\n{' ' * 4}{line}\n",
        encoding="utf-8",
    )
    padded_result = parse_file(padded)
    padded_closures = sorted(
        n["qualified_name"] for n in padded_result["nodes"] if n["name"] == "{closure}"
    )
    # Padding shifts both columns by 4; the second still encodes its own column, not an ordinal.
    assert padded_closures == [
        "\\N\\C::m::{closure@3}",
        "\\N\\C::m::{closure@3}:52",
    ]


@needs_php
def test_i8_closure_is_a_function_with_line_anchored_qname() -> None:
    nodes = by_qname(parse_grammar())
    closures = [q for q, n in nodes.items() if n["name"] == "{closure}"]
    assert len(closures) == 1
    assert re.fullmatch(r"\\App\\Grammar\\Sample::run::\{closure@\d+\}", closures[0])
    assert nodes[closures[0]]["kind"] == "Function"
    assert nodes[closures[0]]["params"] == [{"name": "$n", "type": "int"}]


@needs_php
def test_i9_arrow_function_is_a_function_with_line_anchored_qname() -> None:
    nodes = by_qname(parse_grammar())
    arrows = [q for q, n in nodes.items() if n["name"] == "{fn}"]
    assert len(arrows) == 1
    assert re.fullmatch(r"\\App\\Grammar\\Sample::run::\{fn@\d+\}", arrows[0])
    assert nodes[arrows[0]]["kind"] == "Function"


@needs_php
def test_i10_file_level_const_uses_the_const_node_kind() -> None:
    node = by_qname(parse_grammar())["\\App\\Grammar\\GLOBAL_FLAG"]
    assert node["kind"] == "Const"


@needs_php
def test_i11_trait_use_emits_uses_trait_edges() -> None:
    targets = {edge["target_raw"] for edge in edges_of(parse_grammar(), "USES_TRAIT")}
    assert targets == {"\\App\\Grammar\\Alpha", "\\App\\Grammar\\Beta"}


@needs_php
def test_i12_trait_adaptations_are_on_the_owning_class() -> None:
    adaptations = by_qname(parse_grammar())["\\App\\Grammar\\Sample"]["extra"]["trait_adaptations"]
    assert {"kind": "insteadof", "trait": "\\App\\Grammar\\Alpha", "method": "shared",
            "insteadof": ["\\App\\Grammar\\Beta"]} in adaptations
    assert {"kind": "alias", "trait": "\\App\\Grammar\\Beta", "method": "shared",
            "new_name": "betaShared"} in adaptations


@needs_php
def test_i13_nullsafe_method_call_is_a_heuristic_call() -> None:
    calls = [
        edge for edge in edges_of(parse_grammar(), "CALLS")
        if edge["target_raw"] == "ping"
    ]
    assert len(calls) == 1
    assert calls[0]["confidence_tier"] == "HEURISTIC"


@needs_php
def test_i14_first_class_callable_emits_no_calls_edge() -> None:
    targets = {edge["target_raw"] for edge in edges_of(parse_grammar(), "CALLS")}
    assert "\\strlen" not in targets
    assert not any("strlen" in str(t) for t in targets)


@needs_php
def test_i15_new_anonymous_and_dynamic_variable() -> None:
    news = edges_of(parse_grammar(), "NEW")
    targets = {edge["target_raw"]: edge for edge in news}
    assert "(dynamic)" in targets
    assert targets["(dynamic)"]["confidence_tier"] == "DYNAMIC"
    anon = [t for t in targets if re.fullmatch(r"\\App\\Grammar\\Sample::run::\{class@\d+\}", t)]
    assert len(anon) == 1


@needs_php
def test_i16_import_alias_is_recorded_on_the_file_node() -> None:
    imports = by_qname(parse_grammar())[FIXTURE]["extra"]["imports"]
    assert {"fqn": "\\App\\Other\\Helper", "alias": "Help", "type": "class"} in imports


@needs_php
def test_i17_function_and_const_import_types_are_distinguished() -> None:
    imports = by_qname(parse_grammar())[FIXTURE]["extra"]["imports"]
    assert {"fqn": "\\strlen", "alias": "str_len", "type": "function"} in imports
    assert {"fqn": "\\PHP_EOL", "alias": "EOL", "type": "const"} in imports


@needs_php
def test_i18_group_use_including_mixed_types_is_expanded() -> None:
    imports = by_qname(parse_grammar())[FIXTURE]["extra"]["imports"]
    assert {"fqn": "\\App\\Mix\\Thing", "alias": None, "type": "class"} in imports
    assert {"fqn": "\\App\\Mix\\mix_fn", "alias": None, "type": "function"} in imports
    assert {"fqn": "\\App\\Mix\\MIX_CONST", "alias": None, "type": "const"} in imports
    targets = {edge["target_raw"] for edge in edges_of(parse_grammar(), "IMPORTS")}
    assert {"\\App\\Mix\\Thing", "\\App\\Mix\\mix_fn", "\\App\\Mix\\MIX_CONST"} <= targets


@needs_php
def test_i19_attributes_are_raw_on_the_declaration() -> None:
    node = by_qname(parse_grammar())["\\App\\Grammar\\Sample"]
    assert node["extra"]["attributes"] == [{"name": "\\App\\Grammar\\Attr", "args": [1]}]


@needs_php
def test_i20_method_return_type_is_extra_type() -> None:
    """AC4 (144): Method/Function return type reuses property's ``extra['type']`` key."""
    nodes = by_qname(parse_grammar())
    method = nodes["\\App\\Grammar\\Sample::run"]
    assert method["kind"] == "Method"
    assert method["extra"]["type"] == "void"
    assert nodes["\\App\\Grammar\\helper"]["extra"]["type"] == "string"
    closures = [q for q, n in nodes.items() if n["name"] == "{closure}"]
    assert len(closures) == 1
    assert nodes[closures[0]]["extra"]["type"] == "int"


# --- AC3 / AC4 ------------------------------------------------------------------------------------

# AC3 (R2.2 framework-name ban) moved to tests/contract/test_guardrail_gates.py in task 012 —
# that gate sweeps all authored adapter files with vendor exclusion + a non-empty guard.


def test_ac4_contract_vocabulary_pins_current_kinds() -> None:
    """Keep the pin current: 030 v2, 049 v3 `args`, 063 v5, 129 v6, 144 v7, 022 v9, 236 v10, 321, 328."""
    assert CONTRACT_VERSION == 12
    assert NODE_KINDS == (
        "File", "Namespace", "Class", "Interface", "Trait", "Enum",
        "Function", "Method", "Property", "ClassConst", "Const", "Table", "Column", "ForeignKey",
    )
    assert EDGE_KINDS == (
        "CONTAINS", "EXTENDS", "IMPLEMENTS", "USES_TRAIT", "CALLS",
        "NEW", "IMPORTS", "INCLUDES", "REFERENCES", "ALIASES", "PROVIDES_VIEW_DATA", "WRITES",
        "ALTERS", "DELETES",
    )
    assert "extra" in NODE_FIELDS
    assert "extra" not in EDGE_FIELDS
    assert "arg_keys" in EDGE_FIELDS
