"""Task 242 — ``read_symbol`` surfaces ``params``; ``file_outline`` does not.

Proving path: planted multi-language nodes + capability stamp (honesty predicate from 231),
then the two-call twin route that replaces a file read / new tool.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.contract import CONTRACT_VERSION
from code_atlas.store import CAPABILITIES_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import file_outline, read_symbol


def _plant(
    store: GraphStore,
    root: Path,
    *,
    path: str,
    language: str,
    nodes: list[dict[str, object]],
    caps: dict[str, dict[str, bool]] | None,
) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    target.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    store.upsert_file(path, digest, language)
    store.replace_file_rows(path, nodes, [])
    if caps is not None:
        store.set_meta(CAPABILITIES_BY_LANGUAGE_KEY, json.dumps(caps))


def _fn(
    *,
    kind: str,
    name: str,
    qname: str,
    path: str,
    params: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
        "line_end": 1,
        "params": params,
    }


def test_read_symbol_returns_params_for_php_ts_and_sql(tmp_path: Path) -> None:
    """AC1: Function / Method / stored-proc shapes for php · ts · sql."""
    db = tmp_path / "graph.db"
    cases = [
        (
            "php",
            "a.php",
            _fn(
                kind="Method",
                name="rename",
                qname="\\App\\User::rename",
                path="a.php",
                params=[{"name": "newName", "type": "string"}],
            ),
            [{"name": "newName", "type": "string"}],
        ),
        (
            "ts",
            "b.ts",
            _fn(
                kind="Function",
                name="find",
                qname="find",
                path="b.ts",
                params=[{"name": "u", "type": "User"}],
            ),
            [{"name": "u", "type": "User"}],
        ),
        (
            "sql",
            "c.sql",
            _fn(
                kind="Function",
                name="CheckLedgerDays",
                qname="dbo.CheckLedgerDays",
                path="c.sql",
                params=[
                    {"name": "@CustomerCode", "type": "varchar(8)"},
                    {"name": "@StartDate", "type": "datetime"},
                ],
            ),
            [
                {"name": "@CustomerCode", "type": "varchar(8)"},
                {"name": "@StartDate", "type": "datetime"},
            ],
        ),
    ]
    caps = {lang: {"params": True} for lang, *_ in cases}
    with GraphStore(db) as store:
        for language, path, node, _expected in cases:
            _plant(store, tmp_path, path=path, language=language, nodes=[node], caps=None)
        store.set_meta(CAPABILITIES_BY_LANGUAGE_KEY, json.dumps(caps))
    from dataclasses import replace

    tool = read_symbol.create(replace(load_config(tmp_path, {}), db_path=db))
    for language, _path, node, expected in cases:
        payload = tool(str(node["qualified_name"]))
        assert payload["found"] is True, language
        assert payload["params"] == expected, language
        assert "params_not_captured_by_adapter" not in payload


def test_non_capturing_language_discloses_not_empty_list(tmp_path: Path) -> None:
    """AC2: stamp says params:false → disclosure, never ``params: []``."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="x.py",
            language="python",
            nodes=[
                _fn(
                    kind="Function",
                    name="target",
                    qname="x::target",
                    path="x.py",
                    params=[],
                )
            ],
            caps={"python": {"params": False}},
        )
    from dataclasses import replace

    payload = read_symbol.create(replace(load_config(tmp_path, {}), db_path=db))("x::target")
    assert payload["found"] is True
    assert payload["params_not_captured_by_adapter"] is True
    assert "params" not in payload


def test_pre_231_index_discloses_when_stamp_absent(tmp_path: Path) -> None:
    """R5.6: no capabilities stamp → cannot tell; disclose, do not invent []."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="a.php",
            language="php",
            nodes=[
                _fn(
                    kind="Function",
                    name="helper",
                    qname="\\helper",
                    path="a.php",
                    params=[{"name": "x", "type": "int"}],
                )
            ],
            caps=None,
        )
    from dataclasses import replace

    payload = read_symbol.create(replace(load_config(tmp_path, {}), db_path=db))("\\helper")
    assert payload["params_not_captured_by_adapter"] is True
    assert "params" not in payload


def test_minimal_omits_params(tmp_path: Path) -> None:
    """HOW: minimal is a subset — no params field even when the stamp captures."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="a.php",
            language="php",
            nodes=[
                _fn(
                    kind="Function",
                    name="helper",
                    qname="\\helper",
                    path="a.php",
                    params=[{"name": "x", "type": "int"}],
                )
            ],
            caps={"php": {"params": True}},
        )
    from dataclasses import replace

    payload = read_symbol.create(replace(load_config(tmp_path, {}), db_path=db))(
        "\\helper", detail_level="minimal"
    )
    assert "params" not in payload
    assert "params_not_captured_by_adapter" not in payload


