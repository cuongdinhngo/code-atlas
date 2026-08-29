"""Task 191: no test may put every one of its assertions under a conditional.

181 shipped `test_a_qname_subject_still_ranks_as_it_did` with both assertions inside
`if SIBLING_DEFINITIONS in payload:`. The payload answered `index_stale`, the branch was never
taken, and the test reported green while asserting nothing — for two tickets, with nothing in the
suite able to tell that apart from a pass. This is the guard that can.
"""

from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).parent

# A site allowed to assert only under a conditional, with the reason it is legitimately so. Named
# in the tree rather than remembered: an empty allowlist is the claim that no such site exists.
LEGITIMATELY_CONDITIONAL: dict[tuple[str, str], str] = {}

# The sweep must not pass by scanning nothing (R6.5). Well below the real count, so it fails on a
# broken glob and never on an ordinary addition.
MIN_TEST_FUNCTIONS_SCANNED = 500


def assertions(node: ast.AST) -> list[ast.Assert]:
    return [child for child in ast.walk(node) if isinstance(child, ast.Assert)]


def sweep() -> tuple[list[tuple[str, str, int]], int]:
    """Every test whose assertions ALL sit inside an `if`/`while`, and how many were read."""
    offenders: list[tuple[str, str, int]] = []
    scanned = 0
    for path in sorted(TESTS.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not function.name.startswith("test_"):
                continue
            scanned += 1
            total = assertions(function)
            if not total:
                continue
            conditional = {
                id(found)
                for statement in function.body
                for node in ast.walk(statement)
                if isinstance(node, ast.If | ast.While)
                for found in assertions(node)
            }
            if all(id(found) in conditional for found in total):
                offenders.append((path.name, function.name, function.lineno))
    return offenders, scanned


def test_the_sweep_has_something_to_read() -> None:
    """Guards the guard: a broken glob would make every check below vacuously true."""
    _, scanned = sweep()
    assert scanned >= MIN_TEST_FUNCTIONS_SCANNED, (
        f"only {scanned} test function(s) parsed — the sweep is not reading the suite"
    )


def test_no_test_asserts_only_under_a_conditional() -> None:
    """A conditional that is never true makes a test that cannot fail (R6.5)."""
    offenders, _ = sweep()
    unexplained = [
        site for site in offenders if (site[0], site[1]) not in LEGITIMATELY_CONDITIONAL
    ]
    assert not unexplained, "\n".join(
        f"{name}:{line} {function} asserts only inside a conditional — make the assertion "
        "unconditional, or add it to LEGITIMATELY_CONDITIONAL with the reason"
        for name, function, line in unexplained
    )
