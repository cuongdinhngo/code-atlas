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
    # +1 each: coverage (160), cli (176), config_provenance (175), check_column_defaults (194),
    # trace_capability (199), onboarding scope (206), community (211), provenance (209),
    # orientation (207), audience (210), sequence_diagram (225), er_diagram (224), preflight (237),
    # fit (260), symbol_role (262), worktree_guard + nominate_roots (268), instructions (300)
    assert len(core_modules()) == 91
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


def test_onboarding_and_tools_are_sql_free() -> None:
    """AC1 (task 112): every onboarding aggregate is a ``store.py`` query, so no SQL and no
    ``sqlite3`` import lives under ``onboarding/`` or ``tools/`` — the prototype's direct reads
    must never be copied into the core (R1.4)."""
    scoped = sorted((CORE / "onboarding").rglob("*.py")) + sorted((CORE / "tools").rglob("*.py"))
    assert scoped, "the scoped sweep found no module — it would pass vacuously"
    offenders = [
        module.relative_to(CORE).as_posix()
        for module in scoped
        if SQL.search(module.read_text(encoding="utf-8"))
    ]
    assert offenders == []


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
