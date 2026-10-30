"""Text read back from the index, checked before a log, the instructions or a hook carries it (421).

The index directory and every string stamped into ``graph.db`` are the indexed repo's to write
(SECURITY.md). A name is kept only whole; free text is kept only scrubbed and capped.
"""

from __future__ import annotations

import re

# One name: an adapter, a shape kind, a language id. Longer is not a name code-atlas wrote.
NAME_CAP = 256
# A CSI or OSC escape sequence whole, so no printable tail (`[31m`) survives its ESC.
_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)?|[@-_]?)")
_WHITESPACE = frozenset("\t\n\r\v\f")


def checked_name(value: object) -> str | None:
    """``value`` when it is one line of printable text within ``NAME_CAP``, else ``None``."""
    if isinstance(value, str) and 0 < len(value) <= NAME_CAP and value.isprintable():
        return value
    return None


def scrubbed(value: object, cap: int) -> str:
    """``value`` as one line: ANSI sequences removed, control and bidi characters dropped, capped.

    ``str.isprintable`` is false for every control, format (the bidi marks) and separator
    character but the space; line breaks and tabs become a space so words stay apart.
    """
    text = _ANSI.sub("", str(value))
    text = "".join(c if c.isprintable() else " " if c in _WHITESPACE else "" for c in text)
    return text if len(text) <= cap else text[: cap - 1] + "…"
