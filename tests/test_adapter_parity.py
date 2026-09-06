"""`ADAPTER_PLAYBOOK.md` §7 must equal what the adapters actually emit, not what an author believed.

The playbook shipped with a hand-typed parity table under a *"measured"* header, and three of its
cells were assumptions: SQL's dropped procedure parameters read as ``n/a``, and ``modifiers`` was
absent because nobody thought to probe it. The table is now generated
(``scripts/adapter_parity_report.py``) and pinned here, so an optional field an adapter starts or
stops filling turns this red instead of quietly outdating a document.

Needs every adapter's toolchain; the whole module skips otherwise rather than pinning a table with
``n/r`` holes in it, which would be a ceiling nobody can trust (R6.5).
"""

from __future__ import annotations

import shutil

import pytest

from scripts.adapter_parity_report import (
    COUNT_PROBES,
    PARITY_DIR,
    PROBES,
    RATIO_PROBES,
    fixture_for,
    measure,
    playbook_table,
    render,
)
from tests.contract.adapter_registry import REGISTRY

needs_every_adapter = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("php", "node")),
    reason="the parity table is pinned only where every adapter can run",
)


def test_every_registered_adapter_has_a_parity_fixture() -> None:
    """R6.7: adapter #5 appears in the table by adding a fixture, never by editing the script."""
    for name in sorted(REGISTRY):
        assert fixture_for(name).is_file()


def test_a_registered_adapter_without_a_fixture_fails_loudly() -> None:
    """R6.5 guard-the-guard: a missing fixture must raise, never shorten the table in silence."""
    with pytest.raises(SystemExit, match="expected exactly one parity fixture"):
        fixture_for("no-such-adapter")


def test_the_probe_set_is_non_empty_and_disjoint() -> None:
    # An empty probe set would make the pinning below vacuously true.
    assert RATIO_PROBES and COUNT_PROBES
    assert not set(RATIO_PROBES) & set(COUNT_PROBES)
    assert len(PROBES) == len(RATIO_PROBES) + len(COUNT_PROBES)


@needs_every_adapter
def test_the_playbook_table_is_what_the_adapters_emit() -> None:
    assert playbook_table() == render(), (
        "docs/ADAPTER_PLAYBOOK.md §7 disagrees with the adapters. Regenerate it: "
        "`python scripts/adapter_parity_report.py` and paste between the parity-table markers."
    )


@needs_every_adapter
def test_a_ratio_cell_distinguishes_nothing_to_find_from_dropped() -> None:
    """The distinction the table is built on, pinned so a refactor cannot collapse it.

    ``0/0`` is a language without that construct; ``0/1`` is an adapter that dropped one. If both
    rendered the same the table would read as a defect list for every language.
    """
    cells = measure("sql")
    assert cells is not None
    assert cells["`extra.type` on a member"] == "0/0", "SQL declares no Method/Property here"
    assert cells["`params` on a callable"] == "0/2", "two procedures declare parameters"


@needs_every_adapter
def test_the_fixtures_encode_one_construct_set() -> None:
    """Every parity fixture declares a callable, or the ratio rows measure nothing (R6.5)."""
    for name in sorted(REGISTRY):
        cells = measure(name)
        assert cells is not None, f"{name} did not run; the skip marker should have caught it"
        _, total = cells["`params` on a callable"].split("/")
        assert int(total) > 0, f"{PARITY_DIR.name}/{name}.* declares no callable to probe"
