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

from code_atlas.containment import resolves_inside

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
# Built-ins have no filename; file sources derive from COMPOSED_IGNORE_FILES (095, not a hand list).
SOURCE_BUILTIN = "builtin"
COMPOSED_IGNORE_FILES: tuple[str, ...] = (GITIGNORE_FILE, ATLAS_IGNORE_FILE)

_MAGIC = re.compile(r"\*\*|[*?\[]")


def source_name(ignore_file: str) -> str:
    """Payload key for a composed ignore file: strip the leading dot from its name."""
    return ignore_file.lstrip(".")


def composed_source_names() -> frozenset[str]:
    """Every source ``load_ignore`` can stamp — derived from the composition, never listed."""
    return frozenset((SOURCE_BUILTIN, *(source_name(name) for name in COMPOSED_IGNORE_FILES)))


@dataclass(frozen=True, slots=True)
class _Rule:
    """One ignore pattern: its regex, whether it re-includes, directory-only, and which source."""

    regex: re.Pattern[str]
    negated: bool
    dir_only: bool
    source: str


class IgnoreMatcher:
    """Decides whether a repo-relative path is ignored, the last matching rule winning."""

    def __init__(self, rules: tuple[_Rule, ...]) -> None:
        self.rules = rules

    def is_ignored(self, path: str, *, is_dir: bool = False) -> bool:
        """True when ``path`` — or any directory above it — is excluded."""
        return self.ignore_source(path, is_dir=is_dir) is not None

    def ignore_source(self, path: str, *, is_dir: bool = False) -> str | None:
        """The source that excluded ``path``, or ``None`` when it is kept.

        Same ancestor walk as :meth:`is_ignored`: a path under an excluded directory stays
        excluded (later ``!`` cannot re-include it). Within one path, the last match wins.
        """
        parts = PurePosixPath(path.strip("/")).parts
        for depth in range(1, len(parts)):
            source = self._decide_source("/".join(parts[:depth]), is_dir=True)
            if source is not None:
                return source
        return self._decide_source("/".join(parts), is_dir=is_dir)

    def _decide_source(self, path: str, *, is_dir: bool) -> str | None:
        """Apply every rule in order; the last excluding decision names the source."""
        ignored = False
        source: str | None = None
        for rule in self.rules:
            if rule.dir_only and not is_dir:
                continue
            if rule.regex.fullmatch(path):
                ignored = not rule.negated
                source = rule.source if ignored else None
        return source


def load_ignore(root: Path) -> IgnoreMatcher:
    """Built-ins, then ``.gitignore``, then the optional ``.codeatlasignore`` — later rules win."""
    rules: list[_Rule] = []
    for pattern in BUILTIN_PATTERNS:
        if (rule := compile_pattern(pattern, source=SOURCE_BUILTIN)) is not None:
            rules.append(rule)
    for name in COMPOSED_IGNORE_FILES:
        path = root / name
        if path.is_file() and resolves_inside(root, path):
            origin = source_name(name)
            for line in path.read_text(encoding="utf-8").splitlines():
                if (rule := compile_pattern(line, source=origin)) is not None:
                    rules.append(rule)
    return IgnoreMatcher(tuple(rules))


def compile_pattern(line: str, source: str = SOURCE_BUILTIN) -> _Rule | None:
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
    return _Rule(re.compile(prefix + _translate(pattern)), negated, dir_only, source)


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
