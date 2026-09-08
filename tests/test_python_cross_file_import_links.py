"""Task 226 — an imported type name qualifies so EXTENDS/REFERENCES link cross-file.

AC1 red-before was observed on origin/main (61d992a) against the two-file fixture: all three
edges emitted bare ``Entity``/``audit`` with ``target_qname`` NULL. This module asserts the after
state (AC2–AC5) at the store/consumer (R6.9).
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import SCHEMA_VERSION, GraphStore
from code_atlas.tools import find_implementations
from tests.python_adapter_cli import ENTRY, needs_python

pytestmark = needs_python

ENTITY = "pkg.entities.Entity"
USER = "pkg.user.User"
DECORATED = "pkg.user.Decorated"
AUDIT = "pkg.entities.audit"
REL_USER = "pkg.relative_child.RelativeUser"


def _seed_pkg(root: Path) -> None:
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "entities.py").write_text(
        "class Entity:\n    pass\n\n\ndef audit(fn):\n    return fn\n",
        encoding="utf-8",
    )
    (pkg / "user.py").write_text(
        "from pkg.entities import Entity, audit\n\n\n"
        "class User(Entity):\n"
        "    def save(self, e: Entity) -> None:\n"
        "        return None\n\n\n"
        "@audit\n"
        "class Decorated:\n"
        "    pass\n",
        encoding="utf-8",
    )
    (pkg / "relative_child.py").write_text(
        "from .entities import Entity\n\n\nclass RelativeUser(Entity):\n    pass\n",
        encoding="utf-8",
    )
    (pkg / "external.py").write_text(
        "from nonexistent_pkg.mod import ExternalBase\n\n\n"
        "class Child(ExternalBase):\n"
        "    pass\n",
        encoding="utf-8",
    )
    (pkg / "typed.py").write_text(
        "from abc import ABC\nfrom typing import Protocol\nfrom enum import Enum\n\n\n"
        "class Drawable(Protocol):\n"
        "    def draw(self) -> None: ...\n\n\n"
        "class Shape(ABC):\n"
        "    pass\n\n\n"
        "class Color(Enum):\n"
        "    RED = 1\n\n\n"
        "class Circle(Drawable):\n"
        "    def draw(self) -> None:\n"
        "        return None\n\n\n"
        "class Square(Shape):\n"
        "    pass\n",
        encoding="utf-8",
    )


def _index(tmp_path: Path) -> GraphStore:
    _seed_pkg(tmp_path)
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=tmp_path, check=True, capture_output=True)
    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(ENTRY), "--server"]),
        },
    )
    store = GraphStore(db_path)
    report = full_build(config, store)
    assert report.failed == 0 and report.parsed >= 6
    return store


def _edge(store: GraphStore, source: str, kind: str) -> dict[str, object]:
    rows = [dict(r) for r in store.edges_by_source(source, kinds=(kind,), limit=20)]
    assert rows, f"no {kind} from {source}"
    return rows[0]


def test_imported_base_annotation_decorator_link_resolved(tmp_path: Path) -> None:
    """AC2 — the three cross-file uses link at RESOLVED (adapter read a declaration)."""
    with _index(tmp_path) as store:
        extends = _edge(store, USER, "EXTENDS")
        assert extends["target_raw"] == ENTITY
        assert extends["target_qname"] == ENTITY
        assert extends["confidence_tier"] == "RESOLVED"

        refs = [
            dict(r)
            for r in store.edges_by_source(f"{USER}::save", kinds=("REFERENCES",), limit=20)
        ]
        entity_refs = [r for r in refs if r["target_raw"] == ENTITY]
        assert entity_refs, refs
        assert entity_refs[0]["target_qname"] == ENTITY
        assert entity_refs[0]["confidence_tier"] == "RESOLVED"

        deco = _edge(store, DECORATED, "REFERENCES")
        assert deco["target_raw"] == AUDIT
        assert deco["target_qname"] == AUDIT
        assert deco["confidence_tier"] == "RESOLVED"


def test_relative_import_base_links(tmp_path: Path) -> None:
    """Relative ``from .entities import Entity`` uses the same binding path."""
    with _index(tmp_path) as store:
        extends = _edge(store, REL_USER, "EXTENDS")
        assert extends["target_qname"] == ENTITY
        assert extends["confidence_tier"] == "RESOLVED"


def test_external_import_stays_unlinked(tmp_path: Path) -> None:
    """AC3 — filesystem miss keeps bare target_raw; no invented FQN."""
    with _index(tmp_path) as store:
        extends = _edge(store, "pkg.external.Child", "EXTENDS")
        assert extends["target_raw"] == "ExternalBase"
        assert extends["target_qname"] is None


def test_versions_unchanged(tmp_path: Path) -> None:
    """AC4 — CONTRACT_VERSION and SCHEMA_VERSION stay put."""
    assert contract.CONTRACT_VERSION == 9
    assert SCHEMA_VERSION == "5"
    with _index(tmp_path) as store:
        assert store.get_meta("schema_version") == SCHEMA_VERSION


def test_classification_markers_untouched(tmp_path: Path) -> None:
    """AC5 — Protocol/ABC/Enum still classify; IMPLEMENTS stay honest."""
    with _index(tmp_path) as store:
        kinds = {
            n["qualified_name"]: n["kind"] for n in store.nodes_by_file_all("pkg/typed.py")
        }
        assert kinds["pkg.typed.Drawable"] == "Interface"
        assert kinds["pkg.typed.Shape"] == "Interface"
        assert kinds["pkg.typed.Color"] == "Enum"
        assert kinds["pkg.typed.Circle"] == "Class"
        assert kinds["pkg.typed.Square"] == "Class"
        circle = _edge(store, "pkg.typed.Circle", "IMPLEMENTS")
        assert circle["target_qname"] == "pkg.typed.Drawable"
        drawable = _edge(store, "pkg.typed.Drawable", "IMPLEMENTS")
        assert drawable["target_raw"] == "Protocol"
        assert drawable["target_qname"] is None


def test_find_implementations_sees_cross_file_subclass(tmp_path: Path) -> None:
    """Consumer proof: find_implementations on Entity answers User + RelativeUser."""
    config_root = tmp_path
    _seed_pkg(config_root)
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=config_root, check=True, capture_output=True)
    db_path = config_root / ".code-atlas" / "graph.db"
    config = load_config(
        config_root,
        {
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(ENTRY), "--server"]),
        },
    )
    with GraphStore(db_path) as store:
        assert full_build(config, store).failed == 0
    payload = find_implementations.create(config)(qname=ENTITY, detail_level="minimal")
    names = {hit["qname"] for hit in payload["results"]}
    assert USER in names
    assert REL_USER in names
    assert payload["total_count"] >= 2


def test_ac1_unresolved_import_keeps_bare_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1 / R6.5 — filesystem miss leaves bare tokens (today's pre-fix shape for imports)."""
    import sys

    adapter_root = str(ENTRY.parent)
    if adapter_root not in sys.path:
        sys.path.insert(0, adapter_root)
    from src import parse as parse_mod

    monkeypatch.setattr(parse_mod, "resolve_import", lambda **_kwargs: None)
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "user.py").write_text(
        "from pkg.entities import Entity, audit\n\n"
        "class User(Entity):\n"
        "    def save(self, e: Entity) -> None:\n"
        "        return None\n\n"
        "@audit\n"
        "class Decorated:\n"
        "    pass\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    result = parse_mod.parse_file("pkg/user.py")
    assert result["ok"] is True
    targets = sorted(
        {
            e["target_raw"]
            for e in result["edges"]
            if e["kind"] in ("EXTENDS", "REFERENCES")
        }
    )
    assert targets == ["Entity", "audit"], targets

