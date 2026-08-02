#!/usr/bin/env python3
"""Opt-in cross-repo validation harness (task 018 / Plan §16 / R6.3).

Clones pinned public PHP samples (see ``cross_repo_samples.json``), runs ``full_build``,
and asserts crash-free + plausible counts. The private large monorepo stays operator-local
via ``CODE_ATLAS_SCALE_SAMPLE`` (optional; folds the 015 timing capture when set).

Not part of per-PR CI — use ``workflow_dispatch`` / weekly schedule, or run locally.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.config import load_config  # noqa: E402
from code_atlas.indexer import BuildReport, full_build  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402

_MANIFEST = Path(__file__).resolve().with_name("cross_repo_samples.json")
_DEFAULT_CACHE = _REPO / "artifacts" / "cross-repo-cache"
_DEFAULT_REPORT = _REPO / "artifacts" / "cross-repo-report.json"
_DEFAULT_PHP = shlex.join(
    ["php", str(_REPO / "adapters" / "php" / "index.php"), "--server"]
)


class PlausibleCountsError(AssertionError):
    """A2 / AC1 bar failed for one sample."""


def assert_plausible_counts(report: BuildReport, *, label: str = "sample") -> None:
    """Crash-free build already implied; enforce A2 measurable floors."""
    if report.files <= 0:
        raise PlausibleCountsError(f"{label}: files must be > 0, got {report.files}")
    if report.nodes <= 0:
        raise PlausibleCountsError(f"{label}: nodes must be > 0, got {report.nodes}")
    if report.edges < 0:
        raise PlausibleCountsError(f"{label}: edges must be >= 0, got {report.edges}")


def assert_parse_isolation(
    report: BuildReport, *, label: str = "sample", expect_failures: bool = False
) -> None:
    """A5: build completed (caller has a report); optional expect_failures for mini-repos."""
    if expect_failures and report.failed < 1:
        raise PlausibleCountsError(
            f"{label}: expected >=1 parse failure for isolation proof, got {report.failed}"
        )


def load_manifest(path: Path = _MANIFEST) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError(f"manifest has no samples: {path}")
    return samples


def _php_cmd() -> str:
    """Return ``CA_PHP_CMD`` with repo-relative adapter paths made absolute.

    ``LanguageAdapter`` runs with ``cwd=sample_root``, so a relative
    ``adapters/php/index.php`` from the code-atlas checkout would miss.
    """
    raw = os.environ.get("CA_PHP_CMD", "").strip() or _DEFAULT_PHP
    parts = shlex.split(raw)
    fixed: list[str] = []
    for part in parts:
        path = Path(part)
        if path.is_absolute():
            fixed.append(part)
            continue
        candidate = (_REPO / path).resolve()
        if candidate.is_file():
            fixed.append(str(candidate))
        else:
            fixed.append(part)
    return shlex.join(fixed)


def _ensure_checkout(sample: dict[str, Any], cache_root: Path) -> Path:
    """Fetch a pinned SHA into ``cache_root/<id>`` (shallow when possible)."""
    dest = cache_root / str(sample["id"])
    url = str(sample["url"])
    sha = str(sample["sha"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    git_base = ["git", "-c", "advice.detachedHead=false"]
    if (dest / ".git").is_dir():
        subprocess.run(
            [*git_base, "-C", str(dest), "fetch", "--depth", "1", "origin", sha],
            check=True,
        )
        subprocess.run(
            [*git_base, "-C", str(dest), "checkout", "--force", "FETCH_HEAD"],
            check=True,
        )
        return dest

    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run([*git_base, "init", str(dest)], check=True)
    subprocess.run(
        [*git_base, "-C", str(dest), "remote", "add", "origin", url],
        check=True,
    )
    subprocess.run(
        [*git_base, "-C", str(dest), "fetch", "--depth", "1", "origin", sha],
        check=True,
    )
    subprocess.run(
        [*git_base, "-C", str(dest), "checkout", "--force", "FETCH_HEAD"],
        check=True,
    )
    return dest


def index_root(root: Path, *, db_path: Path | None = None) -> BuildReport:
    """Run ``full_build`` against ``root`` using the host PHP adapter command."""
    db = db_path or (root / ".code-atlas" / "graph.db")
    env = {k: v for k, v in os.environ.items() if k.startswith("CA_")}
    # Always rewrite: sample cwd would break a relative adapters/php path.
    env["CA_PHP_CMD"] = _php_cmd()
    config = replace(load_config(root, env), db_path=db, root=root)
    with GraphStore(config.db_path) as store:
        return full_build(config, store)


def _report_row(
    *,
    sample_id: str,
    kind: str,
    root: Path,
    report: BuildReport,
    elapsed: float,
) -> dict[str, Any]:
    return {
        "id": sample_id,
        "kind": kind,
        "root": str(root),
        "elapsed_seconds": round(elapsed, 3),
        "files": report.files,
        "parsed": report.parsed,
        "failed": report.failed,
        "nodes": report.nodes,
        "edges": report.edges,
        "ok": True,
    }


def run_public_samples(
    *,
    cache_root: Path,
    skip_clone: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sample in load_manifest():
        sid = str(sample["id"])
        kind = str(sample["kind"])
        if skip_clone:
            root = cache_root / sid
            if not root.is_dir():
                raise FileNotFoundError(
                    f"--skip-clone set but cache missing for {sid}: {root}"
                )
        else:
            root = _ensure_checkout(sample, cache_root)
        started = time.perf_counter()
        report = index_root(root)
        elapsed = time.perf_counter() - started
        assert_plausible_counts(report, label=sid)
        assert_parse_isolation(report, label=sid, expect_failures=False)
        rows.append(
            _report_row(
                sample_id=sid,
                kind=kind,
                root=root,
                report=report,
                elapsed=elapsed,
            )
        )
    return rows


def run_scale_sample_if_configured() -> dict[str, Any] | None:
    """A4: when ``CODE_ATLAS_SCALE_SAMPLE`` is set, capture timing via scale script semantics."""
    sample = os.environ.get("CODE_ATLAS_SCALE_SAMPLE", "").strip()
    if not sample:
        return {
            "skipped": True,
            "reason": "CODE_ATLAS_SCALE_SAMPLE unset — public CI / local skip is OK (A4)",
        }
    root = Path(sample).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"CODE_ATLAS_SCALE_SAMPLE is not a directory: {root}")

    # Prefer the dedicated 015 script so the JSON shape stays one artifact family.
    scale_script = _REPO / "scripts" / "scale_full_build.py"
    proc = subprocess.run(
        [sys.executable, str(scale_script)],
        cwd=str(_REPO),
        env=os.environ.copy(),
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"scale_full_build failed ({proc.returncode}): {proc.stderr or proc.stdout}"
        )
    return {
        "skipped": False,
        "root": str(root),
        "scale_stdout": proc.stdout.strip(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(
            os.environ.get("CODE_ATLAS_CROSS_REPO_CACHE", str(_DEFAULT_CACHE))
        ),
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=Path(
            os.environ.get("CODE_ATLAS_CROSS_REPO_REPORT", str(_DEFAULT_REPORT))
        ),
    )
    parser.add_argument(
        "--skip-clone",
        action="store_true",
        help="Use existing cache checkouts only (no network).",
    )
    parser.add_argument(
        "--public-only",
        action="store_true",
        help="Skip the optional CODE_ATLAS_SCALE_SAMPLE timing fold-in.",
    )
    args = parser.parse_args(argv)

    cache_root = args.cache_dir.expanduser()
    if not cache_root.is_absolute():
        cache_root = (_REPO / cache_root).resolve()
    else:
        cache_root = cache_root.resolve()

    public_rows = run_public_samples(cache_root=cache_root, skip_clone=args.skip_clone)
    scale_row: dict[str, Any] | None
    if args.public_only:
        scale_row = {
            "skipped": True,
            "reason": "--public-only (GHA public job)",
        }
    else:
        scale_row = run_scale_sample_if_configured()

    out = args.report_out.expanduser()
    if not out.is_absolute():
        out = (_REPO / out).resolve()
    else:
        out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "public_samples": public_rows,
        "scale_sample": scale_row,
        "note": (
            "Task 018 / R6.3. Pass = each public sample crash-free with files>0, "
            "nodes>0, edges>=0. Large/private sample is optional (A4)."
        ),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), "public_ok": len(public_rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
