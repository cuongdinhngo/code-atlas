"""Text read back from the index, checked before a log, the instructions or a hook carries it (421).

The index directory and every string stamped into ``graph.db`` are the indexed repo's to write
(SECURITY.md). A name is kept only whole; free text is kept only scrubbed and capped.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# One name: an adapter, a shape kind, a language id. Longer is not a name code-atlas wrote.
NAME_CAP = 256
# A CSI or OSC escape sequence whole, so no printable tail (`[31m`) survives its ESC.
_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)?|[@-_]?)")
_WHITESPACE = frozenset("\t\n\r\v\f")
# Controls, invisible format characters (the bidi marks, zero-width) and the line separators.
# Surrogates too, and the blank-looking characters no category flags: a conjoining-joiner, the
# Hangul fillers and the braille blank. Private use and variation selectors stay: real text.
_HOSTILE = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp"})
_BLANK = "\u034f\u115f\u1160\u2800\u3164\uffa0"
_BLANK_RUN = re.compile(f"[{_BLANK}]")


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


def escaped(text: object, multiline: bool = False) -> str:
    """``text`` with each control, format and line-separator character made a visible ``\\u{XXXX}``.

    Nothing is dropped: an ANSI escape or a bidi override arrives inert and readable instead of
    vanishing (429). ``multiline`` keeps ``\\n`` and ``\\t`` for source and markdown.
    """
    value = str(text)
    keep = "\n\t" if multiline else ""
    probe = value.translate({ord(c): None for c in keep}) if keep else value
    if probe.isprintable() and not _BLANK_RUN.search(probe):
        return value
    return "".join(
        char
        if char in keep or (unicodedata.category(char) not in _HOSTILE and char not in _BLANK)
        else f"\\u{{{ord(char):04X}}}"
        for char in value
    )


def escaped_tree(node: Any) -> Any:
    """``node`` with every string and object key ``escaped`` (multiline), recursively (429).

    Tuples become lists, as JSON would; any other value is returned as it came.
    """
    if isinstance(node, str):
        return escaped(node, multiline=True)
    if isinstance(node, dict):
        return {
            (escaped(key, multiline=True) if isinstance(key, str) else key): escaped_tree(value)
            for key, value in node.items()
        }
    if isinstance(node, (list, tuple)):
        return [escaped_tree(item) for item in node]
    return node
