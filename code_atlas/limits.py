"""Every bound the indexed repo cannot lift: file and reply size, regex shape, ceilings (430).

The repo is untrusted input. Its files are sized before a parser sees them, its regexes are read by
their parse (never their text, 410-C1) before they run, and a cap its project file sets is clamped
to a ceiling written here. The operator's environment is not clamped: it is the operator's.
"""

import importlib
import re
from typing import Any

# The grammar `re` itself compiles with; typeshed does not describe it, so it is read as Any.
_sre: Any = importlib.import_module("re._parser")

# A source file above this is skipped and counted, never truncated (a partial parse reads as whole).
DEFAULT_MAX_FILE_BYTES = 4 * 1024 * 1024
# A project file may lower the file cap, never raise it past this.
MAX_FILE_BYTES_CEILING = 64 * 1024 * 1024
# One adapter reply line. A longer one fails that file loudly and the process is replaced.
MAX_REPLY_BYTES = 64 * 1024 * 1024

MAX_PATTERN_CHARS = 512

# Project-file values only, by knob key; an environment value is never clamped.
CONFIG_CEILINGS: dict[str, int] = {
    "workers": 64,
    "adapter_timeout": 3600,
    "max_candidates": 1000,
    "page_limit": 1000,
    "max_subjects": 1000,
    "impact_depth": 64,
    "impact_max_nodes": 100_000,
    "orphans_max_nodes": 100_000,
    "full_build_crossover": 1_000_000,
    "path_index_max": 1_000_000,
    "max_file_bytes": MAX_FILE_BYTES_CEILING,
}


def checked_pattern(pattern: str, origin: str) -> re.Pattern[str]:
    """``pattern`` compiled, or a ``ConfigError`` naming ``origin`` (the rule) when it is unsafe.

    Refused: a pattern over 512 characters, any backreference, and a repeat that can run twice whose
    body holds a repeat or an alternation (the shape of catastrophic backtracking).
    A pattern that does not compile raises ``re.error``, which the caller already names.
    """
    from code_atlas.config import ConfigError

    if len(pattern) > MAX_PATTERN_CHARS:
        raise ConfigError(
            f"{origin}: pattern is {len(pattern)} characters, over the {MAX_PATTERN_CHARS} limit"
        )
    reason = _unsafe(_sre.parse(pattern), inside_repeat=False)
    if reason is not None:
        raise ConfigError(f"{origin}: pattern {pattern!r} refused — {reason}")
    return re.compile(pattern)


_REPEATS = (_sre.MAX_REPEAT, _sre.MIN_REPEAT)


def _unsafe(node: object, *, inside_repeat: bool) -> str | None:
    """The first reason a parsed pattern (or part of one) is refused, else ``None``.

    Inside a repeat that can run twice, any further repeat (``?`` too) and any alternation is
    refused: two ways to match the same text there is what backtracks without end.
    """
    if isinstance(node, _sre.SubPattern):
        for op, argument in node.data:
            if op == _sre.GROUPREF:
                return "a backreference"
            if inside_repeat and op in _REPEATS:
                return "a repeat inside a repeat"
            if inside_repeat and op == _sre.BRANCH:
                return "an alternation inside a repeat"
            if op in _REPEATS:
                _, high, body = argument
                found = _unsafe(body, inside_repeat=inside_repeat or high > 1)
            else:
                found = _unsafe(argument, inside_repeat=inside_repeat)
            if found is not None:
                return found
    elif isinstance(node, tuple | list):
        for item in node:
            found = _unsafe(item, inside_repeat=inside_repeat)
            if found is not None:
                return found
    return None
