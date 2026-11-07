"""``compute`` — exact answers over the whole graph from a named template, never caller SQL (440).

A model cannot count, group or prove an absence from inside its context. A template is an id, a
one-line question, typed parameters, and a body ``store.py`` holds and runs in a read-only sandbox
with a deadline and a row cap. Every answer carries a data-driven ``caveat``, a truthful
``total_count`` and, when empty, the reason it is empty. An absence names its evidence level.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from code_atlas import contract, gitutil
from code_atlas.config import Config, clamp_limit
from code_atlas.store import COMPUTE_QUERIES, COMPUTE_ROW_CAP, ComputeRefused, ComputeSandbox

NAME = "compute"
TemplateId = Literal["tier_mix", "no_referrer"]
# Evidence for an absence (440): never "dead" — an unmentioned name is a strong candidate only.
NO_EDGE_NO_MENTION = "no_edge_no_mention"
NO_EDGE_BUT_MENTIONED = "no_edge_but_mentioned"
MENTION_UNCHECKED = "mention_unchecked"
# A trigram index cannot look up a shorter name; the grep still can.
_MIN_TEXT_MATCH = 3
# One git grep for the page's names; past it an absence is `mention_unchecked`, never strong.
GREP_DEADLINE_S = 3.0


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    required: bool
    meaning: str


@dataclass(frozen=True, slots=True)
class Template:
    id: str
    question: str
    params: tuple[Param, ...]
    absence: bool = False


_PREFIX = Param("path_prefix", False, "only files under this repo-relative prefix")
TEMPLATES: tuple[Template, ...] = (
    Template(
        "tier_mix",
        "How are the edges of each kind split across confidence tiers?",
        (Param("edge_kind", False, "one edge kind, e.g. CALLS"), _PREFIX),
    ),
    Template(
        "no_referrer",
        "Which symbols of one kind does no edge reach — and is each name mentioned anywhere?",
        (Param("kind", True, "a node kind, e.g. Function"), _PREFIX),
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
                    p.name: {"required": p.required, "meaning": p.meaning} for p in t.params
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
    prefix = given.get("path_prefix")
    return {
        "kind": str(kind) if kind else None,
        "edge_kind": str(edge_kind) if edge_kind else None,
        "prefix": str(prefix).strip().lstrip("./").rstrip("/") + "/" if prefix else None,
    }


def _share(part: object, whole: object) -> float:
    total = int(str(whole or 0))
    return round(int(str(part or 0)) / total, 4) if total else 0.0


def tier_mix(
    box: ComputeSandbox, params: dict[str, str | None], cap: int, root: Path
) -> dict[str, object]:
    body = COMPUTE_QUERIES["tier_mix"]
    rows, truncated = box.query(body, params, cap=cap)
    edges, heuristic, unlinked = box.scalar(COMPUTE_QUERIES["tier_mix.caveat"], params)
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
    body = COMPUTE_QUERIES["no_referrer"]
    rows, truncated = box.query(body, params, cap=cap)
    sites = gitutil.word_sites(root, sorted({str(r[1]) for r in rows}), timeout=GREP_DEADLINE_S)
    shaped: list[dict[str, object]] = []
    levels = {NO_EDGE_NO_MENTION: 0, NO_EDGE_BUT_MENTIONED: 0, MENTION_UNCHECKED: 0}
    for qname, name, file, line in rows:
        level = _evidence(box, (str(qname), str(name), str(file), int(str(line))), sites)
        levels[level] += 1
        shaped.append({"qname": qname, "name": name, "file": file, "line": line, "evidence": level})
    edges, unlinked = box.scalar(COMPUTE_QUERIES["no_referrer.caveat"])
    population = box.scalar(COMPUTE_QUERIES["no_referrer.population"], params)
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
    sites: Mapping[str, set[tuple[str, int]]] | None,
) -> str:
    """Whether a name no edge reaches is still named: an unlinked reference, another symbol's
    text, or anywhere in the tracked tree but its own definition line (a time-capped grep)."""
    qname, name, file, line = symbol
    if box.scalar(COMPUTE_QUERIES["mention.raw"], {"name": name, "qname": qname}):
        return NO_EDGE_BUT_MENTIONED
    if len(name) >= _MIN_TEXT_MATCH:
        phrase = '{name params} : "' + name.replace('"', '""') + '"'
        if box.scalar(COMPUTE_QUERIES["mention.text"], {"phrase": phrase, "qname": qname}):
            return NO_EDGE_BUT_MENTIONED
    if sites is None:
        return MENTION_UNCHECKED
    if sites.get(name, set()) - {(file, line)}:
        return NO_EDGE_BUT_MENTIONED
    return NO_EDGE_NO_MENTION


_Runner = Callable[[ComputeSandbox, dict[str, str | None], int, Path], dict[str, object]]
_RUNNERS: Mapping[str, _Runner]
_RUNNERS = {"tier_mix": tier_mix, "no_referrer": no_referrer}


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def compute(
        template: TemplateId | None = None,
        params: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> dict[str, object]:
        """Count, group or prove an absence over the whole graph — exact, not sampled.

        Use for "how many", "which have none", "what share" questions; leave a template out
        to list the catalogue (id, question, params). `no_referrer` overlaps `find_orphans`
        but needs no entry points and labels each absence `no_edge_no_mention` (a strong
        candidate) or `no_edge_but_mentioned` (unknown, never dead). Set `template`,
        `params`, `limit`. Read `caveat`, `total_count`, `truncated`, `reason` when empty.
        """
        if template is None:
            return catalogue()
        chosen = _BY_ID.get(template)
        if chosen is None:
            raise ValueError(f"unknown template {template!r}; one of {', '.join(_BY_ID)}")
        bound = _checked(chosen, dict(params or {}))
        cap, clamped = clamp_limit(limit, min(config.page_limit, COMPUTE_ROW_CAP))
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        answer: dict[str, object] = {"template": chosen.id, "question": chosen.question}
        try:
            with ComputeSandbox(config.db_path) as box:
                answer.update(_RUNNERS[chosen.id](box, bound, cap, config.root))
        except ComputeRefused as refused:
            # Never a partial answer presented as complete: no rows, and why.
            return {**answer, "reason": refused.reason, "detail": refused.detail, "rows": []}
        empty = answer.pop("empty_reason")
        answer["reason"] = "ok" if answer["rows"] else empty
        answer["limit"] = cap
        if clamped:
            answer["limit_capped_to"] = cap
        return answer

    return compute
