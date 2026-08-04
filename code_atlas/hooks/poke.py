"""Claude Code PostToolUse helper — poke one edited file into the index (task 036).

Reads hook stdin JSON (``tool_input.file_path``) or a CLI path, then calls
:func:`code_atlas.indexer.reparse_file`. Safe no-op when no index exists (never builds).
Always exits 0 so a failed poke never blocks the editor round-trip; pair with
``"async": true`` in the settings snippet. Use ``--verbose`` (or ``CA_POKE_VERBOSE=1``)
for an observable install check; install failures always print one stderr line.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _verbose(argv: list[str]) -> bool:
    if "--verbose" in argv or "-v" in argv:
        return True
    return os.environ.get("CA_POKE_VERBOSE", "").strip() in {"1", "true", "yes"}


def _note(message: str, *, verbose: bool) -> None:
    if verbose:
        print(f"code-atlas poke: {message}", file=sys.stderr)


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
    root = root.resolve()
    candidate = Path(raw)
    absolute = candidate if candidate.is_absolute() else (root / candidate)
    try:
        return absolute.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def poke(root: Path, abs_or_rel: str, *, verbose: bool = False) -> int:
    """Reparse one path when an index exists. Returns a process exit code (always 0)."""
    try:
        from code_atlas.config import load_config
        from code_atlas.indexer import file_is_current, reparse_file
        from code_atlas.store import GraphStore

        config = load_config(root)
        if not config.db_path.is_file():
            _note("skipped: no index", verbose=verbose)
            return 0
        rel = _repo_relative(root, abs_or_rel)
        if not rel:
            _note("skipped: path outside project", verbose=verbose)
            return 0
        with GraphStore(config.db_path) as store:
            if file_is_current(store, config.root, rel):
                _note(f"skipped: current {rel}", verbose=verbose)
                return 0
            if reparse_file(config, store, rel):
                _note(f"poked {rel}", verbose=verbose)
            else:
                # Normal when no adapter owns the suffix — not an install failure.
                _note(f"skipped: no adapter owns {rel}", verbose=verbose)
    except Exception as error:
        # Install / config failures must be visible (async hooks surface stderr in --debug).
        print(
            f"code-atlas poke skipped: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-poke`` / ``python -m code_atlas.hooks.poke``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        print(__doc__.strip(), file=sys.stderr)
        return 0
    verbose = _verbose(args)
    paths = [arg for arg in args if arg not in {"--verbose", "-v"}]
    root = _project_root()
    if paths:
        return poke(root, paths[0], verbose=verbose)
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        _note("skipped: invalid JSON on stdin", verbose=verbose)
        return 0
    if not isinstance(payload, dict):
        _note("skipped: stdin JSON is not an object", verbose=verbose)
        return 0
    path = _file_path(payload)
    if path is None:
        _note("skipped: no tool_input.file_path", verbose=verbose)
        return 0
    return poke(root, path, verbose=verbose)


if __name__ == "__main__":
    raise SystemExit(main())
