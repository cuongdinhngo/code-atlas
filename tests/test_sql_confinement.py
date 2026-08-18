"""R4 guard: `store.py` is the only core module that touches SQLite (PLAN §2 SRP, CONVENTION §4).

Fails when another core module grows a connection or a SQL string, which is how the storage
boundary stays real as the indexer, resolver, and tools get written.
"""

import re
from pathlib import Path

import pytest

from code_atlas import contract

CORE = Path(contract.__file__).parent
ADAPTERS = CORE.parent / "adapters"
STORE = "store.py"

SQL = re.compile(
    r"\bsqlite3\b|\bPRAGMA\b|\bSELECT\b|\bINSERT INTO\b|\bDELETE FROM\b"
    r"|\bCREATE (?:TABLE|INDEX|TRIGGER|VIRTUAL TABLE)\b"
)
ADAPTER_SOURCE_SUFFIXES = (".php", ".py", ".ts", ".js", ".cs")
VENDORED = frozenset({"vendor", "node_modules"})


def core_modules() -> list[Path]:
    return sorted(CORE.rglob("*.py"))


def test_the_guard_has_something_to_check() -> None:
    # Guards the guard: an empty module list or an empty store would pass every check vacuously.
    assert len(core_modules()) == 45
    assert len((CORE / STORE).read_text(encoding="utf-8").splitlines()) > 50


def test_the_vendor_filter_narrows_the_sweep_without_emptying_it() -> None:
    """A filter that swallowed the authored files too would quietly restore the 0/0 vacuity."""
    present = [path for path in ADAPTERS.rglob("*.php") if path.is_file()]
    if not present:
        pytest.skip("no adapter has source yet (task 006)")

    authored = authored_adapter_sources()
    assert authored, "the vendor filter removed every adapter source"
    assert all(VENDORED.isdisjoint(path.parts) for path in authored)
    if len(present) > len(authored):
        assert any(not VENDORED.isdisjoint(path.parts) for path in present)


def test_exactly_one_core_module_touches_sqlite() -> None:
    touching = [
        module.name
        for module in core_modules()
        if SQL.search(module.read_text(encoding="utf-8"))
    ]
    assert touching == [STORE]


def authored_adapter_sources() -> list[Path]:
    """Authored files only: a dependency an adapter vendors is not something this repo wrote."""
    return [
        path
        for path in sorted(ADAPTERS.rglob("*"))
        if path.is_file()
        and path.suffix in ADAPTER_SOURCE_SUFFIXES
        and VENDORED.isdisjoint(path.parts)
    ]


def test_no_adapter_source_reaches_into_the_core() -> None:
    """Vacuous at 0/0 until an adapter exists — skipped rather than passed green (LESSONS 002)."""
    sources = authored_adapter_sources()
    if not sources:
        pytest.skip("adapters/ has no source yet (task 006); this guard is 0/0, not proven")
    for source in sources:
        assert "code_atlas" not in source.read_text(encoding="utf-8")
