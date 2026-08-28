"""Task 185 — every tool is asked a real question over every registered adapter's own graph.

147 made adapter conformance a per-adapter matrix, and `test_ts_*` reach the indexer and store — but
before this file **no test in `tests/` imported `code_atlas.tools` and asked anything over a
TypeScript-indexed graph.** So "22 tools × every language" was tested for PHP and *asserted* for TS.

The expectations are data (`tool_parity.PARITY`). Adding a language is a row there plus its
fixtures; this module's body is never edited (147 AC2). Every state carries a **checkable
obligation**, so a declaration cannot be a rubber stamp:

  answers                          -> the principal collection is non-empty
  answers_without                  -> non-empty, AND every declared kind is absent from the graph
  empty_relation_not_modelled      -> empty,     AND every declared kind is absent from the graph
  not_applicable_by_language       -> empty,     AND the missing language feature is named
  empty_capability_not_configured  -> empty,     AND the payload says so in its own `reason`
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from code_atlas import contract
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.main import TOOL_NAMES
from code_atlas.store import GraphStore
from tests.contract.adapter_registry import REGISTRY
from tests.contract.tool_parity import (
    ANSWERS,
    ANSWERS_WITHOUT,
    EMPTY_CAPABILITY_NOT_CONFIGURED,
    EMPTY_STATES,
    INVOKERS,
    NOT_APPLICABLE_BY_LANGUAGE,
    PARITY,
    STATES,
    ToolParity,
)


@pytest.fixture(scope="module")
def graphs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[Config, frozenset[str]]]:
    """One indexed repo per language, built once for the whole module.

    Module-scoped because 44 cells over 2 languages must not pay 44 builds: the two builds are the
    only expensive part of this file (measured in the working doc).
    """
    built: dict[str, tuple[Config, frozenset[str]]] = {}
    for name, column in PARITY.items():
        if not _available(column):
            continue
        root = tmp_path_factory.mktemp(f"parity-{name}")
        built[name] = _build(root, column)
    return built


def _available(column: ToolParity) -> bool:
    """The adapter's own availability mark, reused rather than re-derived (R6.7)."""
    return not column.cli.availability.args[0]


def _build(root: Path, column: ToolParity) -> tuple[Config, frozenset[str]]:
    """Copy this language's spec fixtures into a git repo, index it, return config + edge kinds."""
    src = root / "src"
    src.mkdir()
    for pattern in column.globs:
        for directory in (column.cli.fixtures_dir, column.cli.fixtures_dir / "resolve"):
            for fixture in sorted(directory.glob(pattern)):
                shutil.copy(fixture, src / fixture.name)
    argv = ", ".join(f"'{part}'" for part in (*column.cli.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\n{column.cli.name} = [{argv}]\n", encoding="utf-8"
    )
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    db_path = root / ".code-atlas" / "graph.db"
    config = load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_ENTRY_POINTS": column.entry_points,
        },
    )
    with GraphStore(db_path) as store:
        report = full_build(config, store)
        assert report.nodes > 0, f"{column.cli.name}: the fixture repo produced no graph"
        kinds = frozenset(
            str(kind) for (kind,) in store._conn.execute("SELECT DISTINCT kind FROM edges")
        )
    return config, kinds


def _principal(payload: dict[str, object], key: str) -> object:
    return payload.get(key)


def _params() -> list[Any]:
    """Every (adapter, tool) cell, each carrying its adapter's availability mark (R6.5)."""
    cells: list[Any] = []
    for name in sorted(PARITY):
        column = PARITY[name]
        for tool in sorted(column.tools):
            cells.append(
                pytest.param(name, tool, id=f"{name}:{tool}", marks=column.cli.availability)
            )
    return cells


# ── guard-the-guard: the matrix cannot be vacuously green (R6.5, 147's precedent) ────────────────


def test_the_parity_matrix_is_non_empty() -> None:
    assert PARITY, "no languages declared — the parity matrix would be vacuously green"


def test_the_matrix_covers_exactly_the_registered_adapters() -> None:
    """A new adapter cannot land with an undeclared tool surface (AC2/AC3)."""
    assert set(PARITY) == set(REGISTRY), (
        "every conformance-registered adapter must declare a tool-parity column: "
        f"missing {sorted(set(REGISTRY) - set(PARITY))}, "
        f"unregistered {sorted(set(PARITY) - set(REGISTRY))}"
    )


