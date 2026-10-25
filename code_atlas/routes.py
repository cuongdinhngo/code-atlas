"""A route table as data: a URL a tester reports becomes a subject (task 385).

A front controller maps a key it reads from the request to a handler at run time, so the graph
holds no edge for it. A ``routes`` block in a ``CA_INDIRECTION_RULES`` file declares the mapping —
inline, or a TSV or JSON census the consuming repo already keeps (397) — and the build resolves
each target and stores the table in the index's meta, so a tool reads the table of the revision it
answers about (R4.2).

A route is a declared lookup in front of an existing subject, never a node or an edge: it adds no
vocabulary, so the contract does not move. Every answer it shapes says ``tier: HEURISTIC``,
``rule: true`` — declared, not resolved (R5.2).
"""

from __future__ import annotations

import csv
import difflib
import io
import json
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import NamedTuple
from urllib.parse import parse_qsl, urlencode, urlsplit

from code_atlas import contract
from code_atlas.config import ConfigError
from code_atlas.containment import resolves_inside

ROUTES_META_KEY = "routes"
# JSON-source rows whose short-class target named several classes and no `prefer` chose one (397).
ROUTES_AMBIGUOUS_META_KEY = "routes_ambiguous"
# Where every declared row went — stored, or dropped by reason — and the keys that collide (411).
ROUTES_CENSUS_META_KEY = "routes_census"
# A URL whose key several declared rows name with different targets answers every one (411).
ROUTE_COLLISION = "route_collision"
CANDIDATES_FIELD = "route_candidates"
EXAMPLES_CAP = 20
_LABELS = ("when", "source")
UNRESOLVED, SHORT_NAME_TIE, DUPLICATE, INCOMPLETE = (
    "unresolved", "short_name_tie", "duplicate", "incomplete"
)
ROUTE_TIER = contract.CONFIDENCE_TIERS[1]  # HEURISTIC
NEAREST = 5
_WILDCARD = "*"


class Handler(NamedTuple):
    """One declared row: a key, its target, and — for a conditional route — the condition it is
    served under and the dispatching code, both labels nothing evaluates (415)."""

    key: str
    target: str
    when: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class RouteBlock:
    """One ``routes`` block: which query keys decide a route, and its ``(key, target)`` rows."""

    significant: tuple[str, ...] | None
    entries: tuple[Handler | tuple[str, str], ...]
    # A JSON census names a handler by short class; `prefer` breaks a tie by qname segment (397).
    short_names: bool = False
    prefer: tuple[str, ...] = ()
    # A path's own significant keys, overriding the block's for that path (411).
    by_path: tuple[tuple[str, tuple[str, ...]], ...] = ()
    # Census rows read but missing their key or their target, as ``(key, target)`` (411).
    incomplete: tuple[tuple[str, str], ...] = ()

    def significant_for(self, declared: str) -> tuple[str, ...] | None:
        """The keys deciding this row's route: its path's own, else the block's."""
        path = urlsplit(declared.strip()).path.lstrip("/")
        return dict(self.by_path).get(path, self.significant)


@dataclass(frozen=True)
class Route:
    """A declared route whose target the index holds."""

    key: str  # canonical
    declared: str  # as written in the table
    target: str
    file: str
    significant: tuple[str, ...] | None
    when: str | None = None  # a conditional route's label (415)
    source: str | None = None

    def as_row(self) -> dict[str, object]:
        """The route as an answer carries it: declared, so HEURISTIC and rule-derived."""
        row: dict[str, object] = {"route": self.declared, "target": self.target}
        if self.when is not None:
            row["when"] = self.when
        if self.source is not None:
            row["source"] = self.source
        return row | {"file": self.file, "tier": ROUTE_TIER, contract.RULE_FLAG: True}


def canonical(key: str, significant: Sequence[str] | None) -> str:
    """``path?k=v…`` with only the significant query keys, sorted — order and noise ignored."""
    parts = urlsplit(key.strip())
    path = parts.path.lstrip("/")
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    if significant is not None:
        pairs = [(name, value) for name, value in pairs if name in significant]
    query = urlencode(sorted(pairs), safe=_WILDCARD)
    return f"{path}?{query}" if query else path


