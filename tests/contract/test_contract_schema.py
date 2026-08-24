"""Conformance tests for the adapter contract: vocabulary, version, qname helpers, validation.

The same `validate()` the indexer calls per file (task 009) is asserted here, so this file is the
core-side half of the R3.4 guarantee every adapter must also pass.
"""

from code_atlas import contract
from code_atlas.contract import (
    CONFIDENCE_TIERS,
    CONTRACT_VERSION,
    EDGE_FIELDS,
    EDGE_KINDS,
    FQN_EDGE_KINDS,
    KNOWN_CAPABILITIES,
    MEMBER_SEPARATOR,
    META_FIELDS,
    NODE_FIELDS,
    NODE_KINDS,
    join_qname,
    split_qname,
    validate,
    validate_meta,
)


def good_node() -> dict[str, object]:
    return {
        "kind": "Class",
        "name": "User",
        "qualified_name": "\\App\\Models\\User",
        "file_path": "src/Models/User.php",
        "line_start": 7,
    }


def good_edge() -> dict[str, object]:
    return {
        "kind": "EXTENDS",
        "source_qname": "\\App\\Models\\User",
        "target_raw": "\\App\\Models\\Model",
        "file_path": "src/Models/User.php",
        "line": 7,
    }


def good_meta() -> dict[str, object]:
    return {
        "name": "example",
        "extensions": [".ex"],
        "capabilities": {"semantic_types": True},
        "contract_version": CONTRACT_VERSION,
    }


def good_result() -> dict[str, object]:
    return {
        "path": "src/Models/User.php",
        "ok": True,
        "nodes": [good_node()],
        "edges": [good_edge()],
    }


# --- the vocabulary: exact spelling, exact order (CONVENTION §3) --------------------------------


def test_node_kinds_are_the_eleven_contract_kinds() -> None:
    assert NODE_KINDS == (
        "File",
        "Namespace",
        "Class",
        "Interface",
        "Trait",
        "Enum",
        "Function",
        "Method",
        "Property",
        "ClassConst",
        "Const",
    )


def test_edge_kinds_are_the_eleven_contract_kinds() -> None:
    assert EDGE_KINDS == (
        "CONTAINS",
        "EXTENDS",
        "IMPLEMENTS",
        "USES_TRAIT",
        "CALLS",
        "NEW",
        "IMPORTS",
        "INCLUDES",
        "REFERENCES",
        "ALIASES",
        "PROVIDES_VIEW_DATA",
    )


def test_fqn_edge_kinds_opt_in_from_edge_kinds() -> None:
    assert FQN_EDGE_KINDS <= frozenset(EDGE_KINDS)
    assert FQN_EDGE_KINDS == frozenset(
        {"EXTENDS", "IMPLEMENTS", "USES_TRAIT", "CALLS", "NEW", "ALIASES", "REFERENCES"}
    )


def test_caller_and_impl_kinds_are_named_fqn_subsets() -> None:
    from code_atlas.contract import CALLER_KINDS, IMPL_KINDS

    assert frozenset(CALLER_KINDS) <= FQN_EDGE_KINDS
    assert frozenset(IMPL_KINDS) <= FQN_EDGE_KINDS
    assert CALLER_KINDS == ("CALLS", "NEW")
    assert IMPL_KINDS == ("EXTENDS", "IMPLEMENTS")


def test_unmodelled_reference_kinds_are_bare_edge_subset() -> None:
    from code_atlas.contract import UNMODELLED_REFERENCE_KINDS

    assert frozenset(UNMODELLED_REFERENCE_KINDS) <= frozenset(EDGE_KINDS)
    assert "IMPORTS" not in FQN_EDGE_KINDS
    assert "REFERENCES" in FQN_EDGE_KINDS
    assert "INCLUDES" not in UNMODELLED_REFERENCE_KINDS
    assert UNMODELLED_REFERENCE_KINDS == ("REFERENCES", "IMPORTS")


def test_confidence_tiers_are_the_three_contract_tiers() -> None:
    assert CONFIDENCE_TIERS == ("RESOLVED", "HEURISTIC", "DYNAMIC")


def test_node_fields_are_the_ten_contract_fields() -> None:
    assert NODE_FIELDS == (
        "kind",
        "name",
        "qualified_name",
        "file_path",
        "line_start",
        "line_end",
        "modifiers",
        "params",
        "is_test",
        "extra",
    )


def test_edge_fields_are_the_nine_contract_fields() -> None:
    assert EDGE_FIELDS == (
        "kind",
        "source_qname",
        "target_qname",
        "target_raw",
        "file_path",
        "line",
        "confidence_tier",
        "args",
        "arg_keys",
    )


