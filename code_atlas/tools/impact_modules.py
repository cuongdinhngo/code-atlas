"""``impact_modules`` — the blast radius rolled up to the modules it reaches (task 140).

`impact` answers in symbols; the decision that consumes it is module-shaped — *which modules does
this change reach, how many symbols in each, and which single edge do I read first*. Rolling 500
rows up by hand is the reader doing the whole answer.

This is a **join**, not a second model. The walk is `impact`'s own, the seeds are resolved by
`impact`'s own code, and the module names come from 114's table verbatim (PLAN §1: one graph, one
module notion). A file the table does not cover goes to its own bucket — inventing a home for it
would be the four-populations-in-one-number mistake 113 exists to prevent.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Literal, NamedTuple

from code_atlas.build_info import maybe_server_provenance
from code_atlas.config import Config
from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.onboarding.modules import (
    directory_owners,
    find_business_modules,
    module_of_path,
)
from code_atlas.store import GraphStore, Row
from code_atlas.tools import claim
from code_atlas.tools.impact import (
    attach_seed_expansion,
    attach_seed_refusals,
    plan_seeds,
    subject_parts,
)
from code_atlas.tools.nav_result import REASON_NOT_INDEXED, REASON_OK
from code_atlas.tools.staleness import compute_staleness

NAME = "impact_modules"

QUESTION = "blast-radius-by-module"
DetailLevel = Literal["minimal", "standard"]

# The bucket for a file 114's table does not cover. Rows carry ``assigned`` beside the name, so a
# repo that really has a module called this is still distinguishable from the bucket.
UNASSIGNED = "unassigned"

NOTE_UNDER_ESTIMATE = (
    "the walk stopped at CA_IMPACT_MAX_NODES, so every count below is an under-estimate — "
    "modules reached only beyond the bound are missing entirely, not merely undercounted"
)

NOTE_TABLE_TRUNCATED = (
    "the business-module table itself was capped at CA_MAX_RESULTS, so some rows counted under "
    "`unassigned` belong to modules that exist and were cut — that bucket is an over-count, and "
    "the modules named below are the largest, not all of them"
)

NOTE_NO_MODULE_TABLE = (
    "this repo has no business-module table — its layout is not capability-shaped (114), so every "
    "symbol below is unassigned and the answer cannot be module-shaped. That is a fact about the "
    "repo, not a miss: read the symbol-level answer from `impact` instead"
)

CLAIM_CARRY = ("seeds_dropped", "frontier_skipped_non_resolved")

__all__ = [
    "NAME",
    "NOTE_NO_MODULE_TABLE",
    "NOTE_TABLE_TRUNCATED",
    "NOTE_UNDER_ESTIMATE",
    "UNASSIGNED",
    "create",
]


class ModuleRollup(NamedTuple):
    """One module's share of the radius: how much, how well-evidenced, and where to start."""

    module: str
    assigned: bool
    symbols: int
    by_tier: dict[str, int]
    exemplar: str

    def as_row(self, *, detail_level: str) -> dict[str, object]:
        row: dict[str, object] = {
            "assigned": self.assigned,
            "by_tier": self.by_tier,
            "module": self.module,
            "symbols": self.symbols,
        }
        if detail_level == "standard":
            row["exemplar"] = self.exemplar
        return row


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def impact_modules(
        paths: list[str] | None = None,
        qnames: list[str] | None = None,
        depth: int | None = None,
        detail_level: DetailLevel = "standard",
        sign: bool = False,
    ) -> dict[str, object]:
        """Which modules does changing this reach, and how much of each?

        The same bounded walk as ``impact``, summarised by the business-module table the system map
        prints — so the two never disagree. Each row carries the symbol count split by confidence
        tier, because a module reached only through HEURISTIC edges has not been *shown* to be
        reached (136), and at ``standard`` one exemplar ``file:line`` to read first.

        Files no module covers are counted under ``unassigned`` rather than given a home. A walk
        that hits ``CA_IMPACT_MAX_NODES`` sets ``walk_truncated`` and labels every count an
        under-estimate (124) — a bounded walk reporting a total without saying so is a false total.

        ``sign`` adds the quotable ``claim`` line, as on ``impact``.
        """
        hops = config.impact_depth if depth is None else depth
        if hops < 0:
            raise ValueError(f"depth must be >= 0, got {hops}")
        parts = subject_parts(paths, qnames)
        subject = ",".join(parts)
        if not config.db_path.is_file():
            return _empty(
                config, subject, reason=REASON_NOT_INDEXED, depth=hops, detail_level=detail_level
            )

        with GraphStore(config.db_path) as store:
            plan = plan_seeds(
                store, paths=paths or [], qnames=qnames or [], max_results=config.max_results
            )
            outcome = store.impact_radius(
                plan.walk_seeds, depth=hops, max_nodes=config.impact_max_nodes + 1
            )
            truncated = len(outcome.rows) > config.impact_max_nodes
            rows = outcome.rows[: config.impact_max_nodes]
            owners, table_truncated = _owners(store, config)
            staleness = compute_staleness(store, config, include_dirty_count=True) if sign else {}

        rollups = _rollup(rows, owners)
        payload: dict[str, object] = {
            "depth": hops,
            "index_root": config.index_root,
            "indexed": True,
            "module_table_truncated": table_truncated,
            "modules_total": len(rollups),
            "reason": REASON_OK,
            "results": [rollup.as_row(detail_level=detail_level) for rollup in rollups],
            "symbols_total": sum(rollup.symbols for rollup in rollups),
            "walk_truncated": truncated,
            "frontier_skipped_non_resolved": outcome.frontier_skipped_non_resolved,
            "seeds_dropped": outcome.seeds_dropped + plan.refused,
            **maybe_server_provenance(detail_level),
        }
        notes = [NOTE_UNDER_ESTIMATE] if truncated else []
        if table_truncated:
            notes.append(NOTE_TABLE_TRUNCATED)
        if not owners and rows:
            # A single `unassigned` row reads like a miss; say which of the two it is.
            notes.append(NOTE_NO_MODULE_TABLE)
        if notes:
            payload["note"] = " · ".join(notes)
        # A module list that silently lost a seed is worse than one that names the loss, and the
        # rollup hides it better than `impact`'s symbol list does (179). Same disclosure, one site.
        attach_seed_expansion(payload, plan, paths)
        attach_seed_refusals(payload, plan)
        if not sign or not plan.walk_seeds:
            return payload
        return claim.sign(
            payload,
            tool=NAME,
            question=QUESTION,
            subject_parts=parts,
            staleness=staleness,
            carry=CLAIM_CARRY,
            extra=(("seeds", len(plan.walk_seeds)), ("modules", len(rollups))),
        )

    return impact_modules


