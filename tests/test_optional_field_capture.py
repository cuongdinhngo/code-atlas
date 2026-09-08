"""Task 231: optional fields are emitted, declared, and disclosed — not silently null.

AC1's red-before was measured on main at 61d992a via parity fixtures (params/args None for
Python; params None for TS). After the change those fields are lists; asserting ``is not None``
is what distinguishes fill from the empty-list trap the ticket names.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import CAPABILITIES_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import class_diagram, find_callers
from code_atlas.tools.nav_result import (
    AUTHORITATIVE,
    CAVEAT_ARGS_NOT_CAPTURED,
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_NO_MATCHES,
)
from tests.php_adapter_cli import needs_php
from tests.python_adapter_cli import CLI as PY_CLI
from tests.python_adapter_cli import needs_python
from tests.sql_adapter_cli import CLI as SQL_CLI
from tests.sql_adapter_cli import ENTRY as SQL_ENTRY
from tests.sql_adapter_cli import NODE as SQL_ENTRY_NODE
from tests.ts_adapter_cli import CLI as TS_CLI

REPO = Path(__file__).resolve().parent.parent
PY_ENTRY = REPO / "adapters" / "python" / "index.py"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


@needs_python
def test_ac1_ac2_python_parity_fields_are_lists_not_null() -> None:
    """AC1/AC2: after fill, params/args are lists (never None — the null/[] trap)."""
    payload = PY_CLI.parse_file("tests/fixtures/parity/python.py")
    find = next(n for n in payload["nodes"] if n.get("name") == "find")
    assert find.get("params") is not None
    assert find["params"] == [{"name": "u", "type": "User"}]
    assert (find.get("extra") or {}).get("type") == "User"
    call = next(e for e in payload["edges"] if e.get("kind") == "CALLS")
    assert call.get("args") is not None
    assert call["args"] == ["string", "number"]
    assert call.get("arg_keys") == [None, None]


@TS_CLI.availability
def test_ac1_ac2_typescript_params_are_lists_not_null() -> None:
    payload = TS_CLI.parse_file("tests/fixtures/parity/typescript.ts")
    find = next(n for n in payload["nodes"] if n.get("name") == "find")
    assert find.get("params") is not None
    assert find["params"][0]["name"] == "u"
    tag = next(n for n in payload["nodes"] if n.get("name") == "tag")
    assert tag.get("modifiers") == ["private", "static"]


@needs_python
def test_ac3_find_callers_arg_filter_matches_python(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC3: argument filter finds a Python call site that passes a string literal."""
    src = tmp_path / "pkg"
    src.mkdir()
    (src / "mod.py").write_text(
        "def helper(x):\n    return x\n\ndef run():\n    return helper('name')\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    env = {
        "CA_WORKERS": "1",
        "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
    }
    config = replace(load_config(tmp_path, env), db_path=tmp_path / "graph.db")
    assert full_build(config, store).failed == 0
    qname = "pkg.mod.helper"
    matched = find_callers.create(config)(qname, arg_position=1, arg_is="string")
    assert matched["total_count"] >= 1
    assert matched["reason"] != REASON_CAPABILITY_NOT_CONFIGURED


@needs_python
def test_ac3_no_capture_declares_capability_not_configured(tmp_path: Path) -> None:
    """AC3: stamped ``args: false`` → non-no_matches reason + authoritative:false."""
    db = tmp_path / "graph.db"
    body = b"def target():\n    pass\n"
    (tmp_path / "m.py").write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    with GraphStore(db) as planted:
        planted.upsert_file("m.py", digest, "python")
        planted.replace_file_rows(
            "m.py",
            [
                {
                    "kind": "Function",
                    "name": "target",
                    "qualified_name": "m::target",
                    "file_path": "m.py",
                    "line_start": 1,
                }
            ],
            [
                {
                    "kind": "CALLS",
                    "source_qname": "m::caller",
                    "target_raw": "target",
                    "target_qname": "m::target",
                    "file_path": "m.py",
                    "line": 2,
                    "confidence_tier": "RESOLVED",
                }
            ],
        )
        planted.set_meta(
            CAPABILITIES_BY_LANGUAGE_KEY,
            json.dumps({"python": {"params": True, "args": False}}),
        )
    config = replace(load_config(tmp_path, {}), db_path=db)
    payload = find_callers.create(config)(
        "m::target", arg_position=1, arg_is="string"
    )
    assert payload["reason"] == REASON_CAPABILITY_NOT_CONFIGURED
    assert payload["reason"] != REASON_NO_MATCHES
    assert payload.get(AUTHORITATIVE) is False
    assert CAVEAT_ARGS_NOT_CAPTURED in (payload.get("authoritative_caveats") or [])


