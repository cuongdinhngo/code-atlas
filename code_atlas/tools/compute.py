"""``compute`` — exact answers over the whole graph from a named template, never caller SQL (440).

A model cannot count, group or prove an absence from inside its context. A template is an id, a
one-line question, typed parameters, and a body ``store.py`` holds and runs in a read-only sandbox
with a deadline and a row cap. Every answer carries a data-driven ``caveat``, a truthful
``total_count`` and, when empty, the reason it is empty. An absence names its evidence level.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from code_atlas import contract, gitutil
from code_atlas.config import Config, ConfigError, clamp_limit, variant_pattern
from code_atlas.enrichment import DEFINITION_ORDER_META_KEY, DEFINITION_PRECEDENCE_META_KEY
from code_atlas.onboarding.modules import module_of_path
from code_atlas.store import COMPUTE_ROW_CAP, ComputeRefused, ComputeSandbox, GraphStore
from code_atlas.tools.impact_modules import UNASSIGNED, module_owners
from code_atlas.tools.nav_result import attach_limit_capped
from code_atlas.tools.symbol_pointers import DEFINITION_LIVE, definition_states

NAME = "compute"
TemplateId = Literal[
    "tier_mix",
    "no_referrer",
    "unreferenced_objects",
    "calls_by_module",
    "untested_classes",
    "resolved_share",
    "includes_by_dir",
    "multi_defined",
    "variant_pairs",
]
DetailLevel = Literal["minimal", "standard"]
# What `minimal` leaves out: the question echoed back and the numbers behind the caveat.
_STANDARD_ONLY = ("question", "caveat_data", "evidence_levels", "mention_checks")
# Evidence for an absence (440): never "dead" — an unmentioned name is a strong candidate only.
NO_EDGE_NO_MENTION = "no_edge_no_mention"
NO_EDGE_BUT_MENTIONED = "no_edge_but_mentioned"
MENTION_UNCHECKED = "mention_unchecked"
# A trigram index cannot look up a shorter name; the grep still can.
_MIN_TEXT_MATCH = 3
# An aggregate a template reads whole (per file, per type) before it pages: past it, refused.
INTERNAL_CAP = 200_000
# A qname's definitions read for its live one; more and the answer is not complete (437).
SITES_CAP = 50
# One git grep for the page's names; past it an absence is `mention_unchecked`, never strong.
GREP_DEADLINE_S = 3.0
# Every row's mention checks share one budget; a row past it is mention_unchecked.
MENTION_BUDGET_S = 10.0


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    required: bool
    meaning: str
    type: str  # a PARAM_TYPES key: each a closed check in `_checked`


# Each parameter type and the values it admits; a path prefix is any repo-relative string.
PARAM_TYPES: Mapping[str, tuple[str, ...]] = {
    "node_kind": contract.NODE_KINDS,
    "edge_kind": contract.EDGE_KINDS,
    "path_prefix": (),
    "language": (),  # a value the index recorded — never a branch on it (R1.1)
    "qname_glob": (),  # GLOB over a qname: `*` any run, `?` one character
    "name_pattern": (),  # a name with exactly one `*`, the stem two variants share
}


@dataclass(frozen=True, slots=True)
class Template:
    id: str
    question: str
    params: tuple[Param, ...]
    body: str  # its key in store.COMPUTE_QUERIES, the only SQL it runs (store owns SQL)
    absence: bool = False


_PREFIX = Param("path_prefix", False, "only files under this repo-relative prefix", "path_prefix")
_KIND = Param("kind", False, "only symbols of this node kind", "node_kind")
TEMPLATES: tuple[Template, ...] = (
    Template(
        "tier_mix",
        "How are the edges of each kind, per source and target language, split across tiers?",
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
    Template(
        "unreferenced_objects",
        "Which objects of one kind does no edge from one language reach, by evidence level?",
        (
            Param("kind", True, "a node kind, e.g. Table", "node_kind"),
            Param(
                "language", False, "count only referrers in this language, as indexed", "language"
            ),
            _PREFIX,
        ),
        "unreferenced_objects",
        absence=True,
    ),
    Template(
        "calls_by_module",
        "Which modules call into a target set, and how many calls each?",
        (
            Param("target", False, "a qname GLOB, e.g. *Repository::save*", "qname_glob"),
            Param("target_kind", False, "or every symbol of this node kind", "node_kind"),
            Param("edge_kind", False, "the call edge kind; CALLS when left out", "edge_kind"),
            _PREFIX,
        ),
        "calls_by_module",
    ),
    Template(
        "untested_classes",
        "Which classes does no edge from a test reach, per module?",
        (Param("kind", False, "the type kind; Class when left out", "node_kind"), _PREFIX),
        "untested.types",
    ),
    Template(
        "resolved_share",
        "What share of each module's calls resolved to one definition?",
        (_PREFIX,),
        "resolved_share",
    ),
    Template(
        "includes_by_dir",
        "How many include / require edges does each top directory make, by tier?",
        (_PREFIX,),
        "includes_by_dir",
    ),
    Template(
        "multi_defined",
        "Which objects are defined more than once, and which definition is live?",
        (_KIND, Param("language", False, "only definitions in this language, as indexed",
                      "language"), _PREFIX),
        "multi_defined",
    ),
    Template(
        "variant_pairs",
        "Which name variants (e.g. foo / fooAsync) are used on one side only?",
        (
            Param("left", False, "a name with one *, e.g. *Async", "name_pattern"),
            Param("right", False, "its variant, e.g. *; toml variant_pairs when left out",
                  "name_pattern"),
            _KIND,
            _PREFIX,
        ),
        "variant_pairs",
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
    for param in template.params:
        value = given.get(param.name)
        allowed = PARAM_TYPES[param.type]
        if value is not None and allowed and value not in allowed:
            raise ValueError(f"{param.name} must be one of {', '.join(allowed)}")
        if value is not None and param.type == "name_pattern":
            try:
                variant_pattern(param.name, str(value))  # one `*`, nothing a glob reads
            except ConfigError as error:
                raise ValueError(str(error)) from None
    # `.`, `./` and `/` all name the repo root: no filter, never a prefix that matches nothing.
    prefix = str(given.get("path_prefix") or "").strip()
    while prefix.startswith("./"):
        prefix = prefix[2:]
    prefix = "" if prefix == "." else prefix.lstrip("/").rstrip("/")
    bound: dict[str, str | None] = {
        name: (str(given[name]) if given.get(name) else None)
        for name in ("kind", "edge_kind", "language", "target", "target_kind", "left", "right")
    }
    bound["prefix"] = prefix + "/" if prefix else None
    return bound


def _share(part: object, whole: object) -> float:
    total = int(str(whole or 0))
    return round(int(str(part or 0)) / total, 4) if total else 0.0


Params = dict[str, str | None]


def tier_mix(box: ComputeSandbox, params: Params, cap: int, config: Config) -> dict[str, object]:
    # A few hundred groups at most (kinds x languages x tiers): read once, paged and summed here.
    found = _whole(box, "tier_mix", params)
    edges = sum(int(str(r[4])) for r in found)
    heuristic = sum(int(str(r[4])) for r in found if r[3] == "HEURISTIC")
    unlinked = sum(int(str(r[4])) for r in found if r[2] is None)
    data = {
        "edges": edges,
        "heuristic_share": _share(heuristic, edges),
        "unlinked_share": _share(unlinked, edges),
    }
    shaped = []
    for kind, source, target, tier, count in found:
        # One key per statement: the contract's field words stay out of a collection literal.
        row: dict[str, object] = {"edge_kind": kind}
        row["source_language"] = source or None
        row["target_language"] = target or None  # None: never linked, or a target with no node
        row["tier"] = tier
        row["edges"] = count
        shaped.append(row)
    page, truncated = _page(shaped, cap)
    return {
        "rows": page,
        "total_count": len(shaped),
        "truncated": truncated,
        "caveat": (
            f"{data['heuristic_share']:.1%} of these edges are HEURISTIC and "
            f"{data['unlinked_share']:.1%} never linked to a definition; a null target_language "
            "is that, or a target the index holds no symbol for"
        ),
        "caveat_data": data,
        "empty_reason": "no_edge_matches",
    }


def no_referrer(box: ComputeSandbox, params: Params, cap: int, config: Config) -> dict[str, object]:
    return _absence(box, "no_referrer", params, cap, config)


def unreferenced_objects(
    box: ComputeSandbox, params: Params, cap: int, config: Config
) -> dict[str, object]:
    language = params.get("language")
    if language and not int(str(box.scalar("language.files", params)[0])):
        # A language the index never recorded would make every object "unreferenced" from it.
        return {"rows": [], "total_count": 0, "truncated": False,
                "caveat": f"no indexed file is in language {language}",
                "empty_reason": "no_file_in_that_language"}
    return _absence(box, "unreferenced_objects", params, cap, config)


def _absence(
    box: ComputeSandbox, body: str, params: Params, cap: int, config: Config
) -> dict[str, object]:
    rows, truncated = box.query(body, params, cap=cap)
    language = params.get("language")
    # Inside a longer name counts (`tblOrders`): a strong candidate needs no trace at all (444).
    sites = gitutil.word_sites(
        config.root, sorted({str(r[1]) for r in rows}), timeout=GREP_DEADLINE_S, whole_word=False
    )
    if sites is not None and language:
        listed = _whole(box, "language.file_list", params)  # a cut list would hide a mention
        inside = {str(r[0]) for r in listed}
        sites = {name: [s for s in found if s[0] in inside] for name, found in sites.items()}
    shaped: list[dict[str, object]] = []
    levels = {NO_EDGE_NO_MENTION: 0, NO_EDGE_BUT_MENTIONED: 0, MENTION_UNCHECKED: 0}
    until = time.monotonic() + MENTION_BUDGET_S
    for qname, name, file, line in rows:
        symbol = (str(qname), str(name), str(file), int(str(line)))
        level = (
            _evidence(box, symbol, sites, language)
            if time.monotonic() < until
            else MENTION_UNCHECKED
        )
        levels[level] += 1
        row: dict[str, object] = {"qname": qname, "evidence": level}
        row["name"] = name
        row["file"] = file
        row["line"] = line
        shaped.append(row)
    if language:
        edges, unlinked = box.scalar("language.edges", params)
    else:
        edges, unlinked = box.scalar("no_referrer.caveat")
    population = box.scalar("no_referrer.population", params)
    data = {"unlinked_share": _share(unlinked, edges), "population": int(str(population[0]))}
    scope = f"edges from {language}" if language else "the graph's edges"
    return {
        "rows": shaped,
        "total_count": box.count(body, params),
        "truncated": truncated,
        "evidence_levels": levels,
        "mention_checks": len(rows),
        "caveat": (
            f"{data['unlinked_share']:.1%} of {scope} never linked to a definition: "
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
    language: str | None = None,
) -> str:
    """Whether a name no edge reaches is still named: an unlinked reference, another symbol's
    text, or anywhere in the tracked tree but its own definition line (a time-capped grep)."""
    qname, name, file, line = symbol
    try:
        raw = "mention.raw_in" if language else "mention.raw"
        if box.scalar(raw, {"name": name, "qname": qname, "language": language}):
            return NO_EDGE_BUT_MENTIONED
        if len(name) >= _MIN_TEXT_MATCH and not language:
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


def _whole(box: ComputeSandbox, body: str, params: Params) -> list[tuple[object, ...]]:
    """An aggregate read whole before paging; one too large is refused, never cut quietly."""
    rows, truncated = box.query(body, params, cap=INTERNAL_CAP)
    if truncated:
        raise ComputeRefused("over_internal_cap", f"{body} past {INTERNAL_CAP} rows")
    return rows


def _modules(config: Config) -> tuple[Mapping[str, str], bool]:
    """The one module table (PLAN §1) — directory to module — and whether it was capped."""
    with GraphStore(config.db_path) as store:
        return module_owners(store, config)


def _rollup(
    config: Config, per_file: Sequence[tuple[object, ...]]
) -> tuple[dict[str, list[int]], bool]:
    """Per-file counts summed per module; a file no module covers goes to `unassigned`."""
    owners, capped = _modules(config)
    sums: dict[str, list[int]] = {}
    for file, *counts in per_file:
        module = module_of_path(str(file), owners) or UNASSIGNED
        bucket = sums.setdefault(module, [0] * (len(counts) + 1))
        for index, value in enumerate(counts):
            bucket[index] += int(str(value))
        bucket[-1] += 1  # files
    return sums, capped


def _page(rows: list[dict[str, object]], cap: int) -> tuple[list[dict[str, object]], bool]:
    return rows[:cap], len(rows) > cap


def calls_by_module(
    box: ComputeSandbox, params: Params, cap: int, config: Config
) -> dict[str, object]:
    if not params.get("target") and not params.get("target_kind"):
        raise ValueError("calls_by_module needs target (a qname GLOB) or target_kind")
    bound = {**params, "edge_kind": params.get("edge_kind") or "CALLS"}
    sums, capped = _rollup(config, _whole(box, "calls_by_module", bound))
    rows: list[dict[str, object]] = []
    for module, (calls, resolved, files) in sorted(sums.items(), key=lambda kv: (-kv[1][0], kv[0])):
        row: dict[str, object] = {"module": module, "calls": calls}
        row["resolved"] = resolved
        row["files"] = files
        rows.append(row)
    unlinked = int(str(box.scalar("calls_by_module.unlinked", bound)[0]))
    page, truncated = _page(rows, cap)
    return {
        "rows": page,
        "total_count": len(rows),
        "truncated": truncated,
        "caveat": (
            f"{unlinked} {bound['edge_kind']} edges in scope never linked to a definition and may "
            "reach the target unseen; modules are the business-module table's"
            + (" (capped: some files sit in unassigned)" if capped else "")
        ),
        "caveat_data": {"unlinked": unlinked, "module_table_capped": capped},
        "empty_reason": "no_call_reaches_the_target",
    }


def untested_classes(
    box: ComputeSandbox, params: Params, cap: int, config: Config
) -> dict[str, object]:
    bound = {**params, "kind": params.get("kind") or "Class"}
    if not int(str(box.scalar("untested.tests")[0])):
        return {"rows": [], "total_count": 0, "truncated": False,
                "caveat": "no indexed symbol is a test: every type would read untested",
                "empty_reason": "no_test_symbol_indexed"}
    reached: set[str] = set()
    for (target,) in _whole(box, "untested.reached", bound):
        name = str(target)
        reached.add(name)
        # A test that calls `Foo::bar` reaches `Foo`: the member's container counts too.
        while contract.MEMBER_SEPARATOR in name:
            name = name.rpartition(contract.MEMBER_SEPARATOR)[0]
            reached.add(name)
    owners, capped = _modules(config)
    rows: list[dict[str, object]] = []
    per_module: dict[str, list[int]] = {}
    for qname, file, line in _whole(box, "untested.types", bound):
        module = module_of_path(str(file), owners) or UNASSIGNED
        counts = per_module.setdefault(module, [0, 0])
        counts[0] += 1
        if str(qname) in reached:
            continue
        counts[1] += 1
        row: dict[str, object] = {"qname": qname, "module": module}
        row["file"] = file
        row["line"] = line
        rows.append(row)
    rows.sort(key=lambda r: (str(r["module"]), str(r["file"]), int(str(r["line"]))))
    page, truncated = _page(rows, cap)
    return {
        "rows": page,
        "total_count": len(rows),
        "truncated": truncated,
        "by_module": {m: {"types": t, "untested": u} for m, (t, u) in sorted(per_module.items())},
        "caveat": (
            "a test file holds a symbol the adapter or the path convention marked; a type reached "
            "only through a helper or a fixture reads untested"
        ),
        "caveat_data": {"module_table_capped": capped},
        "empty_reason": (
            "every_type_is_reached_from_a_test" if per_module else "no_type_of_that_kind"
        ),
    }


def resolved_share(
    box: ComputeSandbox, params: Params, cap: int, config: Config
) -> dict[str, object]:
    sums, capped = _rollup(config, _whole(box, "resolved_share", params))
    rows: list[dict[str, object]] = []
    for module, (calls, resolved, unlinked, files) in sorted(
        sums.items(), key=lambda kv: (-kv[1][0], kv[0])
    ):
        row: dict[str, object] = {"module": module, "calls": calls}
        row["resolved"] = resolved
        row["unlinked"] = unlinked
        row["share"] = _share(resolved, calls)
        row["files"] = files
        rows.append(row)
    calls_all = sum(v[0] for v in sums.values())
    page, truncated = _page(rows, cap)
    return {
        "rows": page,
        "total_count": len(rows),
        "truncated": truncated,
        "caveat": (
            f"{_share(sum(v[1] for v in sums.values()), calls_all):.1%} of {calls_all} CALLS "
            "resolved; a HEURISTIC or DYNAMIC call is linked but not resolved"
        ),
        "caveat_data": {"calls": calls_all, "module_table_capped": capped},
        "empty_reason": "no_call_indexed",
    }


def includes_by_dir(
    box: ComputeSandbox, params: Params, cap: int, config: Config
) -> dict[str, object]:
    body = "includes_by_dir"
    found, truncated = box.query(body, params, cap=cap)
    rows: list[dict[str, object]] = []
    for directory, total, resolved, dynamic, unlinked in found:
        row: dict[str, object] = {"dir": directory, "includes": total}
        row["resolved"] = resolved
        row["dynamic"] = dynamic
        row["unlinked"] = unlinked
        rows.append(row)
    dynamic_all = sum(int(str(r["dynamic"])) for r in rows)
    return {
        "rows": rows,
        "total_count": box.count(body, params),
        "truncated": truncated,
        "caveat": (
            f"{dynamic_all} include(s) on this page take a path built at run time (DYNAMIC); "
            "the file they load is a guess or unknown"
        ),
        "caveat_data": {"dynamic_on_page": dynamic_all},
        "empty_reason": "no_include_edge",
    }


def _precedence(box: ComputeSandbox) -> tuple[str, ...]:
    """The declared order (437, then 414) as the build stamped it in meta."""
    globs: list[str] = []
    for key in (DEFINITION_ORDER_META_KEY, DEFINITION_PRECEDENCE_META_KEY):
        found = box.scalar("meta.value", {"key": key})
        globs.extend(json.loads(str(found[0])) if found and found[0] else ())
    return tuple(dict.fromkeys(globs))


def multi_defined(
    box: ComputeSandbox, params: Params, cap: int, config: Config
) -> dict[str, object]:
    body = "multi_defined"
    # Namespaces span files: each file declaring one is no second definition (contract, 416).
    params = {**params, "spanning": contract.SPANNING_KINDS[0]}
    found, truncated = box.query(body, params, cap=cap)
    order = _precedence(box)
    rows: list[dict[str, object]] = []
    named = 0
    for qname, kind, count in found:
        sites, cut = box.query(
            "multi_defined.sites", {"qname": qname, "site_kind": kind}, cap=SITES_CAP
        )
        defs: list[dict[str, object]] = []
        for q, f, n, t in sites:
            # One key per statement: the contract's field words stay out of a collection literal.
            site: dict[str, object] = {"qualified_name": q}
            site["file_path"] = f
            site["line_start"] = n
            site["is_test"] = t
            defs.append(site)
        live = [s for s in definition_states(defs, order, complete=not cut)
                if s["state"] == DEFINITION_LIVE]
        row: dict[str, object] = {"qname": qname, "kind": kind, "definitions": count}
        if live:
            named += 1
            row["live"] = {"file": live[0]["file"], "line": live[0]["line"]}
            row["live_state"] = "live"
        else:
            # Never a guess (R5.6): no declared order, or one that does not decide.
            row["live"] = None
            row["live_state"] = "unknown"
            row["why_unknown"] = "order_does_not_decide" if order else "no_order_declared"
        rows.append(row)
    return {
        "rows": rows,
        "total_count": box.count(body, params),
        "truncated": truncated,
        "caveat": (
            (f"a definition_order of {len(order)} glob(s) named the live one for {named} of "
             f"{len(rows)} on this page" if order else
             "no definition_order is declared: no live definition is named")
            + "; one object is one kind and qname; namespaces, test copies and definitions "
            "outside path_prefix are not counted"
        ),
        "caveat_data": {"declared_globs": len(order), "live_named": named},
        "empty_reason": "no_qname_defined_twice",
    }


def variant_pairs(
    box: ComputeSandbox, params: Params, cap: int, config: Config
) -> dict[str, object]:
    left, right = params.get("left"), params.get("right")
    if bool(left) != bool(right):
        raise ValueError("variant_pairs takes left and right together")
    pairs = [(str(left), str(right))] if left and right else list(config.variant_pairs or ())
    if not pairs:
        raise ValueError("variant_pairs needs left and right, or variant_pairs in .code-atlas.toml")
    rows: list[dict[str, object]] = []
    total = 0
    truncated = False
    for lhs, rhs in pairs:
        lp, _, ls = lhs.partition("*")
        rp, _, rs = rhs.partition("*")
        bound = {**params, "lp": lp, "ls": ls, "rp": rp, "rs": rs}
        found, cut = box.query("variant_pairs", bound, cap=max(cap - len(rows), 1))
        total += box.count("variant_pairs", bound)
        for a_q, a_f, a_l, b_q, b_f, b_l, a_used, _b_used in found:
            if len(rows) >= cap:
                truncated = True
                break
            used, unused = ((a_q, (b_q, b_f, b_l)) if a_used else (b_q, (a_q, a_f, a_l)))
            row: dict[str, object] = {"pair": f"{lhs} / {rhs}", "used": used}
            row["unused"] = unused[0]
            row["unused_file"] = unused[1]
            row["unused_line"] = unused[2]
            rows.append(row)
        truncated = truncated or cut
    return {
        "rows": rows,
        "total_count": total,
        "truncated": truncated or total > len(rows),
        "caveat": (
            "pairs share a container and a stem; used means an edge reaches it, so a variant "
            "called only by name at run time reads unused"
        ),
        "caveat_data": {"pairs_checked": len(pairs)},
        "empty_reason": "no_one_sided_pair",
    }


_Runner = Callable[[ComputeSandbox, Params, int, Config], dict[str, object]]
_RUNNERS: Mapping[str, _Runner]
_RUNNERS = {
    "tier_mix": tier_mix,
    "no_referrer": no_referrer,
    "unreferenced_objects": unreferenced_objects,
    "calls_by_module": calls_by_module,
    "untested_classes": untested_classes,
    "resolved_share": resolved_share,
    "includes_by_dir": includes_by_dir,
    "multi_defined": multi_defined,
    "variant_pairs": variant_pairs,
}


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def compute(
        template: TemplateId | None = None,
        params: dict[str, str] | None = None,
        limit: int | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """Exact counts, groupings and absences over the whole graph from a named template.
        No `template` lists the catalogue. Read `caveat`, `total_count`, `truncated`, `reason`.
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
                answer.update(_RUNNERS[chosen.id](box, bound, cap, config))
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
