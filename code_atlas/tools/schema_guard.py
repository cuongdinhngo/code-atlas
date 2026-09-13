"""One answer for the schema-version mismatch every tool would otherwise raise (task 050).

A mismatch is a fact about the *server*, not about the query, so it has to reach the caller as a
payload naming the next action — a stack trace is what sent a field session back to ``grep``.
No query tool rebuilds on its own: a search that silently costs a full build is worse than an error.
"""

import functools
from collections.abc import Callable
from typing import Any

from code_atlas.config import Config
from code_atlas.store import SchemaVersionError
from code_atlas.worktree_guard import worktree_db_refusal

SCHEMA_MISMATCH = "schema_version_mismatch"


def payload(mismatch: SchemaVersionError) -> dict[str, object]:
    """What every tool reports for a mismatch: what is on disk, what this server is, what to do.

    Carries no empty ``results`` list on purpose — an empty hit list reads as proof of absence.
    """
    return {
        "error": SCHEMA_MISMATCH,
        "indexed": False,
        "index_schema_version": mismatch.found,
        "server_schema_version": mismatch.expected,
        "direction": mismatch.direction,
        "action": mismatch.action,
    }


def guard(
    tool: Callable[..., dict[str, object]],
    config: Config | None = None,
) -> Callable[..., dict[str, object]]:
    """Wrap a tool so a mismatch becomes its answer; the signature MCP publishes is preserved.

    With ``config``, a linked-worktree DB outside the worktree refuses first (268). That verdict
    is read once here, not per call: deciding it asks git, and a subprocess on every answer is
    the cost 260 measured against a 0.4 ms nav read.
    """
    refusal = None if config is None else worktree_db_refusal(config)

    @functools.wraps(tool)
    def guarded(*args: Any, **kwargs: Any) -> dict[str, object]:
        if refusal is not None:
            return dict(refusal)
        try:
            return tool(*args, **kwargs)
        except SchemaVersionError as mismatch:
            return payload(mismatch)

    return guarded
