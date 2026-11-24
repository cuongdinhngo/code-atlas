"""Grep-time guard — at ``PreToolUse``, before a symbol grep answers (task 454).

The anchors each kept a bash copy of this; it is now one product script. A grep whose pattern
matches an adapter's stamped ``symbol_shapes`` (the same test as 345's nudge, so the core names no
language) is, by the recorded mode: ``off`` — allowed silently; ``nudge`` — allowed with 345's
rate-limited line; ``refuse`` — denied until the session transcript holds a code-atlas query naming
one of the pattern's identifiers. A code-atlas call that failed for any reason but a bad argument
lifts the refusal for the session: the server is down, so Grep is the fallback. Unsure always
allows; the script always exits 0.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from code_atlas.hooks import nudge
from code_atlas.store import LAST_COMMIT_KEY

MODES = ("off", "nudge", "refuse")
DEFAULT_MODE = "nudge"
EVENT = "PreToolUse"
# A transcript larger than this is not read: allowing is the unsure answer (never a slow hook).
TRANSCRIPT_CAP = 32 * 1024 * 1024
# Identifiers in a grep pattern; a word after a backslash is a regex escape, not a name.
_NAME = re.compile(r"(?<![\\A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]+")
# Not "required": a server refusing with "rebuild required" cannot answer, so it must lift.
_ARGUMENT_ERROR = re.compile(r"argument|validation|invalid", re.IGNORECASE)
_TOOL_PREFIX = re.compile(r"^mcp__(plugin_)?code[-_]atlas")
STATUS_TOOL = "get_index_status"


def mode_of(root: Path) -> str:
    """The mode `code-atlas-setup --guard` recorded; the repo's file: only a known value counts."""
    try:
        record = json.loads((root / ".code-atlas" / "setup.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT_MODE
    mode = record.get("guard") if isinstance(record, dict) else None
    return mode if mode in MODES else DEFAULT_MODE


def names_in(pattern: str, shape_patterns: list[str]) -> set[str]:
    """The identifiers a symbol grep asks about: its words, less the shapes' own keywords."""
    keywords = {w.lower() for text in shape_patterns for w in re.findall(r"[A-Za-z_]{2,}", text)}
    return {name for name in _NAME.findall(pattern) if name.lower() not in keywords}


def _code_atlas_call(item: object) -> tuple[str, str, str] | None:
    """(id, tool, input text) of a code-atlas tool_use content item, else None."""
    if not isinstance(item, dict) or item.get("type") != "tool_use":
        return None
    name = str(item.get("name", ""))
    if not _TOOL_PREFIX.match(name):
        return None
    return str(item.get("id", "")), name, json.dumps(item.get("input", {}))


def asked(transcript: Path | None, names: set[str]) -> bool:
    """Whether this session asked code-atlas about one of ``names``, or a code-atlas call failed.

    A failure that is not a bad argument means the server cannot answer, so the guard must lift.
    """
    if transcript is None or not names:
        return True
    try:
        if transcript.stat().st_size > TRANSCRIPT_CAP:
            return True
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return True
    calls: set[str] = set()
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") if isinstance(entry, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        for item in content if isinstance(content, list) else []:
            call = _code_atlas_call(item)
            if call is not None:
                ident, tool, text = call
                calls.add(ident)
                if not tool.endswith(STATUS_TOOL) and any(name in text for name in names):
                    return True
            elif isinstance(item, dict) and item.get("type") == "tool_result":
                failed = item.get("is_error") is True and item.get("tool_use_id") in calls
                if failed and not _ARGUMENT_ERROR.search(json.dumps(item.get("content", ""))):
                    return True
    return False


def _answers(root: Path, db: Path, built: str | None) -> bool:
    """Built at HEAD, no build running: one git call, not a status payload (seconds at scale)."""
    from code_atlas.gitutil import head_commit
    from code_atlas.index_lock import build_in_progress

    return bool(built) and built == head_commit(root) and not build_in_progress(db)


def deny(reason: str) -> str:
    """The refusal shape Claude Code reads from a PreToolUse hook's stdout."""
    output = {"hookEventName": EVENT, "permissionDecision": "deny"}
    output["permissionDecisionReason"] = reason
    return json.dumps({"hookSpecificOutput": output})


def guard(root: Path, payload: dict[str, object]) -> str | None:
    """The hook's stdout for this call, or ``None`` to allow silently."""
    tool, tool_input = payload.get("tool_name"), payload.get("tool_input")
    if not isinstance(tool, str) or not isinstance(tool_input, dict):
        return None
    if tool == nudge.BASH_TOOL and not re.search(r"\b(grep|rg)\b", str(tool_input.get("command"))):
        return None  # the cheap exit: no search, no index read
    mode = mode_of(root)
    if mode == "off" or not (root / nudge.INDEX_DIR / "graph.db").is_file():
        return None
    session, agent = str(payload.get("session_id") or ""), str(payload.get("agent_id") or "")
    if mode == "nudge":
        line = nudge.nudge(root, tool, tool_input, session, agent)
        return None if line is None else nudge.additional_context(EVENT, line)
    return _refusal(root, tool, tool_input, payload.get("transcript_path"))


def _refusal(root: Path, tool: str, tool_input: dict[str, object], path: object) -> str | None:
    from code_atlas.config import load_config
    from code_atlas.store import GraphStore

    call = nudge.from_grep_tool(tool_input) if tool == nudge.GREP_TOOL else None
    if tool == nudge.BASH_TOOL:
        call = nudge.from_bash(str(tool_input.get("command", "")))
    if call is None:
        return None
    db = load_config(root).db_path
    with GraphStore(db) as store:
        shapes = store.stamped_symbol_shapes()
        built = store.get_meta(LAST_COMMIT_KEY)
    if not nudge.matched_kinds(call, shapes):
        return None
    patterns = [
        str(shape.get("pattern", ""))
        for entry in shapes.values()
        for shape in nudge._items(entry.get("shapes"))
        if isinstance(shape, dict)
    ]
    names = names_in(call.pattern, patterns)
    transcript = Path(path) if isinstance(path, str) and path else None
    if not names or asked(transcript, names) or not _answers(root, db, built):
        return None
    listed = ", ".join(sorted(names)[:3])
    return deny(
        f"code-atlas: this grep looks like a symbol search for {listed} — ask the index first "
        "(search_symbol, then read_symbol / find_callers / find_references), then grep to verify. "
        "Repeating the grep does not lift this; a code-atlas query naming it does "
        "(a human can switch it off: code-atlas-setup --guard nudge)."
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-guard``. Reads the hook payload on stdin; always exits 0."""
    try:
        payload = json.load(sys.stdin)
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
        out = guard(root, payload) if isinstance(payload, dict) else None
    except Exception as error:
        # A broken guard must never block the search it judges: unsure allows.
        print(f"code-atlas guard skipped: {type(error).__name__}: {error}", file=sys.stderr)
        return 0
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
