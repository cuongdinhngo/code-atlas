"""Local fit counters — which tools were asked, counts only (task 260).

Wraps MCP tool callables so each return bumps a ``fit:`` meta row. The increment reads
``reason`` / ``authoritative`` / ``truncated`` from the **return** dict only — never arguments —
so a qname or path cannot reach the meta key (R4). Not a ranking signal; never feeds retrieval.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Mapping
from typing import Any

from code_atlas.config import Config
from code_atlas.store import bump_fit_count

# ``get_index_status`` is the tool that *reports* the counter, so counting it would make its own
# verbose payload differ between two identical calls (R4.2). It is in neither fit bucket anyway —
# the buckets are in docs/design/fit.md.
SELF_OBSERVING_TOOLS: frozenset[str] = frozenset({"get_index_status"})

FIT_COUNTS_FIELD = "fit_counts"


def record(tool_name: str, config: Config, payload: Mapping[str, object] | object) -> None:
    """Increment one fit row from a tool return; no-op when there is no index file yet."""
    if not isinstance(payload, Mapping) or not config.db_path.is_file():
        return
    reason = payload.get("reason")
    # A tool with no reason field (a build, a report) counts under the empty reason, not a guess.
    reason_s = str(reason) if reason is not None else ""
    authoritative = payload.get("authoritative")
    auth = True if authoritative is None else bool(authoritative)
    truncated = bool(payload.get("truncated", False))
    bump_fit_count(
        config.db_path, tool_name, reason_s, authoritative=auth, truncated=truncated
    )


def wrap(
    tool_name: str,
    config: Config,
    tool: Callable[..., dict[str, object]],
) -> Callable[..., dict[str, object]]:
    """Compose after ``guard`` so every served call accrues a count on the common path."""
    if tool_name in SELF_OBSERVING_TOOLS:
        return tool

    @functools.wraps(tool)
    def wrapped(*args: Any, **kwargs: Any) -> dict[str, object]:
        result = tool(*args, **kwargs)
        record(tool_name, config, result)
        return result

    return wrapped
