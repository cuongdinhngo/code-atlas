"""``read_symbol`` — source of one qname + contiguous doc comments above it (§12)."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

from code_atlas import contract
from code_atlas.config import Config
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
    attach_try_instead,
    classify_missing_subject,
    definition_sites,
    is_stub,
    shape_exact_miss,
)

NAME = "read_symbol"

DetailLevel = Literal["minimal", "standard"]

# Heuristic only: adapters should eventually emit a doc range on the node (contract follow-up).
# Union of common comment leaders — not a language branch, but still language knowledge in core.
_COMMENT = re.compile(r"^\s*(#|//|/\*|\*|\*/)")


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def read_symbol(qname: str, detail_level: DetailLevel = "standard") -> dict[str, object]:
        """Read just one symbol's source and its doc comment, without opening the whole file.

        Returns ``line_start…line_end`` for ``qname`` plus contiguous comments above. On hash drift,
        reparses that one file inline (035); returns ``stale: true`` and ``reason=index_stale`` when
        the file is missing, no adapter owns it, or repair fails. Stub-indexed nodes carry
        ``stub: true`` (039). A qname with more than one definition returns
        ``reason=subject_ambiguous`` plus ``ambiguous_definitions`` and **no body** — empty
        ``source``, no ``file``/``line_*`` — so one region's code cannot be read while ignoring the
        list (070 warn; 078 refuse). ``try_instead`` points at ``search_symbol`` / ``file_outline``.
        An untracked indexable file matching the subject is ``reason=not_indexed`` (092).
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
            source = _slice(path, start, end)
            return _result(
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

    return read_symbol


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


def _slice(path: Path, line_start: int, line_end: int) -> str:
    """Lines ``line_start…line_end`` (1-based, inclusive) plus contiguous comments above."""
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    if line_start < 1 or line_start > len(lines):
        return ""
    end = min(max(line_end, line_start), len(lines))
    top = _comment_top(lines, line_start)
    return "".join(lines[top - 1 : end])


def _comment_top(lines: Sequence[str], line_start: int) -> int:
    """Walk upward from the line above ``line_start`` while lines look like comments."""
    top = line_start
    i = line_start - 1  # 1-based index of the line above the declaration
    while i >= 1:
        text = lines[i - 1]
        if not text.strip():
            break
        if not _COMMENT.match(text):
            break
        top = i
        i -= 1
    return top


def _empty(
    qname: str, *, detail_level: str, db_path: str, index_root: str
) -> dict[str, object]:
    del detail_level, db_path
    return {
        "indexed": False,
        "qname": qname,
        "found": False,
        "stale": False,
        "source": "",
        "index_root": index_root,
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
    del detail_level, db_path
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
    return payload
