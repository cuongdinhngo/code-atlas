"""Task 250 — ``read_symbol(stored_fields=True)`` shows what a node row actually holds."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol


def _plant(
    store: GraphStore,
    root: Path,
    *,
    path: str,
    language: str,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]] | None = None,
) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"-- planted\n"
    target.write_bytes(body)
    store.upsert_file(path, hashlib.sha256(body).hexdigest(), language)
    store.replace_file_rows(path, nodes, edges or [])


def _column(
    *,
    name: str,
    qname: str,
    path: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    node: dict[str, object] = {
        "kind": "Column",
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
        "line_end": 1,
    }
    if extra is not None:
        node["extra"] = extra
    return node


def _tool(root: Path, db: Path):
    return read_symbol.create(replace(load_config(root, {}), db_path=db))


def test_pre_247_column_has_no_type_nullability_or_identity_key(tmp_path: Path) -> None:
    """AC2: a Column whose extra never got 247's keys reports their absence."""
    db = tmp_path / "graph.db"
    qname = "dbo.T::id"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="t.sql",
            language="sql",
            nodes=[_column(name="id", qname=qname, path="t.sql", extra={})],
        )
    payload = _tool(tmp_path, db)(qname, stored_fields=True)
    assert payload["found"] is True
    keys = payload["stored_fields"]["extra_keys"]
    assert "type" not in keys
    assert "data_type" not in keys
    assert "nullable" not in keys
    assert "identity" not in keys


def test_post_247_column_reports_type_nullable_identity(tmp_path: Path) -> None:
    """AC2: after 247 the same call reports the keys the adapter now stores."""
    db = tmp_path / "graph.db"
    qname = "dbo.T::id"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="t.sql",
            language="sql",
            nodes=[
                _column(
                    name="id",
                    qname=qname,
                    path="t.sql",
                    extra={
                        "type": "int",
                        "nullable": False,
                        "identity": {"seed": 1, "increment": 1},
                    },
                )
            ],
        )
    keys = _tool(tmp_path, db)(qname, stored_fields=True)["stored_fields"]["extra_keys"]
    assert "type" in keys
    assert "nullable" in keys
    assert "identity" in keys


def test_column_with_fk_reports_references(tmp_path: Path) -> None:
    """AC3: a Column with a REFERENCES edge lists 239's key; empty is not this case."""
    db = tmp_path / "graph.db"
    child = "dbo.Child::parent_id"
    parent = "dbo.Parent::id"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="fk.sql",
            language="sql",
            nodes=[
                _column(name="parent_id", qname=child, path="fk.sql", extra={"type": "int"}),
                _column(name="id", qname=parent, path="fk.sql", extra={"type": "int"}),
            ],
            edges=[
                {
                    "kind": "REFERENCES",
                    "source_qname": child,
                    "target_raw": parent,
                    "target_qname": parent,
                    "file_path": "fk.sql",
                    "line": 1,
                    "confidence_tier": "RESOLVED",
                }
            ],
        )
    block = _tool(tmp_path, db)(child, stored_fields=True)["stored_fields"]
    assert block["references"] == [parent]
    assert block["references_unresolved"] == []


def test_column_without_fk_reports_empty_references(tmp_path: Path) -> None:
    """AC3: no FK is an empty list, not a missing key (tool still returns FKs)."""
    db = tmp_path / "graph.db"
    qname = "dbo.T::name"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="t.sql",
            language="sql",
            nodes=[_column(name="name", qname=qname, path="t.sql", extra={"type": "varchar"})],
        )
    block = _tool(tmp_path, db)(qname, stored_fields=True)["stored_fields"]
    assert block["references"] == []
    assert block["references_unresolved"] == []


def test_non_column_omits_the_239_pair(tmp_path: Path) -> None:
    """AC3 counterpart: a Method has no references key — that is 'tool does not return FKs'."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="a.php",
            language="php",
            nodes=[
                {
                    "kind": "Method",
                    "name": "save",
                    "qualified_name": "\\App\\User::save",
                    "file_path": "a.php",
                    "line_start": 1,
                    "line_end": 1,
                }
            ],
        )
    block = _tool(tmp_path, db)("\\App\\User::save", stored_fields=True)["stored_fields"]
    assert "references" not in block
    assert "references_unresolved" not in block
    assert "kind" in block["node_fields"]
    assert "qualified_name" in block["node_fields"]


def test_default_call_omits_stored_fields(tmp_path: Path) -> None:
    """AC5: flag default off — the existing payload gains no key."""
    db = tmp_path / "graph.db"
    qname = "dbo.T::id"
    with GraphStore(db) as store:
        _plant(
            store,
            tmp_path,
            path="t.sql",
            language="sql",
            nodes=[_column(name="id", qname=qname, path="t.sql", extra={"type": "int"})],
        )
    tool = _tool(tmp_path, db)
    default = tool(qname)
    explicit_off = tool(qname, stored_fields=False)
    assert "stored_fields" not in default
    assert default == explicit_off


def test_answer_is_keys_not_values_and_does_not_scale_with_kind_size(
    tmp_path: Path,
) -> None:
    """AC4: extra values stay out; payload size is the key list, not the kind's node count."""
    db = tmp_path / "graph.db"
    wide: dict[str, object] = {f"k{i}": ("x" * 200) for i in range(20)}
    qname = "dbo.T::wide"
    with GraphStore(db) as store:
        nodes = [_column(name="wide", qname=qname, path="t.sql", extra=wide)]
        nodes.extend(
            _column(name=f"c{i}", qname=f"dbo.T::c{i}", path="t.sql", extra={"type": "int"})
            for i in range(50)
        )
        _plant(store, tmp_path, path="t.sql", language="sql", nodes=nodes)
    block = _tool(tmp_path, db)(qname, stored_fields=True)["stored_fields"]
    assert block["extra_keys"] == sorted(wide)
    dumped = str(block)
    assert "x" * 200 not in dumped
    assert len(block["extra_keys"]) == 20
