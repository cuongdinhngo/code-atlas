#!/usr/bin/env python3
"""Print + CHECK the 114 business-module table for the pinned public repos — AC5's evidence.

Authored fixtures have hidden a path-shape defect repeatedly in this area (retro
`fixture-shape-begs-the-question`), so the real-repo measurement is committed and re-runnable. It
clones+indexes each pin from `cross_repo_samples.json` (reusing task 018's harness) and prints the
module count, coverage percentage and single-tree count, plus every container refused and why.

**The expected answer on all three pins is ZERO modules** — none uses a capability layout, and AC5
asks for an honest zero with the reason rather than invented groups. That is a pass, not a gap.
Not part of per-PR CI — run locally or in Docker (needs php + network):

    scripts/docker-test.sh python scripts/module_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.onboarding.metrics import compute_metrics  # noqa: E402
from code_atlas.onboarding.modules import ModuleMap, find_business_modules  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402
from scripts.cross_repo_validate import (  # noqa: E402
    checkout_pinned,
    index_root,
    load_manifest,
)

MODULE_LIMIT = 50


def format_report(result: ModuleMap) -> str:
    """Module count, coverage and the divergence tally — plus every refusal, named."""
    single = sum(1 for row in result.modules if row.single_tree)
    lines = [
        f"  modules={len(result.modules)}  containers={len(result.containers)}  "
        f"single-tree={single}",
        f"  coverage: {result.covered}/{result.total} files ({result.percent} %); "
        f"{result.excluded} excluded as vendored or test code",
    ]
    for row in result.modules[:8]:
        flag = "  [only tree]" if row.single_tree else ""
        lines.append(
            f"    {row.module:<20} files={row.files:>5} classes={row.classes:>5} "
            f"trees={','.join(row.trees)}{flag}"
        )
    for container, reason in result.refused:
        lines.append(f"    refused {container}: {reason}")
    if not result.modules and not result.refused:
        lines.append("    no capability layout found (an honest zero — AC5)")
    return "\n".join(lines)


def check(result: ModuleMap) -> list[str]:
    """The gate every repo holds, whatever its shape: the table never over-claims its coverage."""
    problems: list[str] = []
    if result.covered > result.total:
        problems.append(f"covered {result.covered} exceeds total {result.total}")
    if not result.modules and result.covered:
        problems.append(f"no modules but {result.covered} files claimed as covered")
    if result.modules and len(result.containers) < 2 and any(
        row.single_tree for row in result.modules
    ):
        problems.append("single-tree divergence claimed with fewer than two containers")
    if any(not reason for _, reason in result.refused):
        problems.append("a refused container carries no reason (AC5)")
    return problems


def main() -> int:
    cache_root = _REPO / "artifacts" / "cross-repo-cache"
    failures = 0
    for sample in load_manifest():
        sid = str(sample["id"])
        print(f"\n### {sid} @ {str(sample['sha'])[:7]}")
        try:
            root = checkout_pinned(sample, cache_root)
            index_root(root)
            with GraphStore(root / ".code-atlas" / "graph.db") as store:
                nodes = store.node_universe()
                edges = store.dependency_edges()
                file_paths = store.file_paths()
                class_counts = dict(store.file_class_counts())
            metrics = compute_metrics(nodes, edges)
            # No declarations passed: the pins carry no `.code-atlas.toml`, so this measures the
            # structural signal alone — the weakest case, which is the one worth recording.
            result = find_business_modules(
                file_paths,
                class_counts=class_counts,
                fan_in={metric.key: metric.fan_in for metric in metrics.modules},
                limit=MODULE_LIMIT,
            )
            print(format_report(result))
            problems = check(result)
            if problems:
                failures += 1
                print(f"  FAIL: {'; '.join(problems)}")
        except Exception as exc:  # noqa: BLE001 — report every repo even if one fails
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    if failures:
        print(f"\n{failures} repo(s) failed the module check")
        return 1
    print("\nall repos pass the module check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
