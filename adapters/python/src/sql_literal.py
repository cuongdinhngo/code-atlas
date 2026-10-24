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


# Reserved words a SELECT uses that never name a column of its source (410), plus the table hints.
# A date part, `Path` or `Rows` is a common column name, so those are read by place instead. A
# delimited `[Status]` is a name however it is spelled, so only bare words are kept.
_NOT_A_COLUMN = frozenset(
    """select from where and or not null is in like between as on join inner left right full
    outer cross apply order by group having union all distinct top percent case when then else end
    asc desc exists with nolock readuncommitted holdlock updlock rowlock readpast into values set
    insert update delete merge using output declare begin return returns if while go create alter
    view procedure proc function table trigger for of over escape collate pivot unpivot except
    intersect default any some current_timestamp current_user session_user system_user identity
    partition interval""".split()
)
_STRING = re.compile(r"N?'(?:[^']|'')*'?", re.IGNORECASE)
# A regular identifier: a letter, `_`, `@` or `#`, then letters, digits and `@#$_` — Unicode too.
_COLUMN_PART = r'(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|(?:[^\W\d]|[@#])[\w@#$]*)'
_CHAIN = re.compile(_COLUMN_PART + r"(?:\s*\.\s*(?:" + _COLUMN_PART + r"|\*))*")
_BARE_STAR = re.compile(
    r"(?:\bselect\s+(?:distinct\s+)?(?:top\s*\(?\s*(?:\d+|@[\w@#$]+)\s*\)?\s*(?:percent\s+)?)?"
    r"|,\s*)\*",
    re.IGNORECASE,
)
_DOTTED_STAR = re.compile("(" + _COLUMN_PART + r"(?:\s*\.\s*" + _COLUMN_PART + r")*)\s*\.\s*\*")
_SECOND_SOURCE = re.compile(r"\bjoin\b|\bapply\b", re.IGNORECASE)
# Words that are syntax, not names: paging, `FOR XML/JSON`, `WITH TIES`, an `INDEX` table hint.
_NOT_NAMES = re.compile(
    r"\boffset\s+\S+\s+rows?\b(?:\s+fetch\s+(?:first|next)\s+\S+\s+rows?\s+only\b)?"
    r"|\bfor\s+(?:xml|json)\b[^;]*|\bwith\s+ties\b|\bindex\s*(?:\([^)]*\)|=\s*[^\s,)]+)",
    re.IGNORECASE,
)
# The first argument of a date function is a date part, of CONVERT a type: never a column.
_DATE_PART_ARG = re.compile(
    r"\b(?:dateadd|datediff|datediff_big|datepart|datename|datetrunc|date_bucket|convert"
    r"|try_convert)\s*\(\s*\Z",
    re.IGNORECASE,
)
# A top-N count precedes the select list; any other number or name before a bare word aliases it.
_TOP_N = re.compile(
    r"\btop\s*\(?\s*(?:\d+|@[\w@#$]+)\s*\)?\s*(?:percent\s*)?(?:with\s+ties\s*)?\Z", re.IGNORECASE
)
_AFTER_EXPRESSION = re.compile(r"(?:\)|\bend)\Z", re.IGNORECASE)
_PRIOR = re.compile(r'(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[\w@#$]+)\Z')
_ORDER_BY = re.compile(r"\border\s+by\b", re.IGNORECASE)
_ASSIGNED = re.compile(r"\A\s*=(?!=)")
_ITEM_START = re.compile(r"(?:,|\bselect|\bdistinct)\Z", re.IGNORECASE)
_AS = re.compile(r"\bas\Z", re.IGNORECASE)
_COLLATE = re.compile(r"\bcollate\Z", re.IGNORECASE)
_ITEM = re.compile(
    r"\b(?:from|join|apply)\s+(" + _COLUMN_PART + r"(?:\s*\.\s*" + _COLUMN_PART + r")*)"
    r"(?:\s+(?:as\s+)?(" + _COLUMN_PART + r"))?",
    re.IGNORECASE,
)
_PLACEHOLDER = (".", ":", "%", "$", "{")


