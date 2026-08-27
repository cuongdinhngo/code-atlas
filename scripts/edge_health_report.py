#!/usr/bin/env python3
"""Break the HEURISTIC edge share down by CAUSE, per pinned public repo (task 136).

`edge_health` reports two thirds of edges as HEURISTIC and has done across two field rounds, but a
single aggregate cannot say whether that is *"the language spec could settle this and no ticket ever
carried it"* (PLAN §1's promised local type table) or *"no adapter can settle it without a semantic
model"* (PLAN §17's defer-to-an-LSP). The two readings imply opposite decisions, so this splits the
share into causes each traceable to one emission site in the adapter, and prints which side of that
line each cause falls on.

Derived, not listed (R6.7): the kinds scanned come from the store's own kind census, so a new
HEURISTIC-emitting kind shows up as a cause rather than vanishing. Read-only, deterministic (R4.2 —
store order is `source_qname, kind, target_raw, file_path, line, id`). Needs php + network:

    scripts/docker-test.sh python scripts/edge_health_report.py
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas import contract  # noqa: E402
from code_atlas.store import GraphStore, Row  # noqa: E402
from scripts.cross_repo_validate import (  # noqa: E402
    checkout_pinned,
    index_root,
    load_manifest,
)

_HEURISTIC = "HEURISTIC"
_SCAN_LIMIT = 200_000  # a pinned sample is ~10^3–10^4 edges; this is a runaway guard, not a page
_HIERARCHY_KINDS = ("EXTENDS", "IMPLEMENTS", "USES_TRAIT")

# Each cause names ONE adapter emission site, and says whether the PHP spec alone can settle it.
# `settleable` is the whole point of the report: it is the number PLAN §1 and §17 disagree about.
CAUSES: dict[str, tuple[bool, str]] = {
    "unknown_receiver": (
        True,
        "`$obj->m()` with no type for `$obj` — settled by `new X`, a typed property, a promoted "
        "param, a param/return hint or `@var`, all of which the spec puts in the file",
    ),
    "inherited_or_trait_receiver": (
        True,
        "`$this->m()` / `$obj->m()` where an ancestor or trait declares `m` — settled by walking "
        "EXTENDS / IMPLEMENTS / USES_TRAIT, which the graph already holds",
    ),
    "late_bound_or_string_name": (
        False,
        "`static::m()`, `'C::m'` callables, string method names — the target depends on runtime "
        "late binding, so no amount of local type information fixes it",
    ),
    "new_from_string_local": (
        False,
        "`$v = 'FQN'; new $v` — already a heuristic WIN over DYNAMIC, not a gap to close",
    ),
    "unwalkable_receiver_chain": (
        False,
        "the receiver is the declared type of a member the graph could not follow — the member "
        "is unindexed, or declares no type at all. Local type information is present and was "
        "used; what is missing is a declaration or a target, so no type table closes it",
    ),
}


def _class_of(qname: str) -> str:
    """The class-like part of a member qname (`\\A\\B::m` → `\\A\\B`); a bare qname is its own."""
    head, sep, _ = qname.rpartition("::")
    return head if sep else qname


def _ancestors(store: GraphStore) -> dict[str, set[str]]:
    """Transitive EXTENDS / IMPLEMENTS / USES_TRAIT closure, per class-like qname."""
    parents: dict[str, set[str]] = {}
    for kind in _HIERARCHY_KINDS:
        for edge in store.edges_matching_kind(kind, limit=_SCAN_LIMIT):
            target = edge.get("target_qname")
            if target:
                parents.setdefault(str(edge["source_qname"]), set()).add(str(target))
    closure: dict[str, set[str]] = {}
    for start in parents:
        seen: set[str] = set()
        queue = list(parents[start])
        while queue:
            current = queue.pop()
            if current in seen:
                continue
            seen.add(current)
            queue.extend(parents.get(current, ()))
        closure[start] = seen
    return closure


def heuristic_edges(store: GraphStore) -> list[Row]:
    """Every HEURISTIC edge, with the scanned kind set derived from the store's own census."""
    found: list[Row] = []
    for kind, _count in store.edge_kind_counts():
        found.extend(
            edge
            for edge in store.edges_matching_kind(str(kind), limit=_SCAN_LIMIT)
            if str(edge.get("confidence_tier")) == _HEURISTIC
        )
    return found