def _empty(
    config: Config, subject: str, *, reason: str, depth: int, detail_level: str = "standard"
) -> dict[str, object]:
    return {
        "depth": depth,
        "index_root": config.index_root,
        "indexed": reason != REASON_NOT_INDEXED,
        "module_table_truncated": False,
        "modules_total": 0,
        "reason": reason,
        "results": [],
        "subject": subject,
        "symbols_total": 0,
        "walk_truncated": False,
        **maybe_server_provenance(detail_level),
    }


def _owners(store: GraphStore, config: Config) -> tuple[Mapping[str, str], bool]:
    """Directory → module from 114's table, plus whether that table was itself capped.

    ``fan_in`` is left empty on purpose: it feeds only each row's ``hub``/``hub_fan_in``, which a
    rollup never reads. The module set, their names and their directories do not depend on it, and
    computing it here would mean a whole-graph metrics pass this tool has no use for — a claim the
    AC3 test checks against the map's own table, which is built WITH fan-in.

    The cap is returned, never swallowed: a file whose module was cut resolves to no owner and
    lands in ``unassigned``, which would report a module that exists as no module at all.
    """
    table = find_business_modules(
        store.file_paths(),
        class_counts=dict(store.file_class_counts()),
        fan_in={},
        stub_roots=config.stub_roots,
        limit=config.max_results,
    )
    return directory_owners(table.modules), table.truncated


def _rollup(rows: Sequence[Row], owners: Mapping[str, str]) -> list[ModuleRollup]:
    """Group the radius by module, largest first; the name breaks ties so R4.2 holds."""
    counts: dict[tuple[str, bool], dict[str, int]] = {}
    best: dict[tuple[str, bool], tuple[float, str, str]] = {}
    for row in rows:
        path = str(row["file"])
        owner = module_of_path(path, owners)
        key = (owner, True) if owner is not None else (UNASSIGNED, False)
        tier = str(row["confidence_tier"])
        bucket = counts.setdefault(key, {name: 0 for name in CONFIDENCE_TIERS})
        bucket[tier] = bucket.get(tier, 0) + 1
        # Best score wins the exemplar; the qname breaks the tie so the pick cannot drift (R4.2).
        candidate = (-float(str(row["score"])), str(row["qname"]), f"{path}:{row['line']}")
        if key not in best or candidate < best[key]:
            best[key] = candidate

    rollups = [
        ModuleRollup(
            module=name,
            assigned=assigned,
            symbols=sum(bucket.values()),
            by_tier=bucket,
            exemplar=best[(name, assigned)][2],
        )
        for (name, assigned), bucket in counts.items()
    ]
    rollups.sort(key=lambda rollup: (-rollup.symbols, rollup.module))
    return rollups
