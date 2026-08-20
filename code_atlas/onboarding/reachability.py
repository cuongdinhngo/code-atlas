"""Zero-inbound modules split into the populations they actually are (task 113, M11).

One number — ``module entry points: 8,477`` — read to a first-day developer as "8,475 endpoints".
Split by signal, the same set is a web surface of ~1,000, vendored code, tests, files reached
dynamically, and the only genuinely suspicious population: those with no edge either way.

Composition, not a new signal: 110's ratified responsibility vocabulary (``layers.py``), 083's
degrees (``metrics.py``), and the operator's own two declarations (``entry_points``/``stub_roots``).
No library-name list — that would be the R2.2 violation this module exists to avoid. Pure: no SQL,
no LLM, no language branch (R1.1/R1.4/R4); fixed bucket order and sorted samples, so identical
input yields byte-identical output (R4.2).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from code_atlas.ignore import translate_path_pattern
from code_atlas.onboarding.layers import responsibility_layer
from code_atlas.onboarding.metrics import GraphMetrics

# The responsibility layers 110 ratified that name a population here. Derived-from-source: a pin
# test asserts every value is a layer 110 can emit, so a renamed layer cannot ship unmatched (R6.7).
LAYER_WEB_ENTRY = "HTTP / Entry"
LAYER_VENDOR = "Vendor / Framework"
LAYER_TESTS = "Tests"

WEB_ENTRY = "web_entry"
VENDOR = "vendor"
TEST = "test"
DYNAMIC = "dynamic_or_unresolved"
ISOLATED = "isolated"

# The reason a bucket is dropped rather than zeroed (AC5): path naming carries no information here.
NO_VOCABULARY_SIGNAL = (
    "no indexed path names a responsibility role; the responsibility-vocabulary "
    "signal carries no information for this repo"
)

# One table, so no renderer re-words a bucket. Order is the reading order and is fixed (R4.2).
# ``note`` is the wording AC3 governs: the dynamic bucket denies deadness outright, and the isolated
# bucket is a suspicion, never a verdict. ``signal`` names what proved membership.
BUCKET_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        WEB_ENTRY,
        "Web entry points",
        "declared entry-point globs, or a path naming a request-handling responsibility",
        "The web surface a request can actually arrive at.",
    ),
    (
        VENDOR,
        "Vendored dependencies",
        "declared dependency roots, or a path naming third-party code",
        "Third-party code that ships with the repo; not this team's surface.",
    ),
    (
        TEST,
        "Tests and fixtures",
        "a path naming a test responsibility",
        "Test and fixture code; nothing in production calls into it by design.",
    ),
    (
        DYNAMIC,
        "Not statically reachable",
        "no inbound edge, but outbound edges of its own",
        "Reached dynamically, or by a caller the index cannot resolve — not dead code.",
    ),
    (
        ISOLATED,
        "No edge either way — worth checking",
        "no inbound and no outbound edge",
        "A list to check, not a conclusion: nothing statically links these either way.",
    ),
)

BUCKETS: tuple[str, ...] = tuple(spec[0] for spec in BUCKET_SPECS)

__all__ = [
    "BUCKETS",
    "BUCKET_SPECS",
    "DYNAMIC",
    "ISOLATED",
    "LAYER_TESTS",
    "LAYER_VENDOR",
    "LAYER_WEB_ENTRY",
    "NO_VOCABULARY_SIGNAL",
    "ReachabilityBucket",
    "ReachabilitySplit",
    "TEST",
    "VENDOR",
    "WEB_ENTRY",
    "classify_reachability",
]


@dataclass(frozen=True)
class ReachabilityBucket:
    """One population of the zero-inbound set: its count, its wording, and a bounded sample."""

    bucket: str
    label: str
    signal: str
    note: str
    count: int
    sample: tuple[str, ...]
    sample_truncated: bool

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view — what every renderer serialises (R4.2)."""
        return {
            "bucket": self.bucket,
            "count": self.count,
            "label": self.label,
            "note": self.note,
            "sample": list(self.sample),
            "sample_truncated": self.sample_truncated,
            "signal": self.signal,
        }


