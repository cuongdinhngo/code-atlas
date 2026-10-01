"""Declarative architecture dependency rules checked against the graph (tasks 138, 359).

Rules are data the operator hands the server — path sets, edge kinds, direction, transitive —
never framework or product names inside ``code_atlas/`` (R2.2). Off when unset. Confirmed
violations need a RESOLVED walk; HEURISTIC-only evidence is a candidate, never a gate failure.
A ``forbidden`` rule finds an edge that is present; a ``required`` rule (359) finds one that is
absent, so its confirmed population needs every edge the walk met to be RESOLVED.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from code_atlas.config import Config, ConfigError
from code_atlas.containment import resolves_inside
from code_atlas.contract import IMPACT_KINDS, NODE_KINDS
from code_atlas.ignore import translate_path_pattern
from code_atlas.store import GraphStore

DIRECTIONS: tuple[str, ...] = ("outgoing", "incoming")

# A rule's own status vocabulary. The payload's REASON codes are the fixed nav vocabulary and
# stay in ``tools/nav_result.py`` — the core never imports a tool.
STATUS_CHECKED = "checked"
STATUS_MATCHED_NO_FILES = "rule_matched_no_files"
# A required rule whose `expect` list named a qname the walk judged otherwise (359).
STATUS_CALIBRATION_FAILED = "calibration_failed"

__all__ = [
    "ArchitectureRule",
    "CheckOutcome",
    "DIRECTIONS",
    "RequiredRule",
    "RequiredRuleReport",
    "RequiredViolation",
    "STATUS_CALIBRATION_FAILED",
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
class RequiredRule:
    """Every selected source symbol must reach one of the required qnames (359)."""

    id: str
    sources: tuple[str, ...]
    name: str | None
    kind: str | None
    required: tuple[str, ...]
    kinds: tuple[str, ...]
    depth: int
    expect_violating: tuple[str, ...] = ()
    expect_passing: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RequiredViolation:
    """One source symbol that reaches no required target within the rule's depth."""

    rule_id: str
    source_qname: str
    source_file: str
    unresolved_outgoing: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class RequiredRuleReport:
    """Per-rule honesty for a required rule, calibration included."""

    rule_id: str
    sources_matched: int
    targets_matched: int
    status: str
    expected_found: int
    expected_missed: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    """Confirmed vs candidate populations, plus per-rule status (R4.2 order)."""

    confirmed: tuple[Violation, ...]
    candidates: tuple[Violation, ...]
    rules: tuple[RuleReport | RequiredRuleReport, ...]
    digest: str
    required_confirmed: tuple[RequiredViolation, ...] = ()
    required_candidates: tuple[RequiredViolation, ...] = ()


def load_architecture_rules(
    config: Config,
) -> tuple[ArchitectureRule | RequiredRule, ...] | None:
    """Load and merge every configured rule file; ``None`` when the knob is off."""
    paths = config.architecture_rules
    if not paths:
        return None
    rules: list[ArchitectureRule | RequiredRule] = []
    for relative in sorted(paths):
        path = config.root / relative
        if not path.is_file():
            raise ConfigError(
                f"architecture_rules: {relative!r} is not a file under {config.root}"
            )
        if not resolves_inside(config.root, path):
            raise ConfigError(f"architecture_rules: {relative!r} resolves outside {config.root}")
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
    rules: Sequence[ArchitectureRule | RequiredRule],
    *,
    max_nodes: int,
) -> CheckOutcome:
    """Evaluate every rule against the indexed graph; identical index → identical lists (R4.2)."""
    files = tuple(store.file_paths())
    confirmed: list[Violation] = []
    candidates: list[Violation] = []
    reports: list[RuleReport | RequiredRuleReport] = []
    forbidden_rules = [rule for rule in rules if isinstance(rule, ArchitectureRule)]
    required_rules = [rule for rule in rules if isinstance(rule, RequiredRule)]
    for rule in forbidden_rules:
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
    required_confirmed: list[RequiredViolation] = []
    required_candidates: list[RequiredViolation] = []
    for required_rule in required_rules:
        report, hits, maybe = _check_required(store, files, required_rule, max_nodes=max_nodes)
        reports.append(report)
        required_confirmed.extend(hits)
        required_candidates.extend(maybe)
    hashed: dict[str, object] = {
        "candidates": [asdict(row) for row in candidates_sorted],
        "confirmed": [asdict(row) for row in confirmed_sorted],
        "rules": [asdict(row) for row in reports],
    }
    # Only a required rule adds keys, so a forbidden-only digest is unchanged (359 AC5).
    if required_rules:
        hashed["required_candidates"] = [asdict(row) for row in required_candidates]
        hashed["required_confirmed"] = [asdict(row) for row in required_confirmed]
    digest = sha256(json.dumps(hashed, sort_keys=True).encode("utf-8")).hexdigest()
    return CheckOutcome(
        confirmed_sorted,
        candidates_sorted,
        tuple(reports),
        digest,
        tuple(required_confirmed),
        tuple(required_candidates),
    )


