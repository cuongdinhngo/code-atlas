"""Task 154: a `.js` file's JSDoc is a type source. `@returns`/`@param`/`@type` fill the same
`extra.type` slot a TS annotation does (AC1), and feed 153's type table so a JSDoc-typed receiver
resolves like a TS one (AC2). The `.mjs`/`.cjs`/`.jsx` flavours are the same mechanism. Needs Node.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.adapter_cli import run_adapter_file
from tests.ts_adapter_cli import ENTRY, NODE, needs_node, parse_file

JSDOC = "tests/fixtures/typescript/jsdoc_types.js"


def _node(result: dict, name: str) -> dict:
    hits = [n for n in result["nodes"] if n["name"] == name]
    assert len(hits) == 1, f"{name}: {len(hits)}"
    return hits[0]


@needs_node
def test_jsdoc_fills_extra_type_and_resolves_the_receiver() -> None:
    result = parse_file(JSDOC)
    # AC1: `@returns {Service}` on a .js function lands in extra.type, as a `.ts` `: Service` would.
    assert (_node(result, "run").get("extra") or {}).get("type") == "Service"
    # `@typedef {Object} Point` -> an Interface declaration (the `.js` analogue of a type alias).
    assert _node(result, "Point")["kind"] == "Interface"
    # AC2: `@param {Service} svc` types the receiver -> `svc.handle()` is Service::handle, RESOLVED.
    calls = [e for e in result["edges"] if e["kind"] == "CALLS"]
    assert len(calls) == 1
    assert calls[0]["target_raw"].endswith("::Service::handle")
    assert "confidence_tier" not in calls[0]  # RESOLVED default, not HEURISTIC


@needs_node
def test_jsdoc_types_resolve_across_js_flavours(tmp_path: Path) -> None:
    # The .mjs/.cjs/.jsx flavours are the same construct at a different ScriptKind (README note).
    body = (
        "class Svc { go() {} }\n"
        "/** @param {Svc} s */\n"
        "function run(s) { s.go(); }\n"
    )
    for ext in (".mjs", ".cjs", ".jsx"):
        path = tmp_path / f"flavour{ext}"
        path.write_text(body, encoding="utf-8")
        proc = run_adapter_file((str(NODE), str(ENTRY)), path.name, cwd=tmp_path)
        result = json.loads(proc.stdout.splitlines()[-1])
        assert result["ok"] is True, ext
        calls = [e for e in result["edges"] if e["kind"] == "CALLS"]
        assert len(calls) == 1 and calls[0]["target_raw"].endswith("::Svc::go"), ext
        assert "confidence_tier" not in calls[0], ext
