"""Local fit counters — which tools were asked, counts only (task 260).

Wraps MCP tool callables so each return bumps a ``fit:`` meta row. The increment reads
``reason`` / ``authoritative`` / ``truncated`` from the **return** dict only — never arguments —
so a qname or path cannot reach the meta key (R4). Not a ranking signal; never feeds retrieval.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any

from code_atlas.config import Config
from code_atlas.containment import resolves_inside
from code_atlas.store import bump_cost_counts, bump_fit_count
from code_atlas.tokens import estimate_tokens

# ``get_index_status`` is the tool that *reports* the counter, so counting it would make its own
# verbose payload differ between two identical calls (R4.2). It is in neither fit bucket anyway —
# the buckets are in docs/design/fit.md.
SELF_OBSERVING_TOOLS: frozenset[str] = frozenset({"get_index_status"})

FIT_COUNTS_FIELD = "fit_counts"
# 379: per-tool token sums — an estimate against a modelled grep+Read, never a benchmark tier.
EST_TOKENS_FIELD = "est_tokens_vs_grep_read"
EST_TOKENS_NOTE_FIELD = "est_tokens_note"
EST_TOKENS_NOTE = (
    "est. grep+Read baseline: response_tokens is chars/4 of each answer's JSON; baseline_tokens "
    "is bytes/4 of the files the answer cites (first 20, whole files, as the benchmark reads "
    "them). cited_calls counts answers that cited a file. Not the fixture or sample tier of "
    "scripts/tokens_to_answer.py, and not a measured saving."
)
BASELINE_FILE_CAP = 20  # the benchmark's max_read_files (tokens_to_answer.run_grep_path)
_CITE_KEYS = frozenset({"file", "file_path", "path"})


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


def cited_files(root: Path, payload: object) -> list[str]:
    """Distinct repo files an answer names, in payload order, first ``BASELINE_FILE_CAP`` (379)."""
    seen: list[str] = []
    for value in _cited_values(payload):
        if value in seen:
            continue
        path = root / value
        if path.is_file() and resolves_inside(root, path):
            seen.append(value)
            if len(seen) == BASELINE_FILE_CAP:
                break
    return seen


def _cited_values(payload: object) -> Iterator[str]:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if key in _CITE_KEYS and isinstance(value, str) and value:
                yield value
            else:
                yield from _cited_values(value)
    elif isinstance(payload, list | tuple):
        for item in payload:
            yield from _cited_values(item)


def record_cost(tool_name: str, config: Config, payload: Mapping[str, object] | object) -> None:
    """Add this answer's est. tokens and its est. grep+Read baseline to the tool's rows (379)."""
    if not isinstance(payload, Mapping) or not config.db_path.is_file():
        return
    try:
        response = estimate_tokens(json.dumps(payload, sort_keys=True, default=str))
        files = cited_files(config.root, payload)
        baseline = sum(-(-(config.root / rel).stat().st_size // 4) for rel in files)
    except (OSError, TypeError, ValueError, RecursionError):
        return  # an uncountable answer is not counted; it is never spoiled
    bump_cost_counts(
        config.db_path,
        tool_name,
        cited=bool(files),
        response_tokens=response,
        baseline_tokens=baseline,
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
        record_cost(tool_name, config, result)
        return result

    return wrapped
