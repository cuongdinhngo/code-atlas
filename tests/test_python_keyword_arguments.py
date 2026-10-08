"""Task 372 — a Python keyword argument is recorded, so ``arg_is`` can read it by name.

``kwargs`` (contract v14) maps each keyword to the same category an ``args`` entry carries, beside
the positional ``args`` it never changes (R1.7). ``{}`` = recorded and none passed; absent = not
recorded — a ``**`` spread, or a language with no keywords — which a filter counts as unrecorded.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from tests.adapter_cli import run_adapter_file
from tests.python_adapter_cli import CLI, ENTRY, needs_python

pytestmark = needs_python

SOURCE = (
    "class Foo:\n"  # 1
    "    def __init__(self, a=0, b=''):\n"  # 2
    "        self.a = a\n"  # 3
    "def by_keyword():\n"  # 4
    "    return Foo(a=1, b='b')\n"  # 5
    "def by_position():\n"  # 6
    "    return Foo(1, 'b')\n"  # 7
    "def by_variable(n):\n"  # 8
    "    return Foo(a=n)\n"  # 9
    "def by_spread(kw):\n"  # 10
    "    return Foo(**kw)\n"  # 11
)


@pytest.fixture(scope="module")
def config(tmp_path_factory: pytest.TempPathFactory) -> Config:
    root = tmp_path_factory.mktemp("repo")
    (root / "m.py").write_text(SOURCE, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    built = load_config(
        root,
        {"CA_WORKERS": "1", "CA_PYTHON_CMD": shlex.join([sys.executable, str(ENTRY), "--server"])},
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def _calls(tmp_path: Path) -> dict[int, dict[str, object]]:
    (tmp_path / "m.py").write_text(SOURCE, encoding="utf-8")
    done = run_adapter_file(CLI.entry_argv, "m.py", cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    edges = json.loads(done.stdout)["edges"]
    return {e["line"]: e for e in edges if e["kind"] == "CALLS" and e["target_raw"] == "m.Foo"}


def _sources(answer: dict[str, object]) -> list[str]:
    results = answer["results"]
    assert isinstance(results, list)
    return sorted(str(hit["qname"]) for hit in results)


def test_keyword_arguments_are_recorded_with_their_shapes(tmp_path: Path) -> None:
    """AC1 — `Foo(a=1, b='b')` records both keywords; a `**` spread records none."""
    calls = _calls(tmp_path)
    assert calls[5]["kwargs"] == {"a": "number", "b": "string"}
    assert calls[9]["kwargs"] == {"a": None}
    assert "kwargs" not in calls[11]
    assert contract.validate({"path": "m.py", "ok": True, "nodes": [], "edges": [calls[5]]}) == []
    bad = {**calls[5], "kwargs": {"a": "seven"}}
    assert contract.validate({"path": "m.py", "ok": True, "nodes": [], "edges": [bad]})


def test_a_positional_call_keeps_its_args_byte_identical(tmp_path: Path) -> None:
    """AC3 — positional `args`/`arg_keys` are what they were before 372; `kwargs` is `{}`."""
    call = _calls(tmp_path)[7]
    assert (call["args"], call["arg_keys"]) == (["number", "string"], [None, None])
    assert call["kwargs"] == {}


def test_arg_is_narrows_callers_by_a_keyword(config: Config) -> None:
    """AC2 — `arg_name` + `arg_is` reads the keyword; the spread call is unrecorded, not a miss."""
    tool = find_callers.create(config)
    literal = tool("m.Foo::__init__", arg_name="a", arg_is="number")
    assert _sources(literal) == ["m.by_keyword"]
    assert literal["args_unrecorded"] == 1
    assert _sources(tool("m.Foo::__init__", arg_name="a", arg_is="dynamic")) == ["m.by_variable"]
    assert _sources(tool("m.Foo::__init__", arg_name="a", arg_is="absent")) == ["m.by_position"]


def test_a_keyword_filter_refuses_a_position_beside_it(config: Config) -> None:
    """R5.3 — `arg_position` and `arg_name` name different arguments; a typo fails loud."""
    tool = find_callers.create(config)
    with pytest.raises(ValueError, match="pass one"):
        tool("m.Foo::__init__", arg_position=1, arg_name="a", arg_is="number")
    with pytest.raises(ValueError, match="keyword's name"):
        tool("m.Foo::__init__", arg_name="a-b", arg_is="number")
