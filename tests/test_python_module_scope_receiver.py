"""Task 368 — a module-level ``x = Foo()`` types ``x.bar()`` at module level, forgetfully.

The module's top-level statements share one local type table (PHP 362, TS 153). A write the table
cannot read re-opens the name, a binding inside a compound statement does not outlive it, a name a
function declares ``global`` is never bound, and a function body never reads the module's table.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.adapter_cli import run_adapter_file
from tests.python_adapter_cli import CLI, needs_python

pytestmark = needs_python

SOURCE = """\
class Foo:
    def bar(self): ...
def make(): ...
x = Foo()
x.bar()
a = Foo(); a = make(); a.bar()
def g():
    x.bar()
if make():
    b = Foo()
b.bar()
if __name__ == '__main__':
    z = Foo(); z.bar()
z.bar()
DEFAULT = Foo(); DEFAULT.bar()
t = Foo(); t, u = 1, 2; t.bar()
w = Foo()
for w in []: pass
w.bar()
e = Foo()
try: pass
except ValueError as e: pass
e.bar()
gl = Foo()
def h():
    global gl
    gl = make()
gl.bar()
k = Foo(); import k; k.bar()
n = Foo(); n += 1; n.bar()
y: Foo = make(); y.bar()
c = Foo()
with open('f') as c: pass
c.bar()
def c2(): ...
v = Foo(); print(v := make()); v.bar()
"""

RESOLVED = "m.Foo::bar"


def _bar_targets(tmp_path: Path) -> dict[int, str]:
    (tmp_path / "m.py").write_text(SOURCE, encoding="utf-8")
    done = run_adapter_file(CLI.entry_argv, "m.py", cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    edges = json.loads(done.stdout)["edges"]
    return {
        e["line"]: e["target_raw"]
        for e in edges
        if e["kind"] == "CALLS" and e["target_raw"] in ("bar", RESOLVED)
    }


def test_a_module_level_binding_types_a_later_module_level_call(tmp_path: Path) -> None:
    """AC1 — and a `Final`-free UPPER name, a settings-module constant, binds alike."""
    targets = _bar_targets(tmp_path)
    assert targets[5] == RESOLVED
    assert targets[15] == RESOLVED
    assert targets[31] == RESOLVED  # an annotation binds, as in a function


def test_a_rebind_the_table_cannot_read_re_opens_the_name(tmp_path: Path) -> None:
    """AC2 — plus every other write the table cannot read: unpack, loop, except, import, augmented,
    `with … as`, a walrus, and a function's `global`."""
    targets = _bar_targets(tmp_path)
    for line in (6, 16, 19, 23, 28, 29, 30, 34, 36):
        assert targets[line] == "bar", line


def test_a_function_never_reads_the_module_table(tmp_path: Path) -> None:
    """AC3 — scope 3: only the module's own top-level statements read the table."""
    assert _bar_targets(tmp_path)[8] == "bar"


def test_a_branch_binding_does_not_outlive_its_branch(tmp_path: Path) -> None:
    """AC4 — no join across branches; `__main__` binds inside its own branch only."""
    targets = _bar_targets(tmp_path)
    assert targets[11] == "bar"
    assert targets[13] == RESOLVED
    assert targets[14] == "bar"
