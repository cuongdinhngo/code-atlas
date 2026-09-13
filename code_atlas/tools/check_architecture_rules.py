"""``check_architecture_rules`` — do declared path-set dependency rules still hold? (task 138)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.architecture_rules import (
    STATUS_MATCHED_NO_FILES,
    Violation,
    load_architecture_rules,
)
from code_atlas.architecture_rules import (
    check_architecture_rules as check_architecture_rules_impl,
)
from code_atlas.config import Config, clamp_limit
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import (
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
    REASON_RULE_MATCHED_NO_FILES,
    attach_limit_capped,
)

NAME = "check_architecture_rules"

DetailLevel = Literal["minimal", "standard"]

__all__ = ["NAME", "create"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def check_architecture_rules(
        detail_level: DetailLevel = "standard",
        limit: int | None = None,
        offset: int = 0,
        rule_id: str | None = None,
    ) -> dict[str, object]:
        """Do the architecture dependency rules still hold on this index?

        Reads ``CA_ARCHITECTURE_RULES`` (JSON files of path-set constraints). Each confirmed
        violation is a RESOLVED walk from a source path set into a forbidden path set;
        HEURISTIC-only evidence is listed under ``candidates`` and never counts as confirmed.
        ``total_count`` is the confirmed population; page with ``limit``/``offset`` until
        ``truncated`` is false. Empty answers name the cause: not indexed, rules unset,
        no source file matched a rule, or no violation.
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.page_limit)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        if not config.db_path.is_file():
            return _envelope(
                indexed=False,
                reason=REASON_NOT_INDEXED,
                config=config,
                total_count=0,
                candidate_count=0,
            )
        rules = load_architecture_rules(config)
        if rules is None:
            return _envelope(
                indexed=True,
                reason=REASON_CAPABILITY_NOT_CONFIGURED,
                config=config,
                total_count=0,
                candidate_count=0,
                message="no architecture rules configured — set CA_ARCHITECTURE_RULES",
            )
        if rule_id is not None:
            rules = tuple(rule for rule in rules if rule.id == rule_id)
            if not rules:
                return _envelope(
                    indexed=True,
                    reason=REASON_NO_MATCHES,
                    config=config,
                    total_count=0,
                    candidate_count=0,
                    message=f"no rule with id {rule_id!r}",
                )
        with GraphStore(config.db_path) as store:
            outcome = check_architecture_rules_impl(
                store, rules, max_nodes=config.impact_max_nodes
            )
        if outcome.rules and all(
            report.status == STATUS_MATCHED_NO_FILES for report in outcome.rules
        ):
            return _envelope(
                indexed=True,
                reason=REASON_RULE_MATCHED_NO_FILES,
                config=config,
                rules=_shape_rules(outcome.rules, detail_level),
                total_count=0,
                candidate_count=0,
            )
        confirmed = outcome.confirmed
        page = confirmed[offset : offset + cap]
        payload = _envelope(
            indexed=True,
            reason=REASON_OK,
            config=config,
            results=[_shape_violation(row, detail_level) for row in page],
            truncated=offset + len(page) < len(confirmed),
            total_count=len(confirmed),
            candidate_count=len(outcome.candidates),
            rules=_shape_rules(outcome.rules, detail_level),
        )
        if detail_level == "standard":
            candidate_page = outcome.candidates[offset : offset + cap]
            payload["candidates"] = [
                _shape_violation(row, detail_level) for row in candidate_page
            ]
            payload["candidates_truncated"] = offset + len(candidate_page) < len(
                outcome.candidates
            )
            payload["digest"] = outcome.digest
        attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
        return payload

    return check_architecture_rules


def _shape_violation(row: Violation, detail_level: DetailLevel) -> dict[str, object]:
    hit: dict[str, object] = {
        "rule_id": row.rule_id,
        "source_file": row.source_file,
        "forbidden_file": row.forbidden_file,
    }
    if detail_level == "standard":
        hit["via_qname"] = row.via_qname
        hit["confidence_tier"] = row.confidence_tier
    return hit


def _shape_rules(reports: tuple, detail_level: DetailLevel) -> list[dict[str, object]]:
    if detail_level == "minimal":
        return [{"rule_id": report.rule_id, "status": report.status} for report in reports]
    return [
        {
            "forbidden_matched": report.forbidden_matched,
            "rule_id": report.rule_id,
            "sources_matched": report.sources_matched,
            "status": report.status,
        }
        for report in reports
    ]


def _envelope(
    *,
    indexed: bool,
    reason: str,
    config: Config,
    results: list[dict[str, object]] | None = None,
    truncated: bool = False,
    total_count: int = 0,
    candidate_count: int = 0,
    rules: list[dict[str, object]] | None = None,
    message: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_count": candidate_count,
        "index_root": config.index_root,
        "indexed": indexed,
        "reason": reason,
        "results": results if results is not None else [],
        "total_count": total_count,
        "truncated": truncated,
    }
    if rules is not None:
        payload["rules"] = rules
    if message is not None:
        payload["message"] = message
    return payload