def _check_required(
    store: GraphStore,
    files: Sequence[str],
    rule: RequiredRule,
    *,
    max_nodes: int,
) -> tuple[RequiredRuleReport, list[RequiredViolation], list[RequiredViolation]]:
    """Walk each source symbol; no target reached is confirmed only over an all-RESOLVED walk."""
    sources = _required_sources(store, files, rule)
    targets = [q for q in rule.required if store.nodes_by_qualified_name(q, limit=1)]
    # Either side empty proves nothing, the forbidden rule's answer for the same shape (138).
    if not sources or not targets:
        missed = tuple(sorted({*rule.expect_violating, *rule.expect_passing}))
        report = RequiredRuleReport(
            rule.id, len(sources), len(targets), STATUS_MATCHED_NO_FILES, 0, missed
        )
        return report, [], []
    confirmed: list[RequiredViolation] = []
    candidates: list[RequiredViolation] = []
    for qname, path in sources:
        walk = store.required_walk(
            qname, targets, kinds=rule.kinds, depth=rule.depth, max_nodes=max_nodes
        )
        if walk.reached:
            continue
        row = RequiredViolation(rule.id, qname, path, walk.unresolved_outgoing, walk.truncated)
        sure = walk.unresolved_outgoing == 0 and not walk.truncated
        (confirmed if sure else candidates).append(row)
    flagged = {row.source_qname for row in confirmed}
    unsure = {row.source_qname for row in candidates}
    matched = {qname for qname, _ in sources}
    missed_list = [q for q in rule.expect_violating if q not in flagged]
    missed_list += [
        q for q in rule.expect_passing if q not in matched or q in flagged or q in unsure
    ]
    missed = tuple(sorted(set(missed_list)))
    expected = len(set(rule.expect_violating) | set(rule.expect_passing))
    status = STATUS_CALIBRATION_FAILED if missed else STATUS_CHECKED
    report = RequiredRuleReport(
        rule.id, len(sources), len(targets), status, expected - len(missed), missed
    )
    return report, confirmed, candidates


def _required_sources(
    store: GraphStore, files: Sequence[str], rule: RequiredRule
) -> list[tuple[str, str]]:
    """``(qname, file)`` per selected symbol, file then node order, each qname once."""
    pattern = re.compile(rule.name) if rule.name is not None else None
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for path in _matching_files(files, rule.sources):
        for row in store.nodes_by_file_all(path):
            qname = str(row["qualified_name"])
            if qname in seen:
                continue
            if rule.kind is not None and row["kind"] != rule.kind:
                continue
            if pattern is not None and not pattern.search(str(row["name"])):
                continue
            seen.add(qname)
            found.append((qname, path))
    return found


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


def _load_rules(label: str, text: str) -> list[ArchitectureRule | RequiredRule]:
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError(f"architecture_rules: {label!r} is not valid JSON ({error})") from error
    if not isinstance(payload, dict):
        raise ConfigError(f"architecture_rules: {label!r} root must be a JSON object")
    raw_rules = payload.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ConfigError(f"architecture_rules: {label!r} rules must be a non-empty list")
    rules: list[ArchitectureRule | RequiredRule] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(raw_rules):
        if not isinstance(entry, dict):
            raise ConfigError(f"architecture_rules: {label!r} rules[{index}] must be an object")
        rule_id = _required_str(label, entry, "id")
        if rule_id in seen_ids:
            raise ConfigError(f"architecture_rules: {label!r} duplicate rule id {rule_id!r}")
        seen_ids.add(rule_id)
        if "required" in entry:
            rules.append(_load_required_rule(label, rule_id, entry))
            continue
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


def _load_required_rule(label: str, rule_id: str, entry: Mapping[str, Any]) -> RequiredRule:
    """A required rule, or a ConfigError naming the field — never a half-read rule (R5.3)."""
    where = f"architecture_rules: {label!r} rule {rule_id!r}"
    misplaced = sorted({"forbidden", "direction", "transitive"} & set(entry))
    if misplaced:
        raise ConfigError(f"{where}: {', '.join(misplaced)} do not apply to a required rule")
    name = entry.get("name")
    if name is not None:
        if not isinstance(name, str) or not name:
            raise ConfigError(f"{where}: name must be a non-empty regex string")
        try:
            re.compile(name)
        except re.error as error:
            raise ConfigError(f"{where}: name is not a valid regex ({error})") from error
    kind = entry.get("kind")
    if kind is not None and kind not in NODE_KINDS:
        raise ConfigError(f"{where}: kind must be one of {', '.join(NODE_KINDS)}")
    depth = entry.get("depth")
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
        raise ConfigError(f"{where}: depth must be an integer >= 1")
    expect = entry.get("expect", {})
    if not isinstance(expect, dict) or set(expect) - {"violating", "passing"}:
        raise ConfigError(f"{where}: expect must be an object with violating / passing lists")
    return RequiredRule(
        id=rule_id,
        sources=_required_patterns(label, entry, "sources"),
        name=name,
        kind=kind,
        required=_qnames(where, entry.get("required"), "required", allow_empty=False),
        kinds=_optional_kinds(label, entry),
        depth=depth,
        expect_violating=_qnames(where, expect.get("violating", []), "expect.violating"),
        expect_passing=_qnames(where, expect.get("passing", []), "expect.passing"),
    )


def _qnames(where: str, raw: object, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(raw, list) or (not raw and not allow_empty):
        raise ConfigError(f"{where}: {field} must be a {'' if allow_empty else 'non-empty '}list")
    if not all(isinstance(item, str) and item.strip() for item in raw):
        raise ConfigError(f"{where}: {field} entries must be non-empty qname strings")
    return tuple(dict.fromkeys(item.strip() for item in raw))


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
