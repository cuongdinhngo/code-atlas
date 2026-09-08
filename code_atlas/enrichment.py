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

# Synthetic path holding rule-emitted edges; replaced each build, dropped when rules are off.
# Not a real on-disk file — no files row / File node (068); nav treats edges as rule-derived.
INDIRECTION_FILE = ".code-atlas/indirection-rules"

_HEURISTIC = contract.CONFIDENCE_TIERS[1]

# One-line call sites only (v1): Nth quoted string literal on the CALLS line.
_STRING_LIT = re.compile(r"""'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*\"""")
# keyed_calls templates: exactly one named placeholder, `{key}` (task 222).
_TEMPLATE_PLACEHOLDER = re.compile(r"\{([^{}]+)\}")


@dataclass(frozen=True, slots=True)
class RulesPayload:
    """Validated aliases/calls/view_data/keyed_calls plus a content digest (load before parse)."""

    aliases: tuple[tuple[str, str], ...]
    calls: tuple[tuple[str, str, int], ...]
    view_data: tuple[tuple[str, int, str], ...]
    keyed_calls: tuple[tuple[str, int, str, str], ...]
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
    view_data: list[tuple[str, int, str]] = []
    keyed_calls: list[tuple[str, int, str, str]] = []
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
        keyed_calls.extend(parsed[3])

    return RulesPayload(
        aliases=tuple(aliases),
        calls=tuple(calls),
        view_data=tuple(view_data),
        keyed_calls=tuple(keyed_calls),
        digest=digester.hexdigest(),
    )


class Enriched(NamedTuple):
    """Rows this run wrote from the rules, counted where they are built — no re-query (task 051)."""

    nodes: int
    edges: int
    # Per keyed_calls rule: stamps it emitted — post-resolve census (task 222).
    keyed_call_groups: tuple[tuple[tuple[str, str, int], ...], ...] = ()


NOTHING = Enriched(nodes=0, edges=0, keyed_call_groups=())


def apply_indirection_rules(
    config: Config, store: GraphStore, *, payload: RulesPayload | None = None
) -> Enriched:
    """Replace synthetic ALIASES/CALLS/PROVIDES_VIEW_DATA rows, or clear when off.

    Edges keep ``file_path=INDIRECTION_FILE``; there is no ``files`` row and no File node
    (task 068 — counters and source-file tools must not treat the bookmark as source).
    """
    # Always purge first so a pre-068 index cannot keep a leftover files/File bookmark.
    store.remove_file(INDIRECTION_FILE)
    if not config.indirection_rules:
        return NOTHING

    loaded = payload if payload is not None else load_indirection_rules(config)
    if loaded is None:
        return NOTHING

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
    keyed_edges, keyed_groups = _keyed_calls_edges(config, store, loaded.keyed_calls)
    edges.extend(keyed_edges)

    store.replace_file_rows(INDIRECTION_FILE, [], edges)
    return Enriched(nodes=0, edges=len(edges), keyed_call_groups=keyed_groups)


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
    config: Config, store: GraphStore, rules: tuple[tuple[str, int, str], ...]
) -> list[dict[str, object]]:
    if not rules:
        return []
    # Indexed per-setter lookups (idx_edges_raw) — O(matching sites), not a capped CALLS prefix.
    out: list[dict[str, object]] = []
    seen: set[tuple[str, str, int]] = set()
    line_cache: dict[tuple[str, int], str | None] = {}
    for setter, key_arg, key_from in rules:
        for edge in _calls_for_setter(store, setter):
            if edge.get("file_path") == INDIRECTION_FILE:
                continue
            args = edge.get("args")
            source = str(edge.get("source_qname") or "")
            line = edge.get("line")
            if not source or type(line) is not int:
                continue
            rel = edge.get("file_path")
            if not isinstance(rel, str) or not rel:
                continue
            keys = _keys_for_rule(
                config, edge, args, key_arg, key_from, rel, line, line_cache
            )
            for key in keys:
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


def _keyed_calls_edges(
    config: Config,
    store: GraphStore,
    rules: tuple[tuple[str, int, str, str], ...],
) -> tuple[list[dict[str, object]], tuple[tuple[tuple[str, str, int], ...], ...]]:
    """CALLS edges whose target is a string key substituted into ``target_template`` (task 222)."""
    if not rules:
        return [], ()
    out: list[dict[str, object]] = []
    groups: list[tuple[tuple[str, str, int], ...]] = []
    seen: set[tuple[str, str, int]] = set()
    line_cache: dict[tuple[str, int], str | None] = {}
    for setter, key_arg, key_from, template in rules:
        group: list[tuple[str, str, int]] = []
        for edge in _calls_for_setter(store, setter):
            if edge.get("file_path") == INDIRECTION_FILE:
                continue
            args = edge.get("args")
            source = str(edge.get("source_qname") or "")
            line = edge.get("line")
            if not source or type(line) is not int:
                continue
            rel = edge.get("file_path")
            if not isinstance(rel, str) or not rel:
                continue
            keys = _keys_for_rule(
                config, edge, args, key_arg, key_from, rel, line, line_cache
            )
            for key in keys:
                target = template.replace("{key}", key)
                stamp = (source, target, line)
                if stamp in seen:
                    continue
                seen.add(stamp)
                group.append(stamp)
                out.append(
                    {
                        "kind": "CALLS",
                        "source_qname": source,
                        "target_raw": target,
                        "file_path": INDIRECTION_FILE,
                        "line": line,
                        "confidence_tier": _HEURISTIC,
                    }
                )
        if group:
            groups.append(tuple(group))
    out.sort(
        key=lambda row: (
            str(row["source_qname"]),
            str(row["target_raw"]),
            int(row["line"]) if type(row["line"]) is int else 0,
        )
    )
    return out, tuple(groups)