def test_required_fields_are_a_subset_of_the_declared_fields() -> None:
    assert set(contract.REQUIRED_NODE_FIELDS) <= set(NODE_FIELDS)
    assert set(contract.REQUIRED_EDGE_FIELDS) <= set(EDGE_FIELDS)


def test_target_qname_is_not_required_so_adapters_can_emit_bare_edges() -> None:
    # R3.3: the resolver fills target_qname later (PLAN §8.2), so an adapter must not have to.
    assert "target_raw" in contract.REQUIRED_EDGE_FIELDS
    assert "target_qname" not in contract.REQUIRED_EDGE_FIELDS


# --- version + capability flags -----------------------------------------------------------------


def test_contract_version_is_exported() -> None:
    assert CONTRACT_VERSION == 8


def test_known_capabilities_advertises_semantic_types() -> None:
    assert "semantic_types" in KNOWN_CAPABILITIES


# --- qualified-name helpers ---------------------------------------------------------------------


def test_member_separator_is_universal_across_languages() -> None:
    assert MEMBER_SEPARATOR == "::"


def test_split_qname_splits_a_namespaced_member() -> None:
    assert split_qname("\\App\\Models\\User::save") == ("\\App\\Models\\User", "save")


def test_split_qname_splits_a_module_anchored_member() -> None:
    assert split_qname("src/user.ts::User::save") == ("src/user.ts::User", "save")


def test_split_qname_returns_no_container_for_a_bare_name() -> None:
    assert split_qname("\\App\\Models\\User") == (None, "\\App\\Models\\User")


def test_join_qname_round_trips_with_split_qname() -> None:
    joined = join_qname("\\App\\Models\\User", "$email")
    assert joined == "\\App\\Models\\User::$email"
    assert split_qname(joined) == ("\\App\\Models\\User", "$email")


# --- validate(): the good shapes -----------------------------------------------------------------


def test_validate_accepts_a_known_good_result() -> None:
    assert validate(good_result()) == []


def test_validate_accepts_a_failed_parse_result() -> None:
    # PLAN §4.1: a syntax error is a valid result with ok:false, not a malformed one (R5.1).
    assert validate({"path": "legacy/foo.php", "ok": False, "error": "syntax error @12"}) == []


def test_validate_accepts_an_aliases_edge() -> None:
    edge = good_edge() | {
        "kind": "ALIASES",
        "source_qname": "\\App\\Alias",
        "target_raw": "\\App\\Real",
    }
    assert validate(good_result() | {"edges": [edge]}) == []


def test_validate_accepts_optional_fields_when_present() -> None:
    node = good_node() | {"line_end": 40, "modifiers": ["final"], "is_test": 0, "extra": {}}
    edge = good_edge() | {"target_qname": "\\App\\Models\\Model", "confidence_tier": "HEURISTIC"}
    assert validate({"path": "a.php", "ok": True, "nodes": [node], "edges": [edge]}) == []


def test_validate_is_deterministic() -> None:
    # R4.2: identical input must give identical output, message order included.
    malformed = {"path": "a.php", "ok": True, "nodes": [{"kind": "Klass"}], "edges": []}
    assert validate(malformed) == validate(malformed)


# --- validate(): one case per malformation class, each naming the path AND the expectation -------


def test_validate_rejects_unknown_node_kind_with_field_path_and_expectation() -> None:
    result = good_result() | {"nodes": [good_node() | {"kind": "Klass"}]}

    errors = validate(result)

    assert errors == [
        "nodes[0].kind: 'Klass' is not an allowed node kind (expected one of File, Namespace, "
        "Class, Interface, Trait, Enum, Function, Method, Property, ClassConst, Const)"
    ]


def test_validate_rejects_unknown_edge_kind_with_field_path_and_expectation() -> None:
    result = good_result() | {"edges": [good_edge() | {"kind": "INHERITS"}]}

    errors = validate(result)

    assert len(errors) == 1
    assert errors[0].startswith("edges[0].kind: 'INHERITS' is not an allowed edge kind (expected ")
    assert "USES_TRAIT" in errors[0]


def test_validate_rejects_missing_required_field_with_field_path_and_expectation() -> None:
    node = good_node()
    del node["qualified_name"]

    errors = validate(good_result() | {"nodes": [node]})

    assert len(errors) == 1
    assert errors[0].startswith("nodes[0].qualified_name: missing (expected ")
    assert "qualified_name" in errors[0]


def test_validate_rejects_a_wrong_top_level_shape_with_field_path_and_expectation() -> None:
    assert validate(["not", "a", "result"]) == ["result: list (expected an object)"]

    errors = validate({"ok": True, "nodes": [], "edges": []})

    assert len(errors) == 1
    assert errors[0].startswith("result.path: missing (expected ")


