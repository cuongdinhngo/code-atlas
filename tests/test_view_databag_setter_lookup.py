"""PR #75 follow-up: view_data enrichment must not stop at a CALLS-prefix cap."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import load_config
from code_atlas.enrichment import apply_indirection_rules
from code_atlas.store import GraphStore

NOISE = 12_000
HANDLER = "\\App\\Late::publish"
SETTER_FILE = "late.php"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def test_view_data_finds_setter_past_former_10k_calls_prefix(
    tmp_path: Path, store: GraphStore
) -> None:
    """Noise CALLS before the publish site must not hide ``setData`` (indexed lookup)."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "rules.json").write_text(
        json.dumps(
            {"view_data": [{"setter": "setData", "key_arg": 1, "key_from": "array_keys"}]}
        ),
        encoding="utf-8",
    )
    config = replace(
        load_config(tmp_path, {"CA_INDIRECTION_RULES": "rules/rules.json"}),
        db_path=tmp_path / "graph.db",
        page_limit=50,
    )

    noise = [
        {
            "kind": "CALLS",
            "source_qname": f"\\Noise::m{i}",
            "target_raw": "other",
            "file_path": SETTER_FILE,
            "line": i + 1,
            "confidence_tier": "HEURISTIC",
            "args": ["string"],
        }
        for i in range(NOISE)
    ]
    publish = {
        "kind": "CALLS",
        "source_qname": HANDLER,
        "target_raw": "setData",
        "file_path": SETTER_FILE,
        "line": NOISE + 1,
        "confidence_tier": "HEURISTIC",
        "args": ["array"],
        "arg_keys": [["items", "title"]],
    }
    store.upsert_file(SETTER_FILE, "seed", "php", parsed_ok=True)
    store.replace_file_rows(
        SETTER_FILE,
        [
            {
                "kind": "Method",
                "name": "publish",
                "qualified_name": HANDLER,
                "file_path": SETTER_FILE,
                "line_start": NOISE + 1,
                "line_end": NOISE + 1,
            }
        ],
        [*noise, publish],
    )

    # Old scan took max(10_000, 50*200)=10_000 CALLS ordered by source_qname — ``\\Noise``
    # sorts before ``\\App``, so the publish site was invisible.
    assert store.edges_matching_kind("CALLS", limit=10_000)[-1]["source_qname"].startswith(
        "\\Noise"
    )

    enriched = apply_indirection_rules(config, store)
    assert enriched.edges >= 2
    keys = {
        row["target_raw"]
        for row in store.edges_by_source(HANDLER, kinds=(contract.PROVIDES_VIEW_DATA,), limit=10)
    }
    assert keys == {
        contract.VIEW_DATA_PREFIX + "items",
        contract.VIEW_DATA_PREFIX + "title",
    }
