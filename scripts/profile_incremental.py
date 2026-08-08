#!/usr/bin/env python3
"""Profile ``incremental_update`` phases against an on-disk repo (task 052).

Local-tier precedent (045): operator-supplied absolute ``--root``, reuse the existing index,
no copy / no rebuild. Report defaults **outside** CI-uploaded ``artifacts/`` so a private path
never lands in this repository.

Scenarios:
  (a) noop — empty changed set, tree left alone
  (b) one_edit — append a byte to one indexed source file, then restore
  (c) pull_shaped — touch ``--pull-files`` indexed sources (default 100), then restore

Example::

  python scripts/profile_incremental.py --root /abs/path/to/checkout
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.config import load_config  # noqa: E402
from code_atlas.indexer import INCREMENTAL_PHASES, incremental_update  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402

PHASES = INCREMENTAL_PHASES

# Phases must sum to wall within this relative slack (timers exclude tiny glue).
WALL_TOLERANCE = 0.15

DEFAULT_REPORT = Path("/tmp/code-atlas-incremental-profile.json")
DEFAULT_PULL_FILES = 100


def bind_index(root: Path, db_path: Path | None) -> object:
    """Load config for ``root`` and require an existing graph DB (045 local-tier)."""
    env = {k: v for k, v in os.environ.items() if k.startswith("CA_")}
    from dataclasses import replace

    config = replace(load_config(root, env), root=root)
    if db_path is not None:
        config = replace(config, db_path=db_path)
    if not config.db_path.is_file():
        raise FileNotFoundError(
            f"no index at {config.db_path} — build it first, then re-run this profiler"
        )
    return config


def _snapshot_counts(store: GraphStore) -> dict[str, int]:
    return dict(store.counts())


def _run_scenario(
    config: object,
    *,
    name: str,
    changed: list[str],
) -> dict[str, object]:
    times: dict[str, float] = {}
    wall_started = time.monotonic()
    with GraphStore(config.db_path) as store:  # type: ignore[attr-defined]
        before = _snapshot_counts(store)
        report = incremental_update(config, store, changed, phase_times=times)  # type: ignore[arg-type]
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
            "within_tolerance": abs(phase_sum - wall) <= max(WALL_TOLERANCE * wall, 0.05),
        },
        "resolve_hypothesis": {
            "resolve_seconds": phases["resolve"],
            "resolve_share_of_wall": round(phases["resolve"] / wall, 4) if wall else None,
            # Confirmed when resolve dominates the wall on a repo-sized noop; fixture runs refute.
            "note": "compare resolve_seconds to wall; field hypothesis = unscoped resolve",
        },
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


def profile(
    root: Path,
    *,
    db_path: Path | None,
    pull_files: int,
) -> dict[str, object]:
    config = bind_index(root, db_path)
    with GraphStore(config.db_path) as store:  # type: ignore[attr-defined]
        sources = _indexed_sources(store, root, max(pull_files, 1))
    if not sources:
        raise SystemExit(f"no on-disk indexed files under {root}")

    scenarios: list[dict[str, object]] = []

    # (a) true no-op
    scenarios.append(_run_scenario(config, name="noop", changed=[]))

    # (b) one source file edited
    one = sources[0]
    prior = _touch_restore(root, one)
    try:
        scenarios.append(_run_scenario(config, name="one_edit", changed=[one]))
    finally:
        (root / one).write_bytes(prior)

    # (c) pull-shaped: touch N files
    batch = sources[:pull_files]
    priors = {rel: _touch_restore(root, rel) for rel in batch}
    try:
        scenarios.append(
            _run_scenario(config, name="pull_shaped", changed=list(batch))
        )
    finally:
        for rel, blob in priors.items():
            (root / rel).write_bytes(blob)

    return {
        "root": str(root),
        "db_path": str(config.db_path),  # type: ignore[attr-defined]
        "pull_files_requested": pull_files,
        "pull_files_used": len(batch),
        "phases": list(PHASES),
        "scenarios": scenarios,
    }


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
    print(json.dumps({"report": str(args.report), "scenarios": [
        {
            "name": s["scenario"],
            "wall_seconds": s["wall_seconds"],
            "resolve_seconds": s["phases"]["resolve"],  # type: ignore[index]
            "changed_files": s["changed_files"],
        }
        for s in payload["scenarios"]  # type: ignore[index]
    ]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
