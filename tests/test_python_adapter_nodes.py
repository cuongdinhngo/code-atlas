"""Task 020: node facts the conformance harness does not assert (it checks kinds + edges).

Lives here rather than beside the CLI helper because ``pytest``'s default ``python_files`` is
``test_*.py``: a guard in ``tests/python_adapter_cli.py`` is collected only when that path is named
on the command line, so a full-suite run never ran it (R6.5 — an absent check is not a pass).
"""

from __future__ import annotations

from tests.python_adapter_cli import ROOT, needs_python, parse_file

pytestmark = needs_python


def test_file_line_end_covers_source() -> None:
    """ast.Module has no end_lineno — File spans must still cover the source (challenger 020)."""
    path = "tests/fixtures/python/module.py"
    result = parse_file(path)
    assert result["ok"] is True
    file_node = next(n for n in result["nodes"] if n["kind"] == "File")
    expected = len((ROOT / path).read_text(encoding="utf-8").splitlines())
    assert file_node["line_end"] == expected
    assert expected > 1


def _props(result: dict) -> set[str]:
    return {n["qualified_name"] for n in result["nodes"] if n["kind"] == "Property"}


def _contains(result: dict) -> set[tuple[str, str]]:
    return {
        (e["source_qname"], e["target_raw"])
        for e in result["edges"]
        if e["kind"] == "CONTAINS"
    }


def test_method_local_assign_is_not_a_class_property() -> None:
    """229 AC2/AC3 — class-body attrs stay; method locals (any depth) do not become Property."""
    path = "tests/fixtures/python/method_local_assign.py"
    result = parse_file(path)
    assert result["ok"] is True
    mod = "tests.fixtures.python.method_local_assign"
    widget = f"{mod}.Widget"
    props = _props(result)
    assert f"{widget}::kind" in props
    assert f"{widget}::tagged" in props
    for local in ("tmp", "nested_if", "nested_for", "nested_with", "nested_def", "local"):
        assert f"{widget}::{local}" not in props
        assert (widget, f"{widget}::{local}") not in _contains(result)
    kind_node = next(n for n in result["nodes"] if n["qualified_name"] == f"{widget}::kind")
    assert kind_node["kind"] == "Property"
    assert kind_node["line_start"] == 9
    assert (widget, f"{widget}::kind") in _contains(result)


def test_annotated_method_local_references_from_scope() -> None:
    """229 AC4/Scope 4 — annotated local keeps REFERENCES from the method, not a Property."""
    path = "tests/fixtures/python/method_local_assign.py"
    result = parse_file(path)
    mod = "tests.fixtures.python.method_local_assign"
    refs = {
        (e["source_qname"], e["target_raw"])
        for e in result["edges"]
        if e["kind"] == "REFERENCES"
    }
    assert (f"{mod}.Widget::typed", f"{mod}.Marker") in refs
    assert f"{mod}.Widget::local" not in _props(result)
    # Class-body annotated attribute still owns its REFERENCES edge.
    assert (f"{mod}.Widget::tagged", f"{mod}.Marker") in refs


def test_module_const_and_class_body_property_unchanged() -> None:
    """229 AC4 — UPPER module Const and class-body assign still emit."""
    const_result = parse_file("tests/fixtures/python/module_const.py")
    assert const_result["ok"] is True
    mod = "tests.fixtures.python.module_const"
    consts = {n["qualified_name"] for n in const_result["nodes"] if n["kind"] == "Const"}
    assert f"{mod}.MAX_SIZE" in consts
    assert f"{mod}.Counter::total" in _props(const_result)

    ann = parse_file("tests/fixtures/python/annotation_references.py")
    amod = "tests.fixtures.python.annotation_references"
    assert f"{amod}.Repo::owner" in _props(ann)
    refs = {
        (e["source_qname"], e["target_raw"])
        for e in ann["edges"]
        if e["kind"] == "REFERENCES"
    }
    assert (f"{amod}.Repo::owner", f"{amod}.User") in refs
ORDER = "tests/fixtures/python/resolve/self_attr_order.py"
_ORDER_MOD = "tests.fixtures.python.resolve.self_attr_order"


def _calls_from(result: dict, scope: str) -> set[tuple[str, str]]:
    """``(target_raw, tier)`` for CALLS leaving one scope; an omitted tier is RESOLVED."""
    return {
        (str(e["target_raw"]), str(e.get("confidence_tier") or "RESOLVED"))
        for e in result["edges"]
        if e["kind"] == "CALLS" and e["source_qname"] == scope
    }


@needs_python
def test_method_order_does_not_change_the_self_attribute_table() -> None:
    """The finding: `self_props` was mutated per method and shared across siblings, so a class
    whose `__init__` came last resolved differently from the identical class with it first.

    Red before the fix: `InitFirst::call_it` resolved to `Service::run` while `InitLast::call_it`
    — byte-identical but for method order — stayed a bare HEURISTIC `run`.
    """
    result = parse_file(ORDER)
    assert result["ok"] is True
    first = _calls_from(result, f"{_ORDER_MOD}.InitFirst::call_it")
    last = _calls_from(result, f"{_ORDER_MOD}.InitLast::call_it")

    assert first == last
    assert first == {(f"{_ORDER_MOD}.Service::run", "RESOLVED")}


@needs_python
def test_an_annotation_outranks_an_untyped_write_in_a_sibling() -> None:
    """A sibling's `self._svc = make()` must not un-type an attribute the class annotated."""
    calls = _calls_from(
        parse_file(ORDER), f"{_ORDER_MOD}.AnnotationSurvivesAnUntypedWrite::call_it"
    )
    assert calls == {(f"{_ORDER_MOD}.Service::run", "RESOLVED")}


@needs_python
def test_two_methods_disagreeing_drops_the_attribute() -> None:
    """Absence is honest; picking the last-visited method's opinion is not (R5.2)."""
    calls = _calls_from(parse_file(ORDER), f"{_ORDER_MOD}.TwoMethodsDisagree::call_it")
    assert calls == {("run", "HEURISTIC")}
