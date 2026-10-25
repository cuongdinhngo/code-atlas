"""Records written about code, attached to the symbols they name (task 407).

A consumer keeps records about its code — a QA ticket, an incident, an ADR — each naming the
symbols it is about. A ``records`` block in a ``CA_INDIRECTION_RULES`` file declares where they
live (globs of JSON or JSON Lines files) and how to read them (a dotted field map), and the
build resolves each target and stores the attached records in the index's meta, so a tool
answers at the revision the index describes (R4.2) — 385's route-table shape.

A record is a declared lookup beside the graph, never a node or an edge, so the contract does not
move. Every row it shapes says ``tier: HEURISTIC``, ``rule: true`` — declared, not resolved (R5.2).
An id named in the block's ``exclude`` file is dropped before anything else reads the record, so
no answer, count list or message can name it; only how many were dropped is kept.
"""

from __future__ import annotations

import fnmatch
import json
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from code_atlas import contract
from code_atlas.config import ConfigError
from code_atlas.containment import resolves_inside

RECORDS_META_KEY = "records"
# The counts block the build result and `get_index_status` report: never an excluded id.
RECORDS_STATUS_META_KEY = "records_status"
# Globs of hub files whose records reach no answer seeded elsewhere (412).
RECORDS_STOP_AT_META_KEY = "records_stop_at"
# The attribute paths the blocks declare: the names a `records_filter` may test (413).
RECORDS_ATTRIBUTES_META_KEY = "records_attributes"
RECORD_TIER = contract.CONFIDENCE_TIERS[1]  # HEURISTIC
DANGLING_FIRST = 10
TITLE_MAX = 200
ATTRIBUTE_LIST_MAX = 20  # a longer list attribute is dropped, never stored (413)
_DEFAULT_FIELDS = {"id": "id", "title": "title", "url": "url", "kind": "kind"}
_LINE_SUFFIXES = frozenset({".jsonl", ".ndjson"})


@dataclass(frozen=True)
class Record:
    """One record as declared, or as stored with only the targets the index holds."""

    id: str
    title: str
    url: str | None
    kind: str | None
    targets: tuple[str, ...]
    # Declared attribute paths and their values, as read (413); empty when none is declared.
    attributes: tuple[tuple[str, object], ...] = ()

    def as_row(
        self, via: str | None = None, distance: int | None = None
    ) -> dict[str, object]:
        """The record as an answer carries it: declared, so HEURISTIC and rule-derived. A
        ``distance`` (hops from the seed) marks the row ``direct`` at 0 (412)."""
        row: dict[str, object] = {"id": self.id, "title": self.title}
        if self.url is not None:
            row["url"] = self.url
        if self.kind is not None:
            row["kind"] = self.kind
        if self.attributes:
            row["attributes"] = dict(self.attributes)
        if via is not None:
            row["via"] = via
        if distance is not None:
            row["distance"] = distance
            row["direct"] = distance == 0
        row["tier"] = RECORD_TIER
        row[contract.RULE_FLAG] = True
        return row


@dataclass(frozen=True)
class RecordSet:
    """One block's records, with what it dropped: excluded ids (a count only) and bad data."""

    records: tuple[Record, ...]
    excluded: int
    skipped: int
    files: int = 0  # files the globs matched: a typo'd glob reads as 0, not as silence
    stop_at: tuple[str, ...] = ()  # hub-file globs (412)
    attributes: tuple[str, ...] = ()  # declared attribute paths (413)


def read_blocks(
    raw: object, label: str, root: Path, digest: Callable[[bytes], None]
) -> list[RecordSet]:
    """Validate a rule file's ``records`` value and read every file its globs match, digested."""
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    sets: list[RecordSet] = []
    for item in items:
        if not isinstance(item, dict):
            raise ConfigError(f"indirection_rules: {label!r} records entries must be objects")
        sets.append(_read_block(item, label, root, digest))
    return sets


