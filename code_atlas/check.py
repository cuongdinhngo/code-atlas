"""``code-atlas-check`` — compose pre-PR Change Assurance evidence from the graph (task 303).

Refreshes the index through the existing build route, then reads the same impact / architecture-
rules / architecture-diff implementations the MCP tools use. One result object; text and JSON are
renders of that object. No 25th MCP tool and no second analysis pipeline (R1.8).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from code_atlas import gitutil
from code_atlas.config import ConfigError, load_config
from code_atlas.evidence_bundle import wrap_check_result, write_bundle
from code_atlas.indexer import indexable
from code_atlas.onboarding.artifact import MANIFEST_NAME, OUTPUT_DIR
from code_atlas.store import INDEXED_SUFFIXES_KEY, GraphStore
from code_atlas.tools import check_architecture_rules, diff_architecture, impact
from code_atlas.tools.build_or_update_index import BUSY as BUSY_MODE
from code_atlas.tools.build_or_update_index import REFUSED as REFUSED_MODE
from code_atlas.tools.build_or_update_index import create as create_build
from code_atlas.tools.generate_onboarding import (
    assemble_onboarding_snapshot,
    manifest_dict_for,
)
from code_atlas.tools.nav_result import (
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_OK,
    REASON_SNAPSHOT_NOT_FOUND,
)

OK = 0
OPERATIONAL = 1
CONFIRMED_VIOLATIONS = 2

REASON_BASE_NOT_RESOLVED = "base_not_resolved"
REASON_BUILD_FAILED = "build_failed"
REASON_BUILD_BUSY = "build_busy"
REASON_INCOMPLETE_INDEX = "incomplete_index"
REASON_SCHEMA_MISMATCH = "schema_mismatch"
REASON_REPORT_ONLY = "report_only"

_DEFAULT_BASE_CANDIDATES = ("main", "master", "origin/main", "origin/master")


def _say(message: str) -> None:
    print(f"code-atlas check: {message}", file=sys.stderr)


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def _git(root: Path, *arguments: str) -> str | None:
    """Thin wrapper so check can resolve merge-base without exporting gitutil internals."""
    # Reuse gitutil's public helpers where they exist; merge-base is check-local.
    import subprocess

    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=gitutil.GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    return text or None


def resolve_base(root: Path, override: str | None) -> str | None:
    """Return the base revision for the change set, or None when it cannot be derived."""
    if override is not None:
        resolved = _git(root, "rev-parse", "--verify", override)
        return resolved
    head = gitutil.head_commit(root)
    if head is None:
        return None
    for candidate in _DEFAULT_BASE_CANDIDATES:
        if _git(root, "rev-parse", "--verify", candidate) is None:
            continue
        merge_base = _git(root, "merge-base", "HEAD", candidate)
        if merge_base:
            return merge_base
    return None


def split_changed_paths(
    root: Path,
    base: str,
    *,
    suffixes: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]] | None:
    """All changed paths, indexed subset, and dirty-unindexed disclosure paths."""
    changed = gitutil.changed_paths(root, base)
    if changed is None:
        return None
    indexed = indexable(changed, root, suffixes) if suffixes else ()
    indexed_set = set(indexed)
    dirty = gitutil.dirty_paths(root) or ()
    dirty_unindexed = tuple(
        path for path in dirty if path not in indexed_set and path in set(changed)
    )
    # Also disclose dirty paths that never entered the change set's indexed subset.
    extra = tuple(
        path
        for path in dirty
        if path not in indexed_set
        and path not in set(dirty_unindexed)
        and not (suffixes and path in indexable((path,), root, suffixes))
    )
    disclosed = tuple(sorted({*dirty_unindexed, *extra}))
    return tuple(changed), tuple(indexed), disclosed


def _suffixes_from_store(db_path: Path) -> tuple[str, ...]:
    if not db_path.is_file():
        return ()
    with GraphStore(db_path) as store:
        raw = store.get_meta(INDEXED_SUFFIXES_KEY) or ""
    return tuple(part for part in raw.split(",") if part)


def _architecture_diff_payload(
    config: Any, before_path: Path, after_dict: Mapping[str, object]
) -> dict[str, object]:
    """Diff committed baseline vs in-memory current via the tool factory (R1.8)."""
    if not before_path.is_file():
        return {
            "index_root": config.index_root,
            "indexed": config.db_path.is_file(),
            "reason": REASON_SNAPSHOT_NOT_FOUND,
            "message": "missing snapshot file(s): before",
            "results": [],
            "total_count": 0,
            "truncated": False,
        }
    # Owned temp only — never rewrite committed onboarding pages (ticket Constraints).
    with tempfile.TemporaryDirectory(prefix="code-atlas-check-") as tmp:
        after_path = Path(tmp) / "after.json"
        after_path.write_text(
            json.dumps(after_dict, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return diff_architecture.create(config)(
            before=str(before_path),
            after=str(after_path),
        )


def run_check(
    root: Path,
    *,
    base_override: str | None = None,
    fail_on_confirmed: bool = False,
    skip_build: bool = False,
) -> tuple[int, dict[str, object]]:
    """Execute the check. Returns ``(exit_code, result)``."""
    config = load_config(root)
    mode = "fail_on_confirmed" if fail_on_confirmed else "report_only"
    head_commit, head_ref = gitutil.head_commit_and_ref(root)

    if not skip_build:
        try:
            build_result = create_build(config)(full=False, allow_full_rebuild=True)
        except Exception as error:  # noqa: BLE001 — operational, not a traceback for CI
            return OPERATIONAL, _operational(
                mode,
                REASON_BUILD_FAILED,
                base=None,
                head=head_commit,
                head_ref=head_ref,
                message=f"{type(error).__name__}: {error}",
            )
        build_mode = build_result.get("mode")
        if build_mode == BUSY_MODE:
            return OPERATIONAL, _operational(
                mode, REASON_BUILD_BUSY, base=None, head=head_commit, head_ref=head_ref
            )
        if build_mode == REFUSED_MODE:
            return OPERATIONAL, _operational(
                mode,
                REASON_BUILD_FAILED,
                base=None,
                head=head_commit,
                head_ref=head_ref,
                message=str(build_result.get("reason") or "refused"),
            )

    if not config.db_path.is_file():
        return OPERATIONAL, _operational(
            mode, REASON_INCOMPLETE_INDEX, base=None, head=head_commit, head_ref=head_ref
        )

    base = resolve_base(root, base_override)
    if base is None or head_commit is None:
        return OPERATIONAL, _operational(
            mode,
            REASON_BASE_NOT_RESOLVED,
            base=base,
            head=head_commit,
            head_ref=head_ref,
        )

    suffixes = _suffixes_from_store(config.db_path)
    split = split_changed_paths(root, base, suffixes=suffixes)
    if split is None:
        return OPERATIONAL, _operational(
            mode,
            REASON_BASE_NOT_RESOLVED,
            base=base,
            head=head_commit,
            head_ref=head_ref,
            message="git could not list changed paths",
        )
    changed, changed_indexed, dirty_unindexed = split

    impact_payload = impact.create(config)(
        paths=list(changed_indexed) if changed_indexed else None,
        sign=True,
    )
    try:
        rules_payload = check_architecture_rules.create(config)()
    except ConfigError as error:
        return OPERATIONAL, _operational(
            mode,
            "malformed_rules",
            base=base,
            head=head_commit,
            head_ref=head_ref,
            message=str(error),
            extra={
                "changed_paths": list(changed),
                "changed_indexed": list(changed_indexed),
                "dirty_unindexed": list(dirty_unindexed),
                "impact": impact_payload,
            },
        )
    rules_reason = str(rules_payload.get("reason") or "")
    if rules_reason == REASON_CAPABILITY_NOT_CONFIGURED:
        return OPERATIONAL, _operational(
            mode,
            REASON_CAPABILITY_NOT_CONFIGURED,
            base=base,
            head=head_commit,
            head_ref=head_ref,
            message=str(rules_payload.get("message") or ""),
            extra={
                "changed_paths": list(changed),
                "changed_indexed": list(changed_indexed),
                "dirty_unindexed": list(dirty_unindexed),
                "impact": impact_payload,
                "architecture_rules": rules_payload,
            },
        )

    baseline = Path(config.root) / OUTPUT_DIR / MANIFEST_NAME
    assembled = assemble_onboarding_snapshot(config)
    if assembled is None:
        return OPERATIONAL, _operational(
            mode,
            REASON_INCOMPLETE_INDEX,
            base=base,
            head=head_commit,
            head_ref=head_ref,
            message="could not assemble current architecture snapshot",
            extra={
                "changed_paths": list(changed),
                "changed_indexed": list(changed_indexed),
                "dirty_unindexed": list(dirty_unindexed),
                "impact": impact_payload,
                "architecture_rules": rules_payload,
            },
        )
    after_dict = manifest_dict_for(assembled, config)
    # Ensure index_root matches the committed baseline's tree identity for fair comparison.
    diff_payload = _architecture_diff_payload(config, baseline, after_dict)
    diff_reason = str(diff_payload.get("reason") or "")
    if diff_reason == REASON_SNAPSHOT_NOT_FOUND:
        return OPERATIONAL, _operational(
            mode,
            REASON_SNAPSHOT_NOT_FOUND,
            base=base,
            head=head_commit,
            head_ref=head_ref,
            message=str(diff_payload.get("message") or ""),
            extra={
                "changed_paths": list(changed),
                "changed_indexed": list(changed_indexed),
                "dirty_unindexed": list(dirty_unindexed),
                "impact": impact_payload,
                "architecture_rules": rules_payload,
                "architecture_diff": diff_payload,
            },
        )
    if diff_reason in {"schema_mismatch", "incomplete_snapshot", "index_root_mismatch"}:
        return OPERATIONAL, _operational(
            mode,
            REASON_SCHEMA_MISMATCH if diff_reason == "schema_mismatch" else diff_reason,
            base=base,
            head=head_commit,
            head_ref=head_ref,
            message=str(diff_payload.get("message") or ""),
            extra={
                "changed_paths": list(changed),
                "changed_indexed": list(changed_indexed),
                "dirty_unindexed": list(dirty_unindexed),
                "impact": impact_payload,
                "architecture_rules": rules_payload,
                "architecture_diff": diff_payload,
            },
        )

    confirmed_raw = rules_payload.get("total_count")
    candidate_raw = rules_payload.get("candidate_count")
    confirmed = int(confirmed_raw) if isinstance(confirmed_raw, int) else 0
    candidates = int(candidate_raw) if isinstance(candidate_raw, int) else 0
    # ``total_count`` is the full confirmed population (tool pages ``results`` only), so the
    # fail-on-confirmed verdict does not depend on page truncation or impact truncation.
    caveats = _collect_caveats(impact_payload, rules_payload, diff_payload, dirty_unindexed)
    result: dict[str, object] = {
        "architecture_diff": diff_payload,
        "architecture_rules": rules_payload,
        "base": base,
        "candidate_count": candidates,
        "caveats": caveats,
        "changed_indexed": list(changed_indexed),
        "changed_paths": list(changed),
        "confirmed_count": confirmed,
        "dirty_unindexed": list(dirty_unindexed),
        "head": head_commit,
        "head_ref": head_ref,
        "impact": impact_payload,
        "mode": mode,
        "reason": REASON_REPORT_ONLY if not fail_on_confirmed else REASON_OK,
    }
    if fail_on_confirmed and confirmed > 0:
        result["reason"] = "confirmed_violations"
        return CONFIRMED_VIOLATIONS, result
    return OK, result


def _collect_caveats(
    impact_payload: Mapping[str, object],
    rules_payload: Mapping[str, object],
    diff_payload: Mapping[str, object],
    dirty_unindexed: Sequence[str],
) -> list[str]:
    caveats: list[str] = []
    if dirty_unindexed:
        caveats.append(
            "dirty_unindexed:"
            + ",".join(dirty_unindexed)
            + " — disclosed; no graph impact invented"
        )
    for label, payload in (
        ("impact", impact_payload),
        ("architecture_rules", rules_payload),
        ("architecture_diff", diff_payload),
    ):
        if payload.get("truncated"):
            caveats.append(f"{label}:truncated")
        staleness = payload.get("staleness")
        if staleness and staleness != "current":
            caveats.append(f"{label}:staleness={staleness}")
        reason = payload.get("reason")
        if reason and reason not in {REASON_OK, "no_architectural_change"}:
            caveats.append(f"{label}:reason={reason}")
    return caveats


def _operational(
    mode: str,
    reason: str,
    *,
    base: str | None,
    head: str | None,
    head_ref: str | None,
    message: str = "",
    extra: Mapping[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "base": base,
        "candidate_count": 0,
        "caveats": [message] if message else [],
        "changed_indexed": [],
        "changed_paths": [],
        "confirmed_count": 0,
        "dirty_unindexed": [],
        "head": head,
        "head_ref": head_ref,
        "mode": mode,
        "reason": reason,
    }
    if message:
        result["message"] = message
    if extra:
        result.update(extra)
    return result


def render_json(result: Mapping[str, object]) -> str:
    """Deterministic JSON — sorted keys, no wall-clock (R4.2)."""
    return json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def render_text(result: Mapping[str, object]) -> str:
    """Human text derived only from ``result`` — never a second computation."""
    changed = result.get("changed_paths")
    indexed = result.get("changed_indexed")
    unindexed = result.get("dirty_unindexed")
    caveats = result.get("caveats")
    lines = [
        f"mode: {result.get('mode')}",
        f"reason: {result.get('reason')}",
        f"base: {result.get('base')}",
        f"head: {result.get('head')} ({result.get('head_ref')})",
        f"changed_paths: {len(changed) if isinstance(changed, list) else 0}",
        f"changed_indexed: {len(indexed) if isinstance(indexed, list) else 0}",
        f"dirty_unindexed: {len(unindexed) if isinstance(unindexed, list) else 0}",
        f"confirmed_count: {result.get('confirmed_count')}",
        f"candidate_count: {result.get('candidate_count')}",
    ]
    rules = result.get("architecture_rules")
    if isinstance(rules, Mapping):
        for row in rules.get("results") or []:
            if isinstance(row, Mapping):
                lines.append(
                    f"CONFIRMED {row.get('rule_id')}: "
                    f"{row.get('source_file')} -> {row.get('forbidden_file')}"
                )
        for row in rules.get("candidates") or []:
            if isinstance(row, Mapping):
                lines.append(
                    f"CANDIDATE {row.get('rule_id')}: "
                    f"{row.get('source_file')} -> {row.get('forbidden_file')}"
                )
    if isinstance(caveats, list):
        for caveat in caveats:
            lines.append(f"caveat: {caveat}")
    message = result.get("message")
    if message:
        lines.append(f"message: {message}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-check`` / ``python -m code_atlas.check``."""
    parser = argparse.ArgumentParser(
        prog="code-atlas-check",
        description=(
            "Compose impact, architecture-rule and architecture-drift evidence for a change."
        ),
        epilog=(
            f"exit: {OK} report_only / clean gate · "
            f"{CONFIRMED_VIOLATIONS} confirmed under --fail-on-confirmed · "
            f"{OPERATIONAL} operational failure"
        ),
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        help="base revision for the change set (default: merge-base with main/master)",
    )
    parser.add_argument(
        "--fail-on-confirmed",
        action="store_true",
        help="exit non-zero when at least one confirmed RESOLVED architecture violation exists",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the result object as deterministic JSON on stdout",
    )
    parser.add_argument(
        "--bundle-json",
        metavar="PATH",
        help="write a versioned evidence bundle JSON to PATH (305; no default write)",
    )
    parser.add_argument(
        "--bundle-md",
        metavar="PATH",
        help="write the evidence-bundle Markdown view to PATH (305)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help=argparse.SUPPRESS,  # tests only — production always refreshes
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = _project_root()
    try:
        code, result = run_check(
            root,
            base_override=args.base,
            fail_on_confirmed=args.fail_on_confirmed,
            skip_build=args.skip_build,
        )
    except Exception as error:  # noqa: BLE001
        _say(f"failed: {type(error).__name__}: {error}")
        return OPERATIONAL
    if args.bundle_json or args.bundle_md:
        try:
            write_bundle(
                wrap_check_result(result, load_config(root)),
                json_path=Path(args.bundle_json) if args.bundle_json else None,
                markdown_path=Path(args.bundle_md) if args.bundle_md else None,
            )
        except Exception as error:  # noqa: BLE001 — a failed write is operational, not a crash
            _say(f"failed: {type(error).__name__}: {error}")
            return OPERATIONAL
    text = render_json(result) if args.json else render_text(result)
    sys.stdout.write(text)
    if code == OPERATIONAL:
        _say(f"operational: {result.get('reason')}")
    elif code == CONFIRMED_VIOLATIONS:
        _say(f"confirmed violations: {result.get('confirmed_count')}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
