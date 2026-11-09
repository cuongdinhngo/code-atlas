"""Task 441 — the first eight ``compute`` templates: each one's answer, caveat, empty result with
its reason, and truncation with a truthful ``total_count``.

The graph is written straight through the store — two languages, every tier, a test file, two
version folders — so each template has a known answer; nothing here depends on an adapter.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from code_atlas.config import Config, ConfigError, load_config
from code_atlas.enrichment import DEFINITION_ORDER_META_KEY
from code_atlas.store import GraphStore
from code_atlas.tools import compute

R, H, D = "RESOLVED", "HEURISTIC", "DYNAMIC"
SOURCES = {
    "app/web/a.php": "class Repo { save saveAsync } class Orphan helper fetch fetchAsync dup\n",
    "app/lib/b.php": "lib_fn class Lonely dup\n",
    "tests/test_repo.php": "test_save\n",
    "db/V1__p.sql": "create procedure Proc\n",
    "db/V2__p.sql": "create procedure Proc\n",
    "db/tables.sql": "create table Orders; create table Unused\n",
}


def node(kind: str, qname: str, file: str, line: int, *, test: bool = False) -> dict[str, Any]:
    name = qname.rsplit("::", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[-1]
    return {"kind": kind, "name": name, "qualified_name": qname, "file_path": file,
            "line_start": line, "line_end": line, "is_test": 1 if test else 0}


def edge(kind: str, source: str, target: str | None, file: str, line: int, tier: str,
         raw: str | None = None) -> dict[str, Any]:
    return {"kind": kind, "source_qname": source, "target_qname": target,
            "target_raw": raw or target, "file_path": file, "line": line, "confidence_tier": tier}


A, B, T = "app/web/a.php", "app/lib/b.php", "tests/test_repo.php"
GRAPH: dict[str, tuple[str, list[dict[str, Any]], list[dict[str, Any]]]] = {
    A: ("php", [
        node("Class", "\\App\\Repo", A, 1),
        node("Method", "\\App\\Repo::save", A, 2),
        node("Method", "\\App\\Repo::saveAsync", A, 3),
        node("Class", "\\App\\Orphan", A, 4),
        node("Function", "\\App\\helper", A, 5),
        node("Function", "\\App\\fetch", A, 6),
        node("Function", "\\App\\fetchAsync", A, 7),
        node("Function", "\\App\\dup", A, 8),
        node("Namespace", "\\App", A, 1),
    ], [
        edge("CALLS", "\\App\\helper", "\\App\\Repo::save", A, 5, R),
        edge("CALLS", "\\App\\helper", "\\App\\fetchAsync", A, 5, R),
        edge("CALLS", "\\App\\helper", None, A, 5, H, raw="mystery"),
        edge("WRITES", "\\App\\helper", "dbo.Orders", A, 5, R),
        edge("INCLUDES", A, B, A, 1, R),
        edge("INCLUDES", A, None, A, 1, D, raw="$path"),
    ]),
    B: ("php", [
        node("Function", "\\App\\lib_fn", B, 1),
        node("Class", "\\App\\Lonely", B, 2),
        node("Class", "\\App\\Covered", B, 4),
        node("Function", "\\App\\dup", B, 3),
        node("Namespace", "\\App", B, 1),
    ], [
        edge("CALLS", "\\App\\lib_fn", "\\App\\Repo::save", B, 1, H),
    ]),
    T: ("php", [node("Function", "\\Tests\\test_save", T, 1, test=True)], [
        edge("CALLS", "\\Tests\\test_save", "\\App\\Repo::save", T, 1, R),
        edge("INCLUDES", T, A, T, 1, R),
        edge("NEW", T, "\\App\\Covered", T, 2, R),  # module level: no test symbol is its source
    ]),
    "db/V1__p.sql": ("sql", [node("Function", "dbo.Proc", "db/V1__p.sql", 1)], []),
    "db/V2__p.sql": ("sql", [node("Function", "dbo.Proc", "db/V2__p.sql", 1)], []),
    "db/tables.sql": ("sql", [
        node("Table", "dbo.Orders", "db/tables.sql", 1),
        node("Table", "dbo.Unused", "db/tables.sql", 2),
    ], []),
}
MODULES = {"app/web": "web", "app/lib": "lib", "tests": "tests", "db": "db"}


def _build(root: Path, *, order: list[str] | None = None) -> Config:
    for rel, body in SOURCES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    for args in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    config = load_config(root, {})
    with GraphStore(config.db_path) as store:
        for path, (language, nodes, edges) in GRAPH.items():
            store.upsert_file(path, "h", language)
            store.replace_file_rows(path, nodes, edges)
        if order is not None:
            store.set_meta(DEFINITION_ORDER_META_KEY, json.dumps(order))
    return config


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return _build(tmp_path_factory.mktemp("catalogue"))


@pytest.fixture(scope="module")
def ordered(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return _build(tmp_path_factory.mktemp("ordered"), order=["db/V<n>__*.sql"])


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fixture this small has no business-module table; the rollup is tested on a given one."""
    monkeypatch.setattr(compute, "module_owners", lambda store, config: (MODULES, False))


