"""Declarative architecture dependency rules checked against the graph (task 138).

Rules are data the operator hands the server — path sets, edge kinds, direction, transitive —
never framework or product names inside ``code_atlas/`` (R2.2). Off when unset. Confirmed
violations need a RESOLVED walk; HEURISTIC-only evidence is a candidate, never a gate failure.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from code_atlas.config import Config, ConfigError
from code_atlas.contract import IMPACT_KINDS
from code_atlas.ignore import translate_path_pattern
from code_atlas.store import GraphStore

DIRECTIONS: tuple[str, ...] = ("outgoing", "incoming")

# A rule's own status vocabulary. The payload's REASON codes are the fixed nav vocabulary and
# stay in ``tools/nav_result.py`` — the core never imports a tool.
STATUS_CHECKED = "checked"
STATUS_MATCHED_NO_FILES = "rule_matched_no_files"

__all__ = [
    "ArchitectureRule",
    "CheckOutcome",
    "DIRECTIONS",
    "STATUS_CHECKED",
    "STATUS_MATCHED_NO_FILES",
    "RuleReport",
    "Violation",
    "check_architecture_rules",
    "load_architecture_rules",
]


@dataclass(frozen=True, slots=True)
class ArchitectureRule:
    """One dependency constraint: sources must not reach forbidden targets."""

    id: str
    sources: tuple[str, ...]
    forbidden: tuple[str, ...]
    kinds: tuple[str, ...]
    direction: str
    transitive: bool


@dataclass(frozen=True, slots=True)
class Violation:
    """One source module that reaches a forbidden module under a named rule."""

    rule_id: str
    source_file: str
    forbidden_file: str
    via_qname: str
    confidence_tier: str


@dataclass(frozen=True, slots=True)
class RuleReport:
    """Per-rule match honesty — zero source hits is not the same as zero violations."""

    rule_id: str
    sources_matched: int
    forbidden_matched: int
    status: str


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    """Confirmed vs candidate populations, plus per-rule status (R4.2 order)."""

    confirmed: tuple[Violation, ...]
    candidates: tuple[Violation, ...]
    rules: tuple[RuleReport, ...]
    digest: str


def load_architecture_rules(config: Config) -> tuple[ArchitectureRule, ...] | None:
    """Load and merge every configured rule file; ``None`` when the knob is off."""
    paths = config.architecture_rules
    if not paths:
        return None
    rules: list[ArchitectureRule] = []
    for relative in sorted(paths):
        path = config.root / relative
        if not path.is_file():
            raise ConfigError(
                f"architecture_rules: {relative!r} is not a file under {config.root}"
            )
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            raise ConfigError(
                f"architecture_rules: {relative!r} could not be read ({error})"
            ) from error
        rules.extend(_load_rules(relative, text))
    if not rules:
        raise ConfigError("architecture_rules: no rules declared in any configured file")
    return tuple(rules)


def check_architecture_rules(
    store: GraphStore,
    rules: Sequence[ArchitectureRule],
    *,
    max_nodes: int,
) -> CheckOutcome:
    """Evaluate every rule against the indexed graph; identical index → identical lists (R4.2)."""
    files = tuple(store.file_paths())
    confirmed: list[Violation] = []
    candidates: list[Violation] = []
    reports: list[RuleReport] = []
    for rule in rules:
        source_files = _matching_files(files, rule.sources)
        forbidden_files = set(_matching_files(files, rule.forbidden))
        # Either side empty and the rule proved nothing — 130's family, an honest signal over a
        # dishonest population. The two counts say which side was empty.
        if not source_files or not forbidden_files:
            reports.append(
                RuleReport(
                    rule.id,
                    len(source_files),
                    len(forbidden_files),
                    STATUS_MATCHED_NO_FILES,
                )
            )
            continue
        reports.append(
            RuleReport(rule.id, len(source_files), len(forbidden_files), STATUS_CHECKED)
        )
        seeds_by_file = {path: _seeds_on_files(store, [path]) for path in source_files}
        depth = None if rule.transitive else 1
        if rule.direction == "outgoing":
            hit_confirmed, hit_candidates = _outgoing_hits(
                store,
                seeds_by_file,
                forbidden_files,
                kinds=rule.kinds,
                depth=depth,
                max_nodes=max_nodes,
            )
        else:
            # No hop can add zero nodes, so max_nodes bounds the closure: it is the
            # transitive case's depth, not a budget reused as a hop count.
            hit_confirmed, hit_candidates = _incoming_hits(
                store,
                seeds_by_file,
                forbidden_files,
                kinds=rule.kinds,
                depth=1 if depth == 1 else max_nodes,
                max_nodes=max_nodes,
            )
        for source_file, forbidden_file, via, tier in hit_confirmed:
            confirmed.append(Violation(rule.id, source_file, forbidden_file, via, tier))
        for source_file, forbidden_file, via, tier in hit_candidates:
            candidates.append(Violation(rule.id, source_file, forbidden_file, via, tier))
    confirmed_sorted = tuple(
        sorted(
            confirmed,
            key=lambda row: (row.rule_id, row.source_file, row.forbidden_file, row.via_qname),
        )
    )
    candidates_sorted = tuple(
        sorted(
            candidates,
            key=lambda row: (row.rule_id, row.source_file, row.forbidden_file, row.via_qname),
        )
    )
    digest = sha256(
        json.dumps(
            {
                "candidates": [asdict(row) for row in candidates_sorted],
                "confirmed": [asdict(row) for row in confirmed_sorted],
                "rules": [asdict(row) for row in reports],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return CheckOutcome(confirmed_sorted, candidates_sorted, tuple(reports), digest)


def _matching_files(files: Sequence[str], patterns: Sequence[str]) -> tuple[str, ...]:
    compiled = tuple(re.compile(f"{translate_path_pattern(pattern)}$") for pattern in patterns)
    return tuple(path for path in files if any(rule.match(path) for rule in compiled))


def _seeds_on_files(store: GraphStore, paths: Sequence[str]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for path in paths:
        for row in store.nodes_by_file_all(path):
            qname = str(row["qualified_name"])
            if qname not in seen:
                seen.add(qname)
                found.append(qname)
    return found


def _outgoing_hits(
    store: GraphStore,
    seeds_by_file: Mapping[str, Sequence[str]],
    forbidden: set[str],
    *,
    kinds: Sequence[str],
    depth: int | None,
    max_nodes: int,
) -> tuple[list[tuple[str, str, str, str]], list[tuple[str, str, str, str]]]:
    """Per source file: RESOLVED reachability into forbidden → confirmed; HEURISTIC → candidate."""
    confirmed: list[tuple[str, str, str, str]] = []
    candidates: list[tuple[str, str, str, str]] = []
    for source_file, seeds in seeds_by_file.items():
        if not seeds:
            continue
        outcome = store.reachable_from(
            list(seeds), depth=depth, max_nodes=max_nodes, kinds=kinds
        )
        for row in outcome.reachable:
            target_file = str(row["file"])
            if target_file not in forbidden or target_file == source_file:
                continue
            confirmed.append((source_file, target_file, str(row["qname"]), "RESOLVED"))
        for row in outcome.unproven:
            target_file = str(row["file"])
            if target_file not in forbidden or target_file == source_file:
                continue
            tier = str(row.get("confidence_tier") or "HEURISTIC")
            candidates.append((source_file, target_file, str(row["qname"]), tier))
    return _dedupe_module_pairs(confirmed), _dedupe_module_pairs(candidates)


def _incoming_hits(
    store: GraphStore,
    seeds_by_file: Mapping[str, Sequence[str]],
    forbidden: set[str],
    *,
    kinds: Sequence[str],
    depth: int,
    max_nodes: int,
) -> tuple[list[tuple[str, str, str, str]], list[tuple[str, str, str, str]]]:
    """Per source file: forbidden callers via impact → confirmed or candidate by tier."""
    confirmed: list[tuple[str, str, str, str]] = []
    candidates: list[tuple[str, str, str, str]] = []
    for source_file, seeds in seeds_by_file.items():
        for seed in seeds:
            outcome = store.impact_radius(
                [seed], depth=depth, max_nodes=max_nodes, kinds=kinds
            )
            for row in outcome.rows:
                caller_file = str(row["file"])
                if caller_file not in forbidden or caller_file == source_file:
                    continue
                # An absent tier is NOT evidence of a resolved walk — default to the
                # candidate side, as the outgoing branch does.
                tier = str(row.get("confidence_tier") or "HEURISTIC")
                via = str(row["qname"])
                bucket = confirmed if tier == "RESOLVED" else candidates
                bucket.append((source_file, caller_file, via, tier))
    return _dedupe_module_pairs(confirmed), _dedupe_module_pairs(candidates)


def _dedupe_module_pairs(
    rows: Sequence[tuple[str, str, str, str]],
) -> list[tuple[str, str, str, str]]:
    """One row per (source_file, forbidden_file); keep the earliest via_qname (R4.2)."""
    best: dict[tuple[str, str], tuple[str, str, str, str]] = {}
    for source, forbidden, via, tier in rows:
        key = (source, forbidden)
        if key not in best or (via, tier) < (best[key][2], best[key][3]):
            best[key] = (source, forbidden, via, tier)
    return [best[key] for key in sorted(best)]


def _load_rules(label: str, text: str) -> list[ArchitectureRule]:
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError(f"architecture_rules: {label!r} is not valid JSON ({error})") from error
    if not isinstance(payload, dict):
        raise ConfigError(f"architecture_rules: {label!r} root must be a JSON object")
    raw_rules = payload.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ConfigError(f"architecture_rules: {label!r} rules must be a non-empty list")
    rules: list[ArchitectureRule] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(raw_rules):
        if not isinstance(entry, dict):
            raise ConfigError(f"architecture_rules: {label!r} rules[{index}] must be an object")
        rule_id = _required_str(label, entry, "id")
        if rule_id in seen_ids:
            raise ConfigError(f"architecture_rules: {label!r} duplicate rule id {rule_id!r}")
        seen_ids.add(rule_id)
        sources = _required_patterns(label, entry, "sources")
        forbidden = _required_patterns(label, entry, "forbidden")
        kinds = _optional_kinds(label, entry)
        direction = str(entry.get("direction", "outgoing"))
        if direction not in DIRECTIONS:
            raise ConfigError(
                f"architecture_rules: {label!r} direction must be one of {DIRECTIONS}"
            )
        transitive = entry.get("transitive", True)
        if not isinstance(transitive, bool):
            raise ConfigError(f"architecture_rules: {label!r} transitive must be a boolean")
        rules.append(
            ArchitectureRule(
                id=rule_id,
                sources=sources,
                forbidden=forbidden,
                kinds=kinds,
                direction=direction,
                transitive=transitive,
            )
        )
    return rules


def _required_str(label: str, entry: Mapping[str, Any], field: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"architecture_rules: {label!r} {field} must be a non-empty string")
    return value.strip()


def _required_patterns(label: str, entry: Mapping[str, Any], field: str) -> tuple[str, ...]:
    raw = entry.get(field)
    if not isinstance(raw, list) or not raw:
        raise ConfigError(f"architecture_rules: {label!r} {field} must be a non-empty list")
    patterns: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ConfigError(
                f"architecture_rules: {label!r} {field} entries must be non-empty strings"
            )
        patterns.append(item.strip().replace("\\", "/"))
    return tuple(patterns)


def _optional_kinds(label: str, entry: Mapping[str, Any]) -> tuple[str, ...]:
    raw = entry.get("kinds")
    if raw is None:
        return IMPACT_KINDS
    if not isinstance(raw, list) or not raw:
        raise ConfigError(f"architecture_rules: {label!r} kinds must be a non-empty list")
    allowed = set(IMPACT_KINDS)
    kinds: list[str] = []
    for item in raw:
        if not isinstance(item, str) or item not in allowed:
            raise ConfigError(
                f"architecture_rules: {label!r} kinds must be IMPACT kinds "
                f"({', '.join(IMPACT_KINDS)})"
            )
        kinds.append(item)
    return tuple(dict.fromkeys(kinds))
