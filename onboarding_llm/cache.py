"""Content-hash cache for LLM summaries (task 090).

Keyed on the symbol's content (not its position), so a rename or reorder is a cache hit and an
edit is a miss. The on-disk form is sorted-key JSON with no timestamps, so it is byte-stable and
**committable** — a committed cache makes every later run (and any diff) deterministic (R4.2). The
core never sees this file; it is written only by the opt-in ``onboarding_llm`` path.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def content_key(*parts: str) -> str:
    """A stable sha256 over the given content parts (NUL-joined so fields can't run together)."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


class ContentHashCache:
    """A JSON dict of ``content-hash → entry``, loaded once and written through on each put.

    Write-through (atomic ``os.replace``) keeps the cache safe if a long run is interrupted; the
    entry count is bounded by the onboarding node budget, so rewriting the whole file per put is
    cheap enough for this opt-in, offline tool.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: dict[str, dict[str, str]] = _read(path)

    def get(self, key: str) -> dict[str, str] | None:
        """The cached entry for ``key``, or ``None`` on a miss."""
        return self._entries.get(key)

    def put(self, key: str, entry: dict[str, str]) -> None:
        """Store ``entry`` under ``key`` and flush the whole cache to disk, deterministically."""
        self._entries[key] = entry
        self._flush()

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(self._entries, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        temporary = self._path.with_name(self._path.name + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, self._path)


def _read(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: LLM summary cache must be a JSON object")
    return loaded