def ask(config: Config, template: str, limit: int | None = None, **params: str) -> dict[str, Any]:
    return compute.create(config)(template=template, params=params, limit=limit)


def by(rows: list[dict[str, Any]], key: str) -> dict[Any, dict[str, Any]]:
    return {row[key]: row for row in rows}


# ------------------------------------------------------------------ the answers (AC1)
def test_tier_mix_splits_each_kind_by_language_pair(repo: Config) -> None:
    rows = ask(repo, "tier_mix")["rows"]
    cross = [r for r in rows if r["edge_kind"] == "WRITES"]
    assert cross == [{"edge_kind": "WRITES", "source_language": "php", "target_language": "sql",
                      "tier": R, "edges": 1}]
    unlinked = [r for r in rows if r["edge_kind"] == "CALLS" and r["target_language"] is None]
    assert unlinked == [{"edge_kind": "CALLS", "source_language": "php", "target_language": None,
                         "tier": H, "edges": 1}]


def test_unreferenced_objects_counts_only_referrers_in_the_language(repo: Config) -> None:
    from_php = ask(repo, "unreferenced_objects", kind="Table", language="php")
    assert [r["qname"] for r in from_php["rows"]] == ["dbo.Unused"]
    from_sql = ask(repo, "unreferenced_objects", kind="Table", language="sql")
    assert [r["qname"] for r in from_sql["rows"]] == ["dbo.Orders", "dbo.Unused"]
    assert set(from_sql["evidence_levels"]) == {
        "no_edge_no_mention", "no_edge_but_mentioned", "mention_unchecked"
    }


def test_calls_by_module_groups_calls_into_the_target(repo: Config, modules: None) -> None:
    answer = ask(repo, "calls_by_module", target="*Repo::save")
    assert by(answer["rows"], "module") == {
        "web": {"module": "web", "calls": 1, "resolved": 1, "files": 1},
        "lib": {"module": "lib", "calls": 1, "resolved": 0, "files": 1},
        "tests": {"module": "tests", "calls": 1, "resolved": 1, "files": 1},
    }
    by_kind = ask(repo, "calls_by_module", target_kind="Function")
    assert [r["module"] for r in by_kind["rows"]] == ["web"]  # fetchAsync


def test_calls_by_module_without_a_module_table_says_unassigned(repo: Config) -> None:
    answer = ask(repo, "calls_by_module", target="*Repo::save")
    assert [r["module"] for r in answer["rows"]] == ["unassigned"]


def test_untested_classes_names_types_no_test_reaches(repo: Config, modules: None) -> None:
    answer = ask(repo, "untested_classes")
    assert [r["qname"] for r in answer["rows"]] == ["\\App\\Lonely", "\\App\\Orphan"]
    assert answer["by_module"]["web"] == {"types": 2, "untested": 1}  # Repo via Repo::save
    assert answer["by_module"]["lib"] == {"types": 2, "untested": 1}  # Covered: a test file's edge