@pytest.mark.parametrize("name", sorted(PARITY))
def test_every_tool_is_declared_for_every_language(name: str) -> None:
    """AC2: an undeclared (adapter, tool) pair FAILS — derived from TOOL_NAMES, never re-listed."""
    declared = set(PARITY[name].tools)
    assert declared == set(TOOL_NAMES), (
        f"{name}: undeclared {sorted(set(TOOL_NAMES) - declared)}, "
        f"unknown {sorted(declared - set(TOOL_NAMES))}"
    )


def test_every_tool_has_exactly_one_invoker() -> None:
    """R6.7: the call table is derived against TOOL_NAMES, so tool N+1 cannot ship undriven."""
    assert set(INVOKERS) == set(TOOL_NAMES)


@pytest.mark.parametrize("name, tool", [(n, t) for n in sorted(PARITY) for t in PARITY[n].tools])
def test_each_declaration_is_well_formed(name: str, tool: str) -> None:
    """Every state's obligation is declared, and every named edge kind is a real contract kind."""
    expect = PARITY[name].tools[tool]
    assert expect.state in STATES, f"{name}:{tool} declares unknown state {expect.state!r}"
    for kind in expect.kinds:
        assert kind in contract.EDGE_KINDS, f"{name}:{tool} names non-kind {kind!r}"
    if expect.state in {ANSWERS_WITHOUT, NOT_APPLICABLE_BY_LANGUAGE}:
        assert expect.because, f"{name}:{tool} must name the missing language feature"
    if expect.state == ANSWERS_WITHOUT:
        assert expect.kinds, f"{name}:{tool} must name what the answer is without"
    if expect.state == EMPTY_CAPABILITY_NOT_CONFIGURED:
        assert expect.reason, f"{name}:{tool} must name the payload's own reason"


# ── the executed matrix ─────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name, tool", _params())
def test_tool_parity(
    name: str, tool: str, graphs: dict[str, tuple[Config, frozenset[str]]]
) -> None:
    config, edge_kinds = graphs[name]
    expect = PARITY[name].tools[tool]
    payload = INVOKERS[tool].call(config, PARITY[name].subjects, TOOL_NAMES)
    principal = _principal(payload, INVOKERS[tool].answer_key)

    if expect.state in EMPTY_STATES:
        assert not principal, (
            f"{name}:{tool} is declared {expect.state} but answered "
            f"{INVOKERS[tool].answer_key}={principal!r}"
        )
    else:
        assert principal, (
            f"{name}:{tool} is declared {expect.state} but "
            f"{INVOKERS[tool].answer_key} is empty; reason={payload.get('reason')!r}"
        )

    # The declared kinds must really be absent — otherwise the declaration explains nothing.
    for kind in expect.kinds:
        assert kind not in edge_kinds, (
            f"{name}:{tool} claims the answer is shaped by a missing {kind}, "
            f"but this language's graph holds {kind} edges"
        )
    if expect.state == EMPTY_CAPABILITY_NOT_CONFIGURED:
        assert payload.get("reason") == expect.reason, (
            f"{name}:{tool} must be empty for a configuration reason the payload states, "
            f"not for a language reason; got {payload.get('reason')!r}"
        )


def test_the_two_languages_disagree_somewhere_and_that_is_the_point(
    graphs: dict[str, tuple[Config, frozenset[str]]],
) -> None:
    """A matrix where every column is identical is not proving anything about parity.

    Guard-the-guard for the matrix's *content*: at least one cell must differ between languages, or
    the declarations could all be `answers` and the file would be a slow way of asserting nothing.
    """
    if len(graphs) < 2:
        pytest.skip("needs both adapters available to compare columns")
    states = {name: {t: e.state for t, e in PARITY[name].tools.items()} for name in graphs}
    columns = list(states.values())
    differing = {tool for tool in TOOL_NAMES if len({c[tool] for c in columns}) > 1}
    assert differing, "every language declares the same state for every tool — nothing is proven"
    assert ANSWERS in {c[tool] for c in columns for tool in differing}


def test_no_language_is_silently_skipped(
    graphs: dict[str, tuple[Config, frozenset[str]]],
) -> None:
    """R6.5: an unrunnable column must be visibly `skipped`, never absent-and-green."""
    unavailable = sorted(set(PARITY) - set(graphs))
    if unavailable:
        pytest.skip(f"adapter(s) unavailable on this host: {', '.join(unavailable)}")
    assert set(graphs) == set(PARITY)
