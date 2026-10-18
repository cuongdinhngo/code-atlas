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
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

from code_atlas import contract
from code_atlas.config import ConfigError
from code_atlas.containment import resolves_inside

ROUTES_META_KEY = "routes"
# JSON-source rows whose short-class target named several classes and no `prefer` chose one (397).
ROUTES_AMBIGUOUS_META_KEY = "routes_ambiguous"
ROUTE_TIER = contract.CONFIDENCE_TIERS[1]  # HEURISTIC
NEAREST = 5
_WILDCARD = "*"


@dataclass(frozen=True)
class RouteBlock:
    """One ``routes`` block: which query keys decide a route, and its ``(key, target)`` rows."""

    significant: tuple[str, ...] | None
    entries: tuple[tuple[str, str], ...]
    # A JSON census names a handler by short class; `prefer` breaks a tie by qname segment (397).
    short_names: bool = False
    prefer: tuple[str, ...] = ()


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
        prefer = item.get("prefer", [])
        if not isinstance(prefer, list) or not all(isinstance(seg, str) and seg for seg in prefer):
            raise ConfigError(f"indirection_rules: {label!r} routes.prefer must be a list of names")
        if prefer and item.get("json") is None:
            raise ConfigError(f"indirection_rules: {label!r} routes.prefer needs a json source")
        keys = tuple(significant) if significant is not None else None
        blocks.append(RouteBlock(keys, tuple(entries)))
        if item.get("json") is not None:
            # Its own block, after the inline and TSV rows: only census rows name a short class.
            rows = tuple(_json(item, label, root, digest))
            blocks.append(RouteBlock(keys, rows, short_names=True, prefer=tuple(prefer)))
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


def _json(
    item: dict[str, object], label: str, root: Path, digest: Callable[[bytes], None]
) -> list[tuple[str, str]]:
    """A JSON route census: ``rows`` is a dotted path to its list of objects, ``columns`` names
    the key and target fields (dotted for a nested one). A row missing either is skipped (397)."""
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
    found: list[tuple[str, str]] = []
    for row in rows:
        key, target = _dig(row, str(columns.get("key"))), _dig(row, str(columns.get("target")))
        if isinstance(key, str) and key.strip() and isinstance(target, str) and target.strip():
            found.append((key.strip(), target.strip()))
    return found


def _dig(value: object, path: str) -> object:
    """``value`` at a dotted object path; ``""`` is the value itself, a miss is ``None``."""
    for part in path.split(".") if path else ():
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def resolve(
    blocks: Iterable[RouteBlock],
    locate: Callable[[str], str | None],
    candidates: Callable[[str], list[tuple[str, str]]] | None = None,
    ambiguous: list[dict[str, object]] | None = None,
) -> tuple[list[Route], int]:
    """Routes whose target ``locate`` finds (its file), first declaration of a key winning; and
    the count of rows naming no indexed symbol — counted, never linked (AC3).

    A short-names block whose target ``locate`` misses asks ``candidates`` for the ``(qname, file)``
    pairs it may name; one, or one its ``prefer`` picks, links, and a tie lands in ``ambiguous``.
    """
    routes: list[Route] = []
    seen: set[str] = set()
    unresolved = 0
    tied: dict[str, dict[str, object]] = {}
    for block in blocks:
        for declared, target in block.entries:
            key = canonical(declared, block.significant)
            if key in seen:
                continue
            file = locate(target)
            linked = target
            if file is None and block.short_names and candidates is not None:
                found = candidates(target)
                picked = _prefer(found, block.prefer)
                if picked is not None:
                    linked, file = picked
                elif len(found) > 1:
                    names = [qname for qname, _ in found]
                    tied.setdefault(key, {"route": declared, "target": target, "candidates": names})
            if file is None:
                unresolved += 1
                continue
            seen.add(key)
            routes.append(Route(key, declared, linked, file, block.significant))
    if ambiguous is not None:
        # A later row of the same key may have linked it; only a key left unrouted is named.
        ambiguous.extend(row for key, row in tied.items() if key not in seen)
    return routes, unresolved


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
        )
        for row in rows
    ]


def match(routes: Sequence[Route], url: str) -> Route | None:
    """The route a URL reaches: an exact canonical key first, then a ``*`` value pattern."""
    for route in routes:
        if canonical(url, route.significant) == route.key and _WILDCARD not in route.key:
            return route
    for route in routes:
        if _WILDCARD in route.key and _glob(route.key).fullmatch(canonical(url, route.significant)):
            return route
    return None


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
