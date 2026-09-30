"""Session-boundary state line for a host hook — the index summary, restated when it has decayed
(task 322).

MCP ``instructions`` carry the state line once, on ``initialize``. A long session outlives it, and a
compaction drops it outright, so an agent that started a multi-minute build goes on to guess at its
health — two field retros filed the running-build signal as a missing feature. This command
restates the same line at the boundaries where the first delivery has decayed:

- ``SessionStart`` (``startup`` / ``resume`` / ``clear`` / ``compact``) — the ``compact`` source is
  the post-compaction delivery;
- ``PreCompact``, and ``PostCompact`` where a host names that event.

No other occasion earns a line (R1.2 — 099 refused a third on the same ground).

**It lifts, never recomposes:** the line is ``get_index_status(...)["summary"]``, the value
``instructions._state()`` already lifts (316/319, R6.7), plus the one field that moves minute to
minute — a running build's live phase and the route to it.

**Silent unless it changes something:** no index, or an index that is ``current`` with no build
running, no full rebuild pending and no refresh refused for a missing adapter, prints nothing.

**Version skew (348).** The hook table passes ``--expect-version`` — the version it was generated
from. When the installed package differs, one more line names both and the command that closes the
gap, so a plugin and the tool install it launches cannot drift apart unnoticed.

**Cardinal rule:** always exits 0 and never builds, reparses or takes the build lock; any error,
broken stdin or unreadable index is silence. The host is never blocked.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from code_atlas.tokens import estimate_tokens

# 099's 150 is a file outline; this is one sentence plus a phase, so the cap is shorter (AC5).
TOKEN_BUDGET = 90

OCCASIONS = frozenset({"SessionStart", "PreCompact", "PostCompact"})
PREFIX = "code-atlas: "
EXPECT_FLAG = "--expect-version"
TOOL_UPGRADE = "`uv tool upgrade code-atlas` (or `pipx upgrade code-atlas`)"
HOOKS_UPGRADE = (
    "`claude plugin marketplace update code-atlas && claude plugin update code-atlas@code-atlas` "
    "(or re-copy the hook snippet)"
)


def _verbose(argv: list[str]) -> bool:
    if "--verbose" in argv or "-v" in argv:
        return True
    return os.environ.get("CA_STATE_VERBOSE", "").strip() in {"1", "true", "yes"}


def _note(message: str, *, verbose: bool) -> None:
    if verbose:
        print(f"code-atlas state: {message}", file=sys.stderr)


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def _build_clause(phase: str | None) -> str:
    from code_atlas.tools.get_index_status import BUILD_PROGRESS_ROUTE

    live = f" ({phase})" if phase else ""
    return f" · a build is running{live} — `{BUILD_PROGRESS_ROUTE}` reads its live phase"


def _release(version: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None


def skew_line(expected: str | None) -> str | None:
    """One line when the hooks and the installed package are different releases, else ``None``."""
    from code_atlas.build_info import UNKNOWN_VERSION, package_version

    installed = package_version()
    if not expected or installed in (expected, UNKNOWN_VERSION):
        return None
    ahead, behind = _release(installed), _release(expected)
    # The older side is the one to move; an unparseable version names both routes.
    fix = HOOKS_UPGRADE if ahead and behind and ahead > behind else TOOL_UPGRADE
    if not (ahead and behind):
        fix = f"{TOOL_UPGRADE}, or {HOOKS_UPGRADE}"
    return f"{PREFIX}hooks expect code-atlas {expected} but {installed} is installed — run {fix}"


def _expected(args: list[str]) -> str | None:
    if EXPECT_FLAG in args:
        index = args.index(EXPECT_FLAG)
        return args[index + 1] if index + 1 < len(args) else None
    return None


def _fit(summary: str, phase: str | None) -> str:
    """The summary is never cut; a phase too long for the budget is dropped, the route kept."""
    line = PREFIX + summary + _build_clause(phase)
    if phase and estimate_tokens(line) > TOKEN_BUDGET:
        line = PREFIX + summary + _build_clause(None)
    return line


def _indexed(root: Path) -> bool:
    from code_atlas.config import load_config

    db = load_config(root).db_path
    return db.is_file() and db.stat().st_size > 0


def state_line(root: Path, *, verbose: bool = False) -> str | None:
    """The state line for this project, or ``None`` when silence is right."""
    from code_atlas.config import load_config
    from code_atlas.index_lock import build_in_progress, read_build_progress
    from code_atlas.tools import get_index_status
    from code_atlas.tools.get_index_status import (
        BUILD_IN_PROGRESS,
        COVERAGE_LOSS_PENDING,
        CURRENT,
        FULL_REBUILD_REQUIRED,
    )

    config = load_config(root)
    db = config.db_path
    # An empty file would be initialised by opening it — that is a write, so it counts as absent.
    if not db.is_file() or db.stat().st_size == 0:
        _note("silent: no index", verbose=verbose)
        return None
    payload = get_index_status.create(config, ())()
    summary = str(payload["summary"])
    building = bool(payload.get(BUILD_IN_PROGRESS)) or build_in_progress(db)
    if not building:
        # An older-era index at an unmoved HEAD still reads `current` — that one must speak (347),
        # and so must one whose every refresh refuses for a missing adapter (355).
        pending = FULL_REBUILD_REQUIRED in payload or COVERAGE_LOSS_PENDING in payload
        if payload.get("staleness") == CURRENT and not pending:
            _note("silent: index current, no build running", verbose=verbose)
            return None
        return PREFIX + summary
    return _fit(summary, read_build_progress(db))


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-state`` / ``python -m code_atlas.hooks.state``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        print(__doc__.strip(), file=sys.stderr)
        return 0
    verbose = _verbose(args)
    expected = _expected(args)
    skew: str | None = None
    try:
        payload = json.load(sys.stdin)
        event = payload.get("hook_event_name") if isinstance(payload, dict) else None
        if event not in OCCASIONS:
            _note(f"silent: {event!r} is not a state occasion", verbose=verbose)
            return 0
        root = _project_root()
        skew = skew_line(expected) if _indexed(root) else None
        line = state_line(root, verbose=verbose)
    except Exception as error:
        # A broken state line must never break the session boundary it rides on.
        print(f"code-atlas state skipped: {type(error).__name__}: {error}", file=sys.stderr)
        line = None
    for text in (skew, line):
        if text:
            print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
