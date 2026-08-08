"""Optional framework-indirection enrichment from JSON rules (task 040 / 062).

Rules live **outside** ``adapters/`` (R2.2). The core applies them generically — no
``if framework == …`` (R1.1). Off when ``config.indirection_rules`` is unset.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from code_atlas import contract
from code_atlas.config import Config, ConfigError
from code_atlas.store import GraphStore

# Synthetic path holding rule-emitted rows; replaced each build, dropped when rules are off.
# Not a real on-disk file — tools must treat edges here as rule-derived (see edge_hit).
INDIRECTION_FILE = ".code-atlas/indirection-rules"

# files.language value — underscore-prefixed so it is never mistaken for a language handshake.
_RULES_LANGUAGE = "_rules"

_HEURISTIC = contract.CONFIDENCE_TIERS[1]

# One-line call sites only (v1): Nth quoted string literal on the CALLS line.
_STRING_LIT = re.compile(r"""'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*\"""")


@dataclass(frozen=True, slots=True)
class RulesPayload:
    """Validated aliases/calls/view_data plus a content digest (load before parse; apply after)."""

    aliases: tuple[tuple[str, str], ...]
    calls: tuple[tuple[str, str, int], ...]
    view_data: tuple[tuple[str, int], ...]
    digest: str


def load_indirection_rules(config: Config) -> RulesPayload | None:
    """Validate and parse configured rule files, or ``None`` when the knob is off.

    Call this **before** the expensive parse so a bad rules file fails loud without leaving
    an unresolved half-built index (R5.3).
    """
    paths = config.indirection_rules
    if not paths:
        return None

    aliases: list[tuple[str, str]] = []
    calls: list[tuple[str, str, int]] = []
    view_data: list[tuple[str, int]] = []
    digester = hashlib.sha256()
    for relative in sorted(paths):
        full = config.root / relative
        if not full.is_file():
            raise ConfigError(f"indirection_rules: {relative!r} is not a file under {config.root}")
        try:
            raw_bytes = full.read_bytes()
        except OSError as error:
            raise ConfigError(
                f"indirection_rules: {relative!r} could not be read ({error})"
            ) from error
        digester.update(relative.encode("utf-8"))
        digester.update(b"\0")
        digester.update(raw_bytes)
        digester.update(b"\0")
        parsed = _load_rules(relative, raw_bytes)
        aliases.extend(parsed[0])
        calls.extend(parsed[1])
        view_data.extend(parsed[2])

    return RulesPayload(
        aliases=tuple(aliases),
        calls=tuple(calls),
        view_data=tuple(view_data),
        digest=digester.hexdigest(),
    )


class Enriched(NamedTuple):
    """Rows this run wrote from the rules, counted where they are built — no re-query (task 051)."""

    nodes: int
    edges: int


NOTHING = Enriched(nodes=0, edges=0)


def apply_indirection_rules(
    config: Config, store: GraphStore, *, payload: RulesPayload | None = None
) -> Enriched:
    """Replace synthetic ALIASES/CALLS/PROVIDES_VIEW_DATA rows, or clear when off."""
    if not config.indirection_rules:
        if INDIRECTION_FILE in store.file_paths():
            store.remove_file(INDIRECTION_FILE)
        return NOTHING

    loaded = payload if payload is not None else load_indirection_rules(config)
    if loaded is None:
        return NOTHING

    nodes: list[dict[str, object]] = [
        {
            "kind": "File",
            "name": Path(INDIRECTION_FILE).name,
            "qualified_name": INDIRECTION_FILE,
            "file_path": INDIRECTION_FILE,
            "line_start": 1,
            "line_end": 1,
        }
    ]
    edges: list[dict[str, object]] = []
    for source, target in loaded.aliases:
        edges.append(
            {
                "kind": "ALIASES",
                "source_qname": source,
                "target_raw": target,
                "file_path": INDIRECTION_FILE,
                "line": 1,
                "confidence_tier": _HEURISTIC,
            }
        )
    for source, target, line in loaded.calls:
        edges.append(
            {
                "kind": "CALLS",
                "source_qname": source,
                "target_raw": target,
                "file_path": INDIRECTION_FILE,
                "line": line,
                "confidence_tier": _HEURISTIC,
            }
        )
    edges.extend(_view_data_edges(config, store, loaded.view_data))

    store.upsert_file(INDIRECTION_FILE, loaded.digest, _RULES_LANGUAGE, parsed_ok=True)
    store.replace_file_rows(INDIRECTION_FILE, nodes, edges)
    return Enriched(nodes=len(nodes), edges=len(edges))


def is_rule_edge_path(path: object) -> bool:
    """True when an edge ``file_path`` is the synthetic indirection bookmark."""
    return path == INDIRECTION_FILE


def is_rule_edge_kind(kind: object) -> bool:
    """True when ``kind`` is only ever emitted by rules (task 062)."""
    return kind == contract.PROVIDES_VIEW_DATA


def view_data_key(target_raw: object) -> str | None:
    """Strip ``viewdata:`` from a PROVIDES_VIEW_DATA ``target_raw``, or ``None`` if malformed."""
    if not isinstance(target_raw, str) or not target_raw.startswith(contract.VIEW_DATA_PREFIX):
        return None
    key = target_raw[len(contract.VIEW_DATA_PREFIX) :]
    return key if key else None