def _read_block(
    item: dict[str, object], label: str, root: Path, digest: Callable[[bytes], None]
) -> RecordSet:
    where = f"indirection_rules: {label!r} records"
    sources = item.get("sources")
    if isinstance(sources, str):
        sources = [sources]
    if not isinstance(sources, list) or not sources or not all(
        isinstance(glob, str) and glob.strip() for glob in sources
    ):
        raise ConfigError(f"{where}.sources must be a list of globs")
    fields, targets = _fields(item.get("fields"), where)
    attributes = item.get("attributes", [])
    if not isinstance(attributes, list) or not all(
        isinstance(path, str) and path.strip() for path in attributes
    ):
        raise ConfigError(f"{where}.attributes must be a list of field paths")
    declared = tuple(dict.fromkeys(path.strip() for path in attributes))
    kind = item.get("kind")
    if kind is not None and not isinstance(kind, str):
        raise ConfigError(f"{where}.kind must be a string")
    excluded_ids = _excluded(item.get("exclude"), where, root, digest)
    stop_at = item.get("stop_at", [])
    if isinstance(stop_at, str):
        stop_at = [stop_at]
    if not isinstance(stop_at, list) or not all(
        isinstance(glob, str) and glob.strip() for glob in stop_at
    ):
        raise ConfigError(f"{where}.stop_at must be a list of globs")
    records: list[Record] = []
    excluded: set[str] = set()
    skipped = 0
    matched = _matches(sources, where, root)
    for relative in matched:
        data = (root / relative).read_bytes()
        digest(relative.encode("utf-8") + b"\0" + data + b"\0")
        entries, bad = _entries(relative, data)
        skipped += bad
        for entry in entries:
            rid = _dig(entry, fields["id"])
            if isinstance(rid, int) and not isinstance(rid, bool):
                rid = str(rid)
            if not isinstance(rid, str) or not rid.strip():
                skipped += 1
                continue
            rid = rid.strip()
            if rid in excluded_ids:
                excluded.add(rid)
                continue
            records.append(_record(entry, rid, fields, targets, kind, declared))
    return RecordSet(
        tuple(records), len(excluded), skipped, len(matched),
        tuple(glob.strip() for glob in stop_at),
        declared,
    )


