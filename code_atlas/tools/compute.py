"""``compute`` — exact answers over the whole graph from a named template, never caller SQL (440).

A model cannot count, group or prove an absence from inside its context. A template is an id, a
one-line question, typed parameters, and a body ``store.py`` holds and runs in a read-only sandbox
with a deadline and a row cap. Every answer carries a data-driven ``caveat``, a truthful
``total_count`` and, when empty, the reason it is empty. An absence names its evidence level.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from code_atlas import contract, gitutil
from code_atlas.config import Config, clamp_limit
from code_atlas.store import COMPUTE_ROW_CAP, ComputeRefused, ComputeSandbox
from code_atlas.tools.nav_result import attach_limit_capped

NAME = "compute"
TemplateId = Literal["tier_mix", "no_referrer"]
DetailLevel = Literal["minimal", "standard"]
# What `minimal` leaves out: the question echoed back and the numbers behind the caveat.
_STANDARD_ONLY = ("question", "caveat_data", "evidence_levels", "mention_checks")
# Evidence for an absence (440): never "dead" — an unmentioned name is a strong candidate only.
NO_EDGE_NO_MENTION = "no_edge_no_mention"
NO_EDGE_BUT_MENTIONED = "no_edge_but_mentioned"
MENTION_UNCHECKED = "mention_unchecked"
# A trigram index cannot look up a shorter name; the grep still can.
_MIN_TEXT_MATCH = 3
# One git grep for the page's names; past it an absence is `mention_unchecked`, never strong.
GREP_DEADLINE_S = 3.0
# Every row's mention checks share one budget; a row past it is mention_unchecked.
MENTION_BUDGET_S = 10.0


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    required: bool
    meaning: str
    type: str  # node_kind · edge_kind · path_prefix: each a closed check in `_checked`


# Each parameter type and the values it admits; a path prefix is any repo-relative string.
PARAM_TYPES: Mapping[str, tuple[str, ...]] = {
    "node_kind": contract.NODE_KINDS,
    "edge_kind": contract.EDGE_KINDS,
    "path_prefix": (),
}


@dataclass(frozen=True, slots=True)
class Template:
    id: str
    question: str
    params: tuple[Param, ...]
    body: str  # its key in store.COMPUTE_QUERIES, the only SQL it runs (store owns SQL)
    absence: bool = False


_PREFIX = Param("path_prefix", False, "only files under this repo-relative prefix", "path_prefix")
TEMPLATES: tuple[Template, ...] = (
    Template(
        "tier_mix",
        "How are the edges of each kind split across confidence tiers?",
        (Param("edge_kind", False, "one edge kind, e.g. CALLS", "edge_kind"), _PREFIX),
        "tier_mix",
    ),
    Template(
        "no_referrer",
        "Which symbols of one kind does no edge reach — and is each name mentioned anywhere?",
        (Param("kind", True, "a node kind, e.g. Function", "node_kind"), _PREFIX),
        "no_referrer",
        absence=True,
    ),
)
_BY_ID: Mapping[str, Template] = {template.id: template for template in TEMPLATES}


def catalogue() -> dict[str, object]:
    """What ``compute`` with no template answers: every template's id, question and params."""
    return {
        "reason": "catalogue",
        "templates": [
            {
                "id": t.id,
                "question": t.question,
                "params": {
                    p.name: {
                        "type": p.type,
                        "required": p.required,
                        "meaning": p.meaning,
                        **({"one_of": list(PARAM_TYPES[p.type])} if PARAM_TYPES[p.type] else {}),
                    }
                    for p in t.params
                },
            }
            for t in TEMPLATES
        ],
    }


def _checked(template: Template, given: Mapping[str, object]) -> dict[str, str | None]:
    """The template's closed parameter set: one it does not take, a missing one, or a value that
    is not a string fails loud."""
    taken = {p.name for p in template.params}
    extra = sorted(name for name in given if name not in taken)
    if extra:
        raise ValueError(f"{template.id} takes {sorted(taken)}; not {', '.join(extra)}")
    for param in template.params:
        if param.required and not given.get(param.name):
            raise ValueError(f"{template.id} needs {param.name} ({param.meaning})")
    for name, value in given.items():
        if not isinstance(value, str):
            raise ValueError(f"{template.id}: {name} must be a string")
    kind, edge_kind = given.get("kind"), given.get("edge_kind")
    if kind is not None and kind not in contract.NODE_KINDS:
        raise ValueError(f"kind must be one of {', '.join(contract.NODE_KINDS)}")
    if edge_kind is not None and edge_kind not in contract.EDGE_KINDS:
        raise ValueError(f"edge_kind must be one of {', '.join(contract.EDGE_KINDS)}")
    # `.`, `./` and `/` all name the repo root: no filter, never a prefix that matches nothing.
    prefix = str(given.get("path_prefix") or "").strip()
    while prefix.startswith("./"):
        prefix = prefix[2:]
    prefix = "" if prefix == "." else prefix.lstrip("/").rstrip("/")
    return {
        "kind": str(kind) if kind else None,
        "edge_kind": str(edge_kind) if edge_kind else None,
        "prefix": prefix + "/" if prefix else None,
    }


def _share(part: object, whole: object) -> float:
    total = int(str(whole or 0))
    return round(int(str(part or 0)) / total, 4) if total else 0.0


