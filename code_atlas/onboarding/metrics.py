"""Deterministic graph-metrics substrate for Phase-3 onboarding (task 083, M10).

Pure functions over graph shape only — no SQL and no language branches (R1.1/R1.4/R4). The store
supplies the raw pulls (``dependency_edges``/``node_universe``); everything here is arithmetic on
generic strings, so identical input yields byte-identical output (R4.2).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

# Derived-from-source: a pin test cross-checks this tuple against direction()'s range rather than
# hardcoding a copy (R6.7 / derived-not-listed-invariant). A node in a cycle reads "mixed" (AC3).
DIRECTION_LABELS: tuple[str, ...] = ("source", "sink", "mixed", "isolated")


def direction(fan_in: int, fan_out: int) -> str:
    """Direction label from a node's degrees; total over the four degree quadrants (R4)."""
    if fan_in and fan_out:
        return "mixed"
    if fan_out:
        return "source"
    if fan_in:
        return "sink"
    return "isolated"


@dataclass(frozen=True)
class NodeMetric:
    """One node's degrees and direction, at either grain (symbol qname or module file_path)."""

    key: str
    fan_in: int
    fan_out: int
    direction: str


@dataclass(frozen=True)
class GraphMetrics:
    """Symbol- and module-grain metrics over the resolved dependency graph (task 083)."""

    symbols: tuple[NodeMetric, ...]
    modules: tuple[NodeMetric, ...]
    entry_points: tuple[str, ...]
    module_entry_points: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """A plain, order-stable dict view — the serialisation consumers (086) build on."""
        return {
            "symbols": [_metric_dict(metric) for metric in self.symbols],
            "modules": [_metric_dict(metric) for metric in self.modules],
            "entry_points": list(self.entry_points),
            "module_entry_points": list(self.module_entry_points),
        }

    def to_json(self) -> str:
        """Deterministic JSON — the byte-stability surface (R4.2)."""
        return json.dumps(self.as_dict(), sort_keys=True, ensure_ascii=False)


def _metric_dict(metric: NodeMetric) -> dict[str, object]:
    return {
        "key": metric.key,
        "fan_in": metric.fan_in,
        "fan_out": metric.fan_out,
        "direction": metric.direction,
    }


def _grain(
    universe: Iterable[str],
    inbound: dict[str, set[str]],
    outbound: dict[str, set[str]],
) -> tuple[tuple[NodeMetric, ...], tuple[str, ...]]:
    """Ordered NodeMetrics for one grain plus its zero-inbound entry-point set (R3)."""
    metrics: list[NodeMetric] = []
    entries: list[str] = []
    for key in sorted(universe):
        fan_in = len(inbound.get(key, ()))
        fan_out = len(outbound.get(key, ()))
        metrics.append(NodeMetric(key, fan_in, fan_out, direction(fan_in, fan_out)))
        if fan_in == 0:
            entries.append(key)
    return tuple(metrics), tuple(entries)


def compute_metrics(
    nodes: Iterable[tuple[str, str]],
    edges: Iterable[tuple[str, str]],
) -> GraphMetrics:
    """Fan-in/out, zero-inbound entry points and direction at symbol and module grain (task 083).

    ``nodes`` is ``(qualified_name, file_path)``; ``edges`` is resolved ``(source, target)`` pairs.
    Deterministic regardless of argument order (R4.2). Entry points are the zero-inbound roots (R3);
    SCC/cycle membership is out of scope (task 087) — a node in a cycle simply reads ``mixed``.
    """
    qname_files: dict[str, set[str]] = {}
    module_universe: set[str] = set()
    for qname, file_path in nodes:
        qname_files.setdefault(qname, set()).add(file_path)
        module_universe.add(file_path)

    sym_in: dict[str, set[str]] = {}
    sym_out: dict[str, set[str]] = {}
    mod_in: dict[str, set[str]] = {}
    mod_out: dict[str, set[str]] = {}
    symbol_universe: set[str] = set(qname_files)
    for source, target in edges:
        if source == target:  # a self-reference is not a dependency on another node
            continue
        symbol_universe.update((source, target))
        sym_out.setdefault(source, set()).add(target)
        sym_in.setdefault(target, set()).add(source)
        for src_file in qname_files.get(source, ()):
            for tgt_file in qname_files.get(target, ()):
                if src_file == tgt_file:  # intra-module edges do not move module direction
                    continue
                mod_out.setdefault(src_file, set()).add(tgt_file)
                mod_in.setdefault(tgt_file, set()).add(src_file)

    symbols, entry_points = _grain(symbol_universe, sym_in, sym_out)
    modules, module_entry_points = _grain(module_universe, mod_in, mod_out)
    return GraphMetrics(
        symbols=symbols,
        modules=modules,
        entry_points=entry_points,
        module_entry_points=module_entry_points,
    )
