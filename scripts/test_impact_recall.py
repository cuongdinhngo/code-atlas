#!/usr/bin/env python3
"""Task 309 — candidate-test recall over real upstream changes (R6.3's committed reporter).

Runs 308's UNCHANGED reporter (``code_atlas.candidate_tests``) over every scenario in
``test_impact_corpus.json``, compares its candidates against the upstream authors' own test
edits, splits every miss by cause, and prints the verdict the pre-registered bar dictates.

Measurement only: this file selects no tests, writes no runner arguments and gates nothing.
The project's normal full suite remains authoritative.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.candidate_tests import (  # noqa: E402
    FULL_SUITE_STATEMENT,
    UNMEASURED_TRUNCATED,
    assert_no_selective_language,
    build_candidate_test_report,
)
from code_atlas.config import load_config  # noqa: E402
from code_atlas.contract import CALLER_KINDS, CONTRACT_VERSION  # noqa: E402
from code_atlas.indexer import indexable  # noqa: E402
from code_atlas.store import INDEXED_SUFFIXES_KEY, GraphStore  # noqa: E402
from code_atlas.symbol_role import path_indicates_test  # noqa: E402
from scripts.cross_repo_validate import index_root  # noqa: E402

_CORPUS = Path(__file__).resolve().with_name("test_impact_corpus.json")
_DEFAULT_CACHE = _REPO / "artifacts" / "309-corpus-cache"
_DEFAULT_OUT = _REPO / "artifacts" / "309-test-impact-recall.json"
_RELATION_KINDS: tuple[str, ...] = (*CALLER_KINDS, "REFERENCES", "IMPORTS")

# The pre-registered bar. Authored and committed BEFORE the first counted run; the verdict is read
# off these numbers, never chosen after seeing them (309 AC1, AC5).
BAR = {
    "min_scenarios": 12,
    "min_repos": 3,
    "min_languages": 2,
    "promote_recall": 0.90,
    "retain_recall": 0.60,
    "metric": "micro-averaged recall = matched labelled test files / all labelled test files",
}

CAUSE_STALE_INDEX = "stale_or_incomplete_index"
CAUSE_TEST_ROLE = "missing_test_role_classification"
CAUSE_TRAVERSAL = "traversal_or_page_bound"
CAUSE_REPORTER = "reporter_defect"
CAUSE_DYNAMIC = "unmodelled_dynamic_relationship"
CAUSE_RUNNER_ONLY = "runner_only_discovery"
CAUSE_UNCLASSIFIED = "unclassified"

CAUSES: tuple[str, ...] = (
    CAUSE_STALE_INDEX,
    CAUSE_TEST_ROLE,
    CAUSE_TRAVERSAL,
    CAUSE_REPORTER,
    CAUSE_DYNAMIC,
    CAUSE_RUNNER_ONLY,
    CAUSE_UNCLASSIFIED,
)

VERDICT_INSUFFICIENT = "insufficient_evidence"
VERDICT_RETAINED = "report_only_retained"
VERDICT_ELIGIBLE = "eligible_for_opt_in_selective_run_ticket"


class CorpusDriftError(RuntimeError):
    """A committed label no longer matches the commit it claims to describe."""


# --------------------------------------------------------------------------- corpus


def load_corpus(path: Path = _CORPUS) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("scenarios"):
        raise ValueError(f"corpus has no scenarios: {path}")
    return data


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return done.stdout


def checkout_scenario(scenario: dict[str, Any], cache_root: Path) -> Path:
    """Fetch head AND its parent — a scenario is a pair of revisions, not one pin."""
    dest = cache_root / str(scenario["sample_id"])
    head = str(scenario["head"])
    if not (dest / ".git").is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(dest)], check=True)
        _git(dest, "remote", "add", "origin", str(scenario["url"]))
    _git(dest, "fetch", "-q", "--depth", "2", "origin", head)
    _git(dest, "-c", "advice.detachedHead=false", "checkout", "-q", "--force", head)
    return dest


def verify_labels(scenario: dict[str, Any], root: Path) -> None:
    """Re-derive both path lists from git; a drifted committed label is a refusal, not a warning."""
    base, head = str(scenario["base"]), str(scenario["head"])
    names = [
        name
        for name in _git(root, "diff", "--name-only", "--diff-filter=M", base, head).splitlines()
        if name
    ]
    suffixes = _LANG_SUFFIXES[str(scenario["language"])]
    prod = sorted(n for n in names if n.endswith(suffixes) and not path_indicates_test(n))
    tests = sorted(n for n in names if n.endswith(suffixes) and path_indicates_test(n))
    if prod != sorted(scenario["changed_production_paths"]):
        raise CorpusDriftError(f"{scenario['id']}: changed_production_paths no longer match {head}")
    if tests != sorted(scenario["expected_test_files"]):
        raise CorpusDriftError(f"{scenario['id']}: expected_test_files no longer match {head}")


_LANG_SUFFIXES: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "typescript": (".ts", ".js", ".mjs", ".cjs"),
    "php": (".php",),
}


# --------------------------------------------------------------------------- cause split


def _files_targeting(store: GraphStore, qnames: list[str]) -> set[str]:
    return set(store.file_paths_targeting(qnames))


def _reach_depth(
    store: GraphStore, seeds: list[str], targets: set[str], *, max_depth: int
) -> dict[str, int]:
    """File-level reverse BFS from the seed qnames; first depth at which each target appears."""
    found: dict[str, int] = {}
    frontier = list(seeds)
    seen_files: set[str] = set()
    for depth in range(1, max_depth + 1):
        if not frontier:
            break
        files = _files_targeting(store, frontier) - seen_files
        seen_files |= files
        for path in files & targets:
            found.setdefault(path, depth)
        frontier = list(store.qnames_in_files(sorted(files)))
    return found


def _as_int_flag(value: object) -> int:
    """``is_test`` reaches here as an int, a digit string or nothing — same read as 308's."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return 0


