"""Task 369 — a TS static field and a Python class attribute are referenced, as PHP's are (336).

A read or write through the class's own name, or through the lexical receiver that names the class
(`this` in a TS static member · `self`/`cls`), is a ``REFERENCES`` onto the declared member. An
untyped receiver, an undeclared name and a method call emit none.
"""

from __future__ import annotations

import shlex
import sqlite3
import subprocess
import sys

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools.find_references import create as create_find_references
from code_atlas.tools.nav_result import REASON_OK
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

pytestmark = needs_node

FILES = {
    "src/counter.ts": (
        "export class Counter {\n"  # 1
        "  static count = 0;\n"  # 2
        "  n = 1;\n"  # 3
        "  static inc(): number {\n"  # 4
        "    this.count++;\n"  # 5
        "    Counter.count = 2;\n"  # 6
        "    const read = () => this.count;\n"  # 7
        "    const own = function (this: { count: number }) { return this.count; };\n"  # 8
        "    this.inc();\n"  # 9
        "    return read() + own.call({ count: 1 });\n"  # 10
        "  }\n"  # 11
        "  bump(): number {\n"  # 12
        "    return this.count + this.n;\n"  # 13
        "  }\n"  # 14
        "}\n"  # 15
        "export const seen = Counter.count;\n"  # 16
    ),
    "pkg/__init__.py": "",
    "pkg/counter.py": (
        "class Counter:\n"  # 1
        "    count = 0\n"  # 2
        "\n"  # 3
        "    def bump(self):\n"  # 4
        "        self.count = self.count + 1\n"  # 5
        "        self.bump()\n"  # 6
        "\n"  # 7
        "    @classmethod\n"  # 8
        "    def reset(cls):\n"  # 9
        "        cls.count = 0\n"  # 10
        "\n"  # 11
        "Counter.count = 2\n"  # 12
        "seen = Counter.count\n"  # 13
        "other = Counter.missing\n"  # 14
    ),
}


@pytest.fixture(scope="module")
def config(tmp_path_factory: pytest.TempPathFactory) -> Config:
    root = tmp_path_factory.mktemp("repo")
    for rel, body in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    built = load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"]),
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
        },
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def _sites(config: Config, qname: str) -> set[tuple[str, int]]:
    payload = create_find_references(config)(qname, detail_level="standard")
    assert payload["reason"] == REASON_OK, payload
    results = payload["results"]
    assert isinstance(results, list)
    return {(str(hit["qname"]), int(hit["line"])) for hit in results}


def test_a_ts_static_field_is_referenced_by_its_class_and_by_static_this(config: Config) -> None:
    """AC1 — `Counter.count` read and write, `this.count` in a static member and its arrow;
    `this.count` in an instance method and in a `function` (which rebinds `this`) add nothing."""
    assert _sites(config, "src/counter.ts::Counter::count") == {
        ("src/counter.ts::Counter::inc", 5),
        ("src/counter.ts::Counter::inc", 6),
        ("src/counter.ts::Counter::inc::read", 7),
        ("src/counter.ts", 16),
    }


def test_a_python_class_attribute_is_referenced_by_class_self_and_cls(config: Config) -> None:
    """AC2 — `Counter.count`, `self.count` (read and write) and `cls.count`."""
    assert _sites(config, "pkg.counter.Counter::count") == {
        ("pkg.counter.Counter::bump", 5),
        ("pkg.counter.Counter::reset", 10),
        ("pkg/counter.py", 12),
        ("pkg/counter.py", 13),
    }


def test_a_method_call_or_an_undeclared_name_adds_no_reference(config: Config) -> None:
    """AC3 — `this.inc()` / `self.bump()` stay CALLS; `Counter.missing` invents nothing (229)."""
    conn = sqlite3.connect(config.db_path)
    query = "SELECT target_raw FROM edges WHERE kind = 'REFERENCES'"
    refs = [row[0] for row in conn.execute(query)]
    conn.close()
    assert refs
    assert not [t for t in refs if t.endswith(("::inc", "::bump", "::missing"))]
