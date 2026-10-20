"""Records written about code, attached to the symbols they name (task 407).

A consumer keeps records about its code — a QA ticket, an incident, an ADR — each naming the
symbols it is about. A ``records`` block in a ``CA_INDIRECTION_RULES`` file declares where they
live (globs of JSON files) and how to read them (a dotted field map), and the build resolves each
target and stores the attached records in the index's meta, so a tool answers at the revision the
index describes (R4.2) — 385's route-table shape.

A record is a declared lookup beside the graph, never a node or an edge, so the contract does not
move. Every row it shapes says ``tier: HEURISTIC``, ``rule: true`` — declared, not resolved (R5.2).
An id named in the block's ``exclude`` file is dropped before anything else reads the record, so
no answer, count list or message can name it; only how many were dropped is kept.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from code_atlas import contract
from code_atlas.config import ConfigError
from code_atlas.containment import resolves_inside

RECORDS_META_KEY = "records"
# The counts block the build result and `get_index_status` report: never an excluded id.
RECORDS_STATUS_META_KEY = "records_status"
RECORD_TIER = contract.CONFIDENCE_TIERS[1]  # HEURISTIC
DANGLING_FIRST = 10
TITLE_MAX = 200
_DEFAULT_FIELDS = {"id": "id", "title": "title", "url": "url", "kind": "kind"}


@dataclass(frozen=True)
class Record:
    """One record as declared, or as stored with only the targets the index holds."""

    id: str
    title: str
    url: str | None
    kind: str | None
    targets: tuple[str, ...]

    def as_row(self, via: str | None = None) -> dict[str, object]:
        """The record as an answer carries it: declared, so HEURISTIC and rule-derived."""
        row: dict[str, object] = {"id": self.id, "title": self.title}
        if self.url is not None:
            row["url"] = self.url
        if self.kind is not None:
            row["kind"] = self.kind
        if via is not None:
            row["via"] = via
        row["tier"] = RECORD_TIER
        row[contract.RULE_FLAG] = True
        return row


@dataclass(frozen=True)
class RecordSet:
    """One block's records, with what it dropped: excluded ids (a count only) and bad data."""

    records: tuple[Record, ...]
    excluded: int
    skipped: int


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
    kind = item.get("kind")
    if kind is not None and not isinstance(kind, str):
        raise ConfigError(f"{where}.kind must be a string")
    excluded_ids = _excluded(item.get("exclude"), where, root, digest)
    records: list[Record] = []
    excluded: set[str] = set()
    skipped = 0
    for relative in _matches(sources, where, root):
        data = (root / relative).read_bytes()
        digest(relative.encode("utf-8") + b"\0" + data + b"\0")
        try:
            document: object = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            skipped += 1  # a data error fails soft (R5.3); the file is not named
            continue
        for entry in document if isinstance(document, list) else [document]:
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
            records.append(_record(entry, rid, fields, targets, kind))
    return RecordSet(tuple(records), len(excluded), skipped)


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
    """Ids never to serve: one per line, ``#`` comments and blanks ignored. A named file that
    is absent fails the build — serving everything would publish what it keeps off (W2)."""
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
    return frozenset(
        line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")
    )


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
) -> Record:
    title = _dig(entry, fields["title"])
    url = _dig(entry, fields["url"])
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
    )


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
    declared = excluded = skipped = attachments = 0
    for block in sets:
        excluded += block.excluded
        skipped += block.skipped
        for record in block.records:
            if record.id in seen:
                skipped += 1
                continue
            seen.add(record.id)
            declared += 1
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
                    Record(record.id, record.title, record.url, record.kind, tuple(found))
                )
    counts: dict[str, object] = {
        "declared": declared,
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
        Record(row["id"], row["title"], row["url"], row["kind"], tuple(row["targets"]))
        for row in json.loads(raw)
    ]


def attached(
    records: Sequence[Record], carriers: Iterable[str], *, via: bool
) -> list[dict[str, object]]:
    """Rows for the records on ``carriers``, in carrier order; each record once, under the
    first carrier that holds it (``via`` names it when asked)."""
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
                rows.append(record.as_row(carrier if via else None))
    return rows


def status_block(raw: str | None) -> dict[str, object] | None:
    """The stored counts block, or ``None`` when no records block was configured at build."""
    return None if raw is None else dict(json.loads(raw))