def _is_classified_test(store: GraphStore, path: str) -> bool:
    if path_indicates_test(path):
        return True
    rows = store.nodes_by_file(path, limit=200)
    return any(_as_int_flag(row.get("is_test")) for row in rows)


def _has_unresolved_seed_site(store: GraphStore, path: str, bare_names: set[str]) -> bool:
    for name in sorted(bare_names):
        for row in store.unresolved_caller_sites(name, kinds=list(CALLER_KINDS)):
            if str(row.get("file_path") or "") == path:
                return True
    return False


def _has_outbound_edges(store: GraphStore, path: str) -> bool:
    for row in store.nodes_by_file(path, limit=200):
        qname = str(row.get("qualified_name") or "")
        if qname and store.count_edges_by_source(qname, kinds=list(_RELATION_KINDS)):
            return True
    return False


def classify_miss(
    store: GraphStore,
    path: str,
    *,
    seeds: list[str],
    indexed_files: set[str],
    direct: set[str],
    depths: dict[str, int],
    truncated: bool,
) -> str:
    """Exactly one cause per miss — the totals reconcile with the miss count by construction."""
    if path not in indexed_files or not store.nodes_by_file(path, limit=1):
        return CAUSE_STALE_INDEX
    if path in direct:
        if not _is_classified_test(store, path):
            return CAUSE_TEST_ROLE
        return CAUSE_TRAVERSAL if truncated else CAUSE_REPORTER
    if depths.get(path, 0) > 1:
        return CAUSE_TRAVERSAL
    bare = {qname.rsplit("\\", 1)[-1].rsplit(".", 1)[-1] for qname in seeds}
    if _has_unresolved_seed_site(store, path, bare):
        return CAUSE_DYNAMIC
    if not _has_outbound_edges(store, path):
        return CAUSE_RUNNER_ONLY
    return CAUSE_UNCLASSIFIED


# --------------------------------------------------------------------------- one scenario


