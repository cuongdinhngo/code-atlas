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
# Public pins: allow a little PHP-version drift, but catch mass-parse regressions.
_PUBLIC_MAX_FAILURE_RATIO = 0.02


class PlausibleCountsError(AssertionError):
    """A2 / AC1 bar failed for one sample."""


def assert_plausible_counts(
    report: BuildReport,
    *,
    label: str = "sample",
    min_files: int = 1,
    min_nodes: int = 1,
    min_edges: int = 1,
) -> None:
    """Enforce measurable floors (per-sample mins from the pinned manifest when set)."""
    if report.files < min_files:
        raise PlausibleCountsError(
            f"{label}: files must be >= {min_files}, got {report.files}"
        )
    if report.nodes < min_nodes:
        raise PlausibleCountsError(
            f"{label}: nodes must be >= {min_nodes}, got {report.nodes}"
        )
    if report.edges < min_edges:
        raise PlausibleCountsError(
            f"{label}: edges must be >= {min_edges}, got {report.edges}"
        )


def assert_parse_isolation(
    report: BuildReport,
    *,
    label: str = "sample",
    expect_failures: bool = False,
    max_failure_ratio: float | None = None,
) -> None:
    """Gate parse-failure volume; optionally require at least one failure (mini-repos)."""
    if expect_failures and report.failed < 1:
        raise PlausibleCountsError(
            f"{label}: expected >=1 parse failure for isolation proof, got {report.failed}"
        )
    if max_failure_ratio is None:
        return
    if report.files <= 0:
        raise PlausibleCountsError(
            f"{label}: cannot compute failure ratio with files={report.files}"
        )
    ratio = report.failed / report.files
    if ratio > max_failure_ratio:
        raise PlausibleCountsError(
            f"{label}: parse failure ratio {ratio:.3f} "
            f"({report.failed}/{report.files}) exceeds max {max_failure_ratio}"
        )


def load_manifest(path: Path = _MANIFEST) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError(f"manifest has no samples: {path}")
    return samples


def resolve_php_cmd() -> str:
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


def checkout_pinned(sample: dict[str, Any], cache_root: Path) -> Path:
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
    env["CA_PHP_CMD"] = resolve_php_cmd()
    config = replace(load_config(root, env), db_path=db, root=root)
    with GraphStore(config.db_path) as store:
        return full_build(config, store)


def _ok_row(
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


def _fail_row(
    *,
    sample_id: str,
    kind: str,
    root: Path | None,
    error: BaseException,
    elapsed: float,
) -> dict[str, Any]:
    return {
        "id": sample_id,
        "kind": kind,
        "root": str(root) if root is not None else None,
        "elapsed_seconds": round(elapsed, 3),
        "ok": False,
        "error": f"{type(error).__name__}: {error}",
    }


def run_public_samples(
    *,
    cache_root: Path,
    skip_clone: bool = False,
) -> list[dict[str, Any]]:
    """Index each pinned sample; catch per row so a report can still be written."""
    rows: list[dict[str, Any]] = []
    for sample in load_manifest():
        sid = str(sample["id"])
        kind = str(sample["kind"])
        root: Path | None = None
        started = time.perf_counter()
        try:
            if skip_clone:
                root = cache_root / sid
                if not root.is_dir():
                    raise FileNotFoundError(
                        f"--skip-clone set but cache missing for {sid}: {root}"
                    )
            else:
                root = checkout_pinned(sample, cache_root)
            report = index_root(root)
            elapsed = time.perf_counter() - started
            assert_plausible_counts(
                report,
                label=sid,
                min_files=int(sample.get("min_files", 1)),
                min_nodes=int(sample.get("min_nodes", 1)),
                min_edges=int(sample.get("min_edges", 1)),
            )
            assert_parse_isolation(
                report,
                label=sid,
                max_failure_ratio=_PUBLIC_MAX_FAILURE_RATIO,
            )
            rows.append(
                _ok_row(
                    sample_id=sid,
                    kind=kind,
                    root=root,
                    report=report,
                    elapsed=elapsed,
                )
            )
        except Exception as exc:  # noqa: BLE001 — record every sample failure in the report
            elapsed = time.perf_counter() - started
            rows.append(
                _fail_row(
                    sample_id=sid,
                    kind=kind,
                    root=root,
                    error=exc,
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


def _write_report(
    out: Path,
    *,
    public_rows: list[dict[str, Any]],
    scale_row: dict[str, Any] | None,
) -> None:
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
            "Task 018 / R6.3. Pass = crash-free + per-sample min_files/nodes/edges "
            f"+ parse failure ratio <= {_PUBLIC_MAX_FAILURE_RATIO}. "
            "Large/private sample is optional (A4)."
        ),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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

    out = args.report_out.expanduser()
    if not out.is_absolute():
        out = (_REPO / out).resolve()
    else:
        out = out.resolve()

    public_rows = run_public_samples(cache_root=cache_root, skip_clone=args.skip_clone)
    scale_row: dict[str, Any] | None
    scale_failed = False
    if args.public_only:
        scale_row = {
            "skipped": True,
            "reason": "--public-only (GHA public job)",
        }
    else:
        try:
            scale_row = run_scale_sample_if_configured()
        except Exception as exc:  # noqa: BLE001 — still write the public report
            scale_failed = True
            scale_row = {
                "skipped": False,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    _write_report(out, public_rows=public_rows, scale_row=scale_row)
    public_ok = sum(1 for row in public_rows if row.get("ok"))
    public_failed = len(public_rows) - public_ok
    print(
        json.dumps(
            {
                "wrote": str(out),
                "public_ok": public_ok,
                "public_failed": public_failed,
            }
        )
    )
    if public_failed or scale_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
