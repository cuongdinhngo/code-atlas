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
from code_atlas.containment import resolves_inside
from code_atlas.store import GraphStore

# Synthetic path holding rule-emitted edges; replaced each build, dropped when rules are off.
# Not a real on-disk file — no files row / File node (068); nav treats edges as rule-derived.
INDIRECTION_FILE = ".code-atlas/indirection-rules"

_HEURISTIC = contract.CONFIDENCE_TIERS[1]

# One-line call sites only (v1): Nth quoted string literal on the CALLS line.
_STRING_LIT = re.compile(r"""'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*\"""")
# What a keyed_calls rule may emit: a call, or a write / row removal of the table it names (364).
_KEYED_KINDS: tuple[str, ...] = ("CALLS", contract.WRITES, contract.DELETES)
# keyed_calls placeholders: `{key}`, or a key_pattern's named groups / an object's fields (361).
_TEMPLATE_PLACEHOLDER = re.compile(r"\{([^{}]+)\}")
# One whole top-level entry `name: 'value'` / `'name' => "value"` of an object/array literal (361).
_LITERAL_FIELD = re.compile(
    r"""\s*(['"]?)([A-Za-z_$][\w$]*)\1\s*(?::|=>)\s*('(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")\s*"""
)
# The callee's own name, the last identifier of its qname: where its argument list starts (352).
_IDENTIFIER = re.compile(r"[A-Za-z_$][\w$]*")
_OPENERS = {"(": ")", "[": "]", "{": "}"}


# One keyed_calls edge as the census sees it: (source, target_raw, line, kind) — 222/352/364.
Stamp = tuple[str, str, int, str]


class KeyedCall(NamedTuple):
    """One ``keyed_calls`` rule: where the key comes from and the template it fills (222/361)."""

    setter: str
    key_arg: int
    key_from: str
    template: str
    # Searched in the string key: its named groups, else group 1 as `{key}`, fill the template.
    pattern: re.Pattern[str] | None = None
    # The edge the rule emits: a call, or a write / row removal onto a `Table` it names (364).
    kind: str = "CALLS"


@dataclass(frozen=True, slots=True)
class RulesPayload:
    """Validated aliases/calls/view_data/keyed_calls plus a content digest (load before parse)."""

    aliases: tuple[tuple[str, str], ...]
    calls: tuple[tuple[str, str, int], ...]
    view_data: tuple[tuple[str, int, str], ...]
    keyed_calls: tuple[KeyedCall, ...]
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
    keyed_calls: list[KeyedCall] = []
    digester = hashlib.sha256()
    for relative in sorted(paths):
        full = config.root / relative
        if not full.is_file():
            raise ConfigError(f"indirection_rules: {relative!r} is not a file under {config.root}")
        if not resolves_inside(config.root, full):
            raise ConfigError(f"indirection_rules: {relative!r} resolves outside {config.root}")
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
    keyed_call_groups: tuple[tuple[Stamp, ...], ...] = ()
    # Per call site and string key: the stamps every keyed_calls rule emitted for it (352).
    keyed_call_sites: tuple[tuple[Stamp, ...], ...] = ()


NOTHING = Enriched(nodes=0, edges=0)


