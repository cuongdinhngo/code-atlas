"""Task 019: the TypeScript adapter's ``--server`` mode, driven by the real core (§4.1, §7).

Mirrors ``test_php_adapter_server.py`` — every assertion drives the real
:class:`SubprocessAdapter`, the same way ``CA_TYPESCRIPT_CMD`` launches it. A fake on either side
would only prove the fake is self-consistent. These skip without Node / ``npm install``, so
``0 skipped`` is the evidence the TS path actually ran.
"""

from __future__ import annotations

import collections
import shutil
from pathlib import Path

import pytest

from code_atlas.adapter import SubprocessAdapter

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = ROOT / "adapters" / "typescript"
ENTRY = ADAPTER / "index.js"
NODE_MODULES = ADAPTER / "node_modules" / "typescript"

GOOD = "tests/fixtures/typescript/module_scoped.ts"
CJS = "tests/fixtures/typescript/module_cjs.ts"
BROKEN = "tests/fixtures/typescript/syntax_error.ts"

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(
    NODE is None or not NODE_MODULES.is_dir(),
    reason=f"needs the Node CLI and `npm install` in {ADAPTER}",
)


def server() -> SubprocessAdapter:
    """The adapter under the core's own driver, exactly as `CA_TYPESCRIPT_CMD` would launch it."""
    return SubprocessAdapter("typescript", [str(NODE), str(ENTRY), "--server"], ROOT)


def test_the_proof_has_something_to_run() -> None:
    # Runs without Node: a skipped proof must not also hide a missing entry point or fixture.
    assert ENTRY.is_file()
    assert "--server" in ENTRY.read_text(encoding="utf-8")
    assert (ROOT / GOOD).read_text(encoding="utf-8").lstrip().startswith(("//", "import"))


@needs_node
def test_the_core_drives_the_real_ts_adapter_end_to_end() -> None:
    with server() as adapter:
        assert adapter.name == "typescript"
        assert adapter.extensions == (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")

        result = adapter.parse(GOOD)
        assert result.ok is True
        assert result.path == GOOD
        assert result.nodes and result.edges


@needs_node
def test_the_handshake_announces_capabilities_as_an_object() -> None:
    # semantic_types is not advertised yet (the inferred-receiver work is a later 019 slice).
    with server() as adapter:
        assert adapter.capabilities == {}


@needs_node
@pytest.mark.parametrize("fixture", [GOOD, CJS], ids=["esm", "cjs"])
def test_declarations_only_drops_body_edges_but_keeps_the_module_shape(fixture: str) -> None:
    """R-039: declarations_only skips CALLS/NEW from bodies; CONTAINS/IMPLEMENTS/IMPORTS survive.

    Both module systems, because a `const x = require(…)` reaches the walk by a different path than
    an ESM `import`: with ESM alone the CJS half could lose every IMPORTS here and stay green.
    """
    with server() as adapter:
        full = collections.Counter(e["kind"] for e in adapter.parse(fixture).edges)
        lean_result = adapter.parse(fixture, declarations_only=True)
        lean = collections.Counter(e["kind"] for e in lean_result.edges)

    assert full["NEW"], "the full parse must have body edges to drop"
    assert lean["CALLS"] == 0 and lean["NEW"] == 0
    assert lean["CONTAINS"] == full["CONTAINS"]
    assert lean["IMPLEMENTS"] == full["IMPLEMENTS"]
    assert full["IMPORTS"], "the fixture must import something for the next assertion to bite"
    assert lean["IMPORTS"] == full["IMPORTS"]
    assert lean_result.nodes, "declarations are still emitted"


@needs_node
def test_a_bad_file_fails_softly_and_the_next_file_still_parses() -> None:
    with server() as adapter:
        broken = adapter.parse(BROKEN)
        assert broken.ok is False
        assert broken.error and "syntax error" in broken.error
        assert not broken.nodes and not broken.edges

        assert adapter.parse(GOOD).ok is True, "one bad file must not end the process"


@needs_node
def test_every_edge_is_bare_in_server_mode() -> None:
    # R3.3: cross-file linking is the resolver's job; the adapter never claims a target_qname.
    with server() as adapter:
        edges = adapter.parse(GOOD).edges

    assert edges
    for edge in edges:
        assert "target_qname" not in edge
        assert edge["target_raw"]
