#!/usr/bin/env python3
"""Profile ``incremental_update`` phases against an on-disk repo (task 052).

Local-tier precedent (045): operator-supplied absolute ``--root``, reuse the existing index,
no copy / no rebuild. Report defaults **outside** CI-uploaded ``artifacts/`` so a private path
never lands in this repository.

Scenarios:
  (a) noop — empty changed set, tree left alone
  (b) one_edit — append a byte to one indexed source file, then restore + re-hash
  (c) pull_shaped — touch ``--pull-files`` indexed sources (default 100), then restore + re-hash

Example::

  python scripts/profile_incremental.py --root /abs/path/to/checkout
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.config import Config, ConfigError, load_config  # noqa: E402
from code_atlas.indexer import INCREMENTAL_PHASES, file_is_current, incremental_update  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402

PHASES = INCREMENTAL_PHASES

# Phases must sum to wall within this relative slack (timers exclude tiny glue).
WALL_TOLERANCE = 0.15
# Floor for the slack on a sub-second scenario. The glue no phase covers — adapter subprocess
# teardown, the store open, the profiler's two count snapshots — has a heavy tail on a contended
# host (p50 8 ms, p90 65 ms, max 115 ms at 0.4 CPU), so a floor at the steady-state cost reds CI.
WALL_FLOOR_SECONDS = 0.20
# Noop: resolve "dominates" when it is at least this share of wall (field hypothesis).
RESOLVE_DOMINANCE = 0.5

DEFAULT_REPORT = Path("/tmp/code-atlas-incremental-profile.json")
DEFAULT_PULL_FILES = 100


def bind_index(root: Path, db_path: Path | None) -> Config:
    """Load config for ``root`` and require an existing graph DB (045 local-tier)."""
    env = {k: v for k, v in os.environ.items() if k.startswith("CA_")}
    config = replace(load_config(root, env), root=root)
    if db_path is not None:
        config = replace(config, db_path=db_path)
    if not config.db_path.is_file():
        raise FileNotFoundError(
            f"no index at {config.db_path} — build it first, then re-run this profiler"
        )
    if not config.adapter_cmds:
        # Empty adapters + reconcile would delete every row — fail loud (R5.3 / R4.2).
        raise ConfigError(
            "no adapters configured for this root — set CA_<LANG>_CMD or "
            ".code-atlas.toml [adapter_cmd] before profiling (refusing to reconcile)"
        )
    return config


def _snapshot_counts(store: GraphStore) -> dict[str, int]:
    return dict(store.counts())


def _resolve_verdict(phases: dict[str, float], wall: float) -> dict[str, object]:
    """Confirm or refute the unscoped-resolve flat-fee hypothesis for this run."""
    resolve = phases["resolve"]
    share = (resolve / wall) if wall else 0.0
    if wall <= 0:
        verdict = "inconclusive"
        reason = "zero wall clock"
    elif share >= RESOLVE_DOMINANCE:
        verdict = "confirmed"
        reason = (
            f"resolve is {share:.0%} of wall (≥ {RESOLVE_DOMINANCE:.0%} dominance threshold)"
        )
    else:
        verdict = "refuted"
        reason = (
            f"resolve is {share:.0%} of wall (< {RESOLVE_DOMINANCE:.0%}); "
            "not the sole flat-fee explanation on this graph"
        )
    return {
        "resolve_seconds": resolve,
        "resolve_share_of_wall": round(share, 4),
        "dominance_threshold": RESOLVE_DOMINANCE,
        "verdict": verdict,
        "reason": reason,
    }


def _run_scenario(
    config: Config,
    *,
    name: str,
    changed: list[str],
) -> dict[str, Any]:
    times: dict[str, float] = {}
    wall_started = time.monotonic()
    with GraphStore(config.db_path) as store:
        before = _snapshot_counts(store)
        report = incremental_update(config, store, changed, phase_times=times)
        after = _snapshot_counts(store)
    wall = time.monotonic() - wall_started
    phases = {phase: round(times.get(phase, 0.0), 4) for phase in PHASES}
    phase_sum = sum(phases.values())
    return {
        "scenario": name,
        "changed_files": len(changed),
        "changed_sample": changed[:5],
        "wall_seconds": round(wall, 4),
        "phases": phases,
        "phase_sum_seconds": round(phase_sum, 4),
        "phase_sum_vs_wall": {
            "tolerance": WALL_TOLERANCE,
            "floor_seconds": WALL_FLOOR_SECONDS,
            "unattributed_seconds": round(wall - phase_sum, 4),
            "within_tolerance": abs(phase_sum - wall)
            <= max(WALL_TOLERANCE * wall, WALL_FLOOR_SECONDS),
        },
        "resolve_hypothesis": _resolve_verdict(phases, wall),
        "report": asdict(report),
        "counts_before": before,
        "counts_after": after,
        "counts_unchanged": before == after,
    }


def _indexed_sources(store: GraphStore, root: Path, limit: int) -> list[str]:
    paths = [p for p in store.file_paths() if (root / p).is_file()]
    return paths[:limit]


def _touch_restore(root: Path, rel: str) -> bytes:
    """Append one newline; return prior bytes for restore."""
    path = root / rel
    prior = path.read_bytes()
    path.write_bytes(prior + b"\n")
    return prior


def _resync(config: Config, changed: list[str]) -> None:
    """After restoring bytes, re-hash so the on-disk index matches the tree again."""
    if not changed:
        return
    with GraphStore(config.db_path) as store:
        incremental_update(config, store, changed)


def profile(
    root: Path,
    *,
    db_path: Path | None,
    pull_files: int,
) -> dict[str, Any]:
    config = bind_index(root, db_path)
    with GraphStore(config.db_path) as store:
        sources = _indexed_sources(store, root, max(pull_files, 1))
    if not sources:
        raise SystemExit(f"no on-disk indexed files under {root}")

    scenarios: list[dict[str, Any]] = []

    scenarios.append(_run_scenario(config, name="noop", changed=[]))

    one = sources[0]
    prior = _touch_restore(root, one)
    try:
        scenarios.append(_run_scenario(config, name="one_edit", changed=[one]))
    finally:
        (root / one).write_bytes(prior)
        _resync(config, [one])

    batch = sources[:pull_files]
    priors = {rel: _touch_restore(root, rel) for rel in batch}
    try:
        scenarios.append(
            _run_scenario(config, name="pull_shaped", changed=list(batch))
        )
    finally:
        for rel, blob in priors.items():
            (root / rel).write_bytes(blob)
        _resync(config, list(batch))

    noop = next(s for s in scenarios if s["scenario"] == "noop")
    pull = next(s for s in scenarios if s["scenario"] == "pull_shaped")
    return {
        "root": str(root),
        "db_path": str(config.db_path),
        "pull_files_requested": pull_files,
        "pull_files_used": len(batch),
        "phases": list(PHASES),
        "scenarios": scenarios,
        "summary": {
            "noop_resolve_verdict": noop["resolve_hypothesis"]["verdict"],
            "pull_shaped_wall_seconds": pull["wall_seconds"],
            "pull_shaped_changed_files": pull["changed_files"],
        },
    }


def assert_tree_matches_index(config: Config) -> None:
    """Every on-disk indexed path is hash-current after a profile run."""
    with GraphStore(config.db_path) as store:
        for path in store.file_paths():
            if (config.root / path).is_file():
                assert file_is_current(store, config.root, path), path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Absolute path to an already-indexed checkout (not copied into this repo).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Optional graph.db path (default: repo-resolved CA_DB_PATH / .code-atlas/graph.db).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"JSON report path (default {DEFAULT_REPORT}; keep outside this repository).",
    )
    parser.add_argument(
        "--pull-files",
        type=int,
        default=DEFAULT_PULL_FILES,
        help=f"How many indexed files to touch for scenario (c) (default {DEFAULT_PULL_FILES}).",
    )
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"--root is not a directory: {root}")
    if args.pull_files < 1:
        raise SystemExit("--pull-files must be >= 1")

    payload = profile(root, db_path=args.db, pull_files=args.pull_files)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(args.report),
                "summary": payload["summary"],
                "scenarios": [
                    {
                        "name": s["scenario"],
                        "wall_seconds": s["wall_seconds"],
                        "resolve_seconds": s["phases"]["resolve"],
                        "resolve_verdict": s["resolve_hypothesis"]["verdict"],
                        "changed_files": s["changed_files"],
                    }
                    for s in payload["scenarios"]
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
