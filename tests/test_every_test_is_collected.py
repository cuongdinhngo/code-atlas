"""A `def test_` in a module pytest does not collect is not a test — it is a comment (R6.5).

Task 020 put the `File.line_end` guard in `tests/python_adapter_cli.py`; 217 put AC3's launch guard
there too. Both read like proof and neither ever ran: pytest's `python_files` is `test_*.py`, so a
helper module is collected only when its path is named on the command line. Twice in two PRs is a
class of defect, not a slip, so it gets a guard rather than a third fix.
"""

from __future__ import annotations

import ast
import fnmatch
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TESTS = REPO / "tests"
# The corpus adapter #4 parses is input, not source — kept out of this repo's tooling (020).
FIXTURE_DIR = TESTS / "fixtures" / "python"
# Derived, never re-listed (R6.7): pytest's own default when the config does not override it.
PYTEST_DEFAULT_PATTERNS = ("test_*.py", "*_test.py")


def _collect_patterns() -> tuple[str, ...]:
    config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    declared = config["tool"]["pytest"]["ini_options"].get("python_files")
    if declared is None:
        return PYTEST_DEFAULT_PATTERNS
    return tuple(declared.split()) if isinstance(declared, str) else tuple(declared)


def _defines_a_test(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and (node.name.startswith("test_") or node.name.startswith("Test"))
    ]


def _uncollected_modules() -> list[Path]:
    patterns = _collect_patterns()
    return [
        path
        for path in sorted(TESTS.rglob("*.py"))
        if FIXTURE_DIR not in path.parents
        and path.name != "__init__.py"
        and not any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns)
    ]


def test_the_sweep_has_uncollected_modules_to_check() -> None:
    """Guards the guard: with nothing uncollected this file would pass vacuously forever."""
    uncollected = _uncollected_modules()
    assert len(uncollected) >= 4, [p.name for p in uncollected]


def test_no_helper_module_hides_a_test_that_never_runs() -> None:
    hidden = {
        path.relative_to(REPO).as_posix(): names
        for path in _uncollected_modules()
        if (names := _defines_a_test(path))
    }
    assert hidden == {}, (
        f"{hidden} — pytest collects {' '.join(_collect_patterns())}, so these never run. "
        "Move each beside the adapter's other tests in a test_*.py module."
    )


def test_the_guard_sees_a_planted_hidden_test(tmp_path: Path) -> None:
    """R6.5 prove-the-guard-fails: the detector must read a `def test_` it should reject."""
    planted = tmp_path / "sneaky_cli.py"
    planted.write_text("def test_nothing() -> None:\n    assert True\n", encoding="utf-8")
    assert _defines_a_test(planted) == ["test_nothing"]
    assert not any(fnmatch.fnmatch(planted.name, p) for p in _collect_patterns())