def measure_scenario(
    scenario: dict[str, Any], cache_root: Path, *, max_depth: int
) -> dict[str, Any]:
    started = time.time()
    root = checkout_scenario(scenario, cache_root)
    verify_labels(scenario, root)
    build = index_root(root, language=str(scenario["language"]))
    config = replace(load_config(root), root=root, db_path=root / ".code-atlas" / "graph.db")

    with GraphStore(config.db_path) as store:
        raw = store.get_meta(INDEXED_SUFFIXES_KEY) or ""
    suffixes = tuple(part for part in raw.split(",") if part)
    declared = [str(p) for p in scenario["changed_production_paths"]]
    changed_indexed = list(indexable(declared, root, suffixes)) if suffixes else []
    unindexed = sorted(set(declared) - set(changed_indexed))

    report = build_candidate_test_report(
        config, changed_indexed=changed_indexed, dirty_unindexed=unindexed
    )
    candidates = {row.test_path for row in report.candidates}
    expected = sorted(str(p) for p in scenario["expected_test_files"])
    matched = sorted(p for p in expected if p in candidates)
    missed = [p for p in expected if p not in candidates]

    causes: dict[str, str] = {}
    details: dict[str, dict[str, object]] = {}
    if missed:
        seeds = list(report.changed_production_qnames)
        with GraphStore(config.db_path) as store:
            indexed_files = set(store.file_paths())
            direct = _files_targeting(store, seeds) if seeds else set()
            depths = (
                _reach_depth(store, seeds, set(missed), max_depth=max_depth)
                if seeds and max_depth > 1
                else {}
            )
            truncated = UNMEASURED_TRUNCATED in report.unmeasured
            for path in missed:
                causes[path] = classify_miss(
                    store,
                    path,
                    seeds=seeds,
                    indexed_files=indexed_files,
                    direct=direct,
                    depths=depths,
                    truncated=truncated,
                )
                details[path] = {
                    "inbound_depth": 1 if path in direct else depths.get(path),
                    "run_truncated": truncated,
                    "indexed": path in indexed_files,
                }

    return {
        "id": scenario["id"],
        "sample_id": scenario["sample_id"],
        "language": scenario["language"],
        "base": scenario["base"],
        "head": scenario["head"],
        "index": {"files": build.files, "nodes": build.nodes, "edges": build.edges,
                  "failed": build.failed},
        "changed_production_paths": declared,
        "changed_indexed": changed_indexed,
        "unindexed_production_paths": unindexed,
        "seeds": len(report.changed_production_qnames),
        "candidate_paths": sorted(candidates),
        "expected_test_files": expected,
        "matched": matched,
        "missed": missed,
        "miss_causes": causes,
        "miss_detail": details,
        "unmeasured": list(report.unmeasured),
        "recall": (len(matched) / len(expected)) if expected else None,
        "elapsed_s": round(time.time() - started, 1),
    }


# --------------------------------------------------------------------------- aggregate


def verdict_for(rows: list[dict[str, Any]], bar: dict[str, Any]) -> tuple[str, float, str]:
    """Read the verdict off the pre-registered bar — never off the numbers once they are known."""
    labelled = sum(len(row["expected_test_files"]) for row in rows)
    matched = sum(len(row["matched"]) for row in rows)
    recall = (matched / labelled) if labelled else 0.0
    repos = len({row["sample_id"] for row in rows})
    languages = len({row["language"] for row in rows})
    if (
        len(rows) < bar["min_scenarios"]
        or repos < bar["min_repos"]
        or languages < bar["min_languages"]
    ):
        return (
            VERDICT_INSUFFICIENT,
            recall,
            f"corpus floor not met: {len(rows)} scenarios / {repos} repos / {languages} languages "
            f"against {bar['min_scenarios']} / {bar['min_repos']} / {bar['min_languages']}",
        )
    if recall >= bar["promote_recall"]:
        return VERDICT_ELIGIBLE, recall, f"recall {recall:.3f} >= {bar['promote_recall']}"
    if recall >= bar["retain_recall"]:
        return VERDICT_RETAINED, recall, f"recall {recall:.3f} >= {bar['retain_recall']}"
    return (
        VERDICT_INSUFFICIENT,
        recall,
        f"recall {recall:.3f} < {bar['retain_recall']}",
    )


