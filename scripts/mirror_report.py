#!/usr/bin/env python3
"""Print + CHECK mirror-subtree detection for the pinned public repos — AC3/AC4's evidence.

AC4 requires the threshold be justified by measurement rather than asserted, so this prints the
**highest-overlap sibling pair regardless of the gates** alongside what the gates actually accept.
That is the number that chose the constants: one pin scores a perfect overlap on a single shared
file, which is why the detector gates on the shared COUNT as well as the fraction.

**The expected answer on all three pins is ZERO accepted pairs** — none mirrors a subtree, and AC3
asks precisely for that, so the detector is not manufacturing structure. Not part of per-PR CI —
run locally or in Docker (needs php + network):

    scripts/docker-test.sh python scripts/mirror_report.py
"""

from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.onboarding.mirrors import (  # noqa: E402
    MIN_OVERLAP,
    MIN_SHARED_PATHS,
    MirrorReport,
    find_mirror_subtrees,
    resolve_counterpart,
)
from code_atlas.store import GraphStore  # noqa: E402
from scripts.cross_repo_validate import (  # noqa: E402
    checkout_pinned,
    index_root,
    load_manifest,
)

SAMPLE_LIMIT = 5


def best_ungated_pair(paths: list[str]) -> tuple[float, int, str, str] | None:
    """The highest-overlap sibling pair with NO gate applied — AC4's justifying measurement."""
    relative: dict[str, set[str]] = {}
    children: dict[str, set[str]] = {}
    for path in paths:
        segments = path.split("/")
        for depth in range(1, len(segments)):
            relative.setdefault("/".join(segments[:depth]), set()).add(
                "/".join(segments[depth:])
            )
        for depth, segment in enumerate(segments[:-1]):
            children.setdefault("/".join(segments[:depth]), set()).add(segment)
    best: tuple[float, int, str, str] | None = None
    for parent, names in children.items():
        for left_name, right_name in combinations(sorted(names), 2):
            left = f"{parent}/{left_name}" if parent else left_name
            right = f"{parent}/{right_name}" if parent else right_name
            left_set, right_set = relative.get(left, set()), relative.get(right, set())
            union = left_set | right_set
            if not union:
                continue
            shared = len(left_set & right_set)
            if not shared:
                continue
            row = (shared / len(union), shared, left, right)
            if best is None or row > best:
                best = row
    return best


def format_report(report: MirrorReport, paths: list[str]) -> str:
    """Accepted pairs, plus the best pair the gates rejected and why."""
    lines = [f"  accepted pairs: {len(report.pairs)}"]
    for pair in report.pairs:
        lines.append(
            f"    {pair.left} <-> {pair.right}  shared={pair.shared} "
            f"overlap={pair.overlap} only={pair.left_only}/{pair.right_only}"
        )
        answer = resolve_counterpart(f"{pair.left}/{pair.sample[0]}", report.pairs, set(paths))
        lines.append(f"      lookup {pair.sample[0]} -> {answer.status} {answer.path}")
    best = best_ungated_pair(paths)
    if best is None:
        lines.append("    best ungated sibling pair: none shares any relative path")
    else:
        overlap, shared, left, right = best
        why = []
        if shared < MIN_SHARED_PATHS:
            why.append(f"shared {shared} < {MIN_SHARED_PATHS}")
        if overlap < MIN_OVERLAP:
            why.append(f"overlap {overlap:.3f} < {MIN_OVERLAP}")
        verdict = "; ".join(why) if why else "clears both gates"
        lines.append(
            f"    best ungated sibling pair: {left} <-> {right} "
            f"overlap={overlap:.3f} shared={shared}  [{verdict}]"
        )
    return "\n".join(lines)


def check(report: MirrorReport, paths: list[str]) -> list[str]:
    """Invariants that hold on any repo, whatever its shape."""
    problems: list[str] = []
    if not report.caveat:
        problems.append("report carries no path-not-content caveat (AC5)")
    for pair in report.pairs:
        if pair.shared < MIN_SHARED_PATHS or pair.overlap < MIN_OVERLAP:
            problems.append(f"{pair.left}<->{pair.right} accepted below a gate")
        if pair.left == pair.right:
            problems.append(f"{pair.left} paired with itself")
        for sample in pair.sample:
            answer = resolve_counterpart(f"{pair.left}/{sample}", report.pairs, set(paths))
            if answer.status != "counterpart":
                problems.append(f"shared path {sample} did not resolve a counterpart")
    outside = resolve_counterpart("definitely/not/indexed.xyz", report.pairs, set(paths))
    if outside.status != "outside_mirror":
        problems.append("a path outside every pair did not return a clean negative (AC2)")
    return problems


def main() -> int:
    cache_root = _REPO / "artifacts" / "cross-repo-cache"
    failures = 0
    print(f"gates: MIN_SHARED_PATHS={MIN_SHARED_PATHS}  MIN_OVERLAP={MIN_OVERLAP}")
    for sample in load_manifest():
        sid = str(sample["id"])
        print(f"\n### {sid} @ {str(sample['sha'])[:7]}")
        try:
            root = checkout_pinned(sample, cache_root)
            language = str(sample.get("language", "php"))
            index_root(root, language=language)
            with GraphStore(root / ".code-atlas" / "graph.db") as store:
                paths = list(store.file_paths())
            report = find_mirror_subtrees(paths, sample_limit=SAMPLE_LIMIT)
            print(f"  {len(paths)} indexed paths")
            print(format_report(report, paths))
            problems = check(report, paths)
            if problems:
                failures += 1
                print(f"  FAIL: {'; '.join(problems)}")
        except Exception as exc:  # noqa: BLE001 — report every repo even if one fails
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    if failures:
        print(f"\n{failures} repo(s) failed the mirror check")
        return 1
    print("\nall repos pass the mirror check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