def tier_mix(
    box: ComputeSandbox, params: dict[str, str | None], cap: int, root: Path
) -> dict[str, object]:
    body = "tier_mix"
    rows, truncated = box.query(body, params, cap=cap)
    edges, heuristic, unlinked = box.scalar("tier_mix.caveat", params)
    data = {
        "edges": int(str(edges)),
        "heuristic_share": _share(heuristic, edges),
        "unlinked_share": _share(unlinked, edges),
    }
    return {
        "rows": [{"edge_kind": r[0], "tier": r[1], "edges": r[2]} for r in rows],
        "total_count": box.count(body, params),
        "truncated": truncated,
        "caveat": (
            f"{data['heuristic_share']:.1%} of these edges are HEURISTIC and "
            f"{data['unlinked_share']:.1%} never linked to a definition"
        ),
        "caveat_data": data,
        "empty_reason": "no_edge_matches",
    }


def no_referrer(
    box: ComputeSandbox, params: dict[str, str | None], cap: int, root: Path
) -> dict[str, object]:
    body = "no_referrer"
    rows, truncated = box.query(body, params, cap=cap)
    sites = gitutil.word_sites(root, sorted({str(r[1]) for r in rows}), timeout=GREP_DEADLINE_S)
    shaped: list[dict[str, object]] = []
    levels = {NO_EDGE_NO_MENTION: 0, NO_EDGE_BUT_MENTIONED: 0, MENTION_UNCHECKED: 0}
    until = time.monotonic() + MENTION_BUDGET_S
    for qname, name, file, line in rows:
        symbol = (str(qname), str(name), str(file), int(str(line)))
        level = _evidence(box, symbol, sites) if time.monotonic() < until else MENTION_UNCHECKED
        levels[level] += 1
        # One key per statement: the contract's field words stay out of a collection literal.
        row: dict[str, object] = {"qname": qname, "evidence": level}
        row["name"] = name
        row["file"] = file
        row["line"] = line
        shaped.append(row)
    edges, unlinked = box.scalar("no_referrer.caveat")
    population = box.scalar("no_referrer.population", params)
    data = {"unlinked_share": _share(unlinked, edges), "population": int(str(population[0]))}
    return {
        "rows": shaped,
        "total_count": box.count(body, params),
        "truncated": truncated,
        "evidence_levels": levels,
        "mention_checks": len(rows),
        "caveat": (
            f"{data['unlinked_share']:.1%} of the graph's edges never linked to a definition: "
            "no edge is not no caller. no_edge_but_mentioned is unknown, never dead"
        ),
        "caveat_data": data,
        "empty_reason": (
            "every_one_is_referenced" if data["population"] else "no_symbol_of_that_kind"
        ),
    }


def _evidence(
    box: ComputeSandbox,
    symbol: tuple[str, str, str, int],
    sites: Mapping[str, list[tuple[str, int]]] | None,
) -> str:
    """Whether a name no edge reaches is still named: an unlinked reference, another symbol's
    text, or anywhere in the tracked tree but its own definition line (a time-capped grep)."""
    qname, name, file, line = symbol
    try:
        if box.scalar("mention.raw", {"name": name, "qname": qname}):
            return NO_EDGE_BUT_MENTIONED
        if len(name) >= _MIN_TEXT_MATCH:
            phrase = '{name params} : "' + name.replace('"', '""') + '"'
            if box.scalar("mention.text", {"phrase": phrase, "qname": qname}):
                return NO_EDGE_BUT_MENTIONED
    except ComputeRefused as refused:
        if refused.reason != "deadline_exceeded":
            raise
        return MENTION_UNCHECKED  # one slow check costs its row, never the page
    if sites is None or name not in sites:
        return MENTION_UNCHECKED  # cut by the deadline, or a name grep cannot search
    # One occurrence is the definition itself; `foo(foo)` on that line is still a mention.
    elsewhere = len(sites[name]) - (1 if (file, line) in sites[name] else 0)
    return NO_EDGE_BUT_MENTIONED if elsewhere > 0 else NO_EDGE_NO_MENTION


_Runner = Callable[[ComputeSandbox, dict[str, str | None], int, Path], dict[str, object]]
_RUNNERS: Mapping[str, _Runner]
_RUNNERS = {"tier_mix": tier_mix, "no_referrer": no_referrer}


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def compute(
        template: TemplateId | None = None,
        params: dict[str, str] | None = None,
        limit: int | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """Count, group or prove an absence over the whole graph — exact, not sampled.

        Use for "how many", "which have none", "what share" questions; leave a template out
        to list the catalogue (id, question, params). `no_referrer` overlaps `find_orphans`
        but needs no entry points and labels each absence `no_edge_no_mention` (a strong
        candidate) or `no_edge_but_mentioned` (unknown, never dead). Set `template`,
        `params`, `limit`. Read `caveat`, `total_count`, `truncated`, `reason` when empty.
        """
        if template is None:
            return {**catalogue(), "index_root": config.index_root}
        chosen = _BY_ID.get(template)
        if chosen is None:
            raise ValueError(f"unknown template {template!r}; one of {', '.join(_BY_ID)}")
        if params is not None and not isinstance(params, dict):
            raise ValueError("params must be an object of name -> string")
        bound = _checked(chosen, dict(params or {}))
        cap, clamped = clamp_limit(limit, min(config.page_limit, COMPUTE_ROW_CAP))
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        answer: dict[str, object] = {
            "template": chosen.id,
            "question": chosen.question,
            "index_root": config.index_root,
        }
        try:
            with ComputeSandbox(config.db_path) as box:
                answer.update(_RUNNERS[chosen.id](box, bound, cap, config.root))
        except ComputeRefused as refused:
            # Never a partial answer presented as complete: no rows, and why.
            return {**answer, "reason": refused.reason, "detail": refused.detail, "rows": []}
        empty = answer.pop("empty_reason")
        answer["reason"] = "ok" if answer["rows"] else empty
        answer["limit"] = cap
        if detail_level == "minimal":
            for key in _STANDARD_ONLY:
                answer.pop(key, None)
        return attach_limit_capped(answer, cap=cap, clamped=clamped)

    return compute
