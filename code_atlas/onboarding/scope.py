"""The reader's working-scope predicate — one implementation for every truncate (task 206).

Presentation only: the graph keeps every file. ``None`` / empty means the whole index (R4.2).
Prefix membership, declared and matched as written (R2.2 — no repo directory in a default).
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = ["in_working_scope", "scoped_paths"]


def in_working_scope(path: str, roots: Sequence[str] | None) -> bool:
    """True when ``path`` sits under a declared working root, or when no root is declared."""
    if not roots:
        return True
    return any(path == root or path.startswith(f"{root}/") for root in roots)


def scoped_paths(paths: Sequence[str], roots: Sequence[str] | None) -> tuple[str, ...]:
    """``paths`` that pass :func:`in_working_scope`, in the given order."""
    return tuple(path for path in paths if in_working_scope(path, roots))
