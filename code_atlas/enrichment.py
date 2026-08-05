"""Optional framework-indirection enrichment from JSON rules (task 040).

Rules live **outside** ``adapters/`` (R2.2). The core applies them generically — no
``if framework == …`` (R1.1). Off when ``config.indirection_rules`` is unset.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from code_atlas import contract
from code_atlas.config import Config, ConfigError
from code_atlas.store import GraphStore

# Synthetic path holding rule-emitted rows; replaced each build, dropped when rules are off.
# Not a real on-disk file — tools must treat edges here as rule-derived (see edge_hit).
INDIRECTION_FILE = ".code-atlas/indirection-rules"

# files.language value — underscore-prefixed so it is never mistaken for a language handshake.
_RULES_LANGUAGE = "_rules"

_HEURISTIC = contract.CONFIDENCE_TIERS[1]


@dataclass(frozen=True, slots=True)
class RulesPayload:
    """Validated aliases/calls plus a content digest (load before parse; apply after)."""

    aliases: tuple[tuple[str, str], ...]
    calls: tuple[tuple[str, str, int], ...]
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

    return RulesPayload(
        aliases=tuple(aliases),
        calls=tuple(calls),
        digest=digester.hexdigest(),
    )


def apply_indirection_rules(
    config: Config, store: GraphStore, *, payload: RulesPayload | None = None
) -> None:
    """Replace synthetic ALIASES/CALLS rows from a (pre-)loaded payload, or clear when off."""
    if not config.indirection_rules:
        if INDIRECTION_FILE in store.file_paths():
            store.remove_file(INDIRECTION_FILE)
        return

    loaded = payload if payload is not None else load_indirection_rules(config)
    if loaded is None:
        return

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

    store.upsert_file(INDIRECTION_FILE, loaded.digest, _RULES_LANGUAGE, parsed_ok=True)
    store.replace_file_rows(INDIRECTION_FILE, nodes, edges)


def is_rule_edge_path(path: object) -> bool:
    """True when an edge ``file_path`` is the synthetic indirection bookmark."""
    return path == INDIRECTION_FILE


def _load_rules(
    label: str, raw_bytes: bytes
) -> tuple[list[tuple[str, str]], list[tuple[str, str, int]]]:
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

    return aliases, calls


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