def aggregate(rows: list[dict[str, Any]], bar: dict[str, Any]) -> dict[str, Any]:
    labelled = sum(len(row["expected_test_files"]) for row in rows)
    matched = sum(len(row["matched"]) for row in rows)
    missed = labelled - matched
    counts = dict.fromkeys(CAUSES, 0)
    for row in rows:
        for cause in row["miss_causes"].values():
            counts[cause] += 1
    if sum(counts.values()) != missed:
        raise AssertionError(
            f"cause totals {sum(counts.values())} do not reconcile with {missed} misses"
        )
    name, recall, reason = verdict_for(rows, bar)
    per_scenario = [row["recall"] for row in rows if row["recall"] is not None]
    return {
        "scenarios": len(rows),
        "repos": sorted({row["sample_id"] for row in rows}),
        "languages": sorted({row["language"] for row in rows}),
        "labelled_test_files": labelled,
        "matched": matched,
        "missed": missed,
        "recall_micro": round(recall, 4),
        "recall_macro": round(sum(per_scenario) / len(per_scenario), 4) if per_scenario else None,
        "precision": None,
        "precision_not_computed_because": (
            "the labels are a commit's own test edits, never the exhaustive set of tests that "
            "exercise it, so an unlabelled candidate is not a false positive (309 scope item 3)"
        ),
        "miss_causes": counts,
        "verdict": name,
        "verdict_reason": reason,
        "statement": FULL_SUITE_STATEMENT,
    }


def provenance(corpus_path: Path) -> dict[str, Any]:
    head = subprocess.run(
        ["git", "-C", str(_REPO), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    return {
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "code_atlas_commit": head,
        "contract_version": CONTRACT_VERSION,
        "corpus": corpus_path.name,
    }


def render_text(payload: dict[str, Any]) -> str:
    agg = payload["aggregate"]
    lines = [
        "309 test-impact recall",
        f"statement: {agg['statement']}",
        f"provenance: {payload['provenance']['code_atlas_commit'][:12]} "
        f"contract v{payload['provenance']['contract_version']} "
        f"python {payload['provenance']['python']} host {payload['provenance']['host']}",
        f"bar: promote >= {payload['bar']['promote_recall']} · "
        f"retain >= {payload['bar']['retain_recall']} · "
        f"floor {payload['bar']['min_scenarios']} scenarios / {payload['bar']['min_repos']} repos "
        f"/ {payload['bar']['min_languages']} languages",
        "",
    ]
    for row in payload["scenarios"]:
        got = "-" if row["recall"] is None else f"{row['recall']:.2f}"
        lines.append(
            f"  {row['id']:<28} {row['language']:<11} "
            f"{len(row['matched'])}/{len(row['expected_test_files'])} recall {got}"
        )
        for path, cause in sorted(row["miss_causes"].items()):
            depth = row.get("miss_detail", {}).get(path, {}).get("inbound_depth")
            reach = "unreached" if depth is None else f"inbound depth {depth}"
            lines.append(f"      MISS {path} -> {cause} ({reach})")
    lines += [
        "",
        f"scenarios: {agg['scenarios']} over {len(agg['repos'])} repos, "
        f"{len(agg['languages'])} languages",
        f"labelled: {agg['labelled_test_files']} · matched {agg['matched']} · "
        f"missed {agg['missed']}",
        f"recall_micro: {agg['recall_micro']} · recall_macro: {agg['recall_macro']}",
        f"precision: not computed — {agg['precision_not_computed_because']}",
        "causes: "
        + (", ".join(f"{k}={v}" for k, v in agg["miss_causes"].items() if v) or "none"),
        f"VERDICT: {agg['verdict']} ({agg['verdict_reason']})",
    ]
    text = "\n".join(lines) + "\n"
    assert_no_selective_language(text)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=_CORPUS)
    parser.add_argument("--cache-dir", type=Path, default=_DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    parser.add_argument("--only", action="append", default=[], help="scenario id substring")
    parser.add_argument("--max-depth", type=int, default=3)
    args = parser.parse_args(argv)

    corpus = load_corpus(args.corpus)
    scenarios = [
        s
        for s in corpus["scenarios"]
        if not args.only or any(token in s["id"] for token in args.only)
    ]
    rows = [
        measure_scenario(s, args.cache_dir, max_depth=args.max_depth) for s in scenarios
    ]
    payload = {
        "bar": BAR,
        "provenance": provenance(args.corpus),
        "ground_truth": corpus["ground_truth"],
        "scenarios": rows,
        "aggregate": aggregate(rows, BAR),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    sys.stdout.write(render_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