def _entries(relative: str, data: bytes) -> tuple[list[object], int]:
    """A file's entries and how many failed to parse: a JSON document (one record or a list),
    or JSON Lines (``.jsonl``/``.ndjson``), where a bad line costs only that line (R5.3)."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], 1
    by_line = Path(relative).suffix.lower() in _LINE_SUFFIXES
    entries: list[object] = []
    bad = 0
    for chunk in (line for line in text.splitlines() if line.strip()) if by_line else [text]:
        try:
            document: object = json.loads(chunk)
        except json.JSONDecodeError:
            bad += 1  # the file is not named
            continue
        entries.extend(document if isinstance(document, list) and not by_line else [document])
    return entries, bad


def _fields(raw: object, where: str) -> tuple[dict[str, str], tuple[str, ...]]:
    """The dotted field map: ``id``/``title``/``url``/``kind`` paths and a ``targets`` list."""
    if raw is None:
        return dict(_DEFAULT_FIELDS), ("targets",)
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}.fields must be an object")
    fields = dict(_DEFAULT_FIELDS)
    for name in _DEFAULT_FIELDS:
        value = raw.get(name, fields[name])
        if not isinstance(value, str) or not value:
            raise ConfigError(f"{where}.fields.{name} must be a field path")
        fields[name] = value
    targets = raw.get("targets", ["targets"])
    if isinstance(targets, str):
        targets = [targets]
    if not isinstance(targets, list) or not targets or not all(
        isinstance(path, str) and path for path in targets
    ):
        raise ConfigError(f"{where}.fields.targets must be a list of field paths")
    return fields, tuple(targets)


def _excluded(
    raw: object, where: str, root: Path, digest: Callable[[bytes], None]
) -> frozenset[str]:
    """Ids never to serve: one per line, a ``#`` and the rest of its line ignored. A named file
    that is absent fails the build — serving everything would publish what it keeps off (W2)."""
    if raw is None:
        return frozenset()
    if not isinstance(raw, str) or not raw:
        raise ConfigError(f"{where}.exclude must be a file path")
    full = root / raw
    if not full.is_file() or not resolves_inside(root, full):
        raise ConfigError(f"{where}.exclude {raw!r} is not a file under {root}")
    data = full.read_bytes()
    digest(data)
    lines = data.decode("utf-8-sig", errors="replace").splitlines()
    # `KEY-1  # why` names KEY-1: an inline comment left on the id would let the record through.
    ids = (line.split("#", 1)[0].strip() for line in lines)
    return frozenset(rid for rid in ids if rid)


def _matches(globs: Sequence[str], where: str, root: Path) -> list[str]:
    """Repo-relative files the globs match, sorted, each inside ``root``."""
    found: set[str] = set()
    for pattern in globs:
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise ConfigError(f"{where}.sources {pattern!r} must stay under {root}")
        for path in root.glob(pattern.strip()):
            if path.is_file() and resolves_inside(root, path):
                found.add(path.relative_to(root).as_posix())
    return sorted(found)


def _record(
    entry: object,
    rid: str,
    fields: dict[str, str],
    targets: Sequence[str],
    kind: str | None,
    attributes: Sequence[str] = (),
) -> Record:
    title = _dig(entry, fields["title"])
    url = _dig(entry, fields["url"])
    if isinstance(url, list):  # a record keeping several links serves its first
        url = next((link for link in url if isinstance(link, str) and link.strip()), None)
    declared_kind = _dig(entry, fields["kind"])
    named: list[str] = []
    for path in targets:
        value = _dig(entry, path)
        listed = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        for target in listed:
            if isinstance(target, str) and target.strip() and target.strip() not in named:
                named.append(target.strip())
    return Record(
        id=rid,
        title=title.strip()[:TITLE_MAX] if isinstance(title, str) else "",
        url=url.strip() if isinstance(url, str) and url.strip() else None,
        kind=declared_kind if isinstance(declared_kind, str) and declared_kind else kind,
        targets=tuple(named),
        attributes=tuple(
            (path, value)
            for path in attributes
            if (value := _attribute(_dig(entry, path))) is not None
        ),
    )


def _attribute(value: object) -> object:
    """A kept attribute value: a string, number or boolean, or a list of up to
    ``ATTRIBUTE_LIST_MAX`` of them — else ``None``, never stored (413)."""
    if _scalar(value):
        return value
    if (
        isinstance(value, list)
        and 0 < len(value) <= ATTRIBUTE_LIST_MAX
        and all(_scalar(item) for item in value)
    ):
        return value
    return None


def _scalar(value: object) -> bool:
    # NaN and the infinities are not JSON; a string past TITLE_MAX would bloat every row.
    # Dropped, never cut: a truncated value would silently miss an exact filter.
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, str):
        return len(value) <= TITLE_MAX
    return isinstance(value, int | bool)


def _dig(value: object, path: str) -> object:
    """``value`` at a dotted object path; a miss is ``None``."""
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def resolve(
    sets: Iterable[RecordSet], locate: Callable[[str], str | None]
) -> tuple[list[Record], dict[str, object]]:
    """Records keeping only the targets ``locate`` finds (as stored), and the counts block.

    A target naming nothing indexed is a dangling pair — counted and listed, never attached
    (AC3). The first record of an id wins; a later one is counted as skipped.
    """
    stored: list[Record] = []
    dangling: list[dict[str, str]] = []
    seen: set[str] = set()
    declared = excluded = skipped = attachments = files = untargeted = 0
    for block in sets:
        excluded += block.excluded
        skipped += block.skipped
        files += block.files
        for record in block.records:
            if record.id in seen:
                skipped += 1
                continue
            seen.add(record.id)
            declared += 1
            untargeted += not record.targets  # a field map naming the wrong key shows here
            found: list[str] = []
            for target in record.targets:
                qname = locate(target)
                if qname is None:
                    dangling.append({"id": record.id, "target": target})
                elif qname not in found:
                    found.append(qname)
            if found:
                attachments += len(found)
                stored.append(
                    Record(
                        record.id, record.title, record.url, record.kind, tuple(found),
                        record.attributes,
                    )
                )
    counts: dict[str, object] = {
        "files": files,
        "declared": declared,
        "untargeted": untargeted,
        "attached": len(stored),
        "attachments": attachments,
        "dangling": len(dangling),
        "dangling_first": dangling[:DANGLING_FIRST],
        "excluded": excluded,
        "skipped": skipped,
    }
    return sorted(stored, key=lambda record: record.id), counts


def dump(records: Sequence[Record]) -> str:
    return json.dumps([asdict(record) for record in records], separators=(",", ":"), sort_keys=True)


def load(raw: str | None) -> list[Record] | None:
    """The stored records; ``None`` when no records block was configured at build."""
    if raw is None:
        return None
    return [
        Record(
            row["id"], row["title"], row["url"], row["kind"], tuple(row["targets"]),
            tuple((str(path), value) for path, value in row.get("attributes", ())),
        )
        for row in json.loads(raw)
    ]


def load_selected(
    raw: str | None, raw_declared: str | None, wanted: Mapping[str, object] | None
) -> list[Record] | None:
    """The stored records a ``records_filter`` keeps (413); ``None`` when no records block was
    built — and a filter then names nothing declared, so it is refused."""
    stored = load(raw)
    declared = json.loads(raw_declared) if raw_declared else []
    selected = select(stored or [], wanted, declared)
    return None if stored is None else selected


def select(
    records: Sequence[Record], wanted: Mapping[str, object] | None, declared: Sequence[str]
) -> list[Record]:
    """The records whose attributes match ``wanted``: each path equal to a value, or to one of a
    list's; a list attribute matches when any element does (413). A path no block declares is
    refused — never read as "matches nothing" or ignored."""
    if wanted is None:
        return list(records)
    check_filter(wanted, declared)
    tests = {
        path: value if isinstance(value, list) else [value] for path, value in wanted.items()
    }
    return [
        record
        for record in records
        if all(_kept(dict(record.attributes).get(path), want) for path, want in tests.items())
    ]


def check_filter(wanted: Mapping[str, object], declared: Sequence[str]) -> None:
    """Refuse a filter naming a path no block declares, or wanting a value no attribute holds:
    an object, a null, a nested or empty list (413)."""
    unknown = sorted(set(wanted) - set(declared))
    if unknown:
        raise ValueError(
            f"records_filter names {unknown}, which no records block declares as attributes; "
            f"declared: {sorted(declared)}"
        )
    for path, value in wanted.items():
        values = value if isinstance(value, list) else [value]
        if not values or not all(_scalar(item) for item in values):
            raise ValueError(
                f"records_filter[{path!r}] must be a string, number or boolean, or a non-empty "
                f"list of them, got {value!r}"
            )


def _kept(value: object, wanted: Sequence[object]) -> bool:
    held = value if isinstance(value, list) else [] if value is None else [value]
    return any(_same(item, want) for item in held for want in wanted)


def _same(left: object, right: object) -> bool:
    # JSON's true is not 1: a boolean equals only a boolean.
    return left == right and isinstance(left, bool) == isinstance(right, bool)


def attached(
    records: Sequence[Record], carriers: Iterable[str], *, via: bool
) -> list[dict[str, object]]:
    """Rows for the records on ``carriers`` — the subject itself, so each is ``direct`` at
    distance 0 (412) — in carrier order; each record once, under the first carrier that holds it
    (``via`` names it when asked)."""
    by_target: dict[str, list[Record]] = {}
    for record in records:
        for target in record.targets:
            by_target.setdefault(target, []).append(record)
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for carrier in dict.fromkeys(carriers):
        for record in by_target.get(carrier, ()):
            if record.id not in seen:
                seen.add(record.id)
                rows.append(record.as_row(carrier if via else None, 0))
    return rows


def ranked(
    records: Sequence[Record],
    seeds: Sequence[str],
    radius: Iterable[tuple[str, int, str]],
    *,
    stop_at: Sequence[str] = (),
    direct_only: bool = False,
) -> tuple[list[dict[str, object]], int]:
    """Rows for a blast radius, direct first, and how many records ``stop_at`` alone kept out
    (412). ``seeds`` are the subject's qnames and files: a record on one, or on a member a seed
    contains, is ``direct`` (distance 0). ``radius`` is ``(carrier, depth, file)`` in walk
    order, read by depth; a carrier in a ``stop_at`` file carries nothing.
    Each record once, under its first carrier, so at its least distance."""
    owners = set(seeds)
    members = sorted(
        {
            target
            for record in records
            for target in record.targets
            if target not in owners and _contained(target, owners)
        }
    )
    by_target: dict[str, list[Record]] = {}
    for record in records:
        for target in record.targets:
            by_target.setdefault(target, []).append(record)
    rows: list[dict[str, object]] = []
    seen: set[str] = set()

    def take(carrier: str, distance: int) -> None:
        for record in by_target.get(carrier, ()):
            if record.id not in seen:
                seen.add(record.id)
                rows.append(record.as_row(carrier, distance))

    for carrier in dict.fromkeys([*seeds, *members]):
        take(carrier, 0)
    if direct_only:
        return rows, 0
    stopped: set[str] = set()
    for carrier, depth, file in sorted(radius, key=lambda hop: hop[1]):
        if any(fnmatch.fnmatchcase(file, glob) for glob in stop_at):
            stopped.update(record.id for record in by_target.get(carrier, ()))
        else:
            take(carrier, max(depth, 1))
    return rows, len(stopped - seen)


def _contained(qname: str, owners: set[str]) -> bool:
    """Is ``qname`` a member, at any depth, of one of ``owners``?"""
    head = qname
    while contract.MEMBER_SEPARATOR in head:
        head = head.rpartition(contract.MEMBER_SEPARATOR)[0]
        if head in owners:
            return True
    return False


def status_block(raw: str | None) -> dict[str, object] | None:
    """The stored counts block, or ``None`` when no records block was configured at build."""
    return None if raw is None else dict(json.loads(raw))
