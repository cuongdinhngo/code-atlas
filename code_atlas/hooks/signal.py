"""Read/write-time signal for a host hook — the line that rides along with a file the agent is
already opening (task 099).

The field named three decisions made *without* calling code-atlas, and all three wanted one line
delivered at the moment of a ``Read`` or a ``Write`` — none wanted a tool call. An MCP tool answers
when asked; this signal fires when the agent was never going to ask. It is therefore
**hook-shaped**: code-atlas offers the command, the host decides whether to wire it (036 / 053).

Never builds, never reparses, never takes the write lock — it answers from the index as-is and says
so when that index is behind. Always exits 0 so a hook cannot break the editor round-trip.

**Which hook event, and why it matters.** ``Read`` wants **PostToolUse** — the field asked for the
line *inside the read result*. ``Write`` wants **PreToolUse**: the create-vs-edit test is whether
the path exists yet, and after a write it always does, so a PostToolUse ``Write`` is silent by
construction. Wiring both events at one command is the host's job; see the README.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from code_atlas.tokens import estimate_tokens

# 061: the cap IS the design. The field: ~150 tokens lands, "past ~500 I would treat it as chrome".
TOKEN_BUDGET = 150

# Below this a file has nothing worth interrupting a read for (the field's case held 9 symbols).
MIN_SYMBOLS = 5

# The only two occasions that earn a line (R1.2 — the field explicitly refused to name a third).
READ_TOOL = "Read"
WRITE_TOOL = "Write"


def _verbose(argv: list[str]) -> bool:
    if "--verbose" in argv or "-v" in argv:
        return True
    return os.environ.get("CA_SIGNAL_VERBOSE", "").strip() in {"1", "true", "yes"}


def _note(message: str, *, verbose: bool) -> None:
    if verbose:
        print(f"code-atlas signal: {message}", file=sys.stderr)


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def _repo_relative(root: Path, raw: str) -> str | None:
    """Map an absolute or relative path to the repo-relative form the index stores."""
    root = root.resolve()
    candidate = Path(raw)
    absolute = candidate if candidate.is_absolute() else (root / candidate)
    try:
        return absolute.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def _fit(prefix: str, parts: list[str], suffix: str) -> str:
    """Join what fits the budget, then say how many were left out — never exceed the cap."""
    kept: list[str] = []
    for index, part in enumerate(parts):
        remaining = len(parts) - index - 1
        tail = f", +{remaining + 1} more" if remaining >= 0 else ""
        candidate = prefix + ", ".join([*kept, part]) + suffix
        if estimate_tokens(candidate + tail) > TOKEN_BUDGET:
            break
        kept.append(part)
    dropped = len(parts) - len(kept)
    body = ", ".join(kept)
    if dropped:
        # No leading comma when nothing fit — "… — +60 more", never "… — , +60 more".
        body = f"{body}, +{dropped} more" if kept else f"+{dropped} more"
    return prefix + body + suffix


def read_signal(root: Path, rel: str, *, verbose: bool = False) -> str | None:
    """The outline line for a file the agent is opening, or ``None`` when silence is right."""
    from code_atlas.config import load_config
    from code_atlas.indexer import file_is_current
    from code_atlas.store import GraphStore

    config = load_config(root)
    if not config.db_path.is_file():
        _note("silent: no index", verbose=verbose)
        return None
    with GraphStore(config.db_path) as store:
        if store.file_hash(rel) is None:
            _note(f"silent: {rel} is not indexed", verbose=verbose)
            return None
        rows = store.nodes_by_file(rel, limit=config.max_results)
        # Read-only: a drifted file still answers, it just says the index may be behind (C3).
        behind = not file_is_current(store, config.root, rel)
    symbols = [row for row in rows if str(row["kind"]) != "File"]
    if len(symbols) < MIN_SYMBOLS:
        _note(f"silent: {rel} holds {len(symbols)} symbols", verbose=verbose)
        return None
    parts = [f"{row['name']}:{row['line_start']}" for row in symbols]
    suffix = " (index may be behind)" if behind else ""
    return _fit(f"code-atlas: {rel} defines {len(symbols)} symbols — ", parts, suffix)


def write_signal(root: Path, rel: str, *, verbose: bool = False) -> str | None:
    """The untracked warning for a file being created, or ``None`` when silence is right (092)."""
    from code_atlas.config import load_config
    from code_atlas.store import INDEXED_SUFFIXES_KEY, GraphStore

    config = load_config(root)
    if not config.db_path.is_file():
        _note("silent: no index", verbose=verbose)
        return None
    with GraphStore(config.db_path) as store:
        if store.file_hash(rel) is not None:
            _note(f"silent: {rel} is already indexed", verbose=verbose)
            return None
        # The suffix set the last build actually indexed — derived, never a hand-kept list (R6.7).
        raw = store.get_meta(INDEXED_SUFFIXES_KEY)
    suffixes = tuple(part for part in (raw or "").split(",") if part)
    if suffixes and not rel.lower().endswith(suffixes):
        _note(f"silent: no adapter owns {rel}", verbose=verbose)
        return None
    return (
        f"code-atlas: {rel} is untracked — symbol queries answer `not_indexed` "
        "until it is committed and reindexed (092)."
    )


def signal(root: Path, tool: str, raw_path: str, *, verbose: bool = False) -> str | None:
    """Route one hook invocation to its signal, or to silence.

    The silence rule is structural (099): anything that is not a ``Read`` or a file-creating
    ``Write`` is silent by construction, which is what keeps the line off the occasions the field
    named as costly — probe output, CI shell results, and authoring writes.
    """
    rel = _repo_relative(root, raw_path)
    if rel is None:
        _note("silent: path outside project", verbose=verbose)
        return None
    if tool == READ_TOOL:
        return read_signal(root, rel, verbose=verbose)
    if tool == WRITE_TOOL:
        if (root / rel).exists():
            _note(f"silent: {rel} already exists (edit, not create)", verbose=verbose)
            return None
        return write_signal(root, rel, verbose=verbose)
    _note(f"silent: {tool} is not a signalling tool", verbose=verbose)
    return None


def _payload_fields(payload: dict[str, object]) -> tuple[str | None, str | None]:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    tool_name = tool.strip() if isinstance(tool, str) and tool.strip() else None
    file_path = path.strip() if isinstance(path, str) and path.strip() else None
    return tool_name, file_path


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-signal`` / ``python -m code_atlas.hooks.signal``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        print(__doc__.strip(), file=sys.stderr)
        return 0
    verbose = _verbose(args)
    rest = [arg for arg in args if arg not in {"--verbose", "-v"}]
    root = _project_root()
    try:
        tool: str | None
        raw_path: str | None
        if len(rest) >= 2:
            tool, raw_path = rest[0], rest[1]
        else:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                _note("silent: stdin JSON is not an object", verbose=verbose)
                return 0
            tool, raw_path = _payload_fields(payload)
        if tool is None or raw_path is None:
            _note("silent: no tool_name / tool_input.file_path", verbose=verbose)
            return 0
        line = signal(root, tool, raw_path, verbose=verbose)
    except json.JSONDecodeError:
        _note("silent: invalid JSON on stdin", verbose=verbose)
        return 0
    except Exception as error:
        # A broken signal must never break the read it rides along with.
        print(f"code-atlas signal skipped: {type(error).__name__}: {error}", file=sys.stderr)
        return 0
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
