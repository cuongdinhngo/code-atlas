"""Task 379 — per-tool est. tokens against an est. grep+Read baseline, beside the fit counts.

Counts only, in `meta`; read through `get_index_status(verbose)`; never in a nav payload. The
number is an estimate against a modelled baseline — never the fixture or sample tier.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.store import COST_KEY_PREFIX, GraphStore, close_fit_connections
from code_atlas.tokens import estimate_tokens
from code_atlas.tools import file_outline, fit, get_index_status, read_symbol, search_symbol
from tests.test_nav_tools import node, seed_file

PATH = "src/Billing.php"
QNAME = "\\App\\Billing"
BODY = (
    "<?php\nnamespace App;\nclass Billing\n{\n"
    "    public function total(): int { return 1; }\n}\n"
)


@pytest.fixture(autouse=True)
def _drop_counter_handles():
    yield
    close_fit_connections()


def _indexed(tmp_path: Path):
    config = load_config(tmp_path, {"CA_DB_PATH": str(tmp_path / ".code-atlas" / "graph.db")})
    with GraphStore(config.db_path) as store:
        row = node("Class", "Billing", QNAME, PATH)
        row["line_start"], row["line_end"] = 3, 6
        seed_file(store, PATH, [row], [], root=tmp_path)
    (tmp_path / PATH).write_text(BODY, encoding="utf-8")
    with GraphStore(config.db_path) as store:  # the planted hash must match the real bytes
        store.upsert_file(PATH, hashlib.sha256(BODY.encode()).hexdigest(), "lang")
    return config


def _costs(config) -> list[dict[str, object]]:
    close_fit_connections()
    with GraphStore(config.db_path) as store:
        return store.list_cost_counts()


def test_a_read_records_its_tokens_and_the_cited_file_and_doubles(tmp_path: Path) -> None:
    """379 AC1 — baseline = ceil(file bytes / 4), response = estimate_tokens of the result."""
    config = _indexed(tmp_path)
    tool = fit.wrap("read_symbol", config, read_symbol.create(config))
    result = tool(QNAME)
    assert result["reason"] == "ok"
    response = estimate_tokens(json.dumps(result, sort_keys=True, default=str, ensure_ascii=False))
    baseline = -(-len(BODY.encode()) // 4)
    one = {"tool": "read_symbol", "calls": 1, "cited_calls": 1,
           "response_tokens": response, "baseline_tokens": baseline}
    assert _costs(config) == [one]
    tool(QNAME)
    assert _costs(config) == [{**one, **{k: 2 * int(v) for k, v in one.items() if k != "tool"}}]


def test_a_miss_counts_its_response_against_nothing(tmp_path: Path) -> None:
    """Scope 1 — an answer that cites no file pays its response for a zero baseline."""
    config = _indexed(tmp_path)
    fit.wrap("search_symbol", config, search_symbol.create(config))("zzzxqyvblarg")
    (row,) = _costs(config)
    assert (row["calls"], row["cited_calls"], row["baseline_tokens"]) == (1, 0, 0)
    assert int(str(row["response_tokens"])) > 0


def test_a_miss_that_echoes_its_path_cites_nothing(tmp_path: Path) -> None:
    """379 review — red before: a `file_outline` miss on an unindexed file was credited it."""
    config = _indexed(tmp_path)
    (tmp_path / "big_unindexed.txt").write_text("x" * 40_000, encoding="utf-8")
    result = fit.wrap("file_outline", config, file_outline.create(config))("big_unindexed.txt")
    assert result["found"] is False
    (row,) = _costs(config)
    assert (row["cited_calls"], row["baseline_tokens"]) == (0, 0)


def test_counting_changes_no_payload(tmp_path: Path) -> None:
    """379 AC2 — nav payloads equal with counting on and off; status `standard` stays still."""
    config = _indexed(tmp_path)
    bare = read_symbol.create(config)
    counted = fit.wrap("read_symbol", config, read_symbol.create(config))
    assert counted(QNAME) == bare(QNAME) == counted(QNAME)
    status = get_index_status.create(config, ())
    first = json.dumps(status(detail_level="standard"), sort_keys=True)
    counted(QNAME)
    assert json.dumps(status(detail_level="standard"), sort_keys=True) == first
    verbose = status(detail_level="verbose")
    assert verbose[fit.EST_TOKENS_FIELD][0]["calls"] == 3
    assert "est. grep+Read baseline" in verbose[fit.EST_TOKENS_NOTE_FIELD]
    assert "not the fixture or sample tier" in verbose[fit.EST_TOKENS_NOTE_FIELD].lower()


def test_no_key_names_a_subject_and_the_fit_reset_clears_them(tmp_path: Path) -> None:
    """379 AC3 — keys hold a tool and a field, never a qname or a path; reset with fit."""
    config = _indexed(tmp_path)
    fit.wrap("read_symbol", config, read_symbol.create(config))(QNAME)
    close_fit_connections()
    with GraphStore(config.db_path) as store:
        keys = [k for (k,) in store._conn.execute("SELECT key FROM meta WHERE key LIKE 'cost:%'")]
    assert keys and all(k.startswith(COST_KEY_PREFIX + "read_symbol|") for k in keys)
    assert not any("Billing" in k or "src/" in k for k in keys)
    get_index_status.create(config, ())(reset_fit_counts=True)
    assert _costs(config) == []


def test_only_repo_files_are_cited_first_twenty_in_payload_order(tmp_path: Path) -> None:
    for index in range(25):
        (tmp_path / f"f{index:02}.py").write_text("x\n", encoding="utf-8")
    payload = {
        "results": [{"file": f"f{index:02}.py"} for index in reversed(range(25))],
        "path": "missing.py",
        "file_path": "../outside.py",
    }
    cited = fit.cited_files(tmp_path, payload)
    assert cited == [f"f{index:02}.py" for index in reversed(range(5, 25))]
    # A real file out of the root is refused by containment, not by a missing file (379 review).
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "outside.py").write_text("x\n", encoding="utf-8")
    (root / "inside.py").write_text("x\n", encoding="utf-8")
    absolute = str(tmp_path / "outside.py")
    outside = {"file_path": "../outside.py", "path": absolute, "file": "inside.py"}
    assert fit.cited_files(root, outside) == ["inside.py"]
