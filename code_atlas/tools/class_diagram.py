"""``class_diagram`` — mermaid classDiagram for one type plus ancestry, or one file (task 144)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Literal

from code_atlas.config import Config, clamp_limit
from code_atlas.contract import CLASS_MEMBER_KINDS, INHERIT_KINDS, TYPE_KINDS
from code_atlas.onboarding.class_diagram import (
    NOTE_NO_ASSOCIATIONS,
    Association,
    ClassBox,
    Inheritance,
    Member,
    declared_type_qnames,
    parse_json_field,
    render_class_diagram,
)
from code_atlas.onboarding.layers import responsibility_of_segment
from code_atlas.onboarding.reachability import LAYER_TESTS
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
    attach_ambiguous_definitions,
    attach_limit_capped,
    definition_sites,
)

NAME = "class_diagram"

MEMBER_KINDS: frozenset[str] = frozenset(CLASS_MEMBER_KINDS)
TYPE_KIND_SET: frozenset[str] = frozenset(TYPE_KINDS)
WALK = 10_000

DetailLevel = Literal["minimal", "standard"]

__all__ = ["NAME", "create"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def class_diagram(
        qname: str | None = None,
        path: str | None = None,
        detail_level: DetailLevel = "standard",
        limit: int | None = None,
    ) -> dict[str, object]:
        """Mermaid class diagram for one class plus its ancestry, or every type in one file.

        Inheritance arrows are ``EXTENDS`` / ``IMPLEMENTS`` / ``USES_TRAIT`` only. Associations
        come from declared property and parameter types — never from CALLS/NEW. ``limit`` caps
        members per type and is disclosed when it bites. Pass ``qname`` or ``path``, not both.
        """
        cap, limit_clamped = clamp_limit(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        if (qname is None) == (path is None):
            raise ValueError("pass exactly one of qname or path")
        if not config.db_path.is_file():
            return _empty(config, reason=REASON_NOT_INDEXED)
        with GraphStore(config.db_path) as store:
            roots, sites = _roots(store, qname=qname, path=path)
            if not roots:
                empty = _empty(config, reason=REASON_NO_MATCHES)
                attach_limit_capped(empty, cap=cap, clamped=limit_clamped)
                return empty
            qnames = _ancestry(store, roots)
            boxes, inheritance, associations, hidden = _project(
                store, qnames, member_cap=cap
            )
        mermaid = render_class_diagram(
            boxes, inheritance, associations, member_cap=cap, hidden_associations=hidden
        )
        capped = any(len(box.members) < box.member_total for box in boxes)
        payload: dict[str, object] = {
            "index_root": config.index_root,
            "indexed": True,
            "reason": REASON_OK,
            "results": [{"qname": box.qname, "kind": box.kind} for box in boxes],
            "total_count": len(boxes),
            "truncated": capped,
        }
        if detail_level == "standard":
            payload["markdown"] = mermaid
        if not associations and not hidden:
            payload["association_note"] = NOTE_NO_ASSOCIATIONS
        if hidden:
            payload["associations_hidden_by_cap"] = hidden
        attach_ambiguous_definitions(payload, sites)
        attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
        return payload

    return class_diagram


def _empty(config: Config, *, reason: str) -> dict[str, object]:
    return {
        "index_root": config.index_root,
        "indexed": reason != REASON_NOT_INDEXED,
        "reason": reason,
        "results": [],
        "total_count": 0,
        "truncated": False,
    }


def _roots(
    store: GraphStore, *, qname: str | None, path: str | None
) -> tuple[list[str], list[dict[str, object]]]:
    """Distinct root qnames, plus the definition sites when the subject is non-unique (070/078).

    One qname declared twice is one box: two boxes would share a mermaid id and double
    ``total_count``. The duplication is disclosed, never merged away silently.
    """
    if qname is not None:
        rows = [row for row in store.nodes_by_qualified_name(qname, limit=8)
                if row.get("kind") in TYPE_KIND_SET]
        return _distinct(str(row["qualified_name"]) for row in rows), definition_sites(rows)
    assert path is not None
    rows = [row for row in store.nodes_by_file_all(path) if row.get("kind") in TYPE_KIND_SET]
    return _distinct(sorted(str(row["qualified_name"]) for row in rows)), []


def _distinct(names: Iterable[str]) -> list[str]:
    """First-seen order, no duplicates — mermaid ids are positional and must stay one per type."""
    seen: dict[str, None] = {}
    for name in names:
        seen.setdefault(name, None)
    return list(seen)


def _ancestry(store: GraphStore, roots: Sequence[str]) -> list[str]:
    seen: list[str] = []
    pending = list(roots)
    known = set(roots)
    while pending:
        current = pending.pop(0)
        seen.append(current)
        for edge in store.edges_by_source(current, kinds=INHERIT_KINDS, limit=WALK):
            target = edge.get("target_qname")
            if not isinstance(target, str) or target in known:
                continue
            known.add(target)
            pending.append(target)
    return seen


def _project(
    store: GraphStore, qnames: Sequence[str], *, member_cap: int
) -> tuple[tuple[ClassBox, ...], tuple[Inheritance, ...], tuple[Association, ...], int]:
    """Boxes, inheritance, associations, and how many associations the member cap hid."""
    nodes = store.nodes_by_qualified_names(list(qnames), limit=8)
    boxes: list[ClassBox] = []
    inherit: list[Inheritance] = []
    assoc: list[Association] = []
    hidden: set[Association] = set()
    present = set(qnames)
    for qname in qnames:
        row = next(iter(nodes.get(qname, ())), None)
        if row is None or row.get("kind") not in TYPE_KIND_SET:
            continue
        members = _members(store, qname)
        shown = members[:member_cap]
        boxes.append(
            ClassBox(
                qname=qname,
                name=str(row.get("name") or qname),
                kind=str(row["kind"]),
                test=_test_path(str(row.get("file_path") or "")),
                members=shown,
                member_total=len(members),
            )
        )
        for edge in store.edges_by_source(qname, kinds=INHERIT_KINDS, limit=WALK):
            target = edge.get("target_qname")
            kind = str(edge.get("kind") or "")
            if isinstance(target, str) and target in present and kind in INHERIT_KINDS:
                inherit.append(Inheritance(qname, target, kind))
        assoc.extend(_associations(shown, qname, present))
        # Counted, never drawn: an arrow off a member the box does not list is unreadable, and a
        # silently missing one reads as "this type has no such dependency" (108/124).
        hidden.update(set(_associations(members[member_cap:], qname, present)) - set(assoc))
    inherit_sorted = tuple(
        sorted(set(inherit), key=lambda rel: (rel.kind, rel.source, rel.target))
    )
    assoc_sorted = tuple(sorted(set(assoc), key=lambda rel: (rel.source, rel.target, rel.label)))
    return tuple(boxes), inherit_sorted, assoc_sorted, len(hidden - set(assoc_sorted))


def _associations(
    members: Sequence[Member], qname: str, present: set[str]
) -> list[Association]:
    """Declared-type arrows a member set contributes — property, return, and param types."""
    found: list[Association] = []
    for member in members:
        hints = [member.declared_type, member.return_type, *(typ for _, typ in member.params)]
        for hint in hints:
            for target in declared_type_qnames(hint):
                if target in present and target != qname:
                    found.append(Association(qname, target, member.name))
    return found


def _members(store: GraphStore, qname: str) -> tuple[Member, ...]:
    """Every contained member, uncapped — the caller slices, so it can count what it dropped."""
    rows = store.edges_by_source(qname, kinds=("CONTAINS",), limit=WALK)
    targets = [str(edge["target_qname"]) for edge in rows if edge.get("target_qname")]
    found = store.nodes_by_qualified_names(targets, limit=8)
    members: list[Member] = []
    for target in sorted(targets):
        row = next(iter(found.get(target, ())), None)
        if row is None or row.get("kind") not in MEMBER_KINDS:
            continue
        extra = parse_json_field(row.get("extra"), {})
        extra_map = extra if isinstance(extra, dict) else {}
        params_raw = parse_json_field(row.get("params"), [])
        params: list[tuple[str, str | None]] = []
        if isinstance(params_raw, list):
            for item in params_raw:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    typ = item.get("type")
                    params.append((item["name"], typ if isinstance(typ, str) else None))
        declared = extra_map.get("type")
        declared_s = declared if isinstance(declared, str) else None
        kind = str(row["kind"])
        members.append(
            Member(
                name=str(row.get("name") or target),
                kind=kind,
                visibility=_visibility(parse_json_field(row.get("modifiers"), [])),
                params=tuple(params),
                return_type=declared_s if kind == "Method" else None,
                declared_type=declared_s if kind != "Method" else None,
            )
        )
    return tuple(members)


def _visibility(modifiers: object) -> str:
    names = modifiers if isinstance(modifiers, list) else []
    if "private" in names:
        return "-"
    if "protected" in names:
        return "#"
    return "+"


def _test_path(path: str) -> bool:
    """Path-segment test role (130) — ``is_test`` is unused by adapters today."""
    return any(
        responsibility_of_segment(segment) == LAYER_TESTS for segment in path.split("/")[:-1]
    )
