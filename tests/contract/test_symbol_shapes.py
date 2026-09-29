"""v13 `symbol_shapes` — every in-tree adapter says what a grep for its symbols looks like (345).

The field is optional in the contract (a third-party adapter may omit it) and required in this repo:
the grep-time nudge reads only what an adapter declares, so a shipped adapter without shapes is a
language the nudge silently never speaks for — the drift 036's PHP-only poke filter was.
"""

from __future__ import annotations

import re

import pytest

from code_atlas import adapter, contract
from tests.contract.adapter_registry import REGISTRY


def test_every_shipped_adapter_is_in_the_registry() -> None:
    """The denominator is the adapters directory (R6.7), so a new adapter is covered on arrival."""
    assert set(adapter.shipped_adapters()) == set(REGISTRY)


def _assert_announces_shapes(name: str, meta: dict[str, object]) -> None:
    assert contract.validate_meta(meta) == []
    assert meta["contract_version"] == contract.CONTRACT_VERSION
    shapes = meta.get("symbol_shapes")
    assert isinstance(shapes, list) and shapes, (
        f"{name} ships without symbol_shapes — the nudge would never speak for it"
    )
    assert {shape["kind"] for shape in shapes} <= set(contract.SHAPE_KINDS)


@pytest.mark.parametrize(
    "name",
    [pytest.param(n, marks=REGISTRY[n].cli.availability, id=n) for n in sorted(REGISTRY)],
)
def test_every_registered_adapter_announces_symbol_shapes(name: str) -> None:
    """AC2: a live handshake — what the core actually receives, not the entry file's text."""
    _assert_announces_shapes(name, REGISTRY[name].cli.handshake())


def test_a_handshake_without_shapes_is_caught() -> None:
    """R6.5: the same assertion goes red on an adapter that drops the field."""
    meta = {"name": "x", "extensions": [".x"], "contract_version": contract.CONTRACT_VERSION}
    assert contract.validate_meta(meta) == []  # optional in the contract …
    with pytest.raises(AssertionError, match="ships without symbol_shapes"):
        _assert_announces_shapes("x", meta)  # … and required of an in-tree adapter


@pytest.mark.parametrize(
    ("shapes", "fragment"),
    [
        ([], "a non-empty list"),
        ([{"kind": "call"}], "meta.symbol_shapes[0].pattern"),
        ([{"kind": "guess", "pattern": "x"}], "meta.symbol_shapes[0].kind"),
        ([{"kind": "call", "pattern": "("}], "a regular expression"),
        ([{"kind": "call", "pattern": "x", "scoped": "yes"}], "meta.symbol_shapes[0].scoped"),
        ([{"kind": "call", "pattern": "x", "extra": 1}], "meta.symbol_shapes[0].extra"),
    ],
)
def test_a_malformed_shape_fails_the_handshake(shapes: object, fragment: str) -> None:
    meta = {"name": "x", "extensions": [".x"], "contract_version": 13, "symbol_shapes": shapes}
    errors = contract.validate_meta(meta)
    assert any(fragment in error for error in errors), errors


def test_the_shape_vocabulary_is_the_one_the_contract_names() -> None:
    assert contract.SHAPE_KINDS == ("declaration", "reference", "call", "name")
    assert all(re.fullmatch(r"[a-z]+", kind) for kind in contract.SHAPE_KINDS)
