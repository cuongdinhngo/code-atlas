"""Task 308: changed-code → candidate test files (report only)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.candidate_tests import (
    DEFAULT_MAX_DEPTH,
    FULL_SUITE_STATEMENT,
    UNMEASURED_DEPTH_BOUND,
    UNMEASURED_NO_RUNNER,
    UNMEASURED_STALE,
    UNMEASURED_TRUNCATED,
    UNMEASURED_UNINDEXED,
    UNMEASURED_UNLINKED,
    assert_no_selective_language,
    build_candidate_test_report,
    render_candidate_tests_json,
    render_candidate_tests_text,
    report_as_dict,
)
from code_atlas.store import LAST_COMMIT_KEY, LAST_REF_KEY, GraphStore
from tests.test_nav_tools import db_config, edge, node, seed_file

PROD = "src/Service.aa"
TEST = "tests/ServiceTest.aa"
OTHER = "src/Other.aa"


def _plant(tmp_path: Path, *, heuristic: bool = False, import_only: bool = False):
    config = replace(db_config(tmp_path), root=tmp_path)
    tier = "HEURISTIC" if heuristic else "RESOLVED"
    kind = "IMPORTS" if import_only else "CALLS"
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            PROD,
            [node("Function", "run", "\\App\\run", PROD)],
            [],
            root=tmp_path,
        )
        seed_file(
            store,
            OTHER,
            [node("Function", "other", "\\App\\other", OTHER)],
            [
                edge(
                    "CALLS",
                    "\\App\\other",
                    "\\App\\run",
                    OTHER,
                    target_qname="\\App\\run",
                    tier="RESOLVED",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            TEST,
            [node("Function", "test_run", "\\Tests\\test_run", TEST,)],
            [
                edge(
                    kind,
                    "\\Tests\\test_run",
                    "\\App\\run",
                    TEST,
                    target_qname="\\App\\run",
                    tier=tier,
                )
            ],
            root=tmp_path,
        )
        # Force adapter is_test on the test symbol (path convention also matches).
        store._conn.execute(
            "UPDATE nodes SET is_test = 1 WHERE file_path = ?", (TEST,)
        )
        store._conn.commit()
    return config


def test_planted_test_caller_listed_with_edge_evidence(tmp_path: Path) -> None:
    config = _plant(tmp_path)
    report = build_candidate_test_report(config, changed_indexed=[PROD])
    assert len(report.candidates) == 1
    row = report.candidates[0]
    assert row.test_path == TEST
    assert row.edge_kind == "CALLS"
    assert row.confidence_tier == "RESOLVED"
    assert row.source_qname == "\\Tests\\test_run"
    assert row.target_qname == "\\App\\run"
    assert row.hop_distance == 1
    assert FULL_SUITE_STATEMENT in report.statement
    assert UNMEASURED_NO_RUNNER in report.unmeasured


def test_production_caller_not_mislabeled_as_test(tmp_path: Path) -> None:
    config = _plant(tmp_path)
    report = build_candidate_test_report(config, changed_indexed=[PROD])
    paths = {row.test_path for row in report.candidates}
    assert OTHER not in paths
    assert all(row.test_role_source in {"adapter", "path_convention"} for row in report.candidates)


def test_import_and_heuristic_labelled(tmp_path: Path) -> None:
    config = _plant(tmp_path, heuristic=True, import_only=True)
    report = build_candidate_test_report(config, changed_indexed=[PROD])
    assert report.candidates[0].edge_kind == "IMPORTS"
    assert report.candidates[0].confidence_tier == "HEURISTIC"
    text = render_candidate_tests_text(report)
    assert "IMPORTS/HEURISTIC" in text


def test_forced_paging_emits_truncated(tmp_path: Path) -> None:
    config = _plant(tmp_path)
    # Two inbound CALLS; max_edges=1 forces truncated_page while page_limit is the fetch size.
    report = build_candidate_test_report(
        config, changed_indexed=[PROD], page_limit=1, max_edges=1
    )
    assert UNMEASURED_TRUNCATED in report.unmeasured


def test_default_walk_keeps_test_caller_behind_production(tmp_path: Path) -> None:
    """Regression for challenger R2: do not drop test edges behind a production page slot."""
    config = _plant(tmp_path)
    report = build_candidate_test_report(config, changed_indexed=[PROD], page_limit=1)
    assert any(row.test_path == TEST for row in report.candidates)
    assert UNMEASURED_TRUNCATED not in report.unmeasured


def test_unindexed_change_emits_unmeasured(tmp_path: Path) -> None:
    config = _plant(tmp_path)
    report = build_candidate_test_report(
        config, changed_indexed=[PROD], dirty_unindexed=["src/New.aa"]
    )
    assert UNMEASURED_UNINDEXED in report.unmeasured


def test_unlinked_same_name_emits_unmeasured(tmp_path: Path) -> None:
    config = _plant(tmp_path)
    with GraphStore(config.db_path) as store:
        store._conn.execute(
            "INSERT INTO edges (kind, source_qname, target_qname, target_raw, "
            "file_path, line, confidence_tier) VALUES "
            "('CALLS', '\\Tests\\orphan', NULL, 'run', ?, 1, 'RESOLVED')",
            (TEST,),
        )
        store._conn.commit()
    report = build_candidate_test_report(config, changed_indexed=[PROD])
    assert UNMEASURED_UNLINKED in report.unmeasured


def test_outputs_carry_full_suite_statement_and_guard(tmp_path: Path) -> None:
    config = _plant(tmp_path)
    report = build_candidate_test_report(config, changed_indexed=[PROD])
    text = render_candidate_tests_text(report)
    payload = render_candidate_tests_json(report)
    assert "full suite remains authoritative" in text
    assert "full suite remains authoritative" in payload
    assert_no_selective_language(text)
    with pytest.raises(AssertionError):
        assert_no_selective_language("please skip these tests")


def test_byte_identical_ordering(tmp_path: Path) -> None:
    config = _plant(tmp_path)
    a = render_candidate_tests_json(
        build_candidate_test_report(config, changed_indexed=[PROD])
    )
    b = render_candidate_tests_json(
        build_candidate_test_report(config, changed_indexed=[PROD])
    )
    assert a == b


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_stale_index_emits_unmeasured_and_current_does_not(tmp_path: Path) -> None:
    """AC — a stale index is disclosed, and the reason is not simply always on."""
    config = _plant(tmp_path)
    # The index is a build artifact, not tracked content — otherwise writing meta dirties HEAD.
    (tmp_path / ".gitignore").write_text(f"{config.db_path.name}*\n", encoding="utf-8")
    _git(tmp_path, "init", "-q", ".")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()

    with GraphStore(config.db_path) as store:
        store.set_meta(LAST_COMMIT_KEY, head)
        store.set_meta(LAST_REF_KEY, "main")
    current = build_candidate_test_report(config, changed_indexed=[PROD])
    assert UNMEASURED_STALE not in current.unmeasured

    with GraphStore(config.db_path) as store:
        store.set_meta(LAST_COMMIT_KEY, "0" * 40)
    behind = build_candidate_test_report(config, changed_indexed=[PROD])
    assert UNMEASURED_STALE in behind.unmeasured


def test_the_embeddable_section_is_report_only(tmp_path: Path) -> None:
    """Scope 5 — any consumer embedding this section gets report-only wording, never a gate."""
    config = _plant_two_hop(tmp_path)
    section = report_as_dict(build_candidate_test_report(config, changed_indexed=[PROD]))
    assert section["mode"] == "report_only"
    assert section["statement"] == FULL_SUITE_STATEMENT
    assert_no_selective_language(json.dumps(section))


def _plant_two_hop(tmp_path: Path) -> object:
    """Changed ← façade (prod) ← test — the 309 miss shape at inbound depth 2."""
    config = replace(db_config(tmp_path), root=tmp_path)
    facade = "src/Facade.aa"
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            PROD,
            [node("Function", "run", "\\App\\run", PROD)],
            [],
            root=tmp_path,
        )
        seed_file(
            store,
            facade,
            [node("Function", "wrap", "\\App\\wrap", facade)],
            [
                edge(
                    "CALLS",
                    "\\App\\wrap",
                    "\\App\\run",
                    facade,
                    target_qname="\\App\\run",
                    tier="RESOLVED",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            TEST,
            [node("Function", "test_wrap", "\\Tests\\test_wrap", TEST)],
            [
                edge(
                    "CALLS",
                    "\\Tests\\test_wrap",
                    "\\App\\wrap",
                    TEST,
                    target_qname="\\App\\wrap",
                    tier="RESOLVED",
                )
            ],
            root=tmp_path,
        )
        store._conn.execute(
            "UPDATE nodes SET is_test = 1 WHERE file_path = ?", (TEST,)
        )
        store._conn.commit()
    return config


def _plant_three_hop(tmp_path: Path) -> object:
    """Changed ← mid1 ← mid2 ← test — beyond DEFAULT_MAX_DEPTH=2."""
    config = replace(db_config(tmp_path), root=tmp_path)
    mid1, mid2 = "src/Mid1.aa", "src/Mid2.aa"
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            PROD,
            [node("Function", "run", "\\App\\run", PROD)],
            [],
            root=tmp_path,
        )
        seed_file(
            store,
            mid1,
            [node("Function", "m1", "\\App\\m1", mid1)],
            [
                edge(
                    "CALLS",
                    "\\App\\m1",
                    "\\App\\run",
                    mid1,
                    target_qname="\\App\\run",
                    tier="RESOLVED",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            mid2,
            [node("Function", "m2", "\\App\\m2", mid2)],
            [
                edge(
                    "CALLS",
                    "\\App\\m2",
                    "\\App\\m1",
                    mid2,
                    target_qname="\\App\\m1",
                    tier="RESOLVED",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            TEST,
            [node("Function", "test_far", "\\Tests\\test_far", TEST)],
            [
                edge(
                    "CALLS",
                    "\\Tests\\test_far",
                    "\\App\\m2",
                    TEST,
                    target_qname="\\App\\m2",
                    tier="RESOLVED",
                )
            ],
            root=tmp_path,
        )
        store._conn.execute(
            "UPDATE nodes SET is_test = 1 WHERE file_path = ?", (TEST,)
        )
        store._conn.commit()
    return config


def test_two_hop_test_listed_below_direct_caller(tmp_path: Path) -> None:
    """AC1 — hop=2 candidate listed and ranked below every direct caller."""
    config = _plant_two_hop(tmp_path)
    # Also plant a direct RESOLVED caller so ranking is observable.
    with GraphStore(config.db_path) as store:
        direct = "tests/DirectTest.aa"
        seed_file(
            store,
            direct,
            [node("Function", "test_direct", "\\Tests\\test_direct", direct)],
            [
                edge(
                    "CALLS",
                    "\\Tests\\test_direct",
                    "\\App\\run",
                    direct,
                    target_qname="\\App\\run",
                    tier="RESOLVED",
                )
            ],
            root=tmp_path,
        )
        store._conn.execute(
            "UPDATE nodes SET is_test = 1 WHERE file_path = ?", (direct,)
        )
        store._conn.commit()
    report = build_candidate_test_report(config, changed_indexed=[PROD])
    assert len(report.candidates) == 2
    assert report.candidates[0].hop_distance == 1
    assert report.candidates[0].test_path == "tests/DirectTest.aa"
    assert report.candidates[1].hop_distance == 2
    assert report.candidates[1].test_path == TEST
    assert report.candidates[1].target_qname == "\\App\\run"
    text = render_candidate_tests_text(report)
    assert "hop=2" in text
    payload = render_candidate_tests_json(report)
    assert '"hop_distance": 2' in payload


def test_beyond_depth_bound_emits_unmeasured_and_omits_test(tmp_path: Path) -> None:
    """AC2 — a hop-3 test is absent and depth_bound is disclosed (R6.8)."""
    config = _plant_three_hop(tmp_path)
    report = build_candidate_test_report(config, changed_indexed=[PROD])
    assert all(row.test_path != TEST for row in report.candidates)
    assert UNMEASURED_DEPTH_BOUND in report.unmeasured


def test_hop_distance_reaches_every_consumer(tmp_path: Path) -> None:
    """AC3 — the embeddable section and the text surface both carry the hop distance."""
    config = _plant_two_hop(tmp_path)
    report = build_candidate_test_report(config, changed_indexed=[PROD])
    section = report_as_dict(report)
    assert all("hop_distance" in row for row in section["candidates"])  # type: ignore[union-attr]
    assert "hop=2" in render_candidate_tests_text(report)


def test_depth_one_reproduces_the_308_walk(tmp_path: Path) -> None:
    """AC1 boundary — max_depth=1 lists only direct callers and still discloses the bound."""
    config = _plant_two_hop(tmp_path)
    report = build_candidate_test_report(config, changed_indexed=[PROD], max_depth=1)
    assert [row.hop_distance for row in report.candidates] == []
    assert UNMEASURED_DEPTH_BOUND in report.unmeasured
    widened = build_candidate_test_report(config, changed_indexed=[PROD])
    assert [row.test_path for row in widened.candidates] == [TEST]


def test_max_depth_below_one_is_rejected(tmp_path: Path) -> None:
    """A zero/negative bound would silently return an empty report instead of failing."""
    config = _plant_two_hop(tmp_path)
    with pytest.raises(ValueError):
        build_candidate_test_report(config, changed_indexed=[PROD], max_depth=0)
    assert DEFAULT_MAX_DEPTH == 2
