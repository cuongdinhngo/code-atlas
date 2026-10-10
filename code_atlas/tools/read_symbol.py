"""``read_symbol`` — source of one qname + contiguous doc comments above it (§12)."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal, NamedTuple

from code_atlas import contract
from code_atlas.build_info import maybe_server_provenance
from code_atlas.config import Config, clamp_limit
from code_atlas.containment import resolves_inside
from code_atlas.indexer import parse_file
from code_atlas.onboarding.class_diagram import parse_json_field
from code_atlas.source_slice import (
    BODY_LINE_THRESHOLD,
    clamp_line_range,
    declaration_line_count,
    declaration_slice,
)
from code_atlas.store import GraphStore, stored
from code_atlas.tools.freshness import (
    FreshnessGuard,
    attach_other_indexed_files_drifted,
    finalize_subject_checked_miss,
    miss_subject_path,
)
from code_atlas.tools.nav_result import (
    CAVEAT_MIRROR_TWIN,
    REASON_INDEX_STALE,
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_SUCH_SYMBOL,
    REASON_OK,
    REASON_PATH_EXCLUDED,
    REASON_PATH_OUTSIDE_ROOT,
    REASON_SEPARATOR_NORMALISED,
    REASON_SUBJECT_AMBIGUOUS,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_MEMBER_SEPARATOR,
    TRY_INSTEAD_HINT_PATH_PREFIX,
    TRY_INSTEAD_READ_SYMBOL,
    answered_about_ref_for,
    attach_ambiguous_definitions,
    attach_answered_about_ref,
    attach_authoritative_caveats,
    attach_limit_capped,
    attach_name_not_qualified,
    attach_next_tools,
    attach_result_kinds,
    attach_try_instead,
    classify_missing_subject,
    definition_sites,
    is_stub,
    is_under_path_prefix,
    require_path_prefix,
    shape_exact_miss,
)
from code_atlas.tools.search_symbol import _column_reference_targets

# Built from the one threshold site (288 / R6.7) — never a second numeric literal.


def _body_elided_hint(decl_start: int, decl_end: int, *, max_lines: int | None) -> str:
    # Name the cap that fired: the caller's max_lines, else the default threshold (337).
    cap = BODY_LINE_THRESHOLD if max_lines is None else f"max_lines={max_lines}"
    return (
        f"body elided above {cap} lines "
        f"(declaration {decl_start}–{decl_end}); pass full_body=true for the whole "
        "declaration, or line_start/line_end for a range within the symbol"
    )


# One page of CONTAINS edges for a Table — not the answer page; paging is separate (248).
_CONTAINS_WALK = 10_000

NAME = "read_symbol"

DetailLevel = Literal["minimal", "standard"]


class _BodyOpts(NamedTuple):
    """Caller body policy for 288 — defaults keep below-threshold payloads byte-identical (061)."""

    full_body: bool = False
    max_lines: int | None = None
    range_start: int | None = None
    range_end: int | None = None


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""
    empty_fn = _empty
    result_fn = _result

    def read_symbol(
        qname: str,
        detail_level: DetailLevel = "standard",
        limit: int | None = None,
        offset: int = 0,
        stored_fields: bool = False,
        full_body: bool = False,
        max_lines: int | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
        path_prefix: str | None = None,
    ) -> dict[str, object]:
        """Read just one symbol's source and its doc comment, without opening the whole file.

        ``standard`` returns ``line_start…line_end`` for ``qname`` plus the contiguous comment
        block above it; ``minimal`` returns the declaration range alone (no docblock), so ``source``
        matches the returned ``line_start``/``line_end`` (163). At ``standard`` a found
        **callable** hit also carries ``params`` (name + declared type, adapter spelling) when the
        language's adapter stamps that capability; otherwise ``params_not_captured_by_adapter`` —
        never an empty list that reads as "takes no arguments" (242 / R5.6). ``minimal``, and every
        non-callable kind, omit both (061). A found **Table** at ``standard`` carries a paged
        ``columns`` list (name + declared type + ``DEFAULT`` when present) from ``CONTAINS``, in
        DDL order — never the CREATE header as the product; a table with no indexed columns says
        so rather than returning an empty list (248 / 061). A found **Class** / **Interface** at
        ``standard`` carries ``supertypes`` (``EXTENDS`` / ``IMPLEMENTS`` in declaration order —
        resolved qname when linked, raw name + ``unresolved`` when not); an adapter that does not
        stamp ``inheritance`` discloses ``supertypes_not_captured_by_adapter`` (285 / R5.6); a type
        that declares none omits the field (061). ``limit`` / ``offset`` page that list
        only; other kinds ignore them. ``stored_fields=True`` adds which ``NODE_FIELDS`` are
        populated and which ``extra`` keys the node carries — key names only, never extra
        values (250). A ``Column`` also always lists ``references`` / ``references_unresolved``
        (empty = no FK). Default off: existing payloads stay byte-identical (061). On
        hash drift, reparses that one file inline (035); returns ``stale: true`` and
        ``reason=index_stale`` when the file is missing, no adapter owns it, or repair fails.
        Stub-indexed nodes carry ``stub: true`` (039). A qname with more than one definition
        returns ``reason=subject_ambiguous`` plus ``ambiguous_definitions`` and **no body** —
        empty ``source``, no ``file``/``line_*`` — so one region's code cannot be read while
        ignoring the list (070 warn; 078 refuse). ``try_instead`` points at ``read_symbol`` with
        ``path_prefix`` (327); ``path_prefix`` filters definition rows first (315's validator),
        and one that drops every definition answers ``path_excluded`` with their files (339).
        An untracked indexable file matching the subject is ``reason=not_indexed`` (092).
        An indexed file that now resolves outside the repo (swapped for a symlink since the build)
        answers ``reason=path_outside_root`` with ``file`` and an empty ``source`` (375).

        Bodies above BODY_LINE_THRESHOLD (600 lines — one site in ``source_slice``) elide by
        default: ``source`` is the signature line only, with ``body_elided: true``, ``line_count``,
        and a route to ``file_outline`` or a line range — never a silent mid-body cut (288). Pass
        ``full_body=true`` (or a ``max_lines`` at/above the span) for the whole declaration;
        ``line_start``/``line_end`` return exactly that clamped range inside the symbol.
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if max_lines is not None and max_lines < 1:
            raise ValueError(f"max_lines must be >= 1, got {max_lines}")
        if (line_start is None) ^ (line_end is None):
            raise ValueError("line_start and line_end must be passed together")
        if line_start is not None and line_start < 1:
            raise ValueError(f"line_start must be >= 1, got {line_start}")
        if line_end is not None and line_end < 1:
            raise ValueError(f"line_end must be >= 1, got {line_end}")
        path_prefix = require_path_prefix(path_prefix)
        body_opts = _BodyOpts(
            full_body=full_body,
            max_lines=max_lines,
            range_start=line_start,
            range_end=line_end,
        )
        if not config.db_path.is_file():
            return empty_fn(
                qname,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
            )
        # +1 so CA_MAX_RESULTS=1 cannot hide a second definition (078).
        fetch_limit = config.page_limit + 1
        with GraphStore(config.db_path) as store:

            about_ref = answered_about_ref_for(store)

            def stamped_result(*a, **k):
                k.setdefault("answered_about_ref", about_ref)
                return result_fn(*a, **k)

            def _stamp(payload: dict[str, object]) -> dict[str, object]:
                from code_atlas.tools.nav_result import attach_answered_about_ref

                return attach_answered_about_ref(payload, about_ref)

            rows = list(store.nodes_by_qualified_name(qname, limit=fetch_limit))
            guard = FreshnessGuard(config, store)
            if not rows:
                status = guard.ensure_miss(miss_subject_path(store, qname, limit=config.page_limit))
                if status == "stale":
                    return attach_try_instead(
                        stamped_result(
                            qname,
                            "",
                            detail_level=detail_level,
                            db_path=str(config.db_path),
                            index_root=config.index_root,
                            found=False,
                            stale=True,
                            reason=REASON_INDEX_STALE,
                        ),
                        TRY_INSTEAD_FILE_OUTLINE,
                    )
                if status == "repaired":
                    rows = list(store.nodes_by_qualified_name(qname, limit=fetch_limit))
                if not rows:
                    normalised = _separator_normalised_hit(
                        store,
                        config,
                        qname,
                        detail_level=detail_level,
                        fetch_limit=fetch_limit,
                        guard=guard,
                        stored_fields=stored_fields,
                        body_opts=body_opts,
                    )
                    if normalised is not None:
                        return _stamp(normalised)
                    qname, rows, miss = _resolve_miss(
                        store, config, qname, detail_level=detail_level, fetch_limit=fetch_limit
                    )
                    if miss is not None:
                        return finalize_subject_checked_miss(_stamp(miss), guard)
            # Refuse before freshness — the list needs no file bytes (078 review).
            # path_prefix filters definition rows before the multiplicity test (327).
            rows, prefix_miss = _apply_path_prefix(
                rows, path_prefix, qname=qname, detail_level=detail_level, config=config
            )
            if prefix_miss is not None:
                return _stamp(prefix_miss)
            if len(rows) > 1:
                return _stamp(
                    _refuse_ambiguous(qname, rows, detail_level=detail_level, config=config)
                )
            node = rows[0]
            rel = str(node["file_path"])
            if not resolves_inside(config.root, config.root / rel):
                # 375: refuse before the repair, which would re-parse and store the outside file.
                return _stamp(_outside_root_refusal(qname, rel, node, config, detail_level))
            status = guard.ensure(rel)
            parsed = None
            if status == "stale" and guard.build_held:
                # 365: a writer holds the index, so read the file through its adapter instead.
                parsed = _parsed_node(config, rel, str(node["qualified_name"]))
            if parsed is not None:
                node = parsed
            elif status == "stale":
                stale = stamped_result(
                    qname,
                    "",
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    index_root=config.index_root,
                    found=True,
                    stale=True,
                    reason=REASON_INDEX_STALE,
                    file=rel,
                )
                _attach_stored_fields(stale, store, node, stored_fields=stored_fields)
                return stale
            if status == "repaired":
                rows = list(store.nodes_by_qualified_name(qname, limit=fetch_limit))
                if not rows:
                    normalised = _separator_normalised_hit(
                        store,
                        config,
                        qname,
                        detail_level=detail_level,
                        fetch_limit=fetch_limit,
                        guard=guard,
                        stored_fields=stored_fields,
                        body_opts=body_opts,
                    )
                    if normalised is not None:
                        return _stamp(normalised)
                    qname, rows, miss = _resolve_miss(
                        store, config, qname, detail_level=detail_level, fetch_limit=fetch_limit
                    )
                    if miss is not None:
                        return _stamp(miss)
                rows, prefix_miss = _apply_path_prefix(
                    rows, path_prefix, qname=qname,
                    detail_level=detail_level, config=config,
                )
                if prefix_miss is not None:
                    return _stamp(prefix_miss)
                if len(rows) > 1:
                    return _stamp(
                        _refuse_ambiguous(
                            qname, rows, detail_level=detail_level, config=config
                        )
                    )
                node = rows[0]
                rel = str(node["file_path"])
            path = config.root / rel
            start_raw = node["line_start"]
            if not isinstance(start_raw, int):
                raise TypeError(f"line_start must be int, got {type(start_raw).__name__}")
            start = start_raw
            end_raw = node["line_end"]
            end = end_raw if isinstance(end_raw, int) else start
            payload = _stamp(
                _found_body_payload(
                    qname,
                    path,
                    rel,
                    start,
                    end,
                    root=config.root,
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    index_root=config.index_root,
                    reason=REASON_OK,
                    stub=is_stub(node.get("extra")),
                    body_opts=body_opts,
                )
            )
            if payload.get("reason") == REASON_PATH_OUTSIDE_ROOT:
                return payload
            if detail_level == "standard":
                _attach_params(payload, store, node, rel)
                _attach_columns(payload, store, node, config=config, limit=limit, offset=offset)
                _attach_supertypes(payload, store, node, rel)
            _attach_stored_fields(payload, store, node, stored_fields=stored_fields)
            if parsed is not None:
                # The body is the working tree's, not the built ref's: claim no ref for it.
                payload["parsed_unstored"] = True
                attach_answered_about_ref(payload, None)
            _attach_mirror_twin(
                payload,
                store,
                rel,
                kind=str(node["kind"]),
                name=str(node["name"]),
            )
            attach_other_indexed_files_drifted(payload, guard)
            return attach_next_tools(payload, str(node["kind"]))

    return read_symbol


def _parsed_node(config: Config, rel: str, qname: str) -> dict[str, object] | None:
    """The one node ``qname`` names in ``rel``'s current bytes, parsed and never stored (365)."""
    try:
        parsed = parse_file(config, rel)
    except (OSError, TimeoutError):
        return None
    if parsed is None or not parsed[1].ok:
        return None
    hits = [n for n in parsed[1].nodes if n.get("qualified_name") == qname]
    if len(hits) != 1:
        return None
    # Shaped as a stored row (JSON text for `extra` and friends), so row readers agree.
    node = {key: stored(value) for key, value in hits[0].items()}
    node.setdefault("file_path", rel)
    return node


def _outside_root_refusal(
    qname: str, rel: str, node: dict[str, object], config: Config, detail_level: str
) -> dict[str, object]:
    """375: the row's file now resolves out of the repo — no text and no graph field leaves."""
    return _result(
        qname,
        "",
        detail_level=detail_level,
        db_path=str(config.db_path),
        index_root=config.index_root,
        found=True,
        stale=False,
        reason=REASON_PATH_OUTSIDE_ROOT,
        file=rel,
        stub=is_stub(node.get("extra")),
    )


def _effective_body_cap(opts: _BodyOpts) -> int | None:
    """None = unlimited; otherwise the inclusive line ceiling before elision."""
    if opts.full_body:
        return None
    if opts.max_lines is not None:
        return opts.max_lines
    return BODY_LINE_THRESHOLD


def _found_body_payload(
    qname: str,
    path: Path,
    rel: str,
    decl_start: int,
    decl_end: int,
    *,
    root: Path,
    detail_level: str,
    db_path: str,
    index_root: str,
    reason: str,
    stub: bool,
    body_opts: _BodyOpts,
) -> dict[str, object]:
    """Build a found-hit payload, applying range / elision / full-body policy (288)."""
    if not resolves_inside(root, path):
        # 375: indexed as a file, since swapped for a link out of the repo — no text leaves.
        return _result(
            qname,
            "",
            detail_level=detail_level,
            db_path=db_path,
            index_root=index_root,
            found=True,
            stale=False,
            reason=REASON_PATH_OUTSIDE_ROOT,
            file=rel,
            stub=stub,
        )
    span = declaration_line_count(decl_start, decl_end)
    if body_opts.range_start is not None and body_opts.range_end is not None:
        start, end = clamp_line_range(
            decl_start,
            decl_end,
            from_line=body_opts.range_start,
            to_line=body_opts.range_end,
        )
        source = declaration_slice(path, start, end, root=root, include_comments=False)
        return _result(
            qname,
            source,
            detail_level=detail_level,
            db_path=db_path,
            index_root=index_root,
            found=True,
            stale=False,
            reason=reason,
            file=rel,
            line_start=start,
            line_end=end,
            stub=stub,
        )
    cap = _effective_body_cap(body_opts)
    if cap is not None and span > cap:
        # Signature only — line_start/line_end match source (163); full span is line_count + hint.
        signature = declaration_slice(
            path, decl_start, decl_start, root=root, include_comments=False
        )
        payload = _result(
            qname,
            signature,
            detail_level=detail_level,
            db_path=db_path,
            index_root=index_root,
            found=True,
            stale=False,
            reason=reason,
            file=rel,
            line_start=decl_start,
            line_end=decl_start,
            stub=stub,
        )
        payload["body_elided"] = True
        payload["line_count"] = span
        return attach_try_instead(
            payload,
            TRY_INSTEAD_FILE_OUTLINE,
            _body_elided_hint(decl_start, decl_end, max_lines=body_opts.max_lines),
        )
    source = _slice(path, decl_start, decl_end, detail_level, root=root)
    return _result(
        qname,
        source,
        detail_level=detail_level,
        db_path=db_path,
        index_root=index_root,
        found=True,
        stale=False,
        reason=reason,
        file=rel,
        line_start=decl_start,
        line_end=decl_end,
        stub=stub,
    )


def _attach_stored_fields(
    payload: dict[str, object],
    store: GraphStore,
    node: Mapping[str, object],
    *,
    stored_fields: bool,
) -> None:
    """List populated NODE_FIELDS + extra keys; Column also lists 239's REFERENCES pair (250)."""
    if not stored_fields:
        return
    node_fields = [
        field
        for field in contract.NODE_FIELDS
        if field != "extra" and _field_is_populated(node, field)
    ]
    extra = parse_json_field(node.get("extra"), {})
    extra_keys = sorted(str(key) for key in extra) if isinstance(extra, dict) else []
    block: dict[str, object] = {"node_fields": node_fields, "extra_keys": extra_keys}
    if str(node["kind"]) == contract.COLUMN_KIND:
        resolved, unresolved = _column_reference_targets(store, str(node["qualified_name"]))
        block["references"] = resolved
        block["references_unresolved"] = unresolved
    payload["stored_fields"] = block


def _field_is_populated(node: Mapping[str, object], field: str) -> bool:
    try:
        value = node[field]
    except (KeyError, IndexError):
        return False
    return value is not None and value != ""


def _attach_columns(
    payload: dict[str, object],
    store: GraphStore,
    node: dict[str, object],
    *,
    config: Config,
    limit: int | None,
    offset: int,
) -> None:
    """Surface a Table's columns via CONTAINS; non-Table stays byte-identical (248 / 061)."""
    if str(node["kind"]) != contract.TABLE_KIND:
        return
    # The CREATE header is a point, not the product — columns are the answer (AC1).
    payload["source"] = ""
    payload.pop("body_elided", None)
    payload.pop("line_count", None)
    payload.pop("try_instead", None)
    payload.pop("try_instead_hint", None)
    edges = store.edges_by_source(
        str(node["qualified_name"]),
        kinds=(contract.CONTAINS,),
        limit=_CONTAINS_WALK,
    )
    if len(edges) >= _CONTAINS_WALK:
        # Past one walk the column list and `total_count` are both short. Say so rather than let a
        # capped scan read as the whole table (R5.6).
        payload["columns_scan_capped_to"] = _CONTAINS_WALK
    # `_EDGE_ORDER` alphabetises target_raw; edge id preserves DDL emission order (scan.js).
    # Filter to Column before paging — Table also CONTAINS ForeignKey (scan.js / 236).
    candidates: list[str] = []
    seen: set[str] = set()
    for edge in sorted(edges, key=lambda row: int(str(row["id"]))):
        qname = str(edge.get("target_qname") or edge["target_raw"])
        if qname in seen:
            continue
        seen.add(qname)
        candidates.append(qname)
    found_all = (
        store.nodes_by_qualified_names(candidates, kind=contract.COLUMN_KIND, limit=1)
        if candidates
        else {}
    )
    ordered = [qname for qname in candidates if found_all.get(qname)]
    if not ordered:
        payload["no_indexed_columns"] = True
        return
    cap, clamped = clamp_limit(limit, config.page_limit)
    page_qnames = ordered[offset : offset + cap]
    columns = [_column_row(found_all[qname][0]) for qname in page_qnames]
    total = len(ordered)
    payload["columns"] = columns
    payload["total_count"] = total
    payload["results_offset"] = offset
    truncated = offset + len(page_qnames) < total
    payload["truncated"] = truncated
    attach_limit_capped(payload, cap=cap, clamped=clamped)
    if truncated:
        attach_result_kinds(payload, {contract.COLUMN_KIND: total})


def _column_row(node: dict[str, object]) -> dict[str, object]:
    """One column: name + declared type + DEFAULT when present. Never invent 247 fields (R5.6)."""
    entry: dict[str, object] = {"name": str(node["name"])}
    extra_raw = node.get("extra")
    extra: dict[str, object] = {}
    if isinstance(extra_raw, str) and extra_raw:
        try:
            parsed = json.loads(extra_raw)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            extra = parsed
    elif isinstance(extra_raw, dict):
        extra = extra_raw
    typ = extra.get("type") or extra.get("data_type")
    if isinstance(typ, str) and typ:
        entry["type"] = typ
    default = extra.get("default")
    if isinstance(default, str):
        entry["default"] = default
    return entry


def _attach_params(
    payload: dict[str, object],
    store: GraphStore,
    node: dict[str, object],
    file_path: str,
) -> None:
    """Surface ``params`` when the stamp says the adapter captures them; else disclose (242).

    Callable kinds only: a Class has no parameter list, so both the field and its disclosure
    would be a claim about a question the subject never asks (061 omit-when-empty, R5.6).
    """
    if str(node["kind"]) not in contract.CALLABLE_KINDS:
        return
    caps = store.stamped_capabilities_by_language()
    language = store.language_of_file(file_path)
    if caps is None or language is None or not (caps.get(language) or {}).get("params", False):
        payload["params_not_captured_by_adapter"] = True
        return
    params_raw = parse_json_field(node.get("params"), [])
    params: list[dict[str, object]] = []
    if isinstance(params_raw, list):
        for item in params_raw:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            entry: dict[str, object] = {"name": item["name"]}
            typ = item.get("type")
            if isinstance(typ, str):
                entry["type"] = typ
            params.append(entry)
    payload["params"] = params


def _attach_supertypes(
    payload: dict[str, object],
    store: GraphStore,
    node: dict[str, object],
    file_path: str,
) -> None:
    """Surface EXTENDS/IMPLEMENTS for Class/Interface; disclose when adapter omits them (285)."""
    if str(node["kind"]) not in contract.SUPERTYPE_SUBJECT_KINDS:
        return
    caps = store.stamped_capabilities_by_language()
    language = store.language_of_file(file_path)
    if (
        caps is None
        or language is None
        or not (caps.get(language) or {}).get("inheritance", False)
    ):
        payload["supertypes_not_captured_by_adapter"] = True
        return
    edges = store.edges_by_source(
        str(node["qualified_name"]),
        kinds=contract.IMPL_KINDS,
        limit=_CONTAINS_WALK,
    )
    if not edges:
        return  # Declares none — omit, never an empty list (061 / R5.6).
    # Edge id preserves declaration order (same rule as Table columns / 248).
    ordered = sorted(edges, key=lambda row: int(str(row["id"])))
    rows: list[dict[str, object]] = []
    for edge in ordered:
        kind = str(edge["kind"])
        linked = edge.get("target_qname")
        entry: dict[str, object] = {"kind": kind}
        if isinstance(linked, str) and linked:
            entry["qname"] = linked
        else:
            entry["name"] = str(edge["target_raw"])
            entry["unresolved"] = True
        rows.append(entry)
    payload["supertypes"] = rows


def _attach_mirror_twin(
    payload: dict[str, object],
    store: GraphStore,
    file_path: str,
    *,
    kind: str,
    name: str,
) -> None:
    """Name an indexed mirror twin on a found hit, or the honest negative (286/331).

    Every kind on a stamped pair — the belief "this is the code that runs" forms on Class
    and Method alike (ticket Scope). No stamp ⇒ no cost (061).
    """
    from code_atlas.mirror_search import attach_mirror_read_fields, load_mirror_search_stamp

    stamp = load_mirror_search_stamp(store)
    if not stamp or not stamp.get("pairs"):
        return
    indexed = frozenset(store.file_paths())
    if attach_mirror_read_fields(
        payload,
        file_path,
        stamp,
        indexed,
        kind=kind,
        name=name,
        store=store,
    ):
        attach_authoritative_caveats(payload, [CAVEAT_MIRROR_TWIN])


def _apply_path_prefix(
    rows: list[dict[str, object]],
    path_prefix: str | None,
    *,
    qname: str,
    detail_level: str,
    config: Config,
) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    """Filter definition rows by path_prefix; empty ⇒ path_excluded naming where it is (327/339)."""
    if path_prefix is None:
        return rows, None
    kept = [row for row in rows if is_under_path_prefix(str(row["file_path"]), path_prefix)]
    if kept:
        return kept, None
    # The symbol is indexed, only outside the filter — search_symbol's shape for that miss (315).
    miss = _miss_result(
        qname, detail_level=detail_level, config=config, reason=REASON_PATH_EXCLUDED
    )
    miss["path_excluded"] = sorted({str(row["file_path"]) for row in rows})
    miss["path_prefix"] = path_prefix
    return [], miss


def _refuse_ambiguous(
    qname: str,
    rows: list[dict[str, object]],
    *,
    detail_level: str,
    config: Config,
) -> dict[str, object]:
    """No body when N>1 — list the sites; never reason=ok with empty source (075/078)."""
    sites = definition_sites(rows)
    stub = any(is_stub(row.get("extra")) for row in rows)
    return attach_try_instead(
        attach_ambiguous_definitions(
            _result(
                qname,
                "",
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
                found=False,
                stale=False,
                reason=REASON_SUBJECT_AMBIGUOUS,
                stub=stub,
            ),
            sites,
        ),
        TRY_INSTEAD_READ_SYMBOL,
        TRY_INSTEAD_HINT_PATH_PREFIX,
    )


def _separator_normalised_hit(
    store: GraphStore,
    config: Config,
    qname: str,
    *,
    detail_level: str,
    fetch_limit: int,
    guard: FreshnessGuard,
    stored_fields: bool = False,
    body_opts: _BodyOpts | None = None,
) -> dict[str, object] | None:
    """If the last separator spelled as MEMBER_SEPARATOR uniquely hits, return that near-miss (249).

    Keeps the asked ``qname`` and sets ``reason=separator_normalised`` — never ``ok`` (R5.6).
    """
    opts = body_opts if body_opts is not None else _BodyOpts()
    alt = contract.member_separator_variant(qname)
    if alt is None:
        return None
    rows = list(store.nodes_by_qualified_name(alt, limit=fetch_limit))
    if len(rows) != 1:
        return None
    node = rows[0]
    rel = str(node["file_path"])
    if not resolves_inside(config.root, config.root / rel):
        return _outside_root_refusal(qname, rel, node, config, detail_level)
    status = guard.ensure(rel)
    if status == "stale":
        return attach_try_instead(
            _result(
                qname,
                "",
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
                found=False,
                stale=True,
                reason=REASON_INDEX_STALE,
            ),
            TRY_INSTEAD_FILE_OUTLINE,
        )
    if status == "repaired":
        rows = list(store.nodes_by_qualified_name(alt, limit=fetch_limit))
        if len(rows) != 1:
            return None
        node = rows[0]
        rel = str(node["file_path"])
    path = config.root / rel
    start_raw = node["line_start"]
    if not isinstance(start_raw, int):
        raise TypeError(f"line_start must be int, got {type(start_raw).__name__}")
    start = start_raw
    end_raw = node["line_end"]
    end = end_raw if isinstance(end_raw, int) else start
    payload = _found_body_payload(
        qname,
        path,
        rel,
        start,
        end,
        root=config.root,
        detail_level=detail_level,
        db_path=str(config.db_path),
        index_root=config.index_root,
        reason=REASON_SEPARATOR_NORMALISED,
        stub=is_stub(node.get("extra")),
        body_opts=opts,
    )
    if payload.get("reason") == REASON_PATH_OUTSIDE_ROOT:
        return payload
    if detail_level == "standard":
        _attach_params(payload, store, node, rel)
    _attach_stored_fields(payload, store, node, stored_fields=stored_fields)
    attach_other_indexed_files_drifted(payload, guard)
    # Prefer the member-separator hint; keep an elision route if the body was also elided.
    if payload.get("body_elided") is True:
        return payload
    return attach_try_instead(payload, TRY_INSTEAD_FILE_OUTLINE, TRY_INSTEAD_HINT_MEMBER_SEPARATOR)


def _resolve_miss(
    store: GraphStore,
    config: Config,
    qname: str,
    *,
    detail_level: str,
    fetch_limit: int,
) -> tuple[str, list[dict[str, object]], dict[str, object] | None]:
    """Classify an exact miss: re-point a unique candidate (returns its rows), else a truthful miss.

    Returns ``(qname, rows, miss)`` — when ``rows`` is non-empty the caller reads on with the
    (possibly re-pointed) ``qname``; when ``miss`` is set the caller returns it verbatim.
    """
    resolution = classify_missing_subject(store, qname, limit=config.page_limit)
    if resolution.status == "resolved_unique":
        rows = list(store.nodes_by_qualified_name(resolution.qname, limit=fetch_limit))
        if rows:
            return resolution.qname, rows, None
    if resolution.status == "ambiguous":
        return (
            qname,
            [],
            attach_name_not_qualified(
                _miss_result(
                    qname,
                    detail_level=detail_level,
                    config=config,
                    reason=REASON_NAME_NOT_QUALIFIED,
                ),
                resolution.candidate_count,
            ),
        )
    if resolution.status == "untracked":
        return (
            qname,
            [],
            shape_exact_miss(
                _miss_result(
                    qname,
                    detail_level=detail_level,
                    config=config,
                    reason=REASON_NO_SUCH_SYMBOL,
                ),
                resolution,
            ),
        )
    return (
        qname,
        [],
        shape_exact_miss(
            _miss_result(
                qname, detail_level=detail_level, config=config, reason=REASON_NO_SUCH_SYMBOL
            ),
            resolution,
        ),
    )


def _miss_result(
    qname: str, *, detail_level: str, config: Config, reason: str
) -> dict[str, object]:
    """A not-found payload that names which kind of nothing this is — never reason=ok (075)."""
    return _result(
        qname,
        "",
        detail_level=detail_level,
        db_path=str(config.db_path),
        index_root=config.index_root,
        found=False,
        reason=reason,
    )


def _slice(path: Path, line_start: int, line_end: int, detail_level: str, *, root: Path) -> str:
    """``standard`` = declaration + docblock above; ``minimal`` = the declaration range alone (163).

    ``minimal``'s slice matches its own ``line_start``/``line_end``, closing the 8-H mismatch where
    ``source`` silently carried the comment block the range did not name.
    """
    return declaration_slice(
        path, line_start, line_end, root=root, include_comments=detail_level != "minimal"
    )


def _empty(
    qname: str,
    *,
    detail_level: str,
    db_path: str,
    index_root: str,
    answered_about_ref: str | None = None,
) -> dict[str, object]:
    del db_path
    from code_atlas.tools.nav_result import attach_answered_about_ref

    return attach_answered_about_ref(
        {
            "indexed": False,
            "qname": qname,
            "found": False,
            "stale": False,
            "source": "",
            "index_root": index_root,
            **maybe_server_provenance(detail_level),
        },
        answered_about_ref,
    )


def _result(
    qname: str,
    source: str,
    *,
    detail_level: str,
    db_path: str,
    index_root: str,
    found: bool,
    stale: bool = False,
    reason: str | None = None,
    file: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
    stub: bool = False,
    answered_about_ref: str | None = None,
) -> dict[str, object]:
    del db_path
    from code_atlas.tools.nav_result import attach_answered_about_ref

    payload: dict[str, object] = {
        "indexed": True,
        "qname": qname,
        "found": found,
        "stale": stale,
        "source": source,
        "index_root": index_root,
    }
    if reason is not None:
        payload["reason"] = reason
    if file is not None:
        payload["file"] = file
    if found and not stale and line_start is not None:
        payload["line_start"] = line_start
        payload["line_end"] = line_end
    if stub:
        payload[contract.STUB_FLAG] = True
    payload.update(maybe_server_provenance(detail_level))
    return attach_answered_about_ref(payload, answered_about_ref)