def test_two_call_route_diffs_twin_param_lists(tmp_path: Path) -> None:
    """AC5 proving: two qnames → parameter-list difference with no file read / new tool."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="procs.sql",
            language="sql",
            nodes=[
                _fn(
                    kind="Function",
                    name="UpdateRecursiveActivitiesUntil",
                    qname="dbo.UpdateRecursiveActivitiesUntil",
                    path="procs.sql",
                    params=[
                        {"name": "@endDate", "type": "datetime"},
                        {"name": "@maxActivities", "type": "int"},
                        {"name": "@maxRecursions", "type": "int"},
                    ],
                ),
                _fn(
                    kind="Function",
                    name="UpdateRecursiveActivitiesUntil_beta",
                    qname="dbo.UpdateRecursiveActivitiesUntil_beta",
                    path="procs.sql",
                    params=[
                        {"name": "@endDate", "type": "datetime"},
                        {"name": "@maxActivities", "type": "int"},
                    ],
                ),
            ],
            caps={"sql": {"params": True}},
        )
    from dataclasses import replace

    tool = read_symbol.create(replace(load_config(tmp_path, {}), db_path=db))
    a = tool("dbo.UpdateRecursiveActivitiesUntil")
    b = tool("dbo.UpdateRecursiveActivitiesUntil_beta")
    names_a = {p["name"] for p in a["params"]}
    names_b = {p["name"] for p in b["params"]}
    assert names_a - names_b == {"@maxRecursions"}
    assert names_b - names_a == set()


def test_file_outline_does_not_carry_params(tmp_path: Path) -> None:
    """AC3: written *no* — outline stays a map of ranges, not signatures."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="a.php",
            language="php",
            nodes=[
                _fn(
                    kind="Function",
                    name="helper",
                    qname="\\helper",
                    path="a.php",
                    params=[{"name": "x", "type": "int"}],
                )
            ],
            caps={"php": {"params": True}},
        )
    from dataclasses import replace

    config = replace(load_config(tmp_path, {}), db_path=db)
    outline = file_outline.create(config)("a.php")
    assert outline["found"] is True
    for hit in outline["results"]:
        assert "params" not in hit
    assert "params_not_captured_by_adapter" not in outline


def test_payload_weight_params_bounded(tmp_path: Path) -> None:
    """AC4: params add measured bytes; 79-param subject stays under a hard ceiling."""
    db = tmp_path / "graph.db"
    many = [{"name": f"p{i}", "type": "int"} for i in range(79)]
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="fat.sql",
            language="sql",
            nodes=[
                _fn(
                    kind="Function",
                    name="FatProc",
                    qname="dbo.FatProc",
                    path="fat.sql",
                    params=many,
                )
            ],
            caps={"sql": {"params": True}},
        )
    from dataclasses import replace

    tool = read_symbol.create(replace(load_config(tmp_path, {}), db_path=db))
    standard = tool("dbo.FatProc")
    minimal = tool("dbo.FatProc", detail_level="minimal")
    std_bytes = len(json.dumps(standard, sort_keys=True))
    min_bytes = len(json.dumps(minimal, sort_keys=True))
    delta = std_bytes - min_bytes
    # 79 name+type pairs: measured ceiling leaves headroom for provenance keys.
    assert len(standard["params"]) == 79
    assert delta < 4000
    assert CONTRACT_VERSION == 12


def test_non_callable_kinds_carry_neither_params_nor_the_disclosure(tmp_path: Path) -> None:
    """Review: a Class has no parameter list — `params: []` would claim it takes none (R5.6)."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="Thing.php",
            language="php",
            nodes=[
                _fn(kind="Class", name="Thing", qname="\\App\\Thing", path="Thing.php", params=[]),
                _fn(kind="Const", name="K", qname="\\App\\Thing::K", path="Thing.php", params=[]),
                _fn(
                    kind="Method",
                    name="run",
                    qname="\\App\\Thing::run",
                    path="Thing.php",
                    params=[{"name": "x", "type": "int"}],
                ),
            ],
            caps={"php": {"params": True}},
        )
    from dataclasses import replace

    tool = read_symbol.create(replace(load_config(tmp_path, {}), db_path=db))
    for qname in ("\\App\\Thing", "\\App\\Thing::K"):
        payload = tool(qname)
        assert payload["found"] is True, qname
        assert "params" not in payload, qname
        assert "params_not_captured_by_adapter" not in payload, qname
    # The callable sibling in the same file still answers — the gate is the kind, not the stamp.
    assert tool("\\App\\Thing::run")["params"] == [{"name": "x", "type": "int"}]
