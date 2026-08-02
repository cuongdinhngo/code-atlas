"""R3.4 live-adapter conformance: every adapter must pass the same schema + count harness.

Task 012 owns this matrix. Construct-level correctness stays in the PHP grammar tests (task 025);
`grammar.php` is deliberately not on this list (A1).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas import contract

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "php"
ENTRY = ADAPTER / "index.php"
AUTOLOAD = ADAPTER / "vendor" / "autoload.php"
FIXTURES = ROOT / "tests" / "fixtures" / "php"

# Scope / R6.2 named inventory — one file per category. Counts frozen from a golden `--file` run.
CASES: dict[str, tuple[str, int, int]] = {
    "namespaced": ("namespaced.php", 15, 20),
    "global": ("global.php", 4, 5),
    "underscore-psr0": ("underscore_psr0.php", 6, 8),
    "trait-conflict": ("trait_conflict.php", 7, 8),
    "enum": ("enum.php", 7, 6),
    "attributes": ("attributes.php", 14, 14),
    "closures-arrow": ("closures_arrow.php", 6, 5),
    "first-class-callable": ("first_class_callable.php", 4, 3),
    "include": ("include_require.php", 1, 2),
    "static-vs-instance": ("static_vs_instance.php", 5, 10),
    "syntax-error": ("syntax_error.php", 0, 0),
}

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not AUTOLOAD.is_file(),
    reason=f"needs the PHP CLI and `composer install` in {ADAPTER}",
)


def parse_fixture(filename: str) -> dict[str, object]:
    relative = (FIXTURES / filename).relative_to(ROOT)
    completed = subprocess.run(
        [str(PHP), str(ENTRY), "--file", str(relative)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.count("\n") == 1, "--file emits one line and nothing else"
    return json.loads(completed.stdout)


def test_the_conformance_inventory_is_the_named_r62_set() -> None:
    assert len(CASES) == 11
    assert "grammar.php" not in {filename for filename, _, _ in CASES.values()}
    for filename, _, _ in CASES.values():
        assert (FIXTURES / filename).is_file(), filename


@needs_php
@pytest.mark.parametrize("case", sorted(CASES), ids=sorted(CASES))
def test_php_adapter_conforms(case: str) -> None:
    filename, expected_nodes, expected_edges = CASES[case]
    result = parse_fixture(filename)

    if case == "syntax-error":
        assert result["ok"] is False
        assert "error" in result and result["error"]
        assert "nodes" not in result and "edges" not in result
        return

    assert result["ok"] is True
    assert contract.validate(result) == []
    nodes = result["nodes"]
    edges = result["edges"]
    assert isinstance(nodes, list) and isinstance(edges, list)
    assert len(nodes) == expected_nodes
    assert len(edges) == expected_edges
