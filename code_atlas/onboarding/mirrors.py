"""Sibling subtrees holding near-copies of each other, discovered rather than configured (115).

Two subtrees of the anchor monorepo share 4,244 relative paths — 62 % of their union — and the map
never said so. That is the highest-value fact it produces, and three numbers are not the useful
form: a reader wants a lookup, and the **absence** answer marks divergence — which is exactly what
they must not assume away.

The pair is discovered. The mockup prototype matched one hardcoded tree prefix and two region names,
and carried those region names in its output keys; here both sides are read from the path set, so no
prefix, region or configured pair appears (R2.2). Pure: no SQL, no LLM, no language branch
(R1.1/R1.4/R4); sorted throughout, so identical input yields byte-identical output (R4.2).

**This compares paths, never bytes** — see :data:`PATH_NOT_CONTENT`, which ships on every report,
so no renderer can show the counts without the limit.
"""

from __future__ import annotations

import re
from collections.abc import Container, Sequence
from dataclasses import dataclass
from itertools import combinations

from code_atlas.ignore import translate_path_pattern
from code_atlas.onboarding.layers import responsibility_layer

# Both gates are needed, and the pinned public repos prove it: one of them scores a PERFECT overlap
# on a sibling pair sharing exactly ONE file, so the fraction alone accepts noise; two large but
# merely-adjacent trees can share many incidental paths, so the count alone accepts the opposite
# error. Chosen from the measurement recorded in the task (anchor 4,244 / 0.615; pins <= 1 / 0.091).
MIN_SHARED_PATHS = 25
MIN_OVERLAP = 0.30

# The 110 layers whose files are not candidates. This removes the measured false positive: a pair of
# mirrored TEST directories is mirrored scaffolding, not a mirrored application.
EXCLUDED_LAYERS = ("Vendor / Framework", "Tests")

PATH_NOT_CONTENT = (
    "Compares relative PATHS, not file contents: a shared path means both subtrees "
    "hold a file of that name, not that the two files are copies of each other."
)

# The three answers a lookup can give. ``no_counterpart`` is the divergence marker — the most useful
# answer, per the ticket — and ``outside_mirror`` is a clean negative rather than a guess.
COUNTERPART = "counterpart"
NO_COUNTERPART = "no_counterpart"
OUTSIDE_MIRROR = "outside_mirror"

__all__ = [
    "COUNTERPART",
    "EXCLUDED_LAYERS",
    "MIN_OVERLAP",
    "MIN_SHARED_PATHS",
    "NO_COUNTERPART",
    "OUTSIDE_MIRROR",
    "PATH_NOT_CONTENT",
    "Counterpart",
    "MirrorPair",
    "MirrorReport",
    "find_mirror_subtrees",
    "resolve_counterpart",
]


@dataclass(frozen=True)
class MirrorPair:
    """Two sibling subtrees and how much of their relative path sets coincide."""

    left: str
    right: str
    shared: int
    left_only: int
    right_only: int
    overlap: float
    sample: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view — what every renderer serialises (R4.2)."""
        return {
            "left": self.left,
            "left_only": self.left_only,
            "overlap": self.overlap,
            "right": self.right,
            "right_only": self.right_only,
            "sample": list(self.sample),
            "shared": self.shared,
        }


@dataclass(frozen=True)
class MirrorReport:
    """Every detected pair, plus the limit the numbers are allowed to claim."""

    pairs: tuple[MirrorPair, ...]
    caveat: str = PATH_NOT_CONTENT

    def as_dict(self) -> dict[str, object]:
        """The caveat rides WITH the counts, so no consumer can render one without the other."""
        return {
            "caveat": self.caveat,
            "pairs": [pair.as_dict() for pair in self.pairs],
        }


@dataclass(frozen=True)
class Counterpart:
    """The answer to "given this path, what is its sibling?" — including the negative."""

    status: str
    path: str = ""
    pair: tuple[str, str] | None = None
    qualified: bool = False

    def as_dict(self) -> dict[str, object]:
        """``qualified`` says the negative was drawn from an incomplete path set (H6)."""
        return {
            "pair": list(self.pair) if self.pair else None,
            "path": self.path,
            "qualified": self.qualified,
            "status": self.status,
        }


def _candidates(
    file_paths: Sequence[str], stub_roots: Sequence[str] | None
) -> tuple[str, ...]:
    """Paths that could belong to a mirrored application — 113's exclusion signals, reused."""
    rules = tuple(
        re.compile(f"{translate_path_pattern(f'{root}/**')}$") for root in stub_roots or ()
    )
    return tuple(
        sorted(
            path
            for path in file_paths
            if not any(rule.match(path) for rule in rules)
            and responsibility_layer(path) not in EXCLUDED_LAYERS
        )
    )


