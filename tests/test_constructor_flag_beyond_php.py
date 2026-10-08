"""Task 367 — the TS and Python adapters flag their constructor, as PHP does (362).

``find_callers`` on a flagged constructor reads its class's construction sites: a TS ``new Foo()``
(``NEW``) and a Python ``Foo()`` (``CALLS`` onto the class), argument shapes included. A method
merely *named* like a constructor carries no flag.
"""

from __future__ import annotations

import shlex
import sqlite3
import subprocess
import sys

import pytest

from code_atlas.config import Config, load_config
from code_atlas.contract import CONSTRUCTOR_FLAG
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import REASON_OK
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

pytestmark = needs_node

FILES = {
    "lib/foo.ts": (
        "export class Foo {\n  constructor(a: number | string) {}\n}\n"
        "export class Sub extends Foo {\n  constructor() {\n    super('sub');\n  }\n}\n"
        "export class Quoted {\n  'constructor'(a: number) {}\n}\n"
        "export const Anon = class {\n  constructor() {}\n};\n"
        "export const literal = { constructor() {} };\n"
        "export interface Shape {\n  constructor(): void;\n}\n"
    ),
    "app/one.ts": "import { Foo } from '../lib/foo';\nexport const one = new Foo(1);\n",
    "app/two.ts": "import { Foo } from '../lib/foo';\nexport const two = new Foo('two');\n",
    "app/three.ts": (
        "import { Foo } from '../lib/foo';\n"
        "export function three(n: number) { return new Foo(n); }\n"
    ),
    "pkg/__init__.py": "",
    "pkg/foo.py": (
        "class Foo:\n    def __init__(self, a=0):\n        self.a = a\n\n"
        "    def __new__(cls, *args):\n        raise NotImplementedError\n\n"
        "class Sub(Foo):\n    def __init__(self):\n        super().__init__('sub')\n\n"
        "class Plain:\n    def helper(self):\n"
        "        def __init__(x):\n            return x\n        return __init__\n\n"
        "def __init__():\n    return None\n\n"
        "def build():\n    return Foo(1)\n"
    ),
    "pkg/use.py": "from pkg.foo import Foo\n\nmade = Foo('x')\n",
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


def _sources(answer: dict[str, object]) -> list[str]:
    return sorted(str(hit["qname"]) for hit in answer["results"])  # type: ignore[union-attr]


def test_ts_constructor_callers_are_the_new_sites_of_its_class(config: Config) -> None:
    """AC1 — every `new Foo(...)` and a subclass's `super(...)`; `arg_is` narrows by a literal."""
    tool = find_callers.create(config)
    every = tool("lib/foo.ts::Foo::__construct")
    assert every["reason"] == REASON_OK, every
    assert _sources(every) == [
        "app/one.ts",
        "app/three.ts::three",
        "app/two.ts",
        "lib/foo.ts::Sub::__construct",
    ]
    numbers = tool("lib/foo.ts::Foo::__construct", arg_position=1, arg_is="number")
    assert _sources(numbers) == ["app/one.ts"]
    strings = tool("lib/foo.ts::Foo::__construct", arg_position=1, arg_is="string")
    assert _sources(strings) == ["app/two.ts", "lib/foo.ts::Sub::__construct"]


def test_python_init_callers_are_the_calls_of_its_class(config: Config) -> None:
    """AC2 — `Foo(...)` is a CALLS onto the class, read through `also_targets` by target alone."""
    tool = find_callers.create(config)
    every = tool("pkg.foo.Foo::__init__")
    assert every["reason"] == REASON_OK, every
    assert _sources(every) == ["pkg.foo.Sub::__init__", "pkg.foo.build", "pkg/use.py"]
    literal = tool("pkg.foo.Foo::__init__", arg_position=1, arg_is="string")
    assert _sources(literal) == ["pkg.foo.Sub::__init__", "pkg/use.py"]
    assert _sources(tool("pkg.foo.Foo::__new__")) == ["pkg.foo.build", "pkg/use.py"]


def test_only_a_named_class_constructor_carries_the_flag(config: Config) -> None:
    """AC3 — a `constructor`/`__init__` outside a class body, or in an anonymous class, is plain."""
    conn = sqlite3.connect(config.db_path)
    rows = conn.execute(
        "SELECT qualified_name FROM nodes"
        " WHERE json_extract(extra, '$." + CONSTRUCTOR_FLAG + "') = 1 ORDER BY qualified_name"
    ).fetchall()
    conn.close()
    assert [row[0] for row in rows] == [
        "lib/foo.ts::Foo::__construct",
        "lib/foo.ts::Quoted::__construct",
        "lib/foo.ts::Sub::__construct",
        "pkg.foo.Foo::__init__",
        "pkg.foo.Foo::__new__",
        "pkg.foo.Sub::__init__",
    ]