def apply_indirection_rules(
    config: Config, store: GraphStore, *, payload: RulesPayload | None = None
) -> Enriched:
    """Replace synthetic ALIASES/CALLS/WRITES/DELETES/PROVIDES_VIEW_DATA rows, or clear when off.

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
    keyed_edges, keyed_groups, keyed_sites = _keyed_calls_edges(config, store, loaded.keyed_calls)
    edges.extend(keyed_edges)

    store.replace_file_rows(INDIRECTION_FILE, [], edges)
    return Enriched(
        nodes=0,
        edges=len(edges),
        keyed_call_groups=keyed_groups,
        keyed_call_sites=keyed_sites,
    )


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
    rules: tuple[KeyedCall, ...],
) -> tuple[
    list[dict[str, object]],
    tuple[tuple[Stamp, ...], ...],
    tuple[tuple[Stamp, ...], ...],
]:
    """CALLS edges whose target is a call's string key filled into ``target_template`` (222/361).

    Also returns, per (source, line, literal) site, the stamps every rule emitted for it (352): a
    literal two rules read differently is still one site, so it is counted once when neither links.
    """
    if not rules:
        return [], (), ()
    out: list[dict[str, object]] = []
    groups: list[tuple[Stamp, ...]] = []
    sites: dict[tuple[str, int, str], list[Stamp]] = {}
    seen: set[Stamp] = set()
    line_cache: dict[tuple[str, int], str | None] = {}
    for rule in rules:
        group: list[Stamp] = []
        for edge in _calls_for_setter(store, rule.setter):
            if edge.get("file_path") == INDIRECTION_FILE:
                continue
            source = str(edge.get("source_qname") or "")
            line = edge.get("line")
            rel = edge.get("file_path")
            if not source or type(line) is not int or not isinstance(rel, str) or not rel:
                continue
            for literal, values in _keyed_values(config, edge, rule, rel, line, line_cache):
                target = _fill(rule.template, values)
                if rule.kind != "CALLS" and contract.MEMBER_SEPARATOR in target:
                    continue  # a key that names a member: a table rule never writes a column
                stamp = (source, target, line, rule.kind)
                site = sites.setdefault((source, line, literal), [])
                if stamp not in site:
                    site.append(stamp)
                if stamp in seen:
                    continue
                seen.add(stamp)
                group.append(stamp)
                out.append(
                    {
                        "kind": rule.kind,
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
            str(row["kind"]),
        )
    )
    return out, tuple(groups), tuple(tuple(sites[site]) for site in sorted(sites))


def _keyed_values(
    config: Config,
    edge: dict[str, object],
    rule: KeyedCall,
    rel: str,
    line: int,
    line_cache: dict[tuple[str, int], str | None],
) -> list[tuple[str, dict[str, str]]]:
    """``(literal, placeholder values)`` this rule reads at one call site — none is invented (361).

    A string key is the whole literal, or what ``key_pattern`` finds in it (named groups, else
    group 1 as ``key``); an ``object`` key is the literal's string fields the template names.
    """
    args = edge.get("args")
    if rule.key_from == "object":
        parsed = _parse_args(args)
        if parsed is None or not 1 <= rule.key_arg <= len(parsed):
            return []
        if parsed[rule.key_arg - 1] != "array":
            return []
        text = _line_text(config.root, rel, line, line_cache)
        argument = (
            _call_argument(text, edge.get("target_raw"), rule.key_arg) if text is not None else None
        )
        if argument is None:
            return []
        fields = _literal_fields(argument)
        names = set(_TEMPLATE_PLACEHOLDER.findall(rule.template))
        if not names <= fields.keys():
            return []
        return [(argument, {name: fields[name] for name in names})]
    found = []
    for key in _keys_for_rule(
        config, edge, args, rule.key_arg, rule.key_from, rel, line, line_cache
    ):
        if rule.pattern is None:
            found.append((key, {"key": key}))
            continue
        match = rule.pattern.search(key)
        if match is None:
            continue
        if rule.pattern.groupindex:
            named = match.groupdict()
            if any(not value for value in named.values()):
                continue
            found.append((key, {name: str(value) for name, value in named.items()}))
        else:
            value = match.group(1) if rule.pattern.groups else match.group(0)
            if value:
                found.append((key, {"key": value}))
    return found


def _fill(template: str, values: dict[str, str]) -> str:
    """``template`` with each ``{name}`` replaced; the loader made every placeholder fillable."""
    return _TEMPLATE_PLACEHOLDER.sub(lambda match: values[match.group(1)], template)


def _literal_fields(argument: str) -> dict[str, str]:
    """The top-level ``name: 'value'`` string fields of one object/array literal argument.

    An entry is read only when it is exactly a name and one string literal, so a nested object,
    a concatenation or a ternary names nothing — never a guess (R5.2). First occurrence kept.
    """
    text = argument.strip()
    if len(text) < 2 or (text[0], text[-1]) not in (("{", "}"), ("[", "]")):
        return {}
    fields: dict[str, str] = {}
    for entry in _top_level_entries(text[1:-1]):
        match = _LITERAL_FIELD.fullmatch(entry)
        if match is None:
            continue
        value = _nth_string_literal(match.group(3), 1)
        if value is not None:
            fields.setdefault(match.group(2), value)
    return fields


def _top_level_entries(body: str) -> list[str]:
    """``body`` split at commas outside brackets and strings; ``[]`` when a string never closes."""
    entries: list[str] = []
    closers: list[str] = []
    start = index = 0
    while index < len(body):
        char = body[index]
        if char in "'\"":
            quoted = _STRING_LIT.match(body, index)
            if quoted is None:
                return []
            index = quoted.end()
            continue
        if char in _OPENERS:
            closers.append(_OPENERS[char])
        elif closers and char == closers[-1]:
            closers.pop()
        elif not closers and char == ",":
            entries.append(body[start:index])
            start = index + 1
        index += 1
    entries.append(body[start:])
    return entries


def count_unresolved_keyed_calls(store: GraphStore, groups: tuple[tuple[Stamp, ...], ...]) -> int:
    """Rules whose every emitted keyed_calls edge stayed unlinked after resolve (task 222 AC4)."""
    linked = _linked_stamps(store, {stamp for stamps in groups for stamp in stamps})
    return sum(1 for stamps in groups if stamps and not any(s in linked for s in stamps))


def count_unresolved_keyed_sites(store: GraphStore, sites: tuple[tuple[Stamp, ...], ...]) -> int:
    """Call sites whose string key linked under no keyed_calls rule (352).

    A literal naming nothing is counted once, however many rules tried it; one target query each.
    """
    linked = _linked_stamps(store, {stamp for stamps in sites for stamp in stamps})
    return sum(1 for stamps in sites if not any(stamp in linked for stamp in stamps))


def _linked_stamps(store: GraphStore, stamps: set[Stamp]) -> set[Stamp]:
    """The stamps whose own rule row — same source, target, line and kind — the resolver linked."""
    linked: set[Stamp] = set()
    for target_raw, kind in sorted({(stamp[1], stamp[3]) for stamp in stamps}):
        for row in store.edges_by_target_raw(target_raw, kinds=(kind,)):
            if row.get("file_path") == INDIRECTION_FILE and row.get("target_qname"):
                line = int(str(row.get("line")))
                linked.add((str(row.get("source_qname")), target_raw, line, kind))
    return linked & stamps


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
    argument = _call_argument(text, edge.get("target_raw"), key_arg) if text is not None else None
    if argument is None or _STRING_LIT.fullmatch(argument) is None:
        # Only an argument that is one whole literal names a key; `'a' . $b` names none.
        return []
    key = _nth_string_literal(argument, 1)
    return [key] if key is not None else []


def _call_argument(line: str, target_raw: object, position: int) -> str | None:
    """The source text of argument ``position`` of the one ``<callee>(`` call on ``line``.

    Split at top-level commas, so a literal before the call (a receiver's ``get('db')``) or inside
    an earlier argument is never read as the key. Two calls of one name on a line: ``None`` (352).
    """
    names = _IDENTIFIER.findall(str(target_raw or ""))
    if not names:
        return None
    opens = list(re.finditer(rf"(?<![\w$]){re.escape(names[-1])}\s*\(", line))
    if len(opens) != 1:
        return None
    arguments: list[str] = []
    closers: list[str] = []
    start = index = opens[0].end()
    while index < len(line):
        char = line[index]
        if char in "'\"":
            quoted = _STRING_LIT.match(line, index)
            if quoted is None:
                return None
            index = quoted.end()
            continue
        if char in _OPENERS:
            closers.append(_OPENERS[char])
        elif closers and char == closers[-1]:
            closers.pop()
        elif not closers and char in ",)":
            arguments.append(line[start:index].strip())
            if char == ")":
                return arguments[position - 1] if position <= len(arguments) else None
            start = index + 1
        index += 1
    return None


def _keys_from_arg_keys(arg_keys: object, args: object, key_arg: int) -> list[str]:
    """Keys from ``arg_keys[key_arg-1]`` when that arg is an array (task 063).

    Absent field, null slot, and ``[]`` all yield no keys here — edge emission cannot
    distinguish them. AC4's "not captured" vs "none found" is enforced by schema refusal
    of pre-v5 indexes; adapters advertise capture via the ``args`` R1.6 capability (231).
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
    list[KeyedCall],
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

    keyed_calls: list[KeyedCall] = []
    for item in _as_list(raw.get("keyed_calls"), label, "keyed_calls"):
        if not isinstance(item, dict):
            raise ConfigError(f"indirection_rules: {label!r} keyed_calls entries must be objects")
        keyed_calls.append(_keyed_call(item, label))

    return aliases, calls, view_data, keyed_calls


def _keyed_call(item: dict[str, Any], label: str) -> KeyedCall:
    """Validate one ``keyed_calls`` entry: every template placeholder must be fillable (R5.3)."""
    where = f"indirection_rules: {label!r} keyed_calls"
    setter = _as_qname(item.get("setter"), label, "keyed_calls.setter")
    key_arg = item.get("key_arg")
    if type(key_arg) is not int or key_arg < 1:
        raise ConfigError(f"{where}.key_arg must be an int >= 1")
    key_from = item.get("key_from", "string")
    if key_from not in ("string", "array_keys", "object"):
        raise ConfigError(f"{where}.key_from must be 'string', 'array_keys' or 'object'")
    template = item.get("target_template")
    if not isinstance(template, str) or not template.strip():
        raise ConfigError(f"{where}.target_template must be a non-empty string")
    template = template.strip()
    names = _TEMPLATE_PLACEHOLDER.findall(template)
    raw_pattern = item.get("key_pattern")
    pattern = None
    if raw_pattern is not None:
        if key_from == "object" or not isinstance(raw_pattern, str) or not raw_pattern:
            raise ConfigError(f"{where}.key_pattern must be a non-empty regex on a string key")
        try:
            pattern = re.compile(raw_pattern)
        except re.error as error:
            raise ConfigError(f"{where}.key_pattern does not compile ({error})") from error
    if key_from == "object":
        wanted = sorted(set(names))
        if not names or "key" in names:
            raise ConfigError(f"{where}.target_template needs placeholder(s) naming object fields")
    elif pattern is not None and pattern.groupindex:
        wanted = sorted(pattern.groupindex)
        if sorted(set(names)) != wanted:
            raise ConfigError(
                f"{where}.target_template placeholders {names!r} must be the key_pattern's "
                f"named groups {wanted!r}"
            )
    elif names != ["key"]:
        raise ConfigError(
            f"{where}.target_template must contain exactly the placeholder '{{key}}' "
            f"(found {names!r})"
        )
    kind = item.get("kind", "CALLS")
    if kind not in _KEYED_KINDS:
        raise ConfigError(f"{where}.kind must be one of {list(_KEYED_KINDS)}")
    if kind != "CALLS" and contract.MEMBER_SEPARATOR in template:
        # A rule names the table, never its columns: the write stays unmeasured (CONVENTION §3).
        raise ConfigError(f"{where}.target_template of a {kind} rule must name a Table, no member")
    return KeyedCall(setter, key_arg, key_from, template, pattern, kind)


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
