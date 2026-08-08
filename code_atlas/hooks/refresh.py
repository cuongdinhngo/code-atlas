"""Git post-merge / post-checkout helper — incremental refresh (task 053).

Runs the same path as ``build_or_update_index(full=false)`` when an index already
exists. Safe no-op with no index (never builds). Always exits 0 so a hook never
fails the git command. Pair with background spawn in ``contrib/git/`` (field ~62s
flat fee — not inline). Concurrent refreshes take a non-blocking lock beside the
DB; the loser skips cleanly (R4.3).
"""

from __future__ import annotations

import fcntl
import os
import sys
from pathlib import Path


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


def refresh(root: Path, *, verbose: bool = False) -> int:
    """Incremental-refresh when an index exists. Always returns exit code 0."""
    try:
        from code_atlas.config import load_config
        from code_atlas.tools.build_or_update_index import create

        config = load_config(root)
        if not config.db_path.is_file():
            _note("skipped: no index", verbose=verbose)
            return 0

        lock_path = config.db_path.parent / "refresh.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                _note("skipped: another refresh is running", verbose=verbose)
                return 0
            try:
                create(config)(full=False)
                _note("refreshed", verbose=verbose)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception as error:
        print(
            f"code-atlas refresh skipped: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
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
