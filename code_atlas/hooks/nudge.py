"""Grep-time nudge — one "ask code-atlas first" line right after a grep for a symbol (task 345).

The field's one channel that fired at the decision was a project-local PostToolUse hook on
``Bash|Grep``. This is its upstream: the patterns are each adapter's own ``symbol_shapes`` (v13),
stamped into the index at build time, so the core names no language (R1.1) and no grep spawns an
adapter. The parse surface is closed — a missed nudge costs nothing, a wrong one costs trust.

Rate-limited to once per shape kind per session; never blocks, always exits 0, silent with no index.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

INDEX_DIR = ".code-atlas"
STATE_FILE = "nudge.json"
LOG_FILE = "nudge.log"
# Sessions kept in the state file; older ones age out so it never grows without bound.
KEPT_SESSIONS = 32

GREP_TOOL = "Grep"
BASH_TOOL = "Bash"
SEARCH_COMMANDS = ("grep", "rg")
# Flags that take a value, by spelling — the value is never mistaken for the pattern.
VALUE_FLAGS = frozenset(
    {
        "-e",
        "-f",
        "-A",
        "-B",
        "-C",
        "-m",
        "-g",
        "--glob",
        "-t",
        "--type",
        "-T",
        "--type-not",
        "--include",
        "--exclude",
        "--exclude-dir",
        "--max-count",
        "--context",
        "-d",
        "-D",
    }
)
SCOPE_FLAGS = {"-g": "glob", "--glob": "glob", "--include": "glob", "-t": "type", "--type": "type"}
SEPARATORS = frozenset({"|", "||", "&&", ";", "&", "(", ")"})


@dataclass(frozen=True)
class GrepCall:
    """What a grep asked: its pattern text, and the suffixes it was limited to (none = unscoped)."""

    pattern: str
    scope: frozenset[str]


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def _suffix_of(text: str) -> str | None:
    suffix = PurePosixPath(text.replace("\\", "/")).suffix.lower()
    return suffix if len(suffix) > 1 else None


def _scope_from(kind: str, value: str) -> str | None:
    """A glob `*.php` or a path names a suffix; a type `php` means `.php` — one rule, no table."""
    if kind == "type":
        return "." + value.lower().lstrip(".")
    return _suffix_of(value)


def from_grep_tool(tool_input: dict[str, object]) -> GrepCall | None:
    pattern = tool_input.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        return None
    scope = set()
    for field, kind in (("glob", "glob"), ("type", "type"), ("path", "path")):
        value = tool_input.get(field)
        if isinstance(value, str) and value:
            suffix = _scope_from(kind, value)
            if suffix:
                scope.add(suffix)
    return GrepCall(pattern, frozenset(scope))


def from_bash(command: str) -> GrepCall | None:
    """A command that starts with `grep`, `rg` or `git grep`, read up to its first separator."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return None
    start = _search_start(tokens)
    if start is None:
        return None
    words: list[str] = []
    for token in tokens[start:]:
        if token in SEPARATORS:
            break
        words.append(token)
    return _read_args(words)


def _search_start(tokens: list[str]) -> int | None:
    """Only a command that STARTS with a search — the same test the hook's `if` filter makes."""
    if tokens[:1] and tokens[0] in SEARCH_COMMANDS:
        return 1
    if tokens[:2] == ["git", "grep"]:
        return 2
    return None


def _read_args(words: list[str]) -> GrepCall | None:
    pattern: str | None = None
    scope: set[str] = set()
    rest: list[str] = []
    index = 0
    while index < len(words):
        word = words[index]
        if word == "--":  # end of options: everything after is the pattern, then paths
            rest.extend(words[index + 1 :])
            break
        flag, _, inline = word.partition("=") if word.startswith("--") else (word, "", "")
        if flag in VALUE_FLAGS:
            value = inline if inline else (words[index + 1] if index + 1 < len(words) else "")
            index += 1 if inline else 2
            if flag == "-e" and pattern is None:
                pattern = value
            elif flag in SCOPE_FLAGS and value:
                suffix = _scope_from(SCOPE_FLAGS[flag], value)
                if suffix:
                    scope.add(suffix)
            continue
        if not word.startswith("-") or word == "-":
            rest.append(word)
        index += 1
    if pattern is None:
        if not rest:
            return None
        pattern, rest = rest[0], rest[1:]
    for path in rest:
        suffix = _suffix_of(path)
        if suffix:
            scope.add(suffix)
    return GrepCall(pattern, frozenset(scope))


