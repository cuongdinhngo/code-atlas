"""Mermaid classDiagram from resolved type rows (task 144).

A projection: inheritance from FQN_EDGE_KINDS only; associations from declared types only.
No inferred receiver, no whole-repo dump. Node ids are positional so qnames never become
mermaid identifiers.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "Association",
    "ClassBox",
    "Inheritance",
    "Member",
    "NOTE_ASSOCIATIONS_CAPPED",
    "NOTE_NO_ASSOCIATIONS",
    "declared_type_qnames",
    "render_class_diagram",
    "validate_mermaid_class_diagram",
]

NOTE_NO_ASSOCIATIONS = "no declared-type associations — inheritance only"
# A member the cap drops takes its arrow with it, so "no associations" would state a fact about the
# code that the cap invented (130's family). The two notes are mutually exclusive.
NOTE_ASSOCIATIONS_CAPPED = "declared-type association(s) hidden with their capped members"

_CLASS = re.compile(r'^class [A-Za-z][A-Za-z0-9_]*\["[^"]*"\]$')
_REL = re.compile(
    r"^[A-Za-z][A-Za-z0-9_]*\s+(<\|--|<\|..|\*--|-->)\s+[A-Za-z][A-Za-z0-9_]*"
    r"( : [^:]*)?$"
)
_MEMBER = re.compile(r"^  [+\-#~].+$")
_STEREOTYPE = re.compile(r"^  <<test>>$")


@dataclass(frozen=True, slots=True)
class Member:
    """One method, property, or class constant in the box."""

    name: str
    kind: str
    visibility: str
    params: tuple[tuple[str, str | None], ...] = ()
    return_type: str | None = None
    declared_type: str | None = None


@dataclass(frozen=True, slots=True)
class ClassBox:
    """One type in the diagram — members may be a capped prefix of member_total."""

    qname: str
    name: str
    kind: str
    test: bool
    members: tuple[Member, ...]
    member_total: int


@dataclass(frozen=True, slots=True)
class Inheritance:
    """EXTENDS / IMPLEMENTS / USES_TRAIT — never CALLS/NEW."""

    source: str
    target: str
    kind: str


@dataclass(frozen=True, slots=True)
class Association:
    """Declared-type field or param pointing at another type already in the diagram."""

    source: str
    target: str
    label: str


def declared_type_qnames(hint: str | None) -> tuple[str, ...]:
    """Class FQNs inside a declared type hint. Scalars and unprefixed names are skipped."""
    if not hint:
        return ()
    found: list[str] = []
    for token in re.split(r"[|&]", hint.replace("?", "")):
        name = token.strip()
        if name.startswith("\\"):
            found.append(name)
    return tuple(found)


def render_class_diagram(
    boxes: Sequence[ClassBox],
    inheritance: Sequence[Inheritance],
    associations: Sequence[Association],
    *,
    member_cap: int,
    hidden_associations: int = 0,
) -> str:
    """Deterministic mermaid ``classDiagram``. Counts and names are interpolated."""
    ids = {box.qname: f"N{index}" for index, box in enumerate(boxes)}
    lines = ["classDiagram"]
    any_capped = False
    for box in boxes:
        shown = box.members[: max(member_cap, 0)]
        if len(shown) < box.member_total:
            any_capped = True
        lines.append(f'class {ids[box.qname]}["{_label(box.qname)}"]')
        body: list[str] = []
        if box.test:
            body.append("  <<test>>")
        for member in shown:
            body.append(f"  {_member_line(member)}")
        if body:
            lines[-1] += " {"
            lines.extend(body)
            lines.append("}")
    for rel in inheritance:
        if rel.source not in ids or rel.target not in ids:
            continue
        if rel.kind == "EXTENDS":
            lines.append(f"{ids[rel.target]} <|-- {ids[rel.source]}")
        elif rel.kind == "IMPLEMENTS":
            lines.append(f"{ids[rel.target]} <|.. {ids[rel.source]}")
        else:
            lines.append(f"{ids[rel.source]} *-- {ids[rel.target]}")
    for link in associations:
        if link.source not in ids or link.target not in ids:
            continue
        lines.append(f"{ids[link.source]} --> {ids[link.target]} : {_edge_label(link.label)}")
    if not associations and not hidden_associations:
        lines.append(f"%% {NOTE_NO_ASSOCIATIONS}")
    if any_capped:
        lines.append("%% members capped")
    if hidden_associations:
        lines.append(f"%% {hidden_associations} {NOTE_ASSOCIATIONS_CAPPED}")
    text = "\n".join(lines) + "\n"
    # Validate what we hand back, not only what a benchmark renders (143's gap, same shape).
    validate_mermaid_class_diagram(text)
    return text


def validate_mermaid_class_diagram(text: str) -> None:
    """Python-side syntax-subset check — no Node, no npm. Raises ValueError on a miss."""
    lines = text.strip().splitlines()
    if not lines or lines[0] != "classDiagram":
        raise ValueError("mermaid must start with 'classDiagram'")
    in_body = False
    for line in lines[1:]:
        if in_body:
            if line == "}":
                in_body = False
                continue
            if _MEMBER.match(line) or _STEREOTYPE.match(line):
                continue
            raise ValueError(f"unrecognised class body line: {line!r}")
        if line.endswith(" {"):
            head = line[: -len(" {")]
            if not _CLASS.match(head):
                raise ValueError(f"unrecognised class header: {line!r}")
            in_body = True
            continue
        if _CLASS.match(line) or _REL.match(line) or line.startswith("%% "):
            continue
        raise ValueError(f"unrecognised mermaid line: {line!r}")
    if in_body:
        raise ValueError("unclosed class body")


def parse_json_field(raw: object, default: object) -> object:
    """SQLite stores lists/dicts as JSON text; planted tests may already pass objects."""
    if raw is None or raw == "":
        return default
    if isinstance(raw, (list, dict)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default
    return default


def _member_line(member: Member) -> str:
    vis = member.visibility if member.visibility in "+-#~" else "+"
    name = _label(member.name)
    if member.kind == "Method":
        args = ", ".join(
            f"{_label(typ)} {_label(pname)}" if typ else _label(pname)
            for pname, typ in member.params
        )
        ret = f" {_label(member.return_type)}" if member.return_type else ""
        return f"{vis}{name}({args}){ret}"
    hint = _label(member.declared_type or "")
    prefix = f"{hint} " if hint else ""
    return f"{vis}{prefix}{name}"


def _label(name: str) -> str:
    """Quotes end a label and a newline would break the line structure; drop both (143)."""
    return name.replace('"', "").replace("\r", " ").replace("\n", " ")


def _edge_label(name: str) -> str:
    """A relation label sits after ``:``, so a second colon would make the line unparseable."""
    return _label(name).replace(":", " ")
