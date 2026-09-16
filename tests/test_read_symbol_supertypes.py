"""Task 285 — ``read_symbol`` on a Class/Interface carries declared supertypes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import CAPABILITIES_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import read_symbol
from code_atlas.tools.nav_result import NEXT_TOOLS_FOR_CALLABLE, NEXT_TOOLS_FOR_TYPE


def _plant(
    store: GraphStore,
    root: Path,
    *,
    path: str,
    language: str,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    caps: dict[str, dict[str, bool]] | None,
) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    target.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    store.upsert_file(path, digest, language)
    store.replace_file_rows(path, nodes, edges)
    if caps is not None:
        store.set_meta(CAPABILITIES_BY_LANGUAGE_KEY, json.dumps(caps))


def _class(
    *, name: str, qname: str, path: str, kind: str = "Class"
) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
        "line_end": 1,
    }


def _edge(
    *, kind: str, source: str, target_raw: str, target_qname: str | None, path: str
) -> dict[str, object]:
    row: dict[str, object] = {
        "kind": kind,
        "source_qname": source,
        "target_raw": target_raw,
        "file_path": path,
        "line": 1,
        "confidence": "EXACT",
    }
    if target_qname is not None:
        row["target_qname"] = target_qname
    return row


def test_class_lists_extends_and_implements_in_declaration_order(tmp_path: Path) -> None:
    """AC1: Class at standard lists both; minimal omits."""
    db = tmp_path / "graph.db"
    path = "a.php"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path=path,
            language="php",
            nodes=[
                _class(name="ServiceViewFile", qname="\\App\\ServiceViewFile", path=path),
                _class(name="Base", qname="\\App\\Base", path=path),
                _class(
                    name="ViewInterface",
                    qname="\\App\\ViewInterface",
                    path=path,
                    kind="Interface",
                ),
            ],
            edges=[
                _edge(
                    kind="EXTENDS",
                    source="\\App\\ServiceViewFile",
                    target_raw="\\App\\Base",
                    target_qname="\\App\\Base",
                    path=path,
                ),
                _edge(
                    kind="IMPLEMENTS",
                    source="\\App\\ServiceViewFile",
                    target_raw="\\App\\ViewInterface",
                    target_qname="\\App\\ViewInterface",
                    path=path,
                ),
            ],
            caps={"php": {"inheritance": True, "params": True}},
        )
    config = load_config(tmp_path, {"CA_DB_PATH": str(db)})
    tool = read_symbol.create(config)
    standard = tool(qname="\\App\\ServiceViewFile", detail_level="standard")
    minimal = tool(qname="\\App\\ServiceViewFile", detail_level="minimal")

    assert standard["supertypes"] == [
        {"kind": "EXTENDS", "qname": "\\App\\Base"},
        {"kind": "IMPLEMENTS", "qname": "\\App\\ViewInterface"},
    ]
    assert "supertypes" not in minimal
    assert standard["next_tool_suggestions"] == list(NEXT_TOOLS_FOR_TYPE)
    assert minimal["next_tool_suggestions"] == list(NEXT_TOOLS_FOR_TYPE)


def test_no_supertypes_omitted_vs_adapter_not_capturing(tmp_path: Path) -> None:
    """AC2: declares-none omits field; inheritance:false discloses not-captured."""
    db = tmp_path / "graph.db"
    path = "a.php"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path=path,
            language="php",
            nodes=[_class(name="Lonely", qname="\\App\\Lonely", path=path)],
            edges=[],
            caps={"php": {"inheritance": True}},
        )
    config = load_config(tmp_path, {"CA_DB_PATH": str(db)})
    tool = read_symbol.create(config)
    none = tool(qname="\\App\\Lonely", detail_level="standard")
    assert "supertypes" not in none
    assert "supertypes_not_captured_by_adapter" not in none

    db2 = tmp_path / "graph2.db"
    with GraphStore(db2) as store:
        _plant(
            store,
            tmp_path,
            path="b.php",
            language="php",
            nodes=[_class(name="Opaque", qname="\\App\\Opaque", path="b.php")],
            edges=[],
            caps={"php": {"inheritance": False}},
        )
    config2 = load_config(tmp_path, {"CA_DB_PATH": str(db2)})
    opaque = read_symbol.create(config2)(qname="\\App\\Opaque", detail_level="standard")
    assert opaque.get("supertypes_not_captured_by_adapter") is True
    assert "supertypes" not in opaque


def test_unresolved_supertype_is_named(tmp_path: Path) -> None:
    """AC3: unlinked base still named and marked unresolved."""
    db = tmp_path / "graph.db"
    path = "a.php"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path=path,
            language="php",
            nodes=[_class(name="Port", qname="\\App\\Port", path=path)],
            edges=[
                _edge(
                    kind="IMPLEMENTS",
                    source="\\App\\Port",
                    target_raw="\\App\\MissingInterface",
                    target_qname=None,
                    path=path,
                ),
            ],
            caps={"php": {"inheritance": True}},
        )
    config = load_config(tmp_path, {"CA_DB_PATH": str(db)})
    out = read_symbol.create(config)(qname="\\App\\Port", detail_level="standard")
    assert out["supertypes"] == [
        {"kind": "IMPLEMENTS", "name": "\\App\\MissingInterface", "unresolved": True}
    ]


def test_callable_next_tools_unchanged_and_table_byte_identical(tmp_path: Path) -> None:
    """AC4/AC5: callable suggestions unchanged; Table has no supertypes fields."""
    db = tmp_path / "graph.db"
    path = "a.php"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path=path,
            language="php",
            nodes=[
                {
                    "kind": "Method",
                    "name": "run",
                    "qualified_name": "\\App\\Svc::run",
                    "file_path": path,
                    "line_start": 1,
                    "line_end": 1,
                    "params": [{"name": "x", "type": "int"}],
                },
                {
                    "kind": "Table",
                    "name": "Assets",
                    "qualified_name": "dbo.Assets",
                    "file_path": path,
                    "line_start": 1,
                    "line_end": 1,
                },
            ],
            edges=[],
            caps={"php": {"inheritance": True, "params": True}},
        )
    config = load_config(tmp_path, {"CA_DB_PATH": str(db)})
    tool = read_symbol.create(config)
    method = tool(qname="\\App\\Svc::run", detail_level="standard")
    table = tool(qname="dbo.Assets", detail_level="standard")

    assert method["next_tool_suggestions"] == list(NEXT_TOOLS_FOR_CALLABLE)
    assert "supertypes" not in method
    assert "supertypes_not_captured_by_adapter" not in method
    assert "supertypes" not in table
    assert "supertypes_not_captured_by_adapter" not in table
    assert "next_tool_suggestions" not in table