def matched_kinds(
    call: GrepCall, shapes_by_language: dict[str, dict[str, object]]
) -> list[tuple[str, str]]:
    """(adapter, kind) pairs whose shape matches — scoped shapes only inside their own suffixes."""
    hits: list[tuple[str, str]] = []
    for name, entry in sorted(shapes_by_language.items()):
        suffixes = {str(s).lower() for s in _items(entry.get("extensions")) if isinstance(s, str)}
        mine = bool(call.scope & suffixes)
        if call.scope and not mine:
            continue
        for shape in _items(entry.get("shapes")):
            if not isinstance(shape, dict):
                continue
            if shape.get("scoped") and not mine:
                continue
            try:
                found = re.search(str(shape.get("pattern", "")), call.pattern)
            except re.error:
                continue
            if found:
                hits.append((name, str(shape.get("kind"))))
    return hits


def _items(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _load_state(path: Path) -> dict[str, list[str]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): [str(x) for x in v] for k, v in raw.items() if isinstance(v, list)}


def nudge(root: Path, tool: str, tool_input: dict[str, object], session: str) -> str | None:
    """The one line to inject, or ``None``. Records each new kind in the state file and the log."""
    index = root / INDEX_DIR
    if not (index / "graph.db").is_file():
        return None
    if tool == GREP_TOOL:
        call = from_grep_tool(tool_input)
    elif tool == BASH_TOOL and isinstance(tool_input.get("command"), str):
        call = from_bash(str(tool_input["command"]))
    else:
        return None
    if call is None:
        return None
    from code_atlas.config import load_config
    from code_atlas.store import GraphStore

    with GraphStore(load_config(root).db_path) as store:
        shapes = store.stamped_symbol_shapes()
    hits = matched_kinds(call, shapes)
    state = _load_state(index / STATE_FILE)
    seen = set(state.get(session, []))
    fresh = [(name, kind) for name, kind in hits if kind not in seen]
    if not fresh:
        return None
    kinds = sorted({kind for _, kind in fresh})
    state[session] = sorted(seen | set(kinds))
    kept = dict(list(state.items())[-KEPT_SESSIONS:])
    (index / STATE_FILE).write_text(json.dumps(kept, sort_keys=True), encoding="utf-8")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with (index / LOG_FILE).open("a", encoding="utf-8") as log:
        for name, kind in sorted(set(fresh)):
            log.write(f"{stamp}\t{session}\t{name}\t{kind}\n")
    return (
        f"code-atlas: this grep looks like a symbol search ({', '.join(kinds)}) — ask the index "
        "first (search_symbol / find_callers / find_references); keep Grep as the cross-check."
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-nudge``. Reads the hook payload on stdin; always exits 0."""
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return 0
        tool = payload.get("tool_name")
        tool_input = payload.get("tool_input")
        if not isinstance(tool, str) or not isinstance(tool_input, dict):
            return 0
        session = payload.get("session_id")
        line = nudge(_project_root(), tool, tool_input, session if isinstance(session, str) else "")
    except Exception as error:
        # A broken nudge must never break the search it rides on.
        print(f"code-atlas nudge skipped: {type(error).__name__}: {error}", file=sys.stderr)
        return 0
    if line:
        # Plain stdout never reaches the model from PostToolUse; additionalContext does (345 spike).
        context = {"hookEventName": "PostToolUse", "additionalContext": line}
        print(json.dumps({"hookSpecificOutput": context}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
