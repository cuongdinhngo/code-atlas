"""424 — SEC-IN-06: `store.py` hands SQLite text it wrote, never text built from a value.

Every `execute` / `executemany` / `executescript` first argument is traced to its source. It must
be a string literal, a module constant, or text assembled (by f-string, `+` or a conditional) from
such pieces and from names on the allow-lists below, each with the reason it carries an identifier,
a placeholder list or a SQL fragment and never a user value. `%` and `.format` are refused, and so
is a function parameter that is not allow-listed: a value reaches SQL only through `?` binding.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STORE = REPO / "code_atlas" / "store.py"
EXECUTORS = frozenset({"execute", "executemany", "executescript"})

# (function, name) pairs the tracer may not follow to a literal, with why each carries no value.
# A parameter is allowed only where every caller passes a literal or a fragment traced at its site.
ALLOWED = {
    ("_insert", "table"): "a table-name constant (NODES, EDGES) from the module's own callers",
    (
        "_insert",
        "columns",
    ): "field names from the contract's constant tuples, one group per field set",
    ("_rows", "sql"): "the read helper; every caller's `sql` is traced at its own assignment",
    (
        "_write_counts",
        "sql",
    ): "the count helper; every caller's `sql` is traced at its own assignment",
    ("_edge_where", "where"): "a fragment each caller builds from literals and `?` marks",
    (
        "_edge_where",
        "extra",
    ): "a predicate from the module's `*_predicate` helpers, text from literals",
    ("_with_exclude_test_nodes", "column"): "a column literal each caller names (default is one)",
    ("_with_namespace", "qname_column"): "a column literal each caller names (default is one)",
    ("_path_under", "column"): "a column literal each caller names",
    ("_exclude_test_sources_predicate", "edges"): "a table alias literal each caller names",
    ("_subtree_crossing", "source_outside"): "a fragment `_path_under` built from a column literal",
    ("_subtree_crossing", "target_inside"): "a fragment `_path_under` built from a column literal",
    ("_subtree_dynamic_bridges", "subtree_clause"): "a fragment `_path_under` built from a literal",
    ("_tour_ranked", "where"): "its callers pass a literal or a literal around a traced fragment",
}


def _module_constants(tree: ast.Module) -> dict[str, ast.expr]:
    return {
        t.id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign | ast.AnnAssign)
        for t in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(t, ast.Name) and node.value is not None
    }


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}


def _function_of(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.FunctionDef | None:
    while node in parents:
        node = parents[node]
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            return node  # type: ignore[return-value]
    return None


def _assignments(func: ast.FunctionDef | None, name: str) -> list[tuple[ast.expr, int | None]]:
    """(value, tuple index) of every assignment to ``name`` in ``func``, loops included."""
    if func is None:
        return []
    found: list[tuple[ast.expr, int | None]] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign | ast.AugAssign) and node.value is not None:
            targets, value = [node.target], node.value
        elif isinstance(node, ast.For | ast.comprehension):
            targets, value = [node.target], node.iter
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                found.append((value, None))
            elif isinstance(target, ast.Tuple):
                found += [
                    (value, i)
                    for i, e in enumerate(target.elts)
                    if isinstance(e, ast.Name) and e.id == name
                ]
    return found


def _appended(func: ast.FunctionDef | None, name: str) -> list[ast.expr]:
    """Arguments of every ``<name>.append(...)`` in ``func``."""
    return [
        n.args[0]
        for n in ast.walk(func or ast.parse(""))
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "append"
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == name
        and n.args
    ]


class Tracer:
    def __init__(self, source: str) -> None:
        self.tree = ast.parse(source)
        self.constants = _module_constants(self.tree)
        self.parents = _parents(self.tree)
        self.used: set[object] = set()
        self.methods = {n.name: n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)}

    def trace(
        self,
        expr: ast.expr,
        func: ast.FunctionDef | None,
        seen: frozenset[str],
        index: int | None = None,
    ) -> list[str]:
        if isinstance(expr, ast.Constant):
            ok = isinstance(expr.value, str) or expr.value is None
            return [] if ok else [f"non-text {expr.value!r}"]
        if isinstance(expr, ast.JoinedStr):
            return [p for part in expr.values for p in self._piece(part, func, seen)]
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
            return self.trace(expr.left, func, seen) + self.trace(expr.right, func, seen)
        if isinstance(expr, ast.BinOp) and self._is_marks(expr):
            return []
        if isinstance(expr, ast.BinOp):
            return [f"`{ast.unparse(expr)[:60]}` builds SQL with an operator that formats values"]
        if isinstance(expr, ast.IfExp):
            return self.trace(expr.body, func, seen) + self.trace(expr.orelse, func, seen)
        if isinstance(expr, ast.Name):
            return self._name(expr.id, func, seen)
        if isinstance(expr, ast.Attribute) and ast.unparse(expr.value) == "contract":
            return []  # the contract module is the single source of names (R3)
        if isinstance(expr, ast.Call):
            return self._call(expr, func, seen, index)
        if isinstance(expr, ast.Tuple | ast.List):
            return [p for e in expr.elts for p in self.trace(e, func, seen)]
        if isinstance(expr, ast.Subscript):
            return self.trace(expr.value, func, seen, index)
        if isinstance(expr, ast.GeneratorExp):
            return self.trace(expr.elt, func, seen)
        return [f"`{ast.unparse(expr)[:60]}` is not a literal, constant or traced name"]

    @staticmethod
    def _is_marks(expr: ast.BinOp) -> bool:
        """``'?' * n`` — a repeated literal, which can hold no value."""
        return (
            isinstance(expr.op, ast.Mult)
            and isinstance(expr.left, ast.Constant)
            and isinstance(expr.left.value, str)
        )

    def _call(
        self, call: ast.Call, func: ast.FunctionDef | None, seen: frozenset[str], index: int | None
    ) -> list[str]:
        f = call.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Constant):
            if f.attr == "join" and call.args:  # '<literal>'.join(<fragments>)
                return self.trace(call.args[0], func, seen)
        if isinstance(f, ast.Attribute) and f.attr == "replace" and len(call.args) == 2:
            args_literal = all(isinstance(a, ast.Constant) for a in call.args)
            return self.trace(f.value, func, seen) if args_literal else ["replace() of a value"]
        if isinstance(f, ast.Name) and f.id in ("len", "int"):
            return []
        method = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        helper = self.methods.get(method)
        if helper is not None:
            return self._returns(helper, index, seen | {method})
        return [f"`{ast.unparse(call)[:60]}` is not a literal, constant or traced name"]

    def _returns(
        self, helper: ast.FunctionDef, index: int | None, seen: frozenset[str]
    ) -> list[str]:
        found = []
        for node in ast.walk(helper):
            if isinstance(node, ast.Return) and node.value is not None:
                value = node.value
                if isinstance(value, ast.Tuple) and index is not None:
                    value, at = value.elts[index], None
                else:
                    at = index
                found += self.trace(value, helper, seen, at)
        return found

    def _piece(
        self, part: ast.expr, func: ast.FunctionDef | None, seen: frozenset[str]
    ) -> list[str]:
        if not isinstance(part, ast.FormattedValue):
            return []
        value = part.value
        if isinstance(value, ast.Name) and isinstance(self.constants.get(value.id), ast.Constant):
            return []  # a module constant, number or text
        return self.trace(value, func, seen)

    def _name(self, name: str, func: ast.FunctionDef | None, seen: frozenset[str]) -> list[str]:
        if name in seen:
            return []
        seen = seen | {name}
        if func is not None:
            if (func.name, name) in ALLOWED:
                self.used.add((func.name, name))
                return []
            if name in {a.arg for a in func.args.args + func.args.kwonlyargs}:
                return [f"`{name}` is a parameter of {func.name}()"]
            local = _assignments(func, name)
            if local:
                found = [p for value, i in local for p in self.trace(value, func, seen, i)]
                return found + [p for v in _appended(func, name) for p in self.trace(v, func, seen)]
        if name in self.constants:
            return self.trace(self.constants[name], None, seen)
        return [f"`{name}` is not a literal, constant, allow-listed name or traced local"]

    def problems(self) -> list[str]:
        found = []
        for node in ast.walk(self.tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in EXECUTORS
                and node.args
            ):
                continue
            func = _function_of(node, self.parents)
            found += [
                f"line {node.lineno}: {p}" for p in self.trace(node.args[0], func, frozenset())
            ]
        return found


def test_no_allow_list_entry_is_stale() -> None:
    """An entry no execute site needs is a standing hole; delete it."""
    tracer = Tracer(STORE.read_text(encoding="utf-8"))
    tracer.problems()
    unused = set(ALLOWED) - tracer.used
    assert not unused, f"allow-listed but never reached: {sorted(map(str, unused))}"


def sites(source: str) -> int:
    return sum(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in EXECUTORS
        for n in ast.walk(ast.parse(source))
    )


def problems(source: str) -> list[str]:
    return Tracer(source).problems()


def test_store_runs_only_literal_or_identifier_built_sql() -> None:
    source = STORE.read_text(encoding="utf-8")
    assert sites(source) > 100, "the reader found almost no execute site; this would pass vacuously"
    assert problems(source) == []


PLANTED = {
    "an f-string over a parameter": (
        "def find(self, name):\n"
        "    self._conn.execute(f\"SELECT * FROM nodes WHERE name = '{name}'\")\n"
    ),
    "a % format": (
        "def find(self, name):\n"
        "    self._conn.execute(\"SELECT * FROM nodes WHERE name = '%s'\" % name)\n"
    ),
    "a .format": ('def find(self, name):\n    self._conn.execute("SELECT {}".format(name))\n'),
    "a concatenated parameter": (
        "def find(self, name):\n    sql = 'SELECT * FROM nodes WHERE name = ' + name\n"
        "    self._conn.execute(sql)\n"
    ),
    "a SQL parameter nobody allow-listed": (
        "def run(self, query):\n    self._conn.executescript(query)\n"
    ),
    "a local built from a call": (
        "def find(self, name):\n    sql = build(name)\n    self._conn.executemany(sql, [])\n"
    ),
    "an interpolated name nobody allow-listed": (
        'def find(self, term):\n    self._conn.execute(f"SELECT {term} FROM nodes")\n'
    ),
}
ACCEPTED = {
    "a literal": "def f(self):\n    self._conn.execute('SELECT 1')\n",
    "a module constant": (
        "DDL = 'CREATE TABLE t (a)'\ndef f(self):\n    self._conn.executescript(DDL)\n"
    ),
    "an allow-listed placeholder list": (
        "def f(self, ids):\n    placeholders = ', '.join('?' * len(ids))\n"
        "    self._conn.execute(f'SELECT 1 WHERE id IN ({placeholders})', ids)\n"
    ),
    "a local traced to literals": (
        "def f(self, flag):\n    sql = 'SELECT 1' if flag else 'SELECT 2'\n"
        "    self._conn.execute(sql)\n"
    ),
}


def test_a_planted_value_interpolation_is_refused() -> None:
    for case, source in PLANTED.items():
        assert problems(source), f"{case} was accepted"


def test_the_shapes_the_store_uses_are_accepted() -> None:
    for case, source in ACCEPTED.items():
        assert problems(source) == [], case