@needs_python
def test_ac4_indirection_string_key_on_python(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC4: CA_INDIRECTION_RULES emits ≥1 PROVIDES_VIEW_DATA edge when args capture is live."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "handler.py").write_text(
        "class Bag:\n"
        "    def set(self, key, value):\n"
        "        pass\n"
        "\n"
        "class Handler:\n"
        "    def index(self):\n"
        "        bag = Bag()\n"
        "        bag.set('user_id', 1)\n",
        encoding="utf-8",
    )
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "rules.json").write_text(
        json.dumps(
            {"view_data": [{"setter": "set", "key_arg": 1, "key_from": "string"}]}
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    env = {
        "CA_WORKERS": "1",
        "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
        "CA_INDIRECTION_RULES": "rules/rules.json",
    }
    config = replace(load_config(tmp_path, env), db_path=tmp_path / "graph.db")
    assert full_build(config, store).failed == 0
    edges = store.edges_matching_kind(contract.PROVIDES_VIEW_DATA, limit=20)
    assert edges, "expected at least one PROVIDES_VIEW_DATA edge from Python string-key capture"
    assert any(str(e.get("target_raw", "")).endswith("user_id") for e in edges)


@needs_php
def test_ac5_php_params_answer_byte_identical() -> None:
    """AC5: PHP parity callable params shape unchanged; two --file runs match (R4.2)."""
    from tests.php_adapter_cli import CLI as PHP_CLI

    a = PHP_CLI.parse_file("tests/fixtures/parity/php.php")
    b = PHP_CLI.parse_file("tests/fixtures/parity/php.php")
    assert a == b
    find = next(n for n in a["nodes"] if n.get("name") == "find")
    assert find["params"] == [{"name": "$u", "type": "\\Parity\\User"}]


def test_known_capabilities_include_capture_flags() -> None:
    for flag in ("params", "args", "modifiers", "declared_types"):
        assert flag in contract.KNOWN_CAPABILITIES


TIERS_FIXTURE = "tests/fixtures/python/call_args_every_tier.py"


@needs_python
def test_every_resolution_tier_records_the_call_arguments() -> None:
    """231 — `args` is threaded per emission site, so a new resolution arm silently drops it.

    227's local type table added one after this capture was written: `bag.set("b", 2)` resolved to
    `Bag::set` and recorded nothing. Asserted over every CALLS edge rather than a list of tiers, so
    the next arm is covered without editing this test (R6.7).
    """
    payload = PY_CLI.parse_file(TIERS_FIXTURE)
    calls = [e for e in payload["edges"] if e["kind"] == "CALLS"]

    assert len(calls) >= 7, calls
    missing = [e["target_raw"] for e in calls if "args" not in e]
    assert missing == [], f"CALLS edges emitted with no args key: {missing}"
    assert [e["target_raw"] for e in calls if e.get("args") == ["string", "number"]].count(
        "tests.fixtures.python.call_args_every_tier.Bag::set"
    ) == 2, "both the `Bag()`-bound and the annotated receiver resolve and record"


WRAPPED = "tests/fixtures/sql/wrapped_routine_header.sql"


@SQL_CLI.availability
def test_a_wrapped_sql_parameter_list_is_still_captured() -> None:
    """231 — the header ends at AS/BEGIN, not at the end of the CREATE line.

    Reading only the CREATE line returned `params: []` for the ticket's own example
    (`CREATE PROCEDURE dbo.Pay @amount int, @who nvarchar(50) = 'x'`) as soon as real T-SQL wraps
    it, while the handshake claimed `params` capture.
    """
    payload = SQL_CLI.parse_file(WRAPPED)
    routines = {n["qualified_name"]: n for n in payload["nodes"] if n["kind"] == "Function"}

    assert routines["dbo.Pay"]["params"] == [
        {"name": "@amount", "type": "int"},
        {"name": "@who", "type": "nvarchar(50)"},
    ]
    assert routines["dbo.Settle"]["params"] == [
        {"name": "@ref", "type": "uniqueidentifier"}
    ]
    # The body's own `@amount` must not be read as a third parameter of dbo.Pay.
    assert len(routines["dbo.Pay"]["params"]) == 2


@SQL_CLI.availability
def test_a_sql_column_declares_its_type_under_the_key_consumers_read() -> None:
    """231 — SQL wrote only `extra.data_type`; every consumer reads `extra.type`."""
    payload = SQL_CLI.parse_file(WRAPPED)
    column = next(n for n in payload["nodes"] if n["qualified_name"] == "dbo.Bill::Total")

    assert column["extra"]["type"] == "decimal(10,2)"
    assert column["extra"]["data_type"] == "decimal(10,2)"


@SQL_CLI.availability
def test_a_language_without_the_construct_declares_no_capture() -> None:
    """231 — a capability is a claim about this adapter, so an unfillable one must read false.

    T-SQL spells no visibility, static or readonly keyword on any object the adapter emits, and
    `scan.js` hard-codes `modifiers: []` at every node site. Declaring `modifiers: true` there made
    the handshake assert capture the graph never has, which is the defect 231 exists to remove.
    """
    handshake = subprocess.run(
        [str(SQL_ENTRY_NODE), str(SQL_ENTRY), "--server"],
        input="",
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO,
    )
    meta = json.loads(handshake.stdout.splitlines()[0])

    assert meta["capabilities"]["modifiers"] is False
    assert meta["capabilities"]["params"] is True
    assert meta["capabilities"]["declared_types"] is True
    assert set(meta["capabilities"]) <= set(contract.KNOWN_CAPABILITIES)


@TS_CLI.availability
def test_a_name_bound_typescript_callable_records_its_parameters() -> None:
    """231 — an arrow or function expression declares its parameters on the initialiser.

    The node is built from the variable declaration, so probing that alone returned `params: []`
    for every `export const f = (…) => …` while the handshake claimed `params` capture.
    """
    payload = TS_CLI.parse_file("tests/fixtures/typescript/arrow_closure.ts")
    callables = {n["name"]: n for n in payload["nodes"] if n["kind"] == "Function"}

    assert callables["greet"]["params"] == [{"name": "name", "type": "string"}]
    assert callables["add"]["params"] == [
        {"name": "a", "type": "number"},
        {"name": "b", "type": "number"},
    ]
    assert callables["run"]["params"] == [], "a nullary function declares an empty list, not null"


def _plant_two_language_index(db: Path, root: Path, *, caps: dict[str, object]) -> None:
    """A Base in one language, a Derived in another, and a stamp saying who fills ``params``."""
    for name in ("base.php", "derived.ts"):
        (root / name).write_bytes(b"x")
    with GraphStore(db) as planted:
        planted.upsert_file("base.php", "h1", "php")
        planted.upsert_file("derived.ts", "h2", "ts")
        planted.replace_file_rows(
            "base.php",
            [
                {
                    "kind": "Class",
                    "name": "Base",
                    "qualified_name": "Base",
                    "file_path": "base.php",
                    "line_start": 1,
                }
            ],
            [],
        )
        planted.replace_file_rows(
            "derived.ts",
            [
                {
                    "kind": "Class",
                    "name": "Derived",
                    "qualified_name": "Derived",
                    "file_path": "derived.ts",
                    "line_start": 1,
                }
            ],
            [
                {
                    "kind": "EXTENDS",
                    "source_qname": "Derived",
                    "target_raw": "Base",
                    "target_qname": "Base",
                    "file_path": "derived.ts",
                    "line": 1,
                }
            ],
        )
        planted.set_meta(CAPABILITIES_BY_LANGUAGE_KEY, json.dumps(caps))


def test_a_diagram_discloses_a_language_it_renders_not_only_the_subject(tmp_path: Path) -> None:
    """231 — the subject's language filling ``params`` does not make the diagram complete.

    The disclosure read the language of ``roots[0]`` alone, so a `Derived` in a capturing language
    rendered an inherited `Base` box from a language that captures nothing and said so nowhere.
    """
    db = tmp_path / "graph.db"
    _plant_two_language_index(
        db, tmp_path, caps={"ts": {"params": True}, "php": {"params": False}}
    )
    config = replace(load_config(tmp_path, {}), db_path=db)

    payload = class_diagram.create(config)(qname="Derived")

    assert {row["qname"] for row in payload["results"]} == {"Derived", "Base"}
    assert payload["params_not_captured_by_adapter"] is True


def test_a_diagram_whose_every_language_captures_grows_no_field(tmp_path: Path) -> None:
    """061/AC5 — a confident answer must not grow a disclosure field."""
    db = tmp_path / "graph.db"
    _plant_two_language_index(
        db, tmp_path, caps={"ts": {"params": True}, "php": {"params": True}}
    )
    config = replace(load_config(tmp_path, {}), db_path=db)

    payload = class_diagram.create(config)(qname="Derived")

    assert "params_not_captured_by_adapter" not in payload
