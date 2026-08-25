"""Task 019: node `extra` facts the conformance harness does not assert (it checks kinds + edges).

Decorators, `type`-alias / `const enum` marks, enum-case marks, the `::default` qname and declared
types all ride on a node's `extra`. These are read via the shared one-shot `--file` spawn.
"""

from __future__ import annotations

from typing import Any

from tests.ts_adapter_cli import CLI, needs_node, parse_file

pytestmark = needs_node


def _nodes_by_qname(fixture: str) -> dict[str, dict[str, Any]]:
    result = parse_file(f"tests/fixtures/typescript/{fixture}")
    assert result["ok"] is True
    return {n["qualified_name"]: n for n in result["nodes"]}


def test_decorators_land_in_extra_and_never_as_edges() -> None:
    nodes = _nodes_by_qname("decorators.ts")
    base = CLI.fixtures_dir.relative_to(CLI.root).as_posix() + "/decorators.ts"
    assert nodes[f"{base}::Widget"]["extra"]["decorators"] == ["Component", "sealed"]
    assert nodes[f"{base}::Widget::title"]["extra"]["decorators"] == ["readonly"]
    assert nodes[f"{base}::Widget::render"]["extra"]["decorators"] == ["log"]


def test_a_type_alias_is_an_interface_marked_in_extra() -> None:
    nodes = _nodes_by_qname("interface_type_alias.ts")
    base = "tests/fixtures/typescript/interface_type_alias.ts"
    assert nodes[f"{base}::Vector"]["kind"] == "Interface"
    assert nodes[f"{base}::Vector"]["extra"]["type_alias"] is True
    assert "type_alias" not in nodes[f"{base}::Point"].get("extra", {})


def test_a_const_enum_is_marked_and_cases_are_flagged() -> None:
    nodes = _nodes_by_qname("enum_const_enum.ts")
    base = "tests/fixtures/typescript/enum_const_enum.ts"
    assert nodes[f"{base}::Direction"]["extra"]["const"] is True
    assert "const" not in nodes[f"{base}::Color"].get("extra", {})
    assert nodes[f"{base}::Color::Red"]["extra"]["enum_case"] is True


def test_an_unnamed_default_export_is_qnamed_default() -> None:
    nodes = _nodes_by_qname("default_export.ts")
    base = "tests/fixtures/typescript/default_export.ts"
    assert nodes[f"{base}::default"]["kind"] == "Function"
    assert nodes[f"{base}::version"]["kind"] == "Const"


def test_a_declared_type_is_carried_in_extra() -> None:
    nodes = _nodes_by_qname("generics.ts")
    base = "tests/fixtures/typescript/generics.ts"
    # A qname carries no type params, but the declared type is preserved in extra.
    assert f"{base}::Box" in nodes and f"{base}::Box<T>" not in nodes
    assert nodes[f"{base}::Box::value"]["extra"]["type"] == "T"
