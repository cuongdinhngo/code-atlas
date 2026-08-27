"""Task 152: the TS adapter fills the contract `args`/`arg_keys` edge fields — the asymmetry a
second adapter exists to expose (only PHP filled them before). Pins the exact payload, not presence,
and asserts it passes `contract.validate` with no validator change (AC1). Needs Node.
"""

from __future__ import annotations

from code_atlas import contract
from tests.ts_adapter_cli import needs_node, parse_file

FIXTURE = "tests/fixtures/typescript/call_args.ts"


def _by_target(edges: list[dict], kind: str, target: str) -> dict:
    hits = [e for e in edges if e["kind"] == kind and e["target_raw"].endswith(target)]
    assert len(hits) == 1, f"{kind} {target}: {len(hits)} matches"
    return hits[0]


@needs_node
def test_ts_call_args_and_arg_keys_are_pinned() -> None:
    result = parse_file(FIXTURE)
    assert result["ok"] is True
    # AC1: the emitted payload validates against the frozen contract with no validator change.
    assert contract.validate(result) == []
    edges = result["edges"]

    # Every args category, in source order; a non-literal (the bare `x`) is null, never a guess.
    literals = _by_target(edges, "CALLS", "literals")
    assert literals["args"] == ["string", "number", "true", "false", "null", None]
    assert literals["arg_keys"] == [None, None, None, None, None, None]

    # Object literal -> category `array`, arg_keys = its keys: normal (`a`,`b`) and shorthand
    # (`short`) properties contribute; a spread (`...rest`) and a computed key (`[k]`) do not.
    keyed = _by_target(edges, "CALLS", "keyed")
    assert keyed["args"] == ["array"]
    assert keyed["arg_keys"] == [["a", "b", "short"]]

    # A positional array literal is category `array` with no string keys -> [].
    positional = _by_target(edges, "CALLS", "positional")
    assert positional["args"] == ["array"]
    assert positional["arg_keys"] == [[]]

    # A template literal is a string-typed expression -> category `string`.
    templated = _by_target(edges, "CALLS", "templated")
    assert templated["args"] == ["string"]
    assert templated["arg_keys"] == [None]

    # A spread argument forwards an unknown count, so no position is trustworthy: args is omitted.
    spread = _by_target(edges, "CALLS", "spread")
    assert "args" not in spread and "arg_keys" not in spread

    # NEW carries args too; the object literal's key rides parallel to the string arg.
    new_thing = _by_target(edges, "NEW", "Thing")
    assert new_thing["args"] == ["array", "string"]
    assert new_thing["arg_keys"] == [["id"], None]
