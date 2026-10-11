"""A route table as data: a URL a tester reports becomes a subject (task 385).

A front controller maps a key it reads from the request to a handler at run time, so the graph
holds no edge for it. A ``routes`` block in a ``CA_INDIRECTION_RULES`` file declares the mapping —
inline, or a TSV the consuming repo already keeps — and the build resolves each target and stores
the table in the index's meta, so a tool reads the table of the revision it answers about (R4.2).

A route is a declared lookup in front of an existing subject, never a node or an edge: it adds no
vocabulary, so the contract does not move. Every answer it shapes says ``tier: HEURISTIC``,
``rule: true`` — declared, not resolved (R5.2).
"""

from __future__ import annotations

import csv
import difflib
import fnmatch
import io
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

from code_atlas import contract
from code_atlas.config import ConfigError
from code_atlas.containment import resolves_inside

ROUTES_META_KEY = "routes"
ROUTE_TIER = contract.CONFIDENCE_TIERS[1]  # HEURISTIC
NEAREST = 5
_WILDCARD = "*"


@dataclass(frozen=True)
class RouteBlock:
    """One ``routes`` block: which query keys decide a route, and its ``(key, target)`` rows."""

    significant: tuple[str, ...] | None
    entries: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Route:
    """A declared route whose target the index holds."""

    key: str  # canonical
    declared: str  # as written in the table
    target: str
    file: str
    significant: tuple[str, ...] | None

    def as_row(self) -> dict[str, object]:
        """The route as an answer carries it: declared, so HEURISTIC and rule-derived."""
        return {
            "route": self.declared,
            "target": self.target,
            "file": self.file,
            "tier": ROUTE_TIER,
            contract.RULE_FLAG: True,
        }


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
        entries = [_entry(row, label) for row in _list(item.get("table"), label)]
        if item.get("tsv") is not None:
            entries.extend(_tsv(item, label, root, digest))
        blocks.append(
            RouteBlock(tuple(significant) if significant is not None else None, tuple(entries))
        )
    return blocks


def _list(raw: object, label: str) -> list[object]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConfigError(f"indirection_rules: {label!r} routes.table must be a list")
    return raw


def _entry(row: object, label: str) -> tuple[str, str]:
    if not isinstance(row, dict):
        raise ConfigError(f"indirection_rules: {label!r} routes.table rows must be objects")
    key, target = row.get("key"), row.get("target")
    if not isinstance(key, str) or not key.strip() or not isinstance(target, str) or not target:
        raise ConfigError(
            f"indirection_rules: {label!r} routes.table rows need a string key and target"
        )
    return key.strip(), target.strip()


def _tsv(
    item: dict[str, object], label: str, root: Path, digest: Callable[[bytes], None]
) -> list[tuple[str, str]]:
    """A measured route census, used as is through a ``columns`` map naming its two columns."""
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
    return [
        (str(row[str(key_column)]).strip(), str(row[str(target_column)]).strip())
        for row in reader
        if row.get(str(key_column)) and row.get(str(target_column))
    ]


def resolve(
    blocks: Iterable[RouteBlock], locate: Callable[[str], str | None]
) -> tuple[list[Route], int]:
    """Routes whose target ``locate`` finds (its file), first declaration of a key winning; and
    the count of rows naming no indexed symbol — counted, never linked (AC3)."""
    routes: list[Route] = []
    seen: set[str] = set()
    unresolved = 0
    for block in blocks:
        for declared, target in block.entries:
            key = canonical(declared, block.significant)
            if key in seen:
                continue
            file = locate(target)
            if file is None:
                unresolved += 1
                continue
            seen.add(key)
            routes.append(Route(key, declared, target, file, block.significant))
    return routes, unresolved


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
        )
        for row in rows
    ]


def match(routes: Sequence[Route], url: str) -> Route | None:
    """The route a URL reaches: an exact canonical key first, then a ``*`` value pattern."""
    for route in routes:
        if canonical(url, route.significant) == route.key and _WILDCARD not in route.key:
            return route
    for route in routes:
        if _WILDCARD in route.key and fnmatch.fnmatchcase(
            canonical(url, route.significant), route.key
        ):
            return route
    return None


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