def test_validate_rejects_a_bad_confidence_tier_with_field_path_and_expectation() -> None:
    result = good_result() | {"edges": [good_edge() | {"confidence_tier": "MAYBE"}]}

    errors = validate(result)

    assert errors == [
        "edges[0].confidence_tier: 'MAYBE' is not an allowed confidence tier "
        "(expected one of RESOLVED, HEURISTIC, DYNAMIC)"
    ]


def test_validate_rejects_an_unknown_field_name() -> None:
    # Catches the adapter typo instead of silently dropping the data (R3.1).
    result = good_result() | {"nodes": [good_node() | {"qualifiedName": "\\App\\Models\\User"}]}

    errors = validate(result)

    assert len(errors) == 1
    assert errors[0].startswith(
        "nodes[0].qualifiedName: 'qualifiedName' is not an allowed contract field (expected "
    )


def test_validate_rejects_rows_on_a_failed_parse() -> None:
    # R5.1: a file that failed to parse contributes no rows.
    errors = validate(
        {"path": "a.php", "ok": False, "error": "syntax error @12", "nodes": [good_node()]}
    )

    assert len(errors) == 1
    assert errors[0].startswith("result.nodes: ")


def test_validate_reports_every_malformed_row_not_just_the_first() -> None:
    result = good_result() | {"nodes": [good_node() | {"kind": "Klass"}, {"kind": "Nope"}]}

    errors = validate(result)

    assert any(error.startswith("nodes[0].kind:") for error in errors)
    assert any(error.startswith("nodes[1].kind:") for error in errors)


def test_validate_never_raises_on_malformed_input() -> None:
    # R5.1/R5.3: the indexer marks parsed_ok=0 and keeps going; validate() must not explode.
    for malformed in (None, 42, "a string", [], {}, {"path": 1, "ok": "yes"}):
        assert isinstance(validate(malformed), list)


# --- validate_meta(): the handshake every adapter opens its stream with (§4.1) -------------------


def test_meta_fields_are_the_four_handshake_fields() -> None:
    assert META_FIELDS == ("name", "extensions", "capabilities", "contract_version")


def test_validate_meta_accepts_a_known_good_handshake() -> None:
    assert validate_meta(good_meta()) == []


def test_validate_meta_accepts_an_adapter_that_offers_no_capabilities() -> None:
    # R1.6: capabilities are advertised, never required — an adapter may simply not have any.
    meta = good_meta()
    del meta["capabilities"]
    assert validate_meta(meta) == []


def test_validate_meta_accepts_a_flag_the_core_has_never_heard_of() -> None:
    meta = good_meta() | {"capabilities": {"semantic_types": True, "some_future_power": False}}
    assert validate_meta(meta) == []


def test_validate_meta_rejects_a_missing_required_field() -> None:
    meta = good_meta()
    del meta["extensions"]

    errors = validate_meta(meta)

    assert len(errors) == 1
    assert errors[0].startswith("meta.extensions: missing (expected ")


def test_validate_meta_rejects_an_adapter_that_claims_no_suffix() -> None:
    # An adapter no file can reach is a configuration error, not a quiet no-op.
    errors = validate_meta(good_meta() | {"extensions": []})

    assert len(errors) == 1
    assert errors[0].startswith("meta.extensions: ")


def test_validate_meta_rejects_a_malformed_suffix() -> None:
    errors = validate_meta(good_meta() | {"extensions": [".ex", "ex", 7]})

    assert [error.split(":")[0] for error in errors] == [
        "meta.extensions[1]",
        "meta.extensions[2]",
    ]


def test_validate_meta_rejects_a_non_boolean_capability() -> None:
    errors = validate_meta(good_meta() | {"capabilities": {"semantic_types": "yes"}})

    assert errors == ["meta.capabilities.semantic_types: str (expected a boolean)"]


def test_validate_meta_rejects_an_unknown_handshake_field() -> None:
    errors = validate_meta(good_meta() | {"languages": ["ex"]})

    assert len(errors) == 1
    assert errors[0].startswith("meta.languages: 'languages' is not an allowed contract field")


def test_validate_meta_rejects_a_non_integer_version() -> None:
    for version in ("1", True, 1.0, None):
        errors = validate_meta(good_meta() | {"contract_version": version})
        assert errors == [
            f"meta.contract_version: {type(version).__name__} (expected an integer)"
        ]


def test_validate_meta_never_raises_on_malformed_input() -> None:
    for malformed in (None, 42, "a string", [], {}, {"name": 1, "extensions": "no"}):
        assert isinstance(validate_meta(malformed), list)
