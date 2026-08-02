#!/usr/bin/env python3
"""Opt-in full-build timing for an out-of-tree PHP sample (task 015 / Plan §6.1).

Not part of per-PR CI — the ~112k sample is private and too slow. Point
``CODE_ATLAS_SCALE_SAMPLE`` at a checkout, run this script, and keep the JSON
artifact (default ``artifacts/scale-full-build.json``).

Pass = build completes without OOM on the documented host. Timing is a baseline
capture, not an SLA gate.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from dataclasses import replace
from pathlib import Path

# Allow `python scripts/scale_full_build.py` from a checkout without install.
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.config import load_config  # noqa: E402
from code_atlas.indexer import full_build  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402


def main() -> int:
    sample = os.environ.get("CODE_ATLAS_SCALE_SAMPLE", "").strip()
    if not sample:
        print(
            "CODE_ATLAS_SCALE_SAMPLE is unset — point it at an out-of-tree PHP checkout.",
            file=sys.stderr,
        )
        return 2
    root = Path(sample).expanduser().resolve()
    if not root.is_dir():
        print(f"sample root is not a directory: {root}", file=sys.stderr)
        return 2

    out = Path(
        os.environ.get("CODE_ATLAS_SCALE_TIMING_OUT", "artifacts/scale-full-build.json")
    ).expanduser()
    if not out.is_absolute():
        out = (_REPO / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    db = Path(os.environ.get("CODE_ATLAS_SCALE_DB", str(root / ".code-atlas" / "graph.db")))
    env = {k: v for k, v in os.environ.items() if k.startswith("CA_")}
    config = replace(load_config(root, env), db_path=db, root=root)

    started = time.perf_counter()
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    elapsed = time.perf_counter() - started

    payload = {
        "sample_root": str(root),
        "db_path": str(config.db_path),
        "elapsed_seconds": round(elapsed, 3),
        "files": report.files,
        "parsed": report.parsed,
        "failed": report.failed,
        "removed": report.removed,
        "nodes": report.nodes,
        "edges": report.edges,
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "note": (
            "Baseline capture (015 A2/A3). Pass = completed without OOM on this host; "
            "no numeric SLA this ticket."
        ),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), "elapsed_seconds": payload["elapsed_seconds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
