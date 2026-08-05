"""Optional framework-indirection enrichment from JSON rules (task 040).

Rules live **outside** ``adapters/`` (R2.2). The core applies them generically — no
``if framework == …`` (R1.1). Off when ``config.indirection_rules`` is unset.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from code_atlas import contract
from code_atlas.config import Config, ConfigError
from code_atlas.store import GraphStore

# Synthetic path holding rule-emitted rows; replaced each build, dropped when rules are off.
INDIRECTION_FILE = ".code-atlas/indirection-rules"

_HEURISTIC = contract.CONFIDENCE_TIERS[1]


def apply_indirection_rules(config: Config, store: GraphStore) -> None:
    """Load configured rule files and replace synthetic ALIASES/CALLS rows (HEURISTIC)."""
    paths = config.indirection_rules
    if not paths:
        if INDIRECTION_FILE in store.file_paths():
            store.remove_file(INDIRECTION_FILE)
        return

    aliases: list[tuple[str, str]] = []
    calls: list[tuple[str, str, int]] = []
    for relative in paths:
        full = config.root / relative
        if not full.is_file():
            raise ConfigError(f"indirection_rules: {relative!r} is not a file under {config.root}")
        payload = _load_rules(relative, full)
        aliases.extend(payload[0])
        calls.extend(payload[1])

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
    for source, target in aliases:
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
    for source, target, line in calls:
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

    digest = _rules_digest(paths, config.root)
    store.upsert_file(INDIRECTION_FILE, digest, "rules", parsed_ok=True)
    store.replace_file_rows(INDIRECTION_FILE, nodes, edges)


def _load_rules(
    label: str, path: Path
) -> tuple[list[tuple[str, str]], list[tuple[str, str, int]]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
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
        if not isinstance(line, int) or line < 1:
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


def _rules_digest(paths: Sequence[str], root: Path) -> str:
    """Stable hash of configured rule file bytes (order-independent content)."""
    import hashlib

    hasher = hashlib.sha256()
    for relative in sorted(paths):
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update((root / relative).read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()
