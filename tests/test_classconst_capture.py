"""Task 234: ClassConst from Final / readonly / PEP 8 upper-case — scope-symmetric.

AC1 red-before was ClassConst 1·0·0·0 on parity (php only). After the change python and
typescript fill the cell from Final / readonly; PHP stays byte-identical on diagrams.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from code_atlas.onboarding.class_diagram import ClassBox, Member, render_class_diagram
from code_atlas.store import GraphStore
from code_atlas.tools.class_diagram import MEMBER_KINDS, _members
from tests.php_adapter_cli import CLI as PHP_CLI
from tests.php_adapter_cli import needs_php
from tests.python_adapter_cli import CLI as PY_CLI
from tests.python_adapter_cli import needs_python
from tests.ts_adapter_cli import CLI as TS_CLI


@needs_python
def test_ac2_python_parity_timeout_is_classconst() -> None:
    payload = PY_CLI.parse_file("tests/fixtures/parity/python.py")
    by_name = {n["name"]: n for n in payload["nodes"] if n.get("kind") != "File"}
    assert by_name["TIMEOUT"]["kind"] == "ClassConst"
    assert by_name["owner"]["kind"] == "Property"


@TS_CLI.availability
def test_ac2_typescript_parity_timeout_is_classconst() -> None:
    payload = TS_CLI.parse_file("tests/fixtures/parity/typescript.ts")
    by_name = {n["name"]: n for n in payload["nodes"] if n.get("kind") != "File"}
    assert by_name["TIMEOUT"]["kind"] == "ClassConst"
    assert by_name["owner"]["kind"] == "Property"
    assert by_name["TIMEOUT"].get("modifiers") == ["static", "readonly"]


@needs_python
def test_ac3_python_constant_rule_is_scope_symmetric() -> None:
    """Upper-case and Final agree at module (Const) and class (ClassConst) scope."""
    payload = PY_CLI.parse_file("tests/fixtures/python/classconst_scopes.py")
    kinds = {n["name"]: n["kind"] for n in payload["nodes"]}
    assert kinds["MODULE_UPPER"] == "Const"
    assert kinds["module_final"] == "Const"
    assert kinds["CLASS_UPPER"] == "ClassConst"
    assert kinds["class_final"] == "ClassConst"
    assert kinds["mutable"] == "Property"


def test_ac4_class_diagram_distinguishes_classconst_and_property(tmp_path: Path) -> None:
    """CLASS_MEMBER_KINDS lists both; the box carries distinct kinds (mermaid labels both)."""
    assert "ClassConst" in MEMBER_KINDS and "Property" in MEMBER_KINDS
    db = tmp_path / "graph.db"
    body = b"class Repo:\n    TIMEOUT = 30\n    owner = 1\n"
    digest = hashlib.sha256(body).hexdigest()
    with GraphStore(db) as store:
        store.upsert_file("repo.py", digest, "python")
        store.replace_file_rows(
            "repo.py",
            [
                {
                    "kind": "Class",
                    "name": "Repo",
                    "qualified_name": "repo.Repo",
                    "file_path": "repo.py",
                    "line_start": 1,
                },
                {
                    "kind": "ClassConst",
                    "name": "TIMEOUT",
                    "qualified_name": "repo.Repo::TIMEOUT",
                    "file_path": "repo.py",
                    "line_start": 2,
                },
                {
                    "kind": "Property",
                    "name": "owner",
                    "qualified_name": "repo.Repo::owner",
                    "file_path": "repo.py",
                    "line_start": 3,
                },
            ],
            [
                {
                    "kind": "CONTAINS",
                    "source_qname": "repo.Repo",
                    "target_raw": "TIMEOUT",
                    "target_qname": "repo.Repo::TIMEOUT",
                    "file_path": "repo.py",
                    "line": 2,
                    "confidence_tier": "RESOLVED",
                },
                {
                    "kind": "CONTAINS",
                    "source_qname": "repo.Repo",
                    "target_raw": "owner",
                    "target_qname": "repo.Repo::owner",
                    "file_path": "repo.py",
                    "line": 3,
                    "confidence_tier": "RESOLVED",
                },
            ],
        )
        members = _members(store, "repo.Repo")
    by_name = {m.name: m.kind for m in members}
    assert by_name["TIMEOUT"] == "ClassConst"
    assert by_name["owner"] == "Property"
    box = ClassBox(
        qname="repo.Repo",
        name="Repo",
        kind="Class",
        test=False,
        members=members,
        member_total=len(members),
    )
    mermaid = render_class_diagram((box,), (), (), member_cap=50)
    assert "TIMEOUT" in mermaid and "owner" in mermaid


@needs_php
def test_ac4_php_parity_classconst_and_diagram_stable() -> None:
    """PHP already emitted ClassConst — adapter output shape for TIMEOUT is unchanged."""
    payload = PHP_CLI.parse_file("tests/fixtures/parity/php.php")
    timeout = next(n for n in payload["nodes"] if n.get("name") == "TIMEOUT")
    assert timeout["kind"] == "ClassConst"
    owner = next(n for n in payload["nodes"] if n.get("name") == "$owner")
    assert owner["kind"] == "Property"
    # Mermaid member lines for ClassConst vs Property share the non-Method form (061/AC3).
    const_m = Member(name="TIMEOUT", kind="ClassConst", visibility="+")
    prop_m = Member(name="$owner", kind="Property", visibility="-")
    box = ClassBox(
        qname="Parity\\Repo",
        name="Repo",
        kind="Class",
        test=False,
        members=(const_m, prop_m),
        member_total=2,
    )
    mermaid = render_class_diagram((box,), (), (), member_cap=50)
    assert "+TIMEOUT" in mermaid
    assert "-$owner" in mermaid
