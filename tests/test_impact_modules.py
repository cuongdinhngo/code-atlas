"""Task 140: the blast radius, answered in the shape the decision has.

`impact` answers in symbols and the decision is module-shaped — *which modules does this change
reach, how many symbols in each, which one edge do I read first*. Today that is a 500-row list the
reader aggregates by hand, and the aggregation is the whole answer.

The rollup is a **join**, not a second model: it uses 114's module table verbatim (PLAN §1's shared
constraint), and it never invents a home for a file the table does not cover.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tokens import estimate_tokens
from code_atlas.tools import generate_onboarding, impact, impact_modules
from tests.php_adapter_cli import ENTRY, PHP, ROOT, needs_php

FIXTURE = ROOT / "tests" / "fixtures" / "php" / "impact_modules"
SUBJECT = "\\Fx\\Billing\\Invoice::total"


@pytest.fixture
def repo(tmp_path: Path):
    """Index the capability-layout fixture once; hand back its Config."""
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"]),
        },
    )
    with GraphStore(db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
    return config


def _rows(payload: dict[str, object]) -> list[dict[str, object]]:
    results = payload["results"]
    assert isinstance(results, list)
    return [row for row in results if isinstance(row, dict)]


@needs_php
def test_ac1_the_per_module_counts_sum_to_the_symbol_population(repo) -> None:
    """127's arithmetic guard: a rollup that does not add up is a summary of nothing."""
    rolled = impact_modules.create(repo)(qnames=[SUBJECT])
    symbols = impact.create(repo)(qnames=[SUBJECT])

    rows = _rows(rolled)
    assert len({str(row["module"]) for row in rows}) >= 3
    assert sum(int(str(row["symbols"])) for row in rows) == len(_rows(symbols))
    assert rolled["symbols_total"] == len(_rows(symbols))


@needs_php
def test_ac1_a_module_is_split_by_tier_because_only_heuristic_is_a_different_fact(repo) -> None:
    """136: a module reached only through guesses has not been shown to be reached."""
    rows = {str(row["module"]): row for row in _rows(impact_modules.create(repo)(qnames=[SUBJECT]))}
    catalog = rows["catalog"]
    tiers = catalog["by_tier"]
    assert isinstance(tiers, dict)
    # Catalog reaches the subject twice: once through a typed receiver, once through a guess.
    assert tiers["RESOLVED"] == 1
    assert tiers["HEURISTIC"] == 1
    assert sum(int(v) for v in tiers.values()) == int(str(catalog["symbols"]))


@needs_php
def test_ac6_a_file_no_module_covers_gets_its_own_bucket(repo) -> None:
    """113: never fold four populations into one number, and never invent a home for a file."""
    rows = {str(row["module"]): row for row in _rows(impact_modules.create(repo)(qnames=[SUBJECT]))}
    assert impact_modules.UNASSIGNED in rows
    unassigned = rows[impact_modules.UNASSIGNED]
    assert unassigned["assigned"] is False
    assert all(
        row["assigned"] is True
        for name, row in rows.items()
        if name != impact_modules.UNASSIGNED
    )


@needs_php
def test_ac3_the_module_names_are_the_ones_the_map_actually_prints(repo) -> None:
    """The join, asserted against the map itself — not against a re-derivation of it.

    `generate_onboarding` builds its table with the real per-file `fan_in`; the tool passes none,
    because fan-in feeds only `hub`/`hub_fan_in`. Comparing the two is what turns that from a
    comment into a checked fact, and it is the only version of this assertion that can fail if the
    two ever stop being the same table (PLAN §1: same graph, no second pipeline).
    """
    generate_onboarding.create(repo)()
    artifact = json.loads(
        (Path(repo.root) / ".code-atlas" / "onboarding" / "artifact.json").read_text(
            encoding="utf-8"
        )
    )
    published = artifact["summary"]["business_modules"]["modules"]
    printed = [str(module["module"]) for module in published]
    assert printed, "the map printed no modules — this assertion would pass vacuously"

    rows = _rows(impact_modules.create(repo)(qnames=[SUBJECT]))
    named = {str(row["module"]) for row in rows if row["assigned"]}
    assert named
    assert named <= set(printed), f"{named - set(printed)} is a name the map never prints"


