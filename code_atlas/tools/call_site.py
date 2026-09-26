"""Call-site source lines for nav hits — one call answers "who calls X" *and* "show me" (037)."""

from __future__ import annotations

from pathlib import Path

from code_atlas import contract
from code_atlas.indexer import file_is_current
from code_atlas.store import GraphStore

# One line per site, truncated here. No CA_* knob until a second value is wanted (R7.1 / YAGNI).
SITE_MAX_CHARS = 160

_ELLIPSIS = "…"


def annotate(
    root: Path,
    store: GraphStore,
    hits: list[dict[str, object]],
    *,
    max_chars: int = SITE_MAX_CHARS,
) -> None:
    """Add ``source`` to each hit in place; mark ``source_stale`` where the file cannot be trusted.

    Reads each distinct file once. A file whose indexed hash no longer matches disk is never
    quoted — a snippet from drifted bytes would be a confident lie (R4; 035 refreshes only
    the subject file, and call sites live in other files).
    """
    if max_chars < 1:
        raise ValueError(f"max_chars must be >= 1, got {max_chars}")
    for rel, group in _by_file(hits).items():
        wanted = {line for _, line in group if line is not None}
        for hit, _ in group:
            wanted.update(_call_lines(hit))
        lines = _read_lines(root, store, rel, wanted)
        for hit, line in group:
            extra = _call_lines(hit)
            if lines is None or line is None or not {line, *extra} <= lines.keys():
                hit["source_stale"] = True
                continue
            hit["source"] = _clip(lines[line], max_chars)
            if extra:
                # Every site a multi-site caller names is quoted, in call_lines order (338).
                hit["call_sources"] = [_clip(lines[n], max_chars) for n in extra]


def _call_lines(hit: dict[str, object]) -> list[int]:
    raw = hit.get("call_lines")
    return [n for n in raw if isinstance(n, int)] if isinstance(raw, list) else []


def _by_file(
    hits: list[dict[str, object]],
) -> dict[str, list[tuple[dict[str, object], int | None]]]:
    grouped: dict[str, list[tuple[dict[str, object], int | None]]] = {}
    for hit in hits:
        if hit.get(contract.RULE_FLAG) is True:
            # Rule-derived: no on-disk site — leave without ``source`` / ``source_stale``.
            continue
        rel = hit.get("file")
        if not isinstance(rel, str) or not rel:
            hit["source_stale"] = True
            continue
        raw = hit.get("line")
        grouped.setdefault(rel, []).append((hit, raw if isinstance(raw, int) else None))
    return grouped


def _read_lines(
    root: Path, store: GraphStore, rel: str, wanted: set[int]
) -> dict[int, str] | None:
    """The wanted 1-based lines of ``rel``, or ``None`` when the file must not be quoted."""
    if not wanted:
        return None
    path = root / rel
    if not path.is_file() or not file_is_current(store, root, rel):
        return None
    found: dict[int, str] = {}
    highest = max(wanted)
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for number, text in enumerate(handle, start=1):
                if number in wanted:
                    found[number] = text
                if number >= highest:
                    break
    except OSError:
        return None
    return found


def _clip(text: str, max_chars: int) -> str:
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    return stripped[:max_chars] + _ELLIPSIS
