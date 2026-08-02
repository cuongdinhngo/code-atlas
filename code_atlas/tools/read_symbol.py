"""``read_symbol`` — source of one qname + contiguous doc comments above it (§12)."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore

NAME = "read_symbol"

DetailLevel = Literal["minimal", "standard"]

# Heuristic only: adapters should eventually emit a doc range on the node (contract follow-up).
# Union of common comment leaders — not a language branch, but still language knowledge in core.
_COMMENT = re.compile(r"^\s*(#|//|/\*|\*|\*/)")

_READ_CHUNK = 1024 * 64


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def read_symbol(qname: str, detail_level: DetailLevel = "standard") -> dict[str, object]:
        """Source for ``qname``: ``line_start…line_end`` plus contiguous comments above.

        Never returns the whole file. If the on-disk file hash no longer matches the index,
        returns ``stale: true`` and an empty ``source`` (call ``build_or_update_index``).
        """
        if not config.db_path.is_file():
            return _empty(qname, detail_level=detail_level, db_path=str(config.db_path))
        with GraphStore(config.db_path) as store:
            rows = store.nodes_by_qualified_name(qname, limit=1)
            if not rows:
                return _result(
                    qname,
                    "",
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    found=False,
                )
            node = rows[0]
            rel = str(node["file_path"])
            indexed_hash = store.file_hash(rel)
        path = config.root / rel
        if indexed_hash is None or _digest(path) != indexed_hash:
            return _result(
                qname,
                "",
                detail_level=detail_level,
                db_path=str(config.db_path),
                found=True,
                stale=True,
                file=rel,
                line_start=None,
                line_end=None,
            )
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
            found=True,
            stale=False,
            file=rel,
            line_start=start,
            line_end=end,
        )

    return read_symbol


def _digest(path: Path) -> str:
    """SHA-256 of file bytes, or empty when unreadable — same idea as ``indexer._digest``."""
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_READ_CHUNK):
                hasher.update(chunk)
    except OSError:
        return ""
    return hasher.hexdigest()


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


def _empty(qname: str, *, detail_level: str, db_path: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": False,
        "qname": qname,
        "found": False,
        "stale": False,
        "source": "",
    }
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload


def _result(
    qname: str,
    source: str,
    *,
    detail_level: str,
    db_path: str,
    found: bool,
    stale: bool = False,
    file: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": True,
        "qname": qname,
        "found": found,
        "stale": stale,
        "source": source,
    }
    if found:
        payload["file"] = file
        if not stale:
            payload["line_start"] = line_start
            payload["line_end"] = line_end
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload
