"""Ignore rules: built-ins + ``.gitignore`` + the optional ``.codeatlasignore`` (§11).

Patterns compile to regexes once, then the **last** matching rule decides — so a later source can
re-include what an earlier one excluded. A path below an excluded **directory** stays excluded,
which is what lets the indexer prune a whole subtree instead of testing every file in it.

The supported gitignore subset: comments and blank lines, ``*`` ``?`` ``[seq]`` within one path
segment, ``**`` across segments, a leading ``/`` anchoring to the repo root, a trailing ``/``
matching directories only, and ``!`` negation. Not supported: per-directory nested ignore files, and
``\\`` escapes. Paths are repo-relative and POSIX-separated (CONVENTION §3).
"""

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

BUILTIN_PATTERNS: tuple[str, ...] = (
    "vendor/",
    "var/",
    "uploads/",
    "log/",
    "node_modules/",
    ".git/",
    # Compound *.blade.<ext> templates (any trailing suffix) — not adapter source (task 041).
    "*.blade.*",
)

GITIGNORE_FILE = ".gitignore"
ATLAS_IGNORE_FILE = ".codeatlasignore"

_MAGIC = re.compile(r"\*\*|[*?\[]")


@dataclass(frozen=True, slots=True)
class _Rule:
    """One ignore pattern: its regex, whether it re-includes, and whether it is directory-only."""

    regex: re.Pattern[str]
    negated: bool
    dir_only: bool


class IgnoreMatcher:
    """Decides whether a repo-relative path is ignored, the last matching rule winning."""

    def __init__(self, rules: tuple[_Rule, ...]) -> None:
        self.rules = rules

    def is_ignored(self, path: str, *, is_dir: bool = False) -> bool:
        """True when ``path`` — or any directory above it — is excluded."""
        parts = PurePosixPath(path.strip("/")).parts
        for depth in range(1, len(parts)):
            if self._decide("/".join(parts[:depth]), is_dir=True):
                return True
        return self._decide("/".join(parts), is_dir=is_dir)

    def _decide(self, path: str, *, is_dir: bool) -> bool:
        """Apply every rule to one path in order; the last match wins, as git does."""
        ignored = False
        for rule in self.rules:
            if rule.dir_only and not is_dir:
                continue
            if rule.regex.fullmatch(path):
                ignored = not rule.negated
        return ignored


def load_ignore(root: Path) -> IgnoreMatcher:
    """Built-ins, then ``.gitignore``, then the optional ``.codeatlasignore`` — later rules win."""
    lines = list(BUILTIN_PATTERNS)
    for name in (GITIGNORE_FILE, ATLAS_IGNORE_FILE):
        path = root / name
        if path.is_file():
            lines += path.read_text(encoding="utf-8").splitlines()
    return IgnoreMatcher(
        tuple(rule for line in lines if (rule := compile_pattern(line)) is not None)
    )


def compile_pattern(line: str) -> _Rule | None:
    """Translate one gitignore-style line into a rule, or None for a blank line or comment."""
    pattern = line.strip()
    if not pattern or pattern.startswith("#"):
        return None

    negated = pattern.startswith("!")
    pattern = pattern[1:] if negated else pattern
    dir_only = pattern.endswith("/")
    pattern = pattern.rstrip("/")
    # A trailing slash does not anchor, so test for a separator only after stripping it.
    anchored = "/" in pattern
    pattern = pattern.lstrip("/")
    if pattern.startswith("**/"):
        pattern, anchored = pattern[3:], False
    if not pattern:
        return None

    prefix = "" if anchored else r"(?:.*/)?"
    return _Rule(re.compile(prefix + _translate(pattern)), negated, dir_only)


def translate_path_pattern(pattern: str) -> str:
    """Glob→regex: ``*``/``?`` stay in-segment; ``/**/`` is zero-or-more dirs (gitignore)."""
    out: list[str] = []
    index = 0
    while (found := _MAGIC.search(pattern, index)) is not None:
        out.append(re.escape(pattern[index : found.start()]))
        token = found.group()
        if token == "**":
            after = found.end()
            before_slash = found.start() > 0 and pattern[found.start() - 1] == "/"
            after_slash = after < len(pattern) and pattern[after] == "/"
            if before_slash and after_slash:
                # Drop the slash already escaped into out; consume the slash after **.
                if out and out[-1].endswith("/"):
                    out[-1] = out[-1][:-1]
                out.append("(?:/|/.*/)")
                index = after + 1
                continue
            out.append(".*")
        elif token == "*":
            out.append("[^/]*")
        elif token == "?":
            out.append("[^/]")
        else:
            index = _append_class(out, pattern, found.start())
            continue
        index = found.end()
    out.append(re.escape(pattern[index:]))
    return "".join(out)


def _translate(pattern: str) -> str:
    """Backward-compatible alias for :func:`translate_path_pattern`."""
    return translate_path_pattern(pattern)


def _append_class(out: list[str], pattern: str, start: int) -> int:
    """Copy a ``[seq]`` class through, mapping git's leading ``!`` to a regex negation."""
    end = pattern.find("]", start + 1)
    if end == -1:
        out.append(re.escape(pattern[start]))
        return start + 1
    body = pattern[start + 1 : end]
    out.append(f"[{'^' + body[1:] if body.startswith('!') else body}]")
    return end + 1