def classify(store: GraphStore, edges: list[Row]) -> list[tuple[str, Row]]:
    """Name the cause of each HEURISTIC edge — one adapter emission site per name."""
    closure = _ancestors(store)
    bare = [e for e in edges if str(e["kind"]) == "CALLS" and "::" not in str(e["target_raw"])]
    # One batched lookup for "does the class itself, or any ancestor, declare this method?"
    probes: set[str] = set()
    for edge in bare:
        owner = _class_of(str(edge["source_qname"]))
        for candidate in (owner, *closure.get(owner, ())):
            probes.add(f"{candidate}::{edge['target_raw']}")
    hits = store.nodes_by_qualified_names(sorted(probes), limit=1) if probes else {}

    labelled: list[tuple[str, Row]] = []
    for edge in edges:
        kind, raw = str(edge["kind"]), str(edge["target_raw"])
        if kind == "NEW":
            labelled.append(("new_from_string_local", edge))
        elif kind != "CALLS":
            labelled.append((f"other_{kind.lower()}", edge))
        elif contract.TYPE_OF_SUFFIX + contract.MEMBER_SEPARATOR in raw:
            # A receiver the adapter named and the walk could not follow (137) — a different
            # complaint from late binding, and counting it as one would overstate that cause.
            labelled.append(("unwalkable_receiver_chain", edge))
        elif "::" in raw:
            labelled.append(("late_bound_or_string_name", edge))
        else:
            owner = _class_of(str(edge["source_qname"]))
            declared = any(
                hits.get(f"{candidate}::{raw}")
                for candidate in (owner, *closure.get(owner, ()))
            )
            cause = "inherited_or_trait_receiver" if declared else "unknown_receiver"
            labelled.append((cause, edge))
    return labelled


def format_report(store: GraphStore, labelled: list[tuple[str, Row]]) -> str:
    """The tier mix, the cause split, and the one number the two plan sections disagree about."""
    health = store.edge_health()
    by_tier = dict(health["by_tier"])  # type: ignore[call-overload]
    total = sum(by_tier.values())
    heuristic = by_tier.get(_HEURISTIC, 0)
    counts = Counter(cause for cause, _ in labelled)
    unlinked = Counter(cause for cause, e in labelled if not e.get("target_qname"))
    ambiguous = Counter(
        cause
        for cause, edge in labelled
        if _sites(labelled)[(str(edge["source_qname"]), str(edge["file_path"]), edge["line"])] > 1
    )
    lines = [
        f"  all edges={total}  HEURISTIC={heuristic} ({100 * heuristic / total:.1f}%)  "
        f"linked={health['linked']} unlinked={health['unlinked']}",
        "  cause                        count    share  unlinked  multi-cand  settleable",
    ]
    for cause, count in counts.most_common():
        settleable, _why = CAUSES.get(cause, (False, "unclassified — the taxonomy has drifted"))
        lines.append(
            f"  {cause:<27} {count:>6}  {100 * count / heuristic:>5.1f}%  "
            f"{unlinked[cause]:>8}  {ambiguous[cause]:>10}  {'YES' if settleable else 'no':>10}"
        )
    settleable_total = sum(c for cause, c in counts.items() if CAUSES.get(cause, (False,))[0])
    # The ceiling, not the cause count: an edge whose target has no node cannot be promoted by
    # knowing the receiver's type — the resolver only leaves HEURISTIC when a lookup HITS.
    ceiling = settleable_total - sum(
        n for cause, n in unlinked.items() if CAUSES.get(cause, (False,))[0]
    )
    lines.append(
        f"  → cause is local type information: {settleable_total}/{heuristic} "
        f"({100 * settleable_total / heuristic:.1f}% of HEURISTIC)"
    )
    lines.append(
        f"  → of those, target is INDEXED: {ceiling}/{heuristic} "
        f"({100 * ceiling / heuristic:.1f}% of HEURISTIC, {100 * ceiling / total:.1f}% of all "
        f"edges) — the ceiling a type table alone can move"
    )
    return "\n".join(lines)


def _sites(labelled: list[tuple[str, Row]]) -> Counter[tuple[str, str, object]]:
    """How many HEURISTIC edges share one call site — >1 means the name matched N candidates."""
    return Counter(
        (str(edge["source_qname"]), str(edge["file_path"]), edge["line"])
        for _cause, edge in labelled
    )


def check(labelled: list[tuple[str, Row]], heuristic: int) -> list[str]:
    """The invariant: every HEURISTIC edge is accounted for, by a cause the report can explain."""
    problems: list[str] = []
    if len(labelled) != heuristic:
        problems.append(f"classified {len(labelled)} of {heuristic} HEURISTIC edges")
    unknown = sorted({cause for cause, _ in labelled if cause not in CAUSES})
    if unknown:
        problems.append(f"unexplained cause(s) {unknown} — a new emission site is unaccounted for")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="run just the sample with this id (faster focused run)")
    args = parser.parse_args(argv)

    cache_root = _REPO / "artifacts" / "cross-repo-cache"
    failures = 0
    for sample in load_manifest():
        sid = str(sample["id"])
        if args.only and sid != args.only:
            continue
        language = str(sample.get("language", "php"))
        print(f"\n### {sid} @ {str(sample['sha'])[:7]} ({language})")
        try:
            root = checkout_pinned(sample, cache_root)
            index_root(root, language=language)
            with GraphStore(root / ".code-atlas" / "graph.db") as store:
                edges = heuristic_edges(store)
                labelled = classify(store, edges)
                print(format_report(store, labelled))
                problems = check(labelled, len(edges))
            if problems:
                failures += 1
                print(f"  FAIL: {'; '.join(problems)}")
        except Exception as exc:  # noqa: BLE001 — report every repo even if one fails
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    print("\nCause → why, and whether the PHP spec alone can settle it:")
    for cause, (settleable, why) in CAUSES.items():
        print(f"  {'YES' if settleable else 'no ':<4} {cause}: {why}")
    if failures:
        print(f"\n{failures} repo(s) failed the cause check")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
