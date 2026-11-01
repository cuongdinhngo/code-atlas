"""Content-hash cache for LLM summaries (task 090).

Keyed on the symbol's content (not its position), so a rename or reorder is a cache hit and an
edit is a miss. The on-disk form is sorted-key JSON with no timestamps, so it is byte-stable and
**committable** — a committed cache makes every later run (and any diff) deterministic (R4.2) — at
a path outside the index directory, which is refused once tracked (420). The core never sees this
file; it is written only by the opt-in ``onboarding_llm`` path.

A committed cache is text anyone can edit, so an entry is read only with its provenance (429): the
model, the cache ``version`` and an ``input_hash`` over the request inputs and the stored value. An
entry missing one, or whose hash no longer matches, or whose text is not bounded and printable, is
a miss — the deterministic text or a fresh call answers. The hash is integrity, not authenticity:
a committed cache is reviewed like code.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from code_atlas.containment import make_private_dir, read_text, safe_write
from code_atlas.index_text import escaped

# Bump to ignore every entry an older layout wrote; 1 was the layout with no provenance.
CACHE_VERSION = "2"
# A cached text is one short generated line; longer, or not printable, is not one code-atlas stored.
MAX_TEXT = 4000
_PROVENANCE = ("model", "version", "input_hash")
_RENDERED = ("docline", "prose", "layer_name")


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

    def __init__(self, path: Path, *, root: Path | None = None) -> None:
        self._path = path
        self._root = root
        self._entries: dict[str, dict[str, str]] = _read(path, root)

    def get(self, key: str, inputs: Sequence[str]) -> dict[str, str] | None:
        """The cached entry for ``key`` when its provenance holds for ``inputs``, else ``None``."""
        entry = self._entries.get(key)
        return entry if entry is not None and _trusted(entry, inputs) else None

    def put(self, key: str, entry: Mapping[str, str], inputs: Sequence[str], *, model: str) -> None:
        """Seal ``entry`` with its provenance, store it under ``key`` and flush the whole cache."""
        sealed = {**entry, "model": model, "version": CACHE_VERSION}
        sealed["input_hash"] = _input_hash(sealed, inputs)
        self._entries[key] = sealed
        self._flush()

    def _flush(self) -> None:
        make_private_dir(self._path.parent)
        text = json.dumps(self._entries, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        safe_write(self._path, text, root=self._root)


def _input_hash(entry: Mapping[str, str], inputs: Sequence[str]) -> str:
    """sha256 over the request inputs, the model and version, and every stored value."""
    stored = [f"{name}={entry[name]}" for name in sorted(entry) if name != "input_hash"]
    return content_key(*inputs, *stored)


def _trusted(entry: object, inputs: Sequence[str]) -> bool:
    """An entry carries every provenance field, a matching hash, and only bounded printable text."""
    if not isinstance(entry, dict):
        return False
    if not all(isinstance(value, str) for value in entry.values()):
        return False
    if any(name not in entry for name in _PROVENANCE) or entry["version"] != CACHE_VERSION:
        return False
    if not all(0 < len(value) <= MAX_TEXT for value in entry.values()):
        return False
    # What is rendered must already be what ``escaped`` makes of it: the predicate that produced it.
    # A path or old name is never rendered, so it may hold any character.
    shown = (*_PROVENANCE, *_RENDERED)
    if any(escaped(entry[name], multiline=True) != entry[name] for name in shown if name in entry):
        return False
    return entry["input_hash"] == _input_hash(entry, inputs)


def _read(path: Path, root: Path | None) -> dict[str, dict[str, str]]:
    try:
        text = read_text(path.parent if root is None else root, path)
    except OSError:  # absent, or a link out of the repo: an empty cache either way
        return {}
    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: LLM summary cache must be a JSON object")
    return loaded