def count_unresolved_keyed_calls(
    store: GraphStore, groups: tuple[tuple[tuple[str, str, int], ...], ...]
) -> int:
    """Rules whose every emitted keyed_calls edge stayed unlinked after resolve (task 222 AC4)."""
    unresolved = 0
    for stamps in groups:
        if not stamps:
            continue
        any_linked = False
        for _source, target_raw, _line in stamps:
            for row in store.calls_by_target_raw(target_raw):
                if row.get("file_path") != INDIRECTION_FILE:
                    continue
                if row.get("target_qname"):
                    any_linked = True
                    break
            if any_linked:
                break
        if not any_linked:
            unresolved += 1
    return unresolved


def _calls_for_setter(store: GraphStore, setter: str) -> list[dict[str, object]]:
    """CALLS matching ``setter`` via exact ``target_raw``, plus ``::setter`` when bare."""
    rows = list(store.calls_by_target_raw(setter))
    if "::" in setter:
        return rows
    seen_ids = {row.get("id") for row in rows if row.get("id") is not None}
    for row in store.calls_ending_with_target_raw(f"::{setter}"):
        edge_id = row.get("id")
        if edge_id is not None and edge_id in seen_ids:
            continue
        if edge_id is not None:
            seen_ids.add(edge_id)
        rows.append(row)
    return rows


def _keys_for_rule(
    config: Config,
    edge: dict[str, object],
    args: object,
    key_arg: int,
    key_from: str,
    rel: str,
    line: int,
    line_cache: dict[tuple[str, int], str | None],
) -> list[str]:
    if key_from == "array_keys":
        return _keys_from_arg_keys(edge.get("arg_keys"), args, key_arg)
    if key_from != "string":
        return []
    if not _arg_is_string(args, key_arg):
        return []
    text = _line_text(config.root, rel, line, line_cache)
    if text is None:
        return []
    parsed = _parse_args(args)
    if parsed is None:
        return []
    ordinal = sum(1 for entry in parsed[:key_arg] if entry == "string")
    key = _nth_string_literal(text, ordinal)
    return [key] if key is not None else []


def _keys_from_arg_keys(arg_keys: object, args: object, key_arg: int) -> list[str]:
    """Keys from ``arg_keys[key_arg-1]`` when that arg is an array (task 063).

    Absent field, null slot, and ``[]`` all yield no keys here — edge emission cannot
    distinguish them. AC4's "not captured" vs "none found" is enforced by schema refusal
    of pre-v5 indexes; adapter #2 should advertise capture via an R1.6 capability.
    """
    parsed_args = _parse_args(args)
    if parsed_args is None or key_arg < 1 or key_arg > len(parsed_args):
        return []
    if parsed_args[key_arg - 1] != "array":
        return []
    slots = _parse_arg_keys(arg_keys)
    if slots is None or key_arg > len(slots):
        return []
    entry = slots[key_arg - 1]
    if not isinstance(entry, list):
        return []
    return [key for key in entry if isinstance(key, str) and key]


def _parse_arg_keys(raw: object) -> list[object] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, list) else None
    return None


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
) -> tuple[
    list[tuple[str, str]],
    list[tuple[str, str, int]],
    list[tuple[str, int, str]],
    list[tuple[str, int, str, str]],
]:
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

    view_data: list[tuple[str, int, str]] = []
    for item in _as_list(raw.get("view_data"), label, "view_data"):
        if not isinstance(item, dict):
            raise ConfigError(f"indirection_rules: {label!r} view_data entries must be objects")
        setter = _as_qname(item.get("setter"), label, "view_data.setter")
        key_arg = item.get("key_arg")
        if type(key_arg) is not int or key_arg < 1:
            raise ConfigError(f"indirection_rules: {label!r} view_data.key_arg must be an int >= 1")
        key_from = item.get("key_from", "string")
        if key_from not in ("string", "array_keys"):
            raise ConfigError(
                f"indirection_rules: {label!r} view_data.key_from must be "
                f"'string' or 'array_keys'"
            )
        view_data.append((setter, key_arg, key_from))

    keyed_calls: list[tuple[str, int, str, str]] = []
    for item in _as_list(raw.get("keyed_calls"), label, "keyed_calls"):
        if not isinstance(item, dict):
            raise ConfigError(f"indirection_rules: {label!r} keyed_calls entries must be objects")
        setter = _as_qname(item.get("setter"), label, "keyed_calls.setter")
        key_arg = item.get("key_arg")
        if type(key_arg) is not int or key_arg < 1:
            raise ConfigError(
                f"indirection_rules: {label!r} keyed_calls.key_arg must be an int >= 1"
            )
        key_from = item.get("key_from", "string")
        if key_from not in ("string", "array_keys"):
            raise ConfigError(
                f"indirection_rules: {label!r} keyed_calls.key_from must be "
                f"'string' or 'array_keys'"
            )
        template = item.get("target_template")
        if not isinstance(template, str) or not template.strip():
            raise ConfigError(
                f"indirection_rules: {label!r} keyed_calls.target_template must be "
                f"a non-empty string"
            )
        template = template.strip()
        names = _TEMPLATE_PLACEHOLDER.findall(template)
        if names != ["key"]:
            raise ConfigError(
                f"indirection_rules: {label!r} keyed_calls.target_template must contain "
                f"exactly the placeholder '{{key}}' (found {names!r})"
            )
        keyed_calls.append((setter, key_arg, key_from, template))

    return aliases, calls, view_data, keyed_calls


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