@needs_php
def test_ac2_a_truncated_module_table_says_the_unassigned_bucket_is_over_counted(repo) -> None:
    """The *second* bound. 114's table is capped at `max_results`, and a file whose module was cut
    lands in `unassigned` — so silence there would report a module that exists as no module at all,
    in the one bucket this tool promised never to guess into (113)."""
    import dataclasses

    narrow = dataclasses.replace(repo, page_limit=2)
    payload = impact_modules.create(narrow)(qnames=[SUBJECT])
    assert payload["module_table_truncated"] is True
    assert impact_modules.NOTE_TABLE_TRUNCATED in str(payload["note"])

    rows = {str(row["module"]): row for row in _rows(payload)}
    assert impact_modules.UNASSIGNED in rows
    # The cut modules' symbols are in `unassigned`, not silently absent from the total.
    assert payload["symbols_total"] == sum(int(str(row["symbols"])) for row in rows.values())

    full = impact_modules.create(repo)(qnames=[SUBJECT])
    assert full["module_table_truncated"] is False


@needs_php
def test_ac2_a_truncated_walk_says_the_rollup_is_an_under_estimate(repo) -> None:
    """124's vocabulary: a bounded walk that reports a total without saying so is a false total."""
    import dataclasses

    tight = dataclasses.replace(repo, impact_max_nodes=2)
    payload = impact_modules.create(tight)(qnames=[SUBJECT])
    assert payload["walk_truncated"] is True
    assert impact_modules.NOTE_UNDER_ESTIMATE in str(payload["note"])

    full = impact_modules.create(repo)(qnames=[SUBJECT])
    assert full["walk_truncated"] is False
    assert "note" not in full


@needs_php
def test_ac5_identical_index_yields_identical_rows(repo) -> None:
    """R4.2 — byte-identical, not merely equal-as-sets."""
    once = impact_modules.create(repo)(qnames=[SUBJECT])
    twice = impact_modules.create(repo)(qnames=[SUBJECT])
    assert json.dumps(once, sort_keys=False) == json.dumps(twice, sort_keys=False)


@needs_php
def test_minimal_is_a_subset_and_standard_adds_the_exemplar(repo) -> None:
    """CONVENTION §6: `minimal` is always a subset, never a superset."""
    minimal = impact_modules.create(repo)(qnames=[SUBJECT], detail_level="minimal")
    standard = impact_modules.create(repo)(qnames=[SUBJECT], detail_level="standard")
    assert set(minimal) <= set(standard)
    assert all("exemplar" not in row for row in _rows(minimal))
    for row in _rows(standard):
        assert ":" in str(row["exemplar"])


@needs_php
def test_ac4_the_rollup_is_cheaper_than_the_symbol_answer_it_summarises(repo) -> None:
    """A number, not a claim (the benchmark records it; this keeps it from silently reversing)."""
    rolled = estimate_tokens(json.dumps(impact_modules.create(repo)(qnames=[SUBJECT])))
    symbols = estimate_tokens(json.dumps(impact.create(repo)(qnames=[SUBJECT])))
    assert rolled < symbols, f"rollup {rolled} tokens is not cheaper than {symbols}"


@needs_php
def test_a_repo_with_no_capability_layout_says_so_instead_of_reading_as_a_miss(
    tmp_path: Path,
) -> None:
    """114 refuses a role-organised tree on purpose. A lone `unassigned` row would read as a bug,
    so the answer names which of the two it is."""
    flat = tmp_path / "flat"
    flat.mkdir()
    shutil.copytree(FIXTURE / "src" / "billing", flat, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=flat, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=flat, check=True, capture_output=True)
    db_path = flat / ".code-atlas" / "graph.db"
    config = load_config(
        flat,
        {
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"]),
        },
    )
    with GraphStore(db_path) as store:
        assert full_build(config, store).failed == 0

    payload = impact_modules.create(config)(qnames=[SUBJECT])
    assert _rows(payload), "the walk must still find symbols; only the module table is absent"
    assert {str(row["module"]) for row in _rows(payload)} == {impact_modules.UNASSIGNED}
    assert impact_modules.NOTE_NO_MODULE_TABLE in str(payload["note"])
