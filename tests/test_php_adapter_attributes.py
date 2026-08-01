"""Attributes land under `extra.attributes` on every declaration kind that can carry them.

Regression guard: functions, methods, closures, arrow functions and anonymous classes used to
hand the raw attribute list straight to the adapter's `extraFields()`, which made `extra` *be*
the list instead of holding it under `attributes` — so `node.extra.attributes` read empty there
while it worked on classes and properties. PHPStan at level max is what surfaced the mismatch.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = ROOT / "adapters" / "php"
ENTRY = ADAPTER / "index.php"
AUTOLOAD = ADAPTER / "vendor" / "autoload.php"
FIXTURE = "tests/fixtures/php/attributes.php"
MARKER = "\\App\\Attributes\\Marker"

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not AUTOLOAD.is_file(),
    reason=f"needs the PHP CLI and `composer install` in {ADAPTER}",
)

# Every declaration kind PHP lets an attribute sit on, mapped to the argument the fixture tags it
# with. Anonymous qnames are line-anchored, so they are matched by suffix rather than spelled out.
EXPECTED = {
    "\\App\\Attributes\\tagged": "fn",
    "\\App\\Attributes\\Tagged": "class",
    "\\App\\Attributes\\Tagged::FLAG": "const",
    "\\App\\Attributes\\Tagged::$field": "prop",
    "\\App\\Attributes\\Tagged::$id": "promoted",
    "\\App\\Attributes\\Tagged::run": "method",
    "\\App\\Attributes\\Flag::On": "case",
}
EXPECTED_ANONYMOUS = {"{closure@": "closure", "{fn@": "arrow", "{class@": "anon"}


def parse_fixture() -> dict[str, object]:
    completed = subprocess.run(
        [str(PHP), str(ENTRY), "--file", FIXTURE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@needs_php
def test_named_declarations_carry_attributes_under_extra_attributes() -> None:
    nodes = {node["qualified_name"]: node for node in parse_fixture()["nodes"]}  # type: ignore[index]
    for qname, argument in EXPECTED.items():
        assert qname in nodes, f"{qname} was not emitted at all"
        assert nodes[qname]["extra"]["attributes"] == [{"name": MARKER, "args": [argument]}]


@needs_php
def test_anonymous_declarations_carry_attributes_under_extra_attributes() -> None:
    nodes = parse_fixture()["nodes"]
    for anchor, argument in EXPECTED_ANONYMOUS.items():
        matches = [n for n in nodes if anchor in n["qualified_name"]]  # type: ignore[index]
        assert len(matches) == 1, f"expected exactly one {anchor}…}} node, got {len(matches)}"
        assert matches[0]["extra"]["attributes"] == [{"name": MARKER, "args": [argument]}]


@needs_php
def test_extra_is_always_a_mapping_never_a_bare_attribute_list() -> None:
    # The precise shape the bug produced: `extra` itself being the list of attributes.
    for node in parse_fixture()["nodes"]:  # type: ignore[union-attr]
        extra = node.get("extra")
        assert extra is None or isinstance(extra, dict), f"{node['qualified_name']}: {extra!r}"
