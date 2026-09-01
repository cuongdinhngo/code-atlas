"""``code-atlas-build`` — run a build from a shell, with no MCP client (task 176).

Reuses ``build_or_update_index`` so the write lock (R4.3), the schema-mismatch answer and the
report shape are identical to the MCP route; this module only maps that payload onto a CI-readable
exit code and one stderr line. Separate from ``code-atlas-refresh``, which must never build without
an index and must never fail a git command (053).
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from code_atlas.index_lock import read_build_progress
from code_atlas.tools.build_or_update_index import BUSY as BUSY_MODE
from code_atlas.tools.build_or_update_index import REFUSED as REFUSED_MODE

OK = 0
FAILED = 1
NOTHING_TO_DO = 3
BUSY_PEER = 4


def _say(message: str) -> None:
    print(f"code-atlas build: {message}", file=sys.stderr)


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def _wrote(result: Mapping[str, object]) -> dict[str, int]:
    wrote = result.get("wrote")
    if not isinstance(wrote, dict):
        return {}
    return {key: value for key, value in wrote.items() if isinstance(value, int)}


def exit_code(result: Mapping[str, object]) -> int:
    """Map one ``build_or_update_index`` payload onto an exit code, and say which in one line."""
    mode = result.get("mode")
    if mode == BUSY_MODE:
        _say("skipped: another build is running")
        return BUSY_PEER
    if mode == REFUSED_MODE:
        detail = result.get("detail")
        _say(f"refused: {result.get('reason')}" + (f" ({detail})" if detail else ""))
        return FAILED
    wrote = _wrote(result)
    files = wrote.get("files", 0)
    _say(
        f"{mode}: {files} file(s), {wrote.get('nodes', 0)} node(s), {wrote.get('edges', 0)} edge(s)"
    )
    return OK if files else NOTHING_TO_DO


def status(root: Path) -> int:
    """Report the running build's progress, so a long build is not read as a hang (task 177).

    The shell path exists because the caller that started the build is blocked inside it: if
    progress were readable only by a second MCP client, CI and a terminal would still be blind.
    """
    try:
        from code_atlas.config import load_config

        line = read_build_progress(load_config(root).db_path)
    except Exception as error:  # noqa: BLE001 — a broken read is an exit code, never a traceback
        _say(f"failed: {type(error).__name__}: {error}")
        return FAILED
    if line is None:
        _say("no build is running")
        return NOTHING_TO_DO
    _say(line)
    return OK


def build(root: Path, *, full: bool = False) -> int:
    """Build this repo's index through the MCP route's own tool. Returns the process exit code."""
    try:
        from code_atlas.config import load_config
        from code_atlas.tools.build_or_update_index import create

        # The refusal exists because an MCP call cannot outlive its client; a shell has no
        # RPC deadline, and the refusal names THIS command as the route (201).
        result = create(load_config(root))(full=full, allow_full_rebuild=True)
    except Exception as error:  # noqa: BLE001 — a broken build is an exit code, never a traceback
        _say(f"failed: {type(error).__name__}: {error}")
        return FAILED
    return exit_code(result)


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-build`` / ``python -m code_atlas.cli``."""
    parser = argparse.ArgumentParser(
        prog="code-atlas-build",
        description="Build or update this repo's code-atlas index from a shell.",
        epilog=(
            f"exit: {OK} built (or, with --status, a build is running) · "
            f"{NOTHING_TO_DO} nothing to do (or no build running) · "
            f"{BUSY_PEER} another build is running · {FAILED} failed"
        ),
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="report the running build's phase and file counts instead of building; the line "
        "comes from the live write lock, so a killed build reports nothing",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="always run a full build (default: incremental, falling back to full when the "
        "index is absent or git cannot supply a diff)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.status:
        return status(_project_root())
    return build(_project_root(), full=args.full)


if __name__ == "__main__":
    raise SystemExit(main())