def _relative_sets(candidates: Sequence[str]) -> dict[str, set[str]]:
    """Every directory's set of paths RELATIVE to it — what two siblings are compared on."""
    relative: dict[str, set[str]] = {}
    for path in candidates:
        segments = path.split("/")
        for depth in range(1, len(segments)):
            relative.setdefault("/".join(segments[:depth]), set()).add(
                "/".join(segments[depth:])
            )
    return relative


def _siblings(candidates: Sequence[str]) -> dict[str, set[str]]:
    """Child directories grouped by parent; ``''`` is the repo root's own children."""
    children: dict[str, set[str]] = {}
    for path in candidates:
        segments = path.split("/")[:-1]
        for depth, segment in enumerate(segments):
            children.setdefault("/".join(segments[:depth]), set()).add(segment)
    return children


def find_mirror_subtrees(
    file_paths: Sequence[str],
    *,
    stub_roots: Sequence[str] | None = None,
    sample_limit: int,
    min_shared: int = MIN_SHARED_PATHS,
    min_overlap: float = MIN_OVERLAP,
) -> MirrorReport:
    """Discover sibling subtrees whose relative path sets largely coincide (task 115).

    Overlap is Jaccard (shared / union) — the measure that reproduces the anchor's reported 62 %.
    A pair must clear BOTH gates: enough shared paths to be a mirror at all, and a high enough
    fraction that "mirror" is not overstating an adjacency. Ranked by shared count, then by name.
    """
    candidates = _candidates(file_paths, stub_roots)
    relative = _relative_sets(candidates)
    pairs: list[MirrorPair] = []
    for parent, names in sorted(_siblings(candidates).items()):
        for left_name, right_name in combinations(sorted(names), 2):
            left = f"{parent}/{left_name}" if parent else left_name
            right = f"{parent}/{right_name}" if parent else right_name
            left_set = relative.get(left, set())
            right_set = relative.get(right, set())
            shared = left_set & right_set
            union = left_set | right_set
            if not union:
                continue
            overlap = len(shared) / len(union)
            if len(shared) < min_shared or overlap < min_overlap:
                continue
            pairs.append(
                MirrorPair(
                    left=left,
                    right=right,
                    shared=len(shared),
                    left_only=len(left_set - right_set),
                    right_only=len(right_set - left_set),
                    overlap=round(overlap, 3),
                    sample=tuple(sorted(shared)[:sample_limit]),
                )
            )
    pairs.sort(key=lambda pair: (-pair.shared, pair.left, pair.right))
    return MirrorReport(pairs=tuple(pairs))


def resolve_counterpart(
    path: str,
    pairs: Sequence[MirrorPair],
    known: Container[str],
    *,
    complete: bool = True,
) -> Counterpart:
    """Given a path, the parallel path in its mirror sibling — or an honest negative (task 115).

    Symmetric by construction: swapping a pair's two prefixes is its own inverse (AC2). ``complete``
    says whether ``known`` holds every indexed path; when it does not, a negative is ``qualified``,
    because a capped path index cannot tell a diverged file from a trimmed one (H6).
    """
    for pair in pairs:
        for source, target in ((pair.left, pair.right), (pair.right, pair.left)):
            prefix = f"{source}/"
            if not path.startswith(prefix):
                continue
            candidate = f"{target}/{path[len(prefix):]}"
            if candidate in known:
                return Counterpart(
                    status=COUNTERPART, path=candidate, pair=(pair.left, pair.right)
                )
            return Counterpart(
                status=NO_COUNTERPART,
                pair=(pair.left, pair.right),
                qualified=not complete,
            )
    return Counterpart(status=OUTSIDE_MIRROR)
