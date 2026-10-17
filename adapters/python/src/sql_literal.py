"""A T-SQL write or EXEC at the start of a string literal (task 371; the PHP adapter's 335 shape).

Statement grammar only — never a driver's method name (R2.2), never a SQL parse: a leading keyword,
one object name, and the clause T-SQL requires after it. Prose such as "Update settings" lacks that
clause and reads as nothing. ``tests/contract/sql_literal_cases.json`` keeps this copy, the PHP
original and the TS port in step.
"""

from __future__ import annotations

import re

KINDS = {
    "insert": "WRITES",
    "update": "WRITES",
    "merge": "WRITES",
    "delete": "DELETES",
    "exec": "CALLS",
    "select": "READS",
}

_HEAD = re.compile(
    r"\A(\s*)(insert\s+into|update|merge\s+into|delete\s+from|exec(?:ute)?|select)\s+",
    re.IGNORECASE,
)
# A SELECT names its table after FROM (390). An unqualified one must be followed by a clause, or end
# a closed literal, so "Select a file from the list" reads as nothing.
_FROM = re.compile(r"\bfrom\s+", re.IGNORECASE)
_AFTER_SOURCE = re.compile(
    r"\A\s*(?:where|join|inner|left|right|full|cross|order|group|having|union|with|;)\b|\A\s*;",
    re.IGNORECASE,
)
_NAME_PART = r'(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_][\w@#$]*)'
_NAME = re.compile(_NAME_PART + r"(?:\s*\.\s*" + _NAME_PART + r")*")
_PART = re.compile(_NAME_PART)
# `FROM users u WHERE` / `FROM users AS u WHERE`: an alias still needs the clause after it.
_ALIAS = re.compile(r"\s+(?:as\s+)?" + _NAME_PART, re.IGNORECASE)
_RETURN_CODE = re.compile(r"@[A-Za-z_]\w*\s*=\s*")
_END = re.compile(r"\A\s*(?:;|\Z)")
# T-SQL resolves an unqualified procedure in the caller's default schema, `dbo` unless set (386).
DEFAULT_SCHEMA = "dbo"
# The EXEC guard also reads the markers DB-API drivers write: `%s` and `%(name)s` (PEP 249).
_CLAUSES = {
    "insert": re.compile(
        r"\A\s*(?:\(|values\b|select\b|default\s+values\b|output\b|with\s*\()", re.IGNORECASE
    ),
    "update": re.compile(r"\A\s*(?:set\b|with\s*\()", re.IGNORECASE),
    "merge": re.compile(
        r"\A\s*(?:with\s*\([^)]*\)\s*)?(?:as\s+)?(?:[A-Za-z_]\w*\s+)?using\b", re.IGNORECASE
    ),
    "delete": re.compile(r"\A\s*(?:where\b|output\b|with\s*\()", re.IGNORECASE),
    "exec": re.compile(r"\A\s+(?:@|\?|:[A-Za-z_]|N?'|-?\d|%s|%\()"),
}


def read(text: str, closed: bool) -> tuple[str, str, int] | None:
    """``(edge kind, target, keyword offset)`` the literal begins, or None.

    ``closed`` says the literal is the whole string, so its end terminates the object name; a
    literal cut short by interpolation or concatenation needs the name ended inside it.
    """
    head = _HEAD.match(text)
    if head is None:
        return None
    verb = head.group(2).split()[0].lower()
    verb = "exec" if verb.startswith("exec") else verb
    start = head.end()
    if verb == "select":
        return _read_select(text, start, closed, len(head.group(1)))
    if verb == "exec":
        rc = _RETURN_CODE.match(text, start)  # `EXEC @rc = dbo.P …`, the return-code capture form
        start = rc.end() if rc else start
    name = _NAME.match(text, start)
    if name is None:
        return None
    parts = [_unquote(part) for part in _PART.findall(name.group(0))]
    if not _follows(verb, text[name.end() :], len(parts) > 1, closed):
        return None
    if verb == "exec" and len(parts) == 1:
        # A dotted target reaches no method through the bare-name fallback (204); a module
        # whose own qname is `dbo.<name>` still matches exactly, as the qualified form always has.
        parts.insert(0, DEFAULT_SCHEMA)
    return KINDS[verb], ".".join(parts), len(head.group(1))


def _read_select(text: str, start: int, closed: bool, offset: int) -> tuple[str, str, int] | None:
    """The table a SELECT reads: the first top-level FROM's name, never a temp or derived one."""
    source = next(
        (m for m in _FROM.finditer(text, start) if _top_level(text, start, m.start())), None
    )
    name = _NAME.match(text, source.end()) if source else None
    if name is None:
        return None
    parts = [_unquote(part) for part in _PART.findall(name.group(0))]
    if len(parts) == 1 and not _source_ends(text, name.end(), closed):
        return None
    return KINDS["select"], ".".join(parts), offset


def _source_ends(text: str, at: int, closed: bool) -> bool:
    """A clause follows a bare source (an alias may sit between); or the closed literal ends."""
    rest = text[at:]
    if _AFTER_SOURCE.match(rest) or (closed and rest.strip() == ""):
        return True
    alias = _ALIAS.match(text, at)
    return alias is not None and _AFTER_SOURCE.match(text[alias.end() :]) is not None


def _top_level(text: str, start: int, end: int) -> bool:
    """Is ``end`` outside every parenthesis and quoted string opened since ``start``?"""
    depth, quoted = 0, False
    for char in text[start:end]:
        if char == "'":
            quoted = not quoted
        elif not quoted and char in "()":
            depth += 1 if char == "(" else -1
    return depth == 0 and not quoted


def _follows(verb: str, rest: str, qualified: bool, closed: bool) -> bool:
    """The clause T-SQL requires after the name; for DELETE / EXEC on a qualified name, its end."""
    if _CLAUSES[verb].match(rest):
        return True
    if not qualified or verb not in ("delete", "exec"):
        return False
    return closed if rest == "" else _END.match(rest) is not None


def _unquote(part: str) -> str:
    if part.startswith("["):
        return part[1:-1].replace("]]", "]")
    if part.startswith('"'):
        return part[1:-1].replace('""', '"')
    return part
