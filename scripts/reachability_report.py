#!/usr/bin/env python3
"""Print + CHECK the 113 zero-inbound split for the pinned public PHP repos — AC4's evidence.

Authored fixtures have hidden a path-shape defect five times in this area (retro
`fixture-shape-begs-the-question`), so the real-repo measurement is committed and re-runnable
rather than eyeballed once. It clones+indexes each pin from `cross_repo_samples.json` (reusing task
018's harness), prints every bucket count — including the honest zeros (AC4) and any dropped bucket
with its reason (AC5) — and **asserts** the invariants the split must hold. Not part of per-PR CI —
run locally or in Docker (needs php + network):

    scripts/docker-test.sh python scripts/reachability_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.onboarding.metrics import compute_metrics  # noqa: E402
from code_atlas.onboarding.reachability import (  # noqa: E402
    BUCKETS,
    ReachabilitySplit,
    classify_reachability,
)
from code_atlas.store import GraphStore  # noqa: E402
from scripts.cross_repo_validate import (  # noqa: E402
    checkout_pinned,
    index_root,
    load_manifest,
)

SAMPLE_LIMIT = 5


def format_report(split: ReachabilitySplit) -> str:
    """Every bucket on its own line, so an empty one is a visible zero rather than an absence."""
    lines = [f"  zero-inbound modules (raw total): {split.total}"]
    for bucket in split.buckets:
        cut = " (sample capped)" if bucket.sample_truncated else ""
        lines.append(f"    {bucket.bucket:<22} {bucket.count:>6}{cut}")
        if bucket.sample:
            lines.append(f"      e.g. {', '.join(bucket.sample[:3])}")
    for bucket_id, reason in split.dropped:
        lines.append(f"    {bucket_id:<22} DROPPED — {reason}")
    return "\n".join(lines)


def check(split: ReachabilitySplit) -> list[str]:
    """The gate every repo holds, whatever its shape: the split loses and invents no file."""
    problems: list[str] = []
    counted = sum(bucket.count for bucket in split.buckets)
    if counted != split.total:
        problems.append(f"buckets sum to {counted}, raw total is {split.total}")
    rendered = {bucket.bucket for bucket in split.buckets} | {b for b, _ in split.dropped}
    if rendered != set(BUCKETS):
        problems.append(f"buckets neither rendered nor dropped: {sorted(set(BUCKETS) - rendered)}")
    if any(not reason for _, reason in split.dropped):
        problems.append("a dropped bucket carries no reason (AC5)")
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
            # No declarations passed: the pins carry no `.code-atlas.toml`, so this measures the
            # path signal alone — the weakest case, which is the one worth recording.
            split = classify_reachability(compute_metrics(nodes, edges), sample_limit=SAMPLE_LIMIT)
            print(format_report(split))
            problems = check(split)
            if problems:
                failures += 1
                print(f"  FAIL: {'; '.join(problems)}")
        except Exception as exc:  # noqa: BLE001 — report every repo even if one fails
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    if failures:
        print(f"\n{failures} repo(s) failed the reachability check")
        return 1
    print("\nall repos pass the reachability check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