def read_blocks(
    raw: object, label: str, root: Path, digest: Callable[[bytes], None]
) -> list[RouteBlock]:
    """Validate a rule file's ``routes`` value; a TSV it names is read here and digested."""
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    blocks: list[RouteBlock] = []
    for item in items:
        if not isinstance(item, dict):
            raise ConfigError(f"indirection_rules: {label!r} routes entries must be objects")
        significant = item.get("significant")
        if significant is not None and (
            not isinstance(significant, list)
            or not all(isinstance(name, str) and name for name in significant)
        ):
            raise ConfigError(
                f"indirection_rules: {label!r} routes.significant must be a list of names"
            )
        by_path = _by_path(item.get("significant_by_path"), label)
        entries = [_entry(row, label) for row in _list(item.get("table"), label)]
        incomplete: list[tuple[str, str]] = []
        if item.get("tsv") is not None:
            rows, incomplete = _tsv(item, label, root, digest)
            entries.extend(rows)
        prefer = item.get("prefer", [])
        if not isinstance(prefer, list) or not all(isinstance(seg, str) and seg for seg in prefer):
            raise ConfigError(f"indirection_rules: {label!r} routes.prefer must be a list of names")
        if prefer and item.get("json") is None:
            raise ConfigError(f"indirection_rules: {label!r} routes.prefer needs a json source")
        keys = tuple(significant) if significant is not None else None
        blocks.append(
            RouteBlock(keys, tuple(entries), by_path=by_path, incomplete=tuple(incomplete))
        )
        if item.get("json") is not None:
            # Its own block, after the inline and TSV rows: only census rows name a short class.
            found, skipped = _json(item, label, root, digest)
            blocks.append(
                RouteBlock(
                    keys, tuple(found), short_names=True, prefer=tuple(prefer),
                    by_path=by_path, incomplete=tuple(skipped),
                )
            )
    return blocks


