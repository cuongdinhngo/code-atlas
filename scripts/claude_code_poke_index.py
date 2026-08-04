#!/usr/bin/env python3
"""Claude Code PostToolUse helper — poke one edited file into `.code-atlas/graph.db` (task 036).

Reads the hook's stdin JSON, extracts ``tool_input.file_path``, and calls
:func:`code_atlas.indexer.reparse_file`. Safe no-op when no index exists (never builds).
Always exits 0 so a failed poke never blocks the editor round-trip; pair with
``"async": true`` in the settings snippet.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path, PurePosixPath


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def _file_path(payload: dict[str, object]) -> str | None:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    path = tool_input.get("file_path")
    if isinstance(path, str) and path.strip():
        return path.strip()
    return None


def _repo_relative(root: Path, raw: str) -> str | None:
    """Map an absolute or relative path to the repo-relative form the index stores."""
    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(root).as_posix()
        except ValueError:
            return None
    return PurePosixPath(raw).as_posix()


def poke(root: Path, abs_or_rel: str) -> int:
    """Reparse one path when an index exists. Returns a process exit code (always 0)."""
    # Import lazily so ``--help`` / missing install still exit cleanly from main.
    from code_atlas.config import load_config
    from code_atlas.indexer import reparse_file
    from code_atlas.store import GraphStore

    config = load_config(root)
    if not config.db_path.is_file():
        return 0
    rel = _repo_relative(root, abs_or_rel)
    if not rel:
        return 0
    try:
        with GraphStore(config.db_path) as store:
            reparse_file(config, store, rel)
    except Exception:
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI: optional path arg, else Claude Code hook JSON on stdin."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        print(__doc__.strip(), file=sys.stderr)
        return 0
    root = _project_root()
    if args:
        return poke(root, args[0])
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    path = _file_path(payload)
    if path is None:
        return 0
    return poke(root, path)


if __name__ == "__main__":
    raise SystemExit(main())