@dataclass(frozen=True)
class ReachabilitySplit:
    """The zero-inbound set as its populations, plus the raw total it used to be reported as."""

    total: int
    buckets: tuple[ReachabilityBucket, ...]
    dropped: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view; ``total`` keeps the raw number, just not as the headline."""
        return {
            "buckets": [bucket.as_dict() for bucket in self.buckets],
            "dropped": [{"bucket": bucket, "reason": reason} for bucket, reason in self.dropped],
            "total": self.total,
        }


def _matcher(patterns: Sequence[str]) -> tuple[re.Pattern[str], ...]:
    """Compile declaration globs with the repo's one glob dialect (``ignore.py``), not a second."""
    return tuple(re.compile(f"{translate_path_pattern(pattern)}$") for pattern in patterns)


def _matches(path: str, rules: Sequence[re.Pattern[str]]) -> bool:
    return any(rule.match(path) for rule in rules)


def _bucket_of(
    path: str,
    *,
    fan_out: int,
    entry_rules: Sequence[re.Pattern[str]],
    stub_rules: Sequence[re.Pattern[str]],
    vocabulary: bool,
) -> str:
    """The one bucket a zero-inbound module lands in. First match wins, so buckets are disjoint.

    Role before structure: a test file with no edges is a test, not a dead-code candidate.
    """
    if _matches(path, entry_rules):
        return WEB_ENTRY
    if _matches(path, stub_rules):
        return VENDOR
    if vocabulary:
        layer = responsibility_layer(path)
        if layer == LAYER_WEB_ENTRY:
            return WEB_ENTRY
        if layer == LAYER_VENDOR:
            return VENDOR
        if layer == LAYER_TESTS:
            return TEST
    return DYNAMIC if fan_out else ISOLATED


def classify_reachability(
    metrics: GraphMetrics,
    *,
    entry_points: Sequence[str] | None = None,
    stub_roots: Sequence[str] | None = None,
    sample_limit: int,
) -> ReachabilitySplit:
    """Split the zero-inbound modules into the populations above (task 113).

    ``entry_points``/``stub_roots`` are the operator's own declarations — the highest-trust signal,
    because they are that operator's statement about their own repo rather than the core guessing.
    A bucket whose every signal is unavailable is DROPPED with its reason, never rendered as a
    misleading zero (AC5); an empty bucket under an available signal is an honest zero (AC4).
    """
    entry_rules = _matcher(tuple(entry_points or ()))
    # A stub root is a DIRECTORY, not a glob: match the dir itself and everything beneath it.
    stub_rules = _matcher(tuple(f"{root}/**" for root in stub_roots or ()))
    # The vocabulary signal informs nothing when no indexed path names any responsibility at all.
    vocabulary = any(responsibility_layer(metric.key) is not None for metric in metrics.modules)
    fan_out_of: Mapping[str, int] = {metric.key: metric.fan_out for metric in metrics.modules}

    members: dict[str, list[str]] = {bucket: [] for bucket in BUCKETS}
    for path in sorted(metrics.module_entry_points):
        bucket = _bucket_of(
            path,
            fan_out=fan_out_of.get(path, 0),
            entry_rules=entry_rules,
            stub_rules=stub_rules,
            vocabulary=vocabulary,
        )
        members[bucket].append(path)

    # A structural bucket is always fillable; a vocabulary-only bucket is not, unless the operator
    # declared its own roots — a declaration stands on its own, whatever the paths look like.
    declared = {WEB_ENTRY: bool(entry_rules), VENDOR: bool(stub_rules), TEST: False}
    buckets: list[ReachabilityBucket] = []
    dropped: list[tuple[str, str]] = []
    for bucket, label, signal, note in BUCKET_SPECS:
        if bucket in declared and not vocabulary and not declared[bucket]:
            dropped.append((bucket, NO_VOCABULARY_SIGNAL))
            continue
        paths = members[bucket]
        buckets.append(
            ReachabilityBucket(
                bucket=bucket,
                label=label,
                signal=signal,
                note=note,
                count=len(paths),
                sample=tuple(paths[:sample_limit]),
                sample_truncated=len(paths) > sample_limit,
            )
        )
    return ReachabilitySplit(
        total=len(metrics.module_entry_points),
        buckets=tuple(buckets),
        dropped=tuple(dropped),
    )