def _view_data_edges(
    config: Config, store: GraphStore, rules: tuple[tuple[str, int], ...]
) -> list[dict[str, object]]:
    if not rules:
        return []
    # Cap the CALLS scan; enrichment must stay bounded (R4 / CA_MAX_RESULTS spirit).
    calls = store.edges_matching_kind("CALLS", limit=max(10_000, config.max_results * 200))
    out: list[dict[str, object]] = []
    seen: set[tuple[str, str, int]] = set()
    line_cache: dict[tuple[str, int], str | None] = {}
    for edge in calls:
        if edge.get("file_path") == INDIRECTION_FILE:
            continue
        target = str(edge.get("target_raw") or "")
        matched = [_key_arg for setter, _key_arg in rules if _setter_matches(target, setter)]
        if not matched:
            continue
        args = edge.get("args")
        source = str(edge.get("source_qname") or "")
        line = edge.get("line")
        if not source or type(line) is not int:
            continue
        rel = edge.get("file_path")
        if not isinstance(rel, str) or not rel:
            continue
        for key_arg in matched:
            if not _arg_is_string(args, key_arg):
                continue
            text = _line_text(config.root, rel, line, line_cache)
            if text is None:
                continue
            parsed = _parse_args(args)
            if parsed is None:
                continue
            # key_arg is the 1-based *argument* index; map to the Nth string literal on the line.
            ordinal = sum(1 for entry in parsed[:key_arg] if entry == "string")
            key = _nth_string_literal(text, ordinal)
            if key is None:
                continue
            stamp = (source, key, line)
            if stamp in seen:
                continue
            seen.add(stamp)
            out.append(
                {
                    "kind": contract.PROVIDES_VIEW_DATA,
                    "source_qname": source,
                    "target_raw": f"{contract.VIEW_DATA_PREFIX}{key}",
                    "file_path": INDIRECTION_FILE,
                    "line": line,
                    "confidence_tier": _HEURISTIC,
                }
            )
    out.sort(
        key=lambda row: (
            str(row["source_qname"]),
            str(row["target_raw"]),
            int(row["line"]) if type(row["line"]) is int else 0,
        )
    )
    return out


def _setter_matches(target_raw: str, setter: str) -> bool:
    if target_raw == setter:
        return True
    if "::" not in setter and target_raw.endswith(f"::{setter}"):
        return True
    return False


def _arg_is_string(args: object, key_arg: int) -> bool:
    parsed = _parse_args(args)
    if parsed is None or key_arg < 1 or key_arg > len(parsed):
        return False
    return parsed[key_arg - 1] == "string"


def _parse_args(args: object) -> list[object] | None:
    """Store rows keep ``args`` as a JSON text column; adapter dicts use a list."""
    if args is None:
        return None
    if isinstance(args, list):
        return args
    if isinstance(args, str):
        try:
            loaded = json.loads(args)
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, list) else None
    return None


def _line_text(
    root: Path, rel: str, line: int, cache: dict[tuple[str, int], str | None]
) -> str | None:
    key = (rel, line)
    if key in cache:
        return cache[key]
    path = root / rel
    text: str | None = None
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for number, raw in enumerate(handle, start=1):
                    if number == line:
                        text = raw
                        break
                    if number > line:
                        break
        except OSError:
            text = None
    cache[key] = text
    return text


def _nth_string_literal(line: str, n: int) -> str | None:
    """1-based Nth quoted string on ``line`` (single/double quotes; simple escapes)."""
    if n < 1:
        return None
    found = _STRING_LIT.findall(line)
    if n > len(found):
        return None
    raw = found[n - 1]
    inner = raw[1:-1]
    if raw[0] == "'":
        return inner.replace("\\\\", "\\").replace("\\'", "'")
    return (
        inner.replace("\\\\", "\\")
        .replace('\\"', '"')
        .replace("\\n", "\n")
        .replace("\\t", "\t")
    )


def _load_rules(
    label: str, raw_bytes: bytes
) -> tuple[list[tuple[str, str]], list[tuple[str, str, int]], list[tuple[str, int]]]:
    try:
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConfigError(f"indirection_rules: {label!r} is not valid JSON ({error})") from error
    if not isinstance(raw, dict):
        raise ConfigError(f"indirection_rules: {label!r} root must be a JSON object")

    aliases: list[tuple[str, str]] = []
    for item in _as_list(raw.get("aliases"), label, "aliases"):
        if not isinstance(item, dict):
            raise ConfigError(f"indirection_rules: {label!r} aliases entries must be objects")
        source = _as_qname(item.get("from"), label, "aliases.from")
        target = _as_qname(item.get("to"), label, "aliases.to")
        aliases.append((source, target))

    calls: list[tuple[str, str, int]] = []
    for item in _as_list(raw.get("calls"), label, "calls"):
        if not isinstance(item, dict):
            raise ConfigError(f"indirection_rules: {label!r} calls entries must be objects")
        source = _as_qname(item.get("source"), label, "calls.source")
        target = _as_qname(item.get("target"), label, "calls.target")
        line = item.get("line", 1)
        if type(line) is not int or line < 1:
            raise ConfigError(f"indirection_rules: {label!r} calls.line must be an int >= 1")
        calls.append((source, target, line))

    view_data: list[tuple[str, int]] = []
    for item in _as_list(raw.get("view_data"), label, "view_data"):
        if not isinstance(item, dict):
            raise ConfigError(f"indirection_rules: {label!r} view_data entries must be objects")
        setter = _as_qname(item.get("setter"), label, "view_data.setter")
        key_arg = item.get("key_arg")
        if type(key_arg) is not int or key_arg < 1:
            raise ConfigError(f"indirection_rules: {label!r} view_data.key_arg must be an int >= 1")
        view_data.append((setter, key_arg))

    return aliases, calls, view_data


def _as_list(raw: object, label: str, field: str) -> list[Any]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConfigError(f"indirection_rules: {label!r} {field} must be a list")
    return raw


def _as_qname(raw: object, label: str, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError(f"indirection_rules: {label!r} {field} must be a non-empty string")
    return raw.strip()
