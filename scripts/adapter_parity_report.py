#!/usr/bin/env python3
"""Which optional contract fields does each adapter actually fill? Measured, never asserted.

`docs/ADAPTER_PLAYBOOK.md` §7 carried a hand-typed version of this table, and three of its cells
were assumptions wearing a "measured" header — SQL's dropped procedure parameters read as `n/a`,
and `modifiers` was missing because nobody thought to look. A table an author types is a table an
author can guess. This one is derived (R6.7): the adapters come from the conformance REGISTRY, the
fixtures from `tests/fixtures/parity/`, and every cell is a count taken from a real `--file` run.

Cells read ``hits/total``. **``0/0`` means the fixture had none of that construct to find** — a
measurement, not a judgement — while ``0/1`` means it was there and the adapter dropped it. There is
no cell an author can fill by opinion, which is the point.

Read-only, no network, deterministic (R4.2). Needs every adapter's toolchain::

    python scripts/adapter_parity_report.py            # the markdown table
    python scripts/adapter_parity_report.py --check    # exit 1 unless the playbook matches
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas import contract  # noqa: E402
from tests.contract.adapter_registry import REGISTRY  # noqa: E402

PARITY_DIR = _REPO / "tests" / "fixtures" / "parity"
PLAYBOOK = _REPO / "docs" / "ADAPTER_PLAYBOOK.md"
TABLE_START = "<!-- parity-table:start -->"
TABLE_END = "<!-- parity-table:end -->"
UNAVAILABLE = "n/r"

Nodes = list[dict[str, Any]]
Edges = list[dict[str, Any]]
Probe = Callable[[Nodes, Edges], tuple[int, int]]


def _members(nodes: Nodes) -> Nodes:
    # `Column` belongs here: a table CONTAINS it exactly as a class CONTAINS a Property, and it is
    # where SQL writes a declared type. Leaving it out rendered SQL's typed member as `0/0` — the
    # cell that means "nothing to find" — when the fixture declares one (231).
    return [n for n in nodes if n.get("kind") in ("Method", "Property", "Column")]


def _callables(nodes: Nodes) -> Nodes:
    return [n for n in nodes if n.get("kind") in contract.CALLABLE_KINDS]


def _call_sites(edges: Edges) -> Edges:
    return [e for e in edges if e.get("kind") in contract.CALLER_KINDS]


def _filled(rows: Sequence[dict[str, Any]], field: str) -> tuple[int, int]:
    """How many of these rows carry a non-empty value for one optional field."""
    return sum(1 for row in rows if row.get(field)), len(rows)


def _typed(nodes: Nodes) -> tuple[int, int]:
    members = _members(nodes)
    hits = sum(1 for n in members if (n.get("extra") or {}).get("type"))
    return hits, len(members)


# Ordered probes, rendered `hits/total`: how many rows that COULD carry an optional field do.
# `0/0` is "the fixture had none of that construct" — a measurement; `0/1` is "it was there and the
# adapter dropped it". Nothing here counts a fixture's own vocabulary: that measures the fixture.
RATIO_PROBES: dict[str, Probe] = {
    "`params` on a callable": lambda nodes, edges: _filled(_callables(nodes), "params"),
    "`extra.type` on a member": lambda nodes, edges: _typed(nodes),
    "`modifiers` on a member": lambda nodes, edges: _filled(_members(nodes), "modifiers"),
    "`args` on a call site": lambda nodes, edges: _filled(_call_sites(edges), "args"),
    "`arg_keys` on a call site": lambda nodes, edges: _filled(_call_sites(edges), "arg_keys"),
}

def _onto_a_field(nodes: Nodes, edges: Edges) -> tuple[int, int]:
    """References onto a declared property or class constant: a use, not an annotation (369)."""
    fields = {n.get("qualified_name") for n in nodes if n.get("kind") in ("Property", "ClassConst")}
    refs = [e for e in edges if e.get("kind") == "REFERENCES"]
    return sum(1 for e in refs if e.get("target_raw") in fields), len(refs)


# Probes with no denominator: the construct is the adapter's choice, not the fixture's supply.
COUNT_PROBES: dict[str, Probe] = {
    "`REFERENCES` edges from the annotations": lambda nodes, edges: (
        _onto_a_field(nodes, edges)[1] - _onto_a_field(nodes, edges)[0],
        0,
    ),
    "`REFERENCES` onto a static / class property": _onto_a_field,
    "`ClassConst` for the class constant": lambda nodes, edges: (
        sum(1 for n in nodes if n.get("kind") == "ClassConst"),
        0,
    ),
}

PROBES: dict[str, Probe] = {**RATIO_PROBES, **COUNT_PROBES}


def fixture_for(adapter: str) -> Path:
    """The parity fixture an adapter owns: `tests/fixtures/parity/<adapter>.*`, exactly one."""
    found = sorted(p for p in PARITY_DIR.glob(f"{adapter}.*") if p.suffix != ".md")
    if len(found) != 1:
        raise SystemExit(
            f"{adapter}: expected exactly one parity fixture at "
            f"{PARITY_DIR.relative_to(_REPO)}/{adapter}.*, found {len(found)}. A registered "
            "adapter with no fixture must fail here, never print a short table (R6.5)."
        )
    return found[0]


def measure(adapter: str) -> dict[str, str] | None:
    """Run one adapter over its parity fixture. ``None`` when its toolchain is absent."""
    cli = REGISTRY[adapter].cli
    relative = fixture_for(adapter).relative_to(_REPO).as_posix()
    try:
        completed = subprocess.run(
            [*cli.entry_argv, "--file", relative],
            cwd=_REPO,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    if not result.get("ok"):
        raise SystemExit(f"{adapter}: {relative} did not parse — {result.get('error')}")
    nodes: Nodes = result.get("nodes") or []
    edges: Edges = result.get("edges") or []
    cells: dict[str, str] = {}
    for label, probe in RATIO_PROBES.items():
        hits, total = probe(nodes, edges)
        cells[label] = f"{hits}/{total}"
    for label, probe in COUNT_PROBES.items():
        cells[label] = str(probe(nodes, edges)[0])
    return cells


def render() -> str:
    adapters = sorted(REGISTRY)
    measured = {name: measure(name) for name in adapters}
    header = "| probe | " + " | ".join(adapters) + " |"
    rule = "|---" * (len(adapters) + 1) + "|"
    lines = [header, rule]
    for label in PROBES:
        cells = [
            UNAVAILABLE if measured[name] is None else measured[name][label]  # type: ignore[index]
            for name in adapters
        ]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    absent = [name for name in adapters if measured[name] is None]
    if absent:
        lines.append("")
        lines.append(
            f"`{UNAVAILABLE}` = not run on the host that produced this table: "
            + ", ".join(absent)
            + "."
        )
    return "\n".join(lines)


def playbook_table() -> str:
    text = PLAYBOOK.read_text(encoding="utf-8")
    if TABLE_START not in text or TABLE_END not in text:
        raise SystemExit(
            f"{PLAYBOOK.relative_to(_REPO)} has no {TABLE_START} / {TABLE_END} markers to pin."
        )
    return text.split(TABLE_START, 1)[1].split(TABLE_END, 1)[0].strip("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 unless the playbook's table equals this run",
    )
    args = parser.parse_args()
    table = render()
    if not args.check:
        print(table)
        return 0
    if playbook_table() == table:
        print("parity table matches the playbook")
        return 0
    print("parity table DIFFERS from the playbook — regenerate §7:\n")
    print(table)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
