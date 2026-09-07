"""Mermaid erDiagram from Table / Column / REFERENCES rows (task 224).

A projection of declared foreign keys only — never inferred from column names.
Node ids are positional so qnames never become mermaid identifiers. The table
cap is disclosed when it bites (108/124 / layer-diagram rule).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "DEFAULT_TABLE_CAP",
    "ErColumn",
    "ErRef",
    "ErTable",
    "NOTE_NO_REFERENCES",
    "NOTE_TABLES_CAPPED",
    "project_er",
    "render_er_diagram",
    "validate_mermaid_er_diagram",
]

DEFAULT_TABLE_CAP = 40
NOTE_NO_REFERENCES = "no REFERENCES edges in scope — tables only"
NOTE_TABLES_CAPPED = "table(s) omitted by the ER cap — diagram is incomplete"

_ENTITY = re.compile(r'^T[0-9]+\["[^"]*"\]$')
_ATTR = re.compile(r"^  \S.+$")
_REL = re.compile(
    r"^T[0-9]+\s+(\|\|--\|\||\|\|--o\{|\}o--\|\||\}o--o\{)\s+T[0-9]+"
    r"( : [^:]*)?$"
)


@dataclass(frozen=True, slots=True)
class ErColumn:
    """One column shown inside a table box."""

    name: str
    data_type: str = ""


@dataclass(frozen=True, slots=True)
class ErTable:
    """One Table in the diagram — columns may be a capped prefix of column_total."""

    qname: str
    name: str
    columns: tuple[ErColumn, ...]
    column_total: int


@dataclass(frozen=True, slots=True)
class ErRef:
    """One REFERENCES fact: source/target are table qnames; label is the column pair."""

    source: str
    target: str
    label: str
    heuristic: bool = False


def render_er_diagram(
    tables: Sequence[ErTable],
    refs: Sequence[ErRef],
    *,
    table_cap: int,
) -> str:
    """Deterministic mermaid ``erDiagram``. Counts and names are interpolated."""
    shown = list(tables[: max(table_cap, 0)])
    ids = {table.qname: f"T{index}" for index, table in enumerate(shown)}
    present = set(ids)
    lines = ["erDiagram"]
    for table in shown:
        lines.append(f'{ids[table.qname]}["{_label(table.qname)}"]')
        body: list[str] = []
        for col in table.columns:
            typ = _label(col.data_type) if col.data_type else "column"
            body.append(f"  {typ} {_label(col.name)}")
        if len(table.columns) < table.column_total:
            body.append(f"  omitted {table.column_total - len(table.columns)} more")
        if body:
            lines[-1] += " {"
            lines.extend(body)
            lines.append("}")
    drawn = 0
    for ref in refs:
        if ref.source not in present or ref.target not in present:
            continue
        arrow = "}o--o{" if ref.heuristic else "}o--||"
        lines.append(
            f"{ids[ref.source]} {arrow} {ids[ref.target]} : {_edge_label(ref.label)}"
        )
        drawn += 1
    if not refs:
        lines.append(f"%% {NOTE_NO_REFERENCES}")
    if len(tables) > len(shown):
        lines.append(f"%% {len(tables) - len(shown)} {NOTE_TABLES_CAPPED}")
    if refs and drawn < len(refs) and len(tables) > len(shown):
        lines.append(f"%% {len(refs) - drawn} REFERENCES edge(s) hidden with capped tables")
    text = "\n".join(lines) + "\n"
    validate_mermaid_er_diagram(text)
    return text


def validate_mermaid_er_diagram(text: str) -> None:
    """Python-side syntax-subset check — no Node, no npm. Raises ValueError on a miss."""
    lines = text.strip().splitlines()
    if not lines or lines[0] != "erDiagram":
        raise ValueError("mermaid must start with 'erDiagram'")
    in_body = False
    for line in lines[1:]:
        if in_body:
            if line == "}":
                in_body = False
                continue
            if _ATTR.match(line):
                continue
            raise ValueError(f"unrecognised entity body line: {line!r}")
        if line.endswith(" {"):
            head = line[: -len(" {")]
            if not _ENTITY.match(head):
                raise ValueError(f"unrecognised entity header: {line!r}")
            in_body = True
            continue
        if _ENTITY.match(line) or _REL.match(line) or line.startswith("%% "):
            continue
        raise ValueError(f"unrecognised mermaid line: {line!r}")
    if in_body:
        raise ValueError("unclosed entity body")


def _label(name: str) -> str:
    return name.replace('"', "").replace("\r", " ").replace("\n", " ")


def _edge_label(name: str) -> str:
    return _label(name).replace(":", " ")


def project_er(
    table_rows: Sequence[Mapping[str, object]],
    column_by_table: Mapping[str, Sequence[Mapping[str, object]]],
    ref_edges: Sequence[Mapping[str, object]],
    *,
    column_cap: int = 30,
) -> tuple[tuple[ErTable, ...], tuple[ErRef, ...]]:
    """Build ER boxes and refs from store-shaped rows. Pure — no SQLite here (R1.4)."""
    from code_atlas.contract import split_qname

    tables: list[ErTable] = []
    for row in sorted(table_rows, key=lambda r: str(r["qualified_name"])):
        qname = str(row["qualified_name"])
        cols_raw = sorted(
            column_by_table.get(qname, ()),
            key=lambda c: str(c.get("name") or ""),
        )
        columns = []
        for col in cols_raw[: max(column_cap, 0)]:
            extra = col.get("extra") or {}
            if isinstance(extra, str):
                try:
                    extra = json.loads(extra) if extra else {}
                except json.JSONDecodeError:
                    extra = {}
            data_type = ""
            if isinstance(extra, dict):
                data_type = str(extra.get("data_type") or "")
            columns.append(ErColumn(name=str(col["name"]), data_type=data_type))
        tables.append(
            ErTable(
                qname=qname,
                name=str(row["name"]),
                columns=tuple(columns),
                column_total=len(cols_raw),
            )
        )
    refs: list[ErRef] = []
    for edge in sorted(
        ref_edges,
        key=lambda e: (str(e["source_qname"]), str(e.get("target_qname") or e.get("target_raw"))),
    ):
        src_container, src_member = split_qname(str(edge["source_qname"]))
        if src_container is None:
            continue
        target = str(edge.get("target_qname") or edge.get("target_raw") or "")
        tgt_container, tgt_member = split_qname(target)
        heuristic = str(edge.get("confidence_tier") or "") == "HEURISTIC" or tgt_container is None
        if heuristic:
            label = src_member
            tgt_table = target if tgt_container is None else tgt_container
        else:
            label = f"{src_member}->{tgt_member}"
            tgt_table = tgt_container or target
        refs.append(
            ErRef(
                source=src_container,
                target=tgt_table,
                label=label,
                heuristic=heuristic,
            )
        )
    return tuple(tables), tuple(refs)
