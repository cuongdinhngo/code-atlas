"""``read_symbol`` — source of one qname + contiguous doc comments above it (§12)."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal

from code_atlas import contract
from code_atlas.build_info import maybe_server_provenance
from code_atlas.config import Config, clamp_limit
from code_atlas.onboarding.class_diagram import parse_json_field
from code_atlas.source_slice import declaration_slice
from code_atlas.store import GraphStore
from code_atlas.tools.freshness import (
    FreshnessGuard,
    attach_other_indexed_files_drifted,
    finalize_subject_checked_miss,
    nameable_subject_path,
)
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_SUCH_SYMBOL,
    REASON_OK,
    REASON_SEPARATOR_NORMALISED,
    REASON_SUBJECT_AMBIGUOUS,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_MEMBER_SEPARATOR,
    TRY_INSTEAD_SEARCH_SYMBOL,
    attach_ambiguous_definitions,
    attach_limit_capped,
    attach_name_not_qualified,
    attach_next_tools,
    attach_result_kinds,
    attach_try_instead,
    classify_missing_subject,
    definition_sites,
    is_stub,
    shape_exact_miss,
)
from code_atlas.tools.search_symbol import _column_reference_targets

# One page of CONTAINS edges for a Table — not the answer page; paging is separate (248).
_CONTAINS_WALK = 10_000

NAME = "read_symbol"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def read_symbol(
        qname: str,
        detail_level: DetailLevel = "standard",
        limit: int | None = None,
        offset: int = 0,
        stored_fields: bool = False,
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
        so rather than returning an empty list (248 / 061). ``limit`` / ``offset`` page that list
        only; other kinds ignore them. ``stored_fields=True`` adds which ``NODE_FIELDS`` are
        populated and which ``extra`` keys the node carries — key names only, never extra
        values (250). A ``Column`` also always lists ``references`` / ``references_unresolved``
        (empty = no FK). Default off: existing payloads stay byte-identical (061). On
        hash drift, reparses that one file inline (035); returns ``stale: true`` and
        ``reason=index_stale`` when the file is missing, no adapter owns it, or repair fails.
        Stub-indexed nodes carry ``stub: true`` (039). A qname with more than one definition
        returns ``reason=subject_ambiguous`` plus ``ambiguous_definitions`` and **no body** —
        empty ``source``, no ``file``/``line_*`` — so one region's code cannot be read while
        ignoring the list (070 warn; 078 refuse). ``try_instead`` points at ``search_symbol`` /
        ``file_outline``. An untracked indexable file matching the subject is
        ``reason=not_indexed`` (092).
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if not config.db_path.is_file():
            return _empty(
                qname,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
            )
        # +1 so CA_MAX_RESULTS=1 cannot hide a second definition (078).
        fetch_limit = config.page_limit + 1
        with GraphStore(config.db_path) as store:
            rows = list(store.nodes_by_qualified_name(qname, limit=fetch_limit))
            guard = FreshnessGuard(config, store)
            if not rows:
                status = guard.ensure_miss(nameable_subject_path(store, qname))
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
                    )
                    if normalised is not None:
                        return normalised
                    qname, rows, miss = _resolve_miss(
                        store, config, qname, detail_level=detail_level, fetch_limit=fetch_limit
                    )
                    if miss is not None:
                        return finalize_subject_checked_miss(miss, guard)
            # Refuse before freshness — the list needs no file bytes (078 review).
            if len(rows) > 1:
                return _refuse_ambiguous(qname, rows, detail_level=detail_level, config=config)
            node = rows[0]
            rel = str(node["file_path"])
            status = guard.ensure(rel)
            if status == "stale":
                stale = _result(
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
                    )
                    if normalised is not None:
                        return normalised
                    qname, rows, miss = _resolve_miss(
                        store, config, qname, detail_level=detail_level, fetch_limit=fetch_limit
                    )
                    if miss is not None:
                        return miss
                if len(rows) > 1:
                    return _refuse_ambiguous(qname, rows, detail_level=detail_level, config=config)
                node = rows[0]
                rel = str(node["file_path"])
            path = config.root / rel
            start_raw = node["line_start"]
            if not isinstance(start_raw, int):
                raise TypeError(f"line_start must be int, got {type(start_raw).__name__}")
            start = start_raw
            end_raw = node["line_end"]
            end = end_raw if isinstance(end_raw, int) else start
            source = _slice(path, start, end, detail_level)
            payload = _result(
                qname,
                source,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
                found=True,
                stale=False,
                reason=REASON_OK,
                file=rel,
                line_start=start,
                line_end=end,
                stub=is_stub(node.get("extra")),
            )
            if detail_level == "standard":
                _attach_params(payload, store, node, rel)
                _attach_columns(payload, store, node, config=config, limit=limit, offset=offset)
            _attach_stored_fields(payload, store, node, stored_fields=stored_fields)
            attach_other_indexed_files_drifted(payload, guard)
            return attach_next_tools(payload, str(node["kind"]))

    return read_symbol


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
        TRY_INSTEAD_SEARCH_SYMBOL,
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
) -> dict[str, object] | None:
    """If the last separator spelled as MEMBER_SEPARATOR uniquely hits, return that near-miss (249).

    Keeps the asked ``qname`` and sets ``reason=separator_normalised`` — never ``ok`` (R5.6).
    """
    alt = contract.member_separator_variant(qname)
    if alt is None:
        return None
    rows = list(store.nodes_by_qualified_name(alt, limit=fetch_limit))
    if len(rows) != 1:
        return None
    node = rows[0]
    rel = str(node["file_path"])
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
    source = _slice(path, start, end, detail_level)
    payload = _result(
        qname,
        source,
        detail_level=detail_level,
        db_path=str(config.db_path),
        index_root=config.index_root,
        found=True,
        stale=False,
        reason=REASON_SEPARATOR_NORMALISED,
        file=rel,
        line_start=start,
        line_end=end,
        stub=is_stub(node.get("extra")),
    )
    if detail_level == "standard":
        _attach_params(payload, store, node, rel)
    _attach_stored_fields(payload, store, node, stored_fields=stored_fields)
    attach_other_indexed_files_drifted(payload, guard)
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
        return qname, [], attach_name_not_qualified(
            _miss_result(qname, detail_level=detail_level, config=config,
                         reason=REASON_NAME_NOT_QUALIFIED),
            resolution.candidate_count,
        )
    if resolution.status == "untracked":
        return qname, [], shape_exact_miss(
            _miss_result(
                qname,
                detail_level=detail_level,
                config=config,
                reason=REASON_NO_SUCH_SYMBOL,
            ),
            resolution,
        )
    return qname, [], _miss_result(
        qname, detail_level=detail_level, config=config, reason=REASON_NO_SUCH_SYMBOL
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


def _slice(path: Path, line_start: int, line_end: int, detail_level: str) -> str:
    """``standard`` = declaration + docblock above; ``minimal`` = the declaration range alone (163).

    ``minimal``'s slice matches its own ``line_start``/``line_end``, closing the 8-H mismatch where
    ``source`` silently carried the comment block the range did not name.
    """
    return declaration_slice(
        path, line_start, line_end, include_comments=detail_level != "minimal"
    )


def _empty(
    qname: str, *, detail_level: str, db_path: str, index_root: str
) -> dict[str, object]:
    del db_path
    return {
        "indexed": False,
        "qname": qname,
        "found": False,
        "stale": False,
        "source": "",
        "index_root": index_root,
        **maybe_server_provenance(detail_level),
    }


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
) -> dict[str, object]:
    del db_path
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
    return payload