def _by_path(raw: object, label: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """``{path: [key, …]}``: a census path whose own query keys decide its routes (411)."""
    if raw is None:
        return ()
    if not isinstance(raw, dict) or not all(
        isinstance(path, str) and path.strip() and isinstance(names, list)
        and all(isinstance(name, str) and name for name in names)
        for path, names in raw.items()
    ):
        raise ConfigError(
            f"indirection_rules: {label!r} routes.significant_by_path must map paths to lists "
            "of names"
        )
    return tuple(
        (urlsplit(path.strip()).path.lstrip("/"), tuple(names)) for path, names in raw.items()
    )


def _list(raw: object, label: str) -> list[object]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConfigError(f"indirection_rules: {label!r} routes.table must be a list")
    return raw


def _entry(row: object, label: str) -> Handler:
    if not isinstance(row, dict):
        raise ConfigError(f"indirection_rules: {label!r} routes.table rows must be objects")
    key, target = row.get("key"), row.get("target")
    if not isinstance(key, str) or not key.strip() or not isinstance(target, str) or not target:
        raise ConfigError(
            f"indirection_rules: {label!r} routes.table rows need a string key and target"
        )
    labels = [row.get("when"), row.get("source")]
    if not all(value is None or isinstance(value, str) for value in labels):
        raise ConfigError(
            f"indirection_rules: {label!r} routes.table when and source must be strings"
        )
    return Handler(key.strip(), target.strip(), *(_label(value) for value in labels))


def _label(value: object) -> str | None:
    """A ``when``/``source`` cell as stored: a blank one is no label (415)."""
    return value.strip() or None if isinstance(value, str) else None


def _tsv(
    item: dict[str, object], label: str, root: Path, digest: Callable[[bytes], None]
) -> tuple[list[Handler], list[tuple[str, str]]]:
    """A measured route census, used as is through a ``columns`` map naming its key and target
    columns, and optionally ``when`` and ``source`` (415); and its rows missing either (411)."""
    relative, columns = item.get("tsv"), item.get("columns") or {"key": "key", "target": "target"}
    if not isinstance(relative, str) or not isinstance(columns, dict):
        raise ConfigError(f"indirection_rules: {label!r} routes.tsv needs a path and columns")
    key_column, target_column = columns.get("key"), columns.get("target")
    full = root / relative
    if not full.is_file() or not resolves_inside(root, full):
        raise ConfigError(
            f"indirection_rules: {label!r} routes.tsv {relative!r} is not a file under {root}"
        )
    data = full.read_bytes()
    digest(data)
    try:
        # utf-8-sig: a spreadsheet export's byte-order mark is not part of the first column's name.
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ConfigError(
            f"indirection_rules: {label!r} routes.tsv {relative!r} is not UTF-8 ({error})"
        ) from None
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    header = reader.fieldnames or []
    if key_column not in header or target_column not in header:
        raise ConfigError(
            f"indirection_rules: {label!r} routes.tsv {relative!r} has no column "
            f"{key_column!r} or {target_column!r}"
        )
    for name in _LABELS:  # a misspelt label column would turn every conditional into a collision
        if columns.get(name) is not None and columns.get(name) not in header:
            raise ConfigError(
                f"indirection_rules: {label!r} routes.tsv {relative!r} has no {name} column "
                f"{columns.get(name)!r}"
            )
    found: list[Handler] = []
    skipped: list[tuple[str, str]] = []
    for row in reader:
        key = str(row.get(str(key_column)) or "").strip()
        target = str(row.get(str(target_column)) or "").strip()
        if key and target:
            when, source = (_label(row.get(str(columns.get(name)))) for name in _LABELS)
            found.append(Handler(key, target, when, source))
        else:
            skipped.append((key, target))
    return found, skipped


def _json(
    item: dict[str, object], label: str, root: Path, digest: Callable[[bytes], None]
) -> tuple[list[Handler], list[tuple[str, str]]]:
    """A JSON route census: ``rows`` is a dotted path to its list of objects, ``columns`` names
    the key and target fields (dotted for a nested one), and optionally ``when``/``source``. A
    row missing a key or a target is skipped (397), and counted (411)."""
    relative, columns = item.get("json"), item.get("columns") or {"key": "key", "target": "target"}
    selector = item.get("rows", "")
    if not (isinstance(relative, str) and isinstance(columns, dict) and isinstance(selector, str)):
        raise ConfigError(f"indirection_rules: {label!r} routes.json needs a path and columns")
    if not all(isinstance(columns.get(name), str) for name in ("key", "target")):
        raise ConfigError(f"indirection_rules: {label!r} routes.json columns need key and target")
    full = root / relative
    if not full.is_file() or not resolves_inside(root, full):
        raise ConfigError(
            f"indirection_rules: {label!r} routes.json {relative!r} is not a file under {root}"
        )
    data = full.read_bytes()
    digest(data)
    try:
        document: object = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConfigError(
            f"indirection_rules: {label!r} routes.json {relative!r} is not UTF-8 JSON ({error})"
        ) from None
    rows = _dig(document, selector)
    if not isinstance(rows, list):
        raise ConfigError(
            f"indirection_rules: {label!r} routes.json {relative!r} has no list at {selector!r}"
        )
    found: list[Handler] = []
    skipped: list[tuple[str, str]] = []
    for row in rows:
        key, target = _dig(row, str(columns.get("key"))), _dig(row, str(columns.get("target")))
        pair = (key.strip() if isinstance(key, str) else "",
                target.strip() if isinstance(target, str) else "")
        if all(pair):
            when, source = (
                _label(_dig(row, str(columns[name]))) if columns.get(name) else None
                for name in _LABELS
            )
            found.append(Handler(*pair, when, source))
        else:
            skipped.append(pair)
    return found, skipped


def _dig(value: object, path: str) -> object:
    """``value`` at a dotted object path; ``""`` is the value itself, a miss is ``None``."""
    for part in path.split(".") if path else ():
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


@dataclass
class Census:
    """Where every declared row went: stored, or dropped for one reason, with examples (411)."""

    declared: int = 0
    stored: int = 0
    dropped: dict[str, int] = field(default_factory=dict)
    examples: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def drop(self, reason: str, declared: str | None = None, target: str | None = None) -> None:
        self.dropped[reason] = self.dropped.get(reason, 0) + 1
        if declared is not None and target is not None:
            shown = self.examples.setdefault(reason, [])
            if len(shown) < EXAMPLES_CAP:
                shown.append({"route": declared, "target": target})

    def as_status(self, routes: Sequence[Route]) -> dict[str, object]:
        """``declared == stored + sum(dropped)``; a key several targets share is a collision."""
        collided = colliding(routes)
        status: dict[str, object] = {
            "declared": self.declared,
            "stored": self.stored,
            "dropped": dict(sorted(self.dropped.items())),
            "collisions": len(collided),
            "conditional": sum(conditional(rows) for rows in _shared(routes).values()),
        }
        if self.examples:
            status["dropped_examples"] = dict(sorted(self.examples.items()))
        if collided:
            status["collision_examples"] = [
                {"key": key, "routes": [_brief(route) for route in rows]}
                for key, rows in list(collided.items())[:EXAMPLES_CAP]
            ]
        return status


def resolve(
    blocks: Iterable[RouteBlock],
    locate: Callable[[str], str | None],
    candidates: Callable[[str], list[tuple[str, str]]] | None = None,
    ambiguous: list[dict[str, object]] | None = None,
    census: Census | None = None,
) -> tuple[list[Route], int]:
    """Routes whose target ``locate`` finds (its file), and the count of rows naming no indexed
    symbol — counted, never linked (AC3). Rows of one key with different targets are all kept —
    a conditional route when each carries its own ``when`` (415), else a collision; one repeating
    a key's target and ``when`` is a duplicate, dropped. ``census`` tallies each (411).

    A short-names block whose target ``locate`` misses asks ``candidates`` for the ``(qname, file)``
    pairs it may name; one, or one its ``prefer`` picks, links, and a tie lands in ``ambiguous``.
    """
    routes: list[Route] = []
    targets: dict[str, set[tuple[str, str | None]]] = {}
    unresolved = 0
    tied: dict[str, dict[str, object]] = {}
    tally = census if census is not None else Census()
    for block in blocks:
        tally.declared += len(block.entries) + len(block.incomplete)
        for declared, target in block.incomplete:
            tally.drop(INCOMPLETE, declared, target)
        for entry in block.entries:
            declared, target, when, source = Handler(*entry)
            significant = block.significant_for(declared)
            key = canonical(declared, significant)
            file = locate(target)
            linked = target
            tie = False
            if file is None and block.short_names and candidates is not None:
                found = candidates(target)
                picked = _prefer(found, block.prefer)
                if picked is not None:
                    linked, file = picked
                elif len(found) > 1:
                    tie = True
                    names = [qname for qname, _ in found]
                    tied.setdefault(key, {"route": declared, "target": target, "candidates": names})
            if file is None:
                unresolved += 1
                tally.drop(SHORT_NAME_TIE if tie else UNRESOLVED, declared, target)
                continue
            if (linked, when) in targets.get(key, ()):
                tally.drop(DUPLICATE, declared, linked)
                continue
            targets.setdefault(key, set()).add((linked, when))
            tally.stored += 1
            routes.append(Route(key, declared, linked, file, significant, when, source))
    if ambiguous is not None:
        # A later row of the same key may have linked it; only a key left unrouted is named.
        ambiguous.extend(row for key, row in tied.items() if key not in targets)
    return routes, unresolved


def colliding(routes: Sequence[Route]) -> dict[str, list[Route]]:
    """Keys that several stored routes share with no condition telling them apart, each with its
    routes in table order (411); a conditional route is not one (415)."""
    return {key: rows for key, rows in _shared(routes).items() if not conditional(rows)}


def conditional(rows: Sequence[Route]) -> bool:
    """Several handlers of one key, each under its own ``when`` label (415)."""
    labels = [route.when for route in rows]
    return len(rows) > 1 and None not in labels and len(set(labels)) == len(labels)


def _shared(routes: Sequence[Route]) -> dict[str, list[Route]]:
    by_key: dict[str, list[Route]] = {}
    for route in routes:
        by_key.setdefault(route.key, []).append(route)
    return {key: rows for key, rows in by_key.items() if len(rows) > 1}


def _brief(route: Route) -> dict[str, str]:
    brief = {"route": route.declared, "target": route.target}
    return brief | ({"when": route.when} if route.when is not None else {})


def collision_fields(candidates: Sequence[Route]) -> dict[str, object]:
    """What an answer adds when its URL reached several handlers: none of them alone (411)."""
    if len(candidates) < 2 or conditional(candidates):
        return {}
    return {
        "ambiguity": ROUTE_COLLISION,
        CANDIDATES_FIELD: [route.as_row() for route in candidates],
    }


def short_target(target: str) -> tuple[str, str] | None:
    """``Class::method()`` / ``Class::method`` as ``(class, method)``, or ``None`` (397)."""
    head, separator, member = target.removesuffix("()").rpartition(contract.MEMBER_SEPARATOR)
    if not separator or not head or not member:
        return None
    return head, member


def _prefer(
    found: list[tuple[str, str]], prefer: Sequence[str]
) -> tuple[str, str] | None:
    """The one candidate left once each ``prefer`` segment that matches any narrows the set."""
    pool = found
    for segment in prefer:
        if len(pool) == 1:
            break
        narrowed = [pair for pair in pool if segment in re.split(r"[^\w$]+", pair[0])]
        pool = narrowed or pool
    return pool[0] if len(pool) == 1 else None


def dump(routes: Sequence[Route]) -> str:
    return json.dumps([asdict(route) for route in routes], separators=(",", ":"), sort_keys=True)


def load(raw: str | None) -> list[Route] | None:
    """The stored table; ``None`` when no routes rule was configured at build."""
    if raw is None:
        return None
    rows = json.loads(raw)
    return [
        Route(
            row["key"],
            row["declared"],
            row["target"],
            row["file"],
            tuple(row["significant"]) if row["significant"] is not None else None,
            row.get("when"),
            row.get("source"),
        )
        for row in rows
    ]


def matches(routes: Sequence[Route], url: str) -> list[Route]:
    """The routes a URL reaches: an exact canonical key first, then a ``*`` value pattern — every
    route of that one key, so a collision answers all of its targets (411)."""
    exact = [
        route for route in routes
        if _WILDCARD not in route.key and canonical(url, route.significant) == route.key
    ]
    if exact:
        return [route for route in exact if route.key == exact[0].key]
    pattern = [
        route for route in routes
        if _WILDCARD in route.key and _glob(route.key).fullmatch(canonical(url, route.significant))
    ]
    return [route for route in pattern if route.key == pattern[0].key] if pattern else []


def _glob(key: str) -> re.Pattern[str]:
    # Only ``*`` is a wildcard: a key's ``?`` separator and any ``[`` are literal, unlike fnmatch.
    return re.compile(".*".join(re.escape(part) for part in key.split(_WILDCARD)), re.DOTALL)


def nearest(routes: Sequence[Route], url: str) -> list[str]:
    """The declared keys closest to an unmatched URL — never an empty miss (Scope 3)."""
    declared = sorted({route.declared for route in routes})
    return difflib.get_close_matches(url.strip(), declared, n=NEAREST, cutoff=0.0)


def containing(routes: Sequence[Route], text: str, *, limit: int) -> list[Route]:
    """Routes whose declared key holds ``text``, case-insensitively, in table order."""
    needle = text.strip().casefold()
    if not needle:
        return []
    return [route for route in routes if needle in route.declared.casefold()][:limit]


def reaching(
    routes: Sequence[Route], qnames: Iterable[str], paths: Iterable[str], files: Iterable[str]
) -> list[Route]:
    """Routes into this radius: a symbol target among ``qnames`` or in a named ``paths`` file,
    or a file target among ``files`` — never a symbol merely sharing a reached file."""
    wanted_q, wanted_p, wanted_f = set(qnames), set(paths), set(files) | set(paths)
    return [
        route
        for route in routes
        if route.target in wanted_q
        or route.file in wanted_p
        or (route.target == route.file and route.file in wanted_f)
    ]
