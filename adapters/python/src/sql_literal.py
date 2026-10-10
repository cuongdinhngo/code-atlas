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
}

_HEAD = re.compile(
    r"\A(\s*)(insert\s+into|update|merge\s+into|delete\s+from|exec(?:ute)?)\s+", re.IGNORECASE
)
_NAME_PART = r'(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_][\w@#$]*)'
_NAME = re.compile(_NAME_PART + r"(?:\s*\.\s*" + _NAME_PART + r")*")
_PART = re.compile(_NAME_PART)
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
        # A dotted name never matches a same-language function by name, so 204 cannot bind it.
        parts.insert(0, DEFAULT_SCHEMA)
    return KINDS[verb], ".".join(parts), len(head.group(1))


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
