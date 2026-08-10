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
    REASON_OK,
    TRY_INSTEAD_FILE_OUTLINE,
    attach_ambiguous_definitions,
    attach_try_instead,
    definition_sites,
    is_stub,
)

NAME = "read_symbol"

DetailLevel = Literal["minimal", "standard"]

# Heuristic only: adapters should eventually emit a doc range on the node (contract follow-up).
# Union of common comment leaders — not a language branch, but still language knowledge in core.
_COMMENT = re.compile(r"^\s*(#|//|/\*|\*|\*/)")


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def read_symbol(qname: str, detail_level: DetailLevel = "standard") -> dict[str, object]:
        """Source for ``qname``: ``line_start…line_end`` plus contiguous comments above.

        Never returns the whole file. On hash drift, reparses that one file inline (035). Returns
        ``stale: true`` and ``reason=index_stale`` when the file is missing, no adapter owns it, or
        repair fails (adapter/DB error). Stub-indexed nodes (task 039) also carry ``stub: true``.
        """
        if not config.db_path.is_file():
            return _empty(
                qname,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
            )
        with GraphStore(config.db_path) as store:
            rows = store.nodes_by_qualified_name(qname, limit=config.max_results)
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
                    rows = store.nodes_by_qualified_name(qname, limit=config.max_results)
                if not rows:
                    return _result(
                        qname,
                        "",
                        detail_level=detail_level,
                        db_path=str(config.db_path),
                        index_root=config.index_root,
                        found=False,
                        reason=REASON_OK,
                    )
            rel = str(rows[0]["file_path"])
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
                    line_start=None,
                    line_end=None,
                )
            if status == "repaired":
                rows = store.nodes_by_qualified_name(qname, limit=config.max_results)
                if not rows:
                    return _result(
                        qname,
                        "",
                        detail_level=detail_level,
                        db_path=str(config.db_path),
                        index_root=config.index_root,
                        found=False,
                        reason=REASON_OK,
                    )
                rel = str(rows[0]["file_path"])
            node = rows[0]
            path = config.root / rel
            start_raw = node["line_start"]
            if not isinstance(start_raw, int):
                raise TypeError(f"line_start must be int, got {type(start_raw).__name__}")
            start = start_raw
            end_raw = node["line_end"]
            end = end_raw if isinstance(end_raw, int) else start
            source = _slice(path, start, end)
            result = _result(
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
            # The source shown is one of N same-qname defs — name them all, pick none (task 070).
            return attach_ambiguous_definitions(result, definition_sites(rows))

    return read_symbol


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
    if found:
        payload["file"] = file
        if not stale:
            payload["line_start"] = line_start
            payload["line_end"] = line_end
        if stub:
            payload[contract.STUB_FLAG] = True
    return payload
