"""``read_symbol`` — source of one qname + contiguous doc comments above it (§12)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from code_atlas import contract
from code_atlas.build_info import maybe_server_provenance
from code_atlas.config import Config
from code_atlas.onboarding.class_diagram import parse_json_field
from code_atlas.source_slice import declaration_slice
from code_atlas.store import GraphStore
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_SUCH_SYMBOL,
    REASON_OK,
    REASON_SUBJECT_AMBIGUOUS,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_SEARCH_SYMBOL,
    attach_ambiguous_definitions,
    attach_name_not_qualified,
    attach_next_tools,
    attach_try_instead,
    classify_missing_subject,
    definition_sites,
    is_stub,
    shape_exact_miss,
)

NAME = "read_symbol"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def read_symbol(qname: str, detail_level: DetailLevel = "standard") -> dict[str, object]:
        """Read just one symbol's source and its doc comment, without opening the whole file.

        ``standard`` returns ``line_start…line_end`` for ``qname`` plus the contiguous comment
        block above it; ``minimal`` returns the declaration range alone (no docblock), so ``source``
        matches the returned ``line_start``/``line_end`` (163). At ``standard`` a found
        **callable** hit also carries ``params`` (name + declared type, adapter spelling) when the
        language's adapter stamps that capability; otherwise ``params_not_captured_by_adapter`` —
        never an empty list that reads as "takes no arguments" (242 / R5.6). ``minimal``, and every
        non-callable kind, omit both (061). On
        hash drift, reparses that one file inline (035); returns ``stale: true`` and
        ``reason=index_stale`` when the file is missing, no adapter owns it, or repair fails.
        Stub-indexed nodes carry ``stub: true`` (039). A qname with more than one definition
        returns ``reason=subject_ambiguous`` plus ``ambiguous_definitions`` and **no body** —
        empty ``source``, no ``file``/``line_*`` — so one region's code cannot be read while
        ignoring the list (070 warn; 078 refuse). ``try_instead`` points at ``search_symbol`` /
        ``file_outline``. An untracked indexable file matching the subject is
        ``reason=not_indexed`` (092).
        """
        if not config.db_path.is_file():
            return _empty(
                qname,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
            )
        # +1 so CA_MAX_RESULTS=1 cannot hide a second definition (078).
        fetch_limit = config.max_results + 1
        with GraphStore(config.db_path) as store:
            rows = list(store.nodes_by_qualified_name(qname, limit=fetch_limit))
            guard = FreshnessGuard(config, store)
            if not rows:
                status = guard.ensure_miss()
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
                    qname, rows, miss = _resolve_miss(
                        store, config, qname, detail_level=detail_level, fetch_limit=fetch_limit
                    )
                    if miss is not None:
                        return miss
            # Refuse before freshness — the list needs no file bytes (078 review).
            if len(rows) > 1:
                return _refuse_ambiguous(qname, rows, detail_level=detail_level, config=config)
            node = rows[0]
            rel = str(node["file_path"])
            status = guard.ensure(rel)
            if status == "stale":
                return _result(
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
            if status == "repaired":
                rows = list(store.nodes_by_qualified_name(qname, limit=fetch_limit))
                if not rows:
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
            return attach_next_tools(payload, str(node["kind"]))

    return read_symbol


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
    resolution = classify_missing_subject(store, qname, limit=config.max_results)
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