def columns(text: str, closed: bool) -> list[str]:
    """The columns a SELECT literal reads of its first FROM's table, first seen, once each (410).

    ``alias.col`` / ``table.col`` always — unless another source in the string shares that name;
    a bare name only when that table is the string's one source, and never a keyword, call, date
    part, alias, parameter or temp. A ``*`` on the table gives none: which columns is not known.
    """
    found = read(text, closed)
    if found is None or found[0] != KINDS["select"]:
        return []
    target = found[1]
    masked = _STRING.sub(lambda m: " " * len(m.group(0)), text)
    masked = _NOT_NAMES.sub(lambda m: " " * len(m.group(0)), masked)
    head = _HEAD.match(masked)
    if head is None:
        return []
    start = head.end()
    source = next(
        (m for m in _FROM.finditer(masked, start) if _top_level(masked, start, m.start())), None
    )
    name = _NAME.match(masked, source.end()) if source else None
    if source is None or name is None:
        return []
    names = {target.lower(), target.split(".")[-1].lower()}
    after = name.end()
    alias = _ALIAS.match(masked, name.end())
    if alias is not None:
        token = _PART.findall(alias.group(0))[-1]
        if token[:1] in '["' or _unquote(token).lower() not in _NOT_A_COLUMN:
            names.add(_unquote(token).lower())
            after = alias.end()
    names -= _shared(masked, target)
    if _stars(masked, names):
        return []
    single = (
        _SECOND_SOURCE.search(masked) is None
        and len(_FROM.findall(masked)) == 1
        and not masked[after:].lstrip().startswith(",")
    )
    # A select-list alias may be an ORDER BY key (the one clause that sees it): never a column.
    keys = (m.start() for m in _ORDER_BY.finditer(masked, start))
    order = max((at for at in keys if _top_level(masked, start, at)), default=-1)
    aliases: set[str] = set()
    out: list[str] = []
    seen: set[str] = set()
    for match in _CHAIN.finditer(masked, start):
        before = masked[: match.start()].rstrip()
        if before.endswith(_PLACEHOLDER) or masked[: match.start()][-1:].isdigit():
            continue
        parts = [_unquote(part) for part in re.split(r"\s*\.\s*", match.group(0))]
        column = parts[-1]
        if len(parts) > 1:
            if ".".join(parts[:-1]).lower() not in names or column == "*":
                continue
        elif not single or source.start() <= match.start() < after:
            continue
        else:
            rest = masked[match.end() :]
            if _excluded(match.group(0), rest, before):
                continue
            if _alias_place(rest, before):
                if match.start() < source.start():
                    aliases.add(column.lower())
                continue
            if 0 <= order < match.start() and column.lower() in aliases:
                continue
        if column.lower() not in seen:
            seen.add(column.lower())
            out.append(column)
    return out


def _shared(masked: str, target: str) -> set[str]:
    """Names another FROM / JOIN item also goes by — an alias reused in a subquery binds neither."""
    other: set[str] = set()
    for item in _ITEM.finditer(masked):
        table = ".".join(_unquote(part) for part in re.split(r"\s*\.\s*", item.group(1)))
        if table.lower() == target.lower():
            continue
        other |= {table.lower(), table.split(".")[-1].lower()}
        if item.group(2):
            other.add(_unquote(item.group(2)).lower())
    return other


def _excluded(token: str, after: str, before: str) -> bool:
    """A word never a column: keyword, call, parameter, temp, date part, CONVERT type, collation."""
    lower = _unquote(token).lower()
    if token.startswith(("@", "#")) or (token[:1] not in '["' and lower in _NOT_A_COLUMN):
        return True
    return (
        after.lstrip().startswith("(")
        or _DATE_PART_ARG.search(before) is not None
        or _COLLATE.search(before) is not None
    )


def _alias_place(after: str, before: str) -> bool:
    """A word where an alias stands: ``x = expr`` opening an item, after AS, ``)``, END, a name."""
    if _ASSIGNED.match(after) and (_ITEM_START.search(before) or _TOP_N.search(before)):
        return True
    if _AS.search(before):
        return True
    if _TOP_N.search(before):
        return False
    if _AFTER_EXPRESSION.search(before):
        return True
    prior = _PRIOR.search(before)
    if prior is None:
        return False
    word = prior.group(0)
    return word[:1] in '["0123456789' or word.lower() not in _NOT_A_COLUMN


def _stars(masked: str, names: set[str]) -> bool:
    """Does the select list read the source with ``*`` — bare, or ``t.*`` naming it?"""
    if _BARE_STAR.search(masked):
        return True
    return any(
        ".".join(_unquote(part) for part in re.split(r"\s*\.\s*", m.group(1))).lower() in names
        for m in _DOTTED_STAR.finditer(masked)
    )
