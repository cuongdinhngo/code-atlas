"""Git post-merge / post-checkout helper — incremental refresh (task 053).

Runs the same path as ``build_or_update_index(full=false)`` when an index already
exists. Safe no-op with no index (never builds). Always exits 0 so a hook never
fails the git command. Pair with background spawn in ``contrib/git/`` (field ~62s
flat fee — not inline). Write locking lives in the build tool (R4.3) so a hook
and the MCP server share one mutex; a busy peer is a clean skip.

A refusal or an error is also recorded beside the index, dated, so ``get_index_status`` names
it until a build succeeds (401): stderr alone reaches only a log nobody reads.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# What a refused refresh records for `get_index_status` (401); the rest of the refusal is dropped.
RECORDED_FIELDS = ("reason", "detail", "route", "hint")


def _verbose(argv: list[str]) -> bool:
    if "--verbose" in argv or "-v" in argv:
        return True
    return os.environ.get("CA_REFRESH_VERBOSE", "").strip() in {"1", "true", "yes"}


def _note(message: str, *, verbose: bool) -> None:
    if verbose:
        print(f"code-atlas refresh: {message}", file=sys.stderr)


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def is_branch_checkout(flag: str | None) -> bool:
    """Git post-checkout third arg is ``1`` only for a branch checkout."""
    return flag == "1"


def _record(db_path: Path | None, fields: dict[str, object]) -> None:
    """Leave the refusal where `get_index_status` reads it, dated in UTC (401)."""
    from code_atlas.index_lock import record_refresh_refused

    if db_path is None:
        return
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record_refresh_refused(db_path, {**{k: v for k, v in fields.items() if v}, "at": at})


def refresh(root: Path, *, verbose: bool = False) -> int:
    """Incremental-refresh when an index exists. Always returns exit code 0."""
    db_path: Path | None = None
    try:
        from code_atlas.config import load_config
        from code_atlas.tools.build_or_update_index import create

        config = load_config(root)
        if not config.db_path.is_file():
            _note("skipped: no index", verbose=verbose)
            return 0
        db_path = config.db_path
        # Never starts a full rebuild: 053 says this hook does not build, and a killed
        # repair would be re-triggered by the next checkout, indefinitely (202).
        result = create(config)(full=False, repair_incomplete=False)
        if result.get("mode") == "busy":
            _note("skipped: another build is running", verbose=verbose)
        elif result.get("mode") == "refused":
            # A refusal with no tool to route to (coverage_loss) ends at the reason (344).
            route = f" — run {result['route']}" if result.get("route") else ""
            print(f"code-atlas refresh skipped: {result.get('reason')}{route}", file=sys.stderr)
            _record(db_path, {key: result.get(key) for key in RECORDED_FIELDS})
        else:
            _note("refreshed", verbose=verbose)
    except Exception as error:
        print(
            f"code-atlas refresh skipped: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        from code_atlas.tools.get_index_status import REFRESH_ERROR

        _record(db_path, {"reason": REFRESH_ERROR, "detail": f"{type(error).__name__}: {error}"})
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-refresh`` / ``python -m code_atlas.hooks.refresh``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        print(__doc__.strip(), file=sys.stderr)
        return 0
    verbose = _verbose(args)
    return refresh(_project_root(), verbose=verbose)


if __name__ == "__main__":
    raise SystemExit(main())
