"""``verify_refs`` — which references in agent-facing docs still resolve, as a tool (439).

The shell route (``code-atlas query --verify-refs``) reaches a person; an agent uses only what it
can call. The payload is ``doc_refs.verify_refs``: reference strings, states and counts, never the
prose around them (429). ``format: patch`` answers each correction as an edit — file, line, the
reference and its replacement — and names the shell command that prints the diff; a diff carries
doc lines, so it never rides the MCP payload.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas import doc_refs
from code_atlas.config import Config, clamp_limit
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import attach_limit_capped

NAME = "verify_refs"
DocClass = Literal["instruction", "memory", "reference", "archive"]
State = Literal["moved", "gone", "never_existed", "ambiguous", "unknown", "ok"]
Strength = Literal["strong", "weak"]
Format = Literal["json", "md", "patch"]
DetailLevel = Literal["minimal", "standard"]
# What `minimal` leaves out: the per-file table and how the corpus was chosen.
_STANDARD_ONLY = ("files", "corpus_globs", "commands", "history_budget_spent")
# A default row: where, what, and the fix — the rest is in the full rows a filter asks for (443).
_COMPACT = ("class", "file", "line", "ref", "state", "reason", "replacement", "successor",
            "last_seen", "nearest_existing")
APPLY_WITH = "code-atlas query --verify-refs --format patch | git apply"


def edits(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Every patch-ready row as one in-place edit, instruction files first."""
    return [
        {key: row[key] for key in ("class", "file", "line", "ref", "replacement")}
        for row in rows
        if row.get("patch_ready")
    ]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def verify_refs(
        globs: list[str] | None = None,
        doc_class: list[DocClass] | None = None,
        state: list[State] | None = None,
        strength: list[Strength] | None = None,
        format: Format = "json",
        limit: int | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """Which paths and symbols in CLAUDE.md, skills, memory and docs moved or are gone:
        counts and up to 20 rows, instruction files first. `format: patch` lists edits.
        """
        explicit = bool(globs or doc_class or state or strength or limit is not None)
        cap, clamped = clamp_limit(limit, min(config.page_limit, doc_refs.MAX_LIMIT))
        if not explicit:
            cap, clamped = doc_refs.DEFAULT_ROWS, False
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        doc_refs.check_filters(state or (), strength or ())
        with GraphStore(config.db_path) as store:
            found = doc_refs.scan(config, store, globs=globs or (), classes=doc_class or ())
        answer = doc_refs.summarize(
            found, states=state or (), strengths=strength or (), limit=cap, actionable=not explicit
        )
        answer["index_root"] = config.index_root
        if not explicit:
            rows = answer["rows"]
            assert isinstance(rows, list)
            answer["rows"] = [_compact(row) for row in rows]
            for key in ("by_class", "corpus_globs", "files"):
                answer.pop(key)
        if format == "md":
            answer["markdown"] = doc_refs.markdown(answer)
            answer.pop("rows")
        elif format == "patch":
            made = edits(found.rows)
            answer["edits"] = made[:cap]
            answer["edits_total"] = len(made)
            answer["apply_with"] = APPLY_WITH
            answer.pop("rows")
        if detail_level == "minimal":
            for key in _STANDARD_ONLY:
                answer.pop(key, None)
        return attach_limit_capped(answer, cap=cap, clamped=clamped)

    return verify_refs


def _compact(row: object) -> dict[str, object]:
    assert isinstance(row, dict)
    return {key: row[key] for key in _COMPACT if row.get(key) is not None}