def test_resolved_share_per_module(repo: Config, modules: None) -> None:
    rows = by(ask(repo, "resolved_share")["rows"], "module")
    assert rows["web"]["calls"] == 3 and rows["web"]["resolved"] == 2
    assert rows["web"]["unlinked"] == 1 and rows["web"]["share"] == 0.6667
    assert rows["lib"]["share"] == 0.0


def test_includes_by_dir_counts_each_top_directory(repo: Config) -> None:
    rows = by(ask(repo, "includes_by_dir")["rows"], "dir")
    assert rows["app"] == {"dir": "app", "includes": 2, "resolved": 1, "dynamic": 1, "unlinked": 1}
    assert rows["tests"]["includes"] == 1


def test_multi_defined_names_the_live_definition_from_the_declared_order(ordered: Config) -> None:
    rows = by(ask(ordered, "multi_defined")["rows"], "qname")
    assert rows["dbo.Proc"]["live"] == {"file": "db/V2__p.sql", "line": 1}
    assert rows["dbo.Proc"]["live_state"] == "live"
    assert rows["\\App\\dup"]["live_state"] == "unknown"  # the order names no glob it matches
    assert rows["\\App\\dup"]["why_unknown"] == "order_does_not_decide"


def test_multi_defined_is_one_object_per_kind_and_qname(repo: Config) -> None:
    """443 A6: a namespace each file re-declares is no object; `language` scopes, `kind` asks."""
    rows = by(ask(repo, "multi_defined")["rows"], "qname")
    assert "\\App" not in rows and rows["dbo.Proc"]["kind"] == "Function"
    assert [r["qname"] for r in ask(repo, "multi_defined", language="sql")["rows"]] == ["dbo.Proc"]
    spanning = ask(repo, "multi_defined", kind="Namespace")
    assert [(r["qname"], r["definitions"]) for r in spanning["rows"]] == [("\\App", 2)]


def test_ac2_multi_defined_without_an_order_never_guesses(repo: Config) -> None:
    """AC2: no 437 order rule — the live definition is unknown, and the answer says why."""
    answer = ask(repo, "multi_defined")
    assert {r["qname"] for r in answer["rows"]} == {"\\App\\dup", "dbo.Proc"}
    for row in answer["rows"]:
        assert row["live"] is None and row["live_state"] == "unknown"
        assert row["why_unknown"] == "no_order_declared"
    assert "no definition_order is declared" in answer["caveat"]


def test_variant_pairs_lists_the_side_left_unused(repo: Config) -> None:
    rows = ask(repo, "variant_pairs", left="*Async", right="*")["rows"]
    assert {(r["used"], r["unused"]) for r in rows} == {
        ("\\App\\Repo::save", "\\App\\Repo::saveAsync"),
        ("\\App\\fetchAsync", "\\App\\fetch"),
    }


def test_variant_pairs_reads_the_toml_when_no_params_name_one(tmp_path: Path) -> None:
    config = _build(tmp_path)
    (tmp_path / ".code-atlas.toml").write_text('variant_pairs = [["*Async", "*"]]\n', "utf-8")
    config = load_config(tmp_path, {})
    assert config.variant_pairs == (("*Async", "*"),)
    assert ask(config, "variant_pairs")["total_count"] == 2


@pytest.mark.parametrize("bad", ["**", "a*b*", "foo", "*[x]", "dir/*"])
def test_a_variant_pattern_takes_exactly_one_star_and_nothing_else(repo: Config, bad: str) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        ask(repo, "variant_pairs", left=bad, right="*")
    with pytest.raises(ConfigError, match="exactly one"):
        load_config(repo.root, {"CA_VARIANT_PAIRS": f"{bad}|*"})


# ------------------------------------------------------------------ caveats (AC1)
@pytest.mark.parametrize(
    ("template", "params", "fact"),
    [
        ("tier_mix", {}, "HEURISTIC"),
        ("unreferenced_objects", {"kind": "Table", "language": "php"}, "edges from php"),
        ("calls_by_module", {"target": "*Repo::save"}, "1 CALLS edges in scope never linked"),
        ("untested_classes", {}, "through a helper"),
        ("resolved_share", {}, "60.0% of 5 CALLS resolved"),
        ("includes_by_dir", {}, "1 include(s) on this page"),
        ("multi_defined", {}, "no definition_order"),
        ("variant_pairs", {"left": "*Async", "right": "*"}, "called only by name"),
    ],
)
def test_every_answer_carries_its_data_driven_caveat(
    repo: Config, template: str, params: Mapping[str, str], fact: str
) -> None:
    answer = ask(repo, template, **params)
    assert fact in answer["caveat"], answer["caveat"]
    assert answer["reason"] == "ok"


# ------------------------------------------------------------------ empty, with a reason (AC1)
@pytest.mark.parametrize(
    ("template", "params", "reason"),
    [
        ("tier_mix", {"edge_kind": "ALTERS"}, "no_edge_matches"),
        ("no_referrer", {"kind": "Trait"}, "no_symbol_of_that_kind"),
        (
            "unreferenced_objects",
            {"kind": "Table", "language": "cobol"},
            "no_file_in_that_language",
        ),
        ("unreferenced_objects", {"kind": "Enum"}, "no_symbol_of_that_kind"),
        ("calls_by_module", {"target": "*Nothing*"}, "no_call_reaches_the_target"),
        ("untested_classes", {"kind": "Enum"}, "no_type_of_that_kind"),
        ("resolved_share", {"path_prefix": "nowhere"}, "no_call_indexed"),
        ("includes_by_dir", {"path_prefix": "db"}, "no_include_edge"),
        ("multi_defined", {"kind": "Class"}, "no_qname_defined_twice"),
        ("variant_pairs", {"left": "*Zzz", "right": "*"}, "no_one_sided_pair"),
    ],
)
def test_an_empty_answer_names_why(
    repo: Config, template: str, params: Mapping[str, str], reason: str
) -> None:
    answer = ask(repo, template, **params)
    assert answer["rows"] == [] and answer["reason"] == reason
    assert answer.get("total_count", 0) == 0


def test_untested_classes_with_no_test_indexed_says_so(tmp_path: Path) -> None:
    config = _build(tmp_path)
    with GraphStore(config.db_path) as store:
        store.replace_file_rows(T, [], [])
    assert ask(config, "untested_classes")["reason"] == "no_test_symbol_indexed"


# ------------------------------------------------------------------ truncation (AC1)
@pytest.mark.parametrize(
    ("template", "params"),
    [
        ("tier_mix", {}),
        ("no_referrer", {"kind": "Function"}),
        ("unreferenced_objects", {"kind": "Table", "language": "sql"}),
        ("calls_by_module", {"target": "*Repo::save"}),
        ("untested_classes", {}),
        ("resolved_share", {}),
        ("includes_by_dir", {}),
        ("multi_defined", {}),
        ("variant_pairs", {"left": "*Async", "right": "*"}),
    ],
)
def test_a_truncated_page_keeps_a_truthful_total(
    repo: Config, modules: None, template: str, params: Mapping[str, str]
) -> None:
    whole = ask(repo, template, **params)
    page = ask(repo, template, limit=1, **params)
    assert whole["total_count"] == len(whole["rows"]) >= 2 and not whole["truncated"]
    assert len(page["rows"]) == 1 and page["truncated"] is True
    assert page["total_count"] == whole["total_count"]
    assert page["rows"][0] == whole["rows"][0]


def test_the_catalogue_lists_every_template_with_its_params(repo: Config) -> None:
    listed = {t["id"]: t for t in compute.create(repo)()["templates"]}
    assert len(listed) == 9
    assert listed["unreferenced_objects"]["params"]["kind"]["required"] is True
    assert listed["calls_by_module"]["params"]["target_kind"]["one_of"]
