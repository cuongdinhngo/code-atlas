"""Python HEURISTIC CALLS receiver-shape census (task 302).

File-at-a-time ``ast`` only — no Jedi. Names whether a bare member call's receiver is an
identifier bound from a same-file explicit return annotation, a direct ``factory().m()`` call
result, an imported/unknown callable, or something else — the ceiling a return-annotation table
could move (assigned + direct forms).
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

_PRIMITIVES = frozenset(
    {
        "str",
        "int",
        "float",
        "bool",
        "bytes",
        "None",
        "Any",
        "object",
        "dict",
        "list",
        "tuple",
        "set",
        "type",
    }
)


def single_class_return(ann: ast.expr | None) -> str | None:
    """One concrete class-like name from a return annotation, or None if unsafe to promote."""
    if ann is None:
        return None
    if isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):
        def _is_none(n: ast.expr) -> bool:
            return (isinstance(n, ast.Constant) and n.value is None) or (
                isinstance(n, ast.Name) and n.id in ("None", "NoneType")
            )

        left = single_class_return(ann.left)
        right = single_class_return(ann.right)
        if _is_none(ann.left) and right:
            return right
        if _is_none(ann.right) and left:
            return left
        if left and right and left != right:
            return None
        return left or right
    if isinstance(ann, ast.Subscript):
        return None  # generic without a concrete binding
    if isinstance(ann, ast.Name):
        return None if ann.id in _PRIMITIVES else ann.id
    if isinstance(ann, ast.Attribute):
        return ann.attr
    return None


def build_return_maps(tree: ast.AST) -> tuple[dict[str, str], dict[str, str]]:
    """Same-file ``fn_name → class`` and ``Class::method → class`` from explicit returns."""

    class _V(ast.NodeVisitor):
        def __init__(self) -> None:
            self.fn: dict[str, str] = {}
            self.meth: dict[str, str] = {}
            self._class: str | None = None

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            prev = self._class
            self._class = node.name
            self.generic_visit(node)
            self._class = prev

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._fn(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._fn(node)

        def _fn(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            ret = single_class_return(node.returns)
            if ret:
                if self._class:
                    self.meth[f"{self._class}::{node.name}"] = ret
                else:
                    self.fn[node.name] = ret
            prev = self._class
            self._class = None
            self.generic_visit(node)
            self._class = prev

    visitor = _V()
    visitor.visit(tree)
    return visitor.fn, visitor.meth


def call_return_class(
    func: ast.expr, fn: dict[str, str], meth: dict[str, str]
) -> str | None:
    if isinstance(func, ast.Name):
        return fn.get(func.id)
    if isinstance(func, ast.Attribute):
        for key, value in meth.items():
            if key.endswith(f"::{func.attr}"):
                return value
    return None


def shape_for_class(
    cls: str, method: str, name_set: set[str], qname_set: set[str]
) -> str:
    type_ok = cls in name_set
    method_ok = any(q.endswith(f"::{method}") and cls in q for q in qname_set)
    if type_ok and method_ok:
        return "explicit_return_indexed"
    if type_ok:
        return "explicit_return_type_only"
    return "explicit_return_unindexed"


def analyze_file(
    path: Path, name_set: set[str], qname_set: set[str]
) -> dict[str, str]:
    """Map ``line:method`` → receiver shape for every attribute call in the file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    fn, meth = build_return_maps(tree)
    sites: dict[str, str] = {}

    class _Walk(ast.NodeVisitor):
        def __init__(self) -> None:
            self.locals: dict[str, str] = {}
            self.stack: list[dict[str, str]] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.stack.append(self.locals)
            self.locals = {}
            self.generic_visit(node)
            self.locals = self.stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.stack.append(self.locals)
            self.locals = {}
            self.generic_visit(node)
            self.locals = self.stack.pop()

        def _bind(self, name: str, value: ast.expr) -> None:
            if isinstance(value, ast.Call):
                cls = call_return_class(value.func, fn, meth)
                if cls:
                    self.locals[name] = cls
                else:
                    self.locals.pop(name, None)
            else:
                self.locals.pop(name, None)

        def visit_Assign(self, node: ast.Assign) -> None:
            self.generic_visit(node)
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                self._bind(node.targets[0].id, node.value)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self.generic_visit(node)
            if isinstance(node.target, ast.Name) and node.value is not None:
                self._bind(node.target.id, node.value)

        def visit_Call(self, node: ast.Call) -> None:
            self.generic_visit(node)
            if not isinstance(node.func, ast.Attribute):
                return
            method = node.func.attr
            key = f"{node.lineno}:{method}"
            if key in sites:
                return
            recv = node.func.value
            shape = "other_receiver"
            ret_cls: str | None = None
            if isinstance(recv, ast.Name):
                if recv.id in self.locals:
                    ret_cls = self.locals[recv.id]
                else:
                    shape = "identifier_receiver"
            elif isinstance(recv, ast.Call):
                ret_cls = call_return_class(recv.func, fn, meth)
                if ret_cls is None:
                    shape = "call_unannotated_or_foreign"
            elif isinstance(recv, ast.Attribute):
                shape = "property_receiver"
            if ret_cls:
                shape = shape_for_class(ret_cls, method, name_set, qname_set)
            sites[key] = shape

    _Walk().visit(tree)
    return sites


def census_receivers(
    root: Path, edges: list[dict[str, Any]], qnames: list[str]
) -> dict[str, Any]:
    name_set = {q.split("::")[-1] for q in qnames}
    qname_set = set(qnames)
    file_cache: dict[str, dict[str, str] | None] = {}
    counts: dict[str, int] = {}
    explicit_indexed = 0
    for edge in edges:
        rel = str(edge["file"])
        if rel not in file_cache:
            abs_path = root / rel
            file_cache[rel] = (
                analyze_file(abs_path, name_set, qname_set) if abs_path.is_file() else None
            )
        info = file_cache[rel]
        if info is None:
            shape = "no_source_file"
        else:
            shape = info.get(f"{edge['line']}:{edge['method']}", "no_ast_at_line")
        counts[shape] = counts.get(shape, 0) + 1
        if shape == "explicit_return_indexed":
            explicit_indexed += 1
    return {
        "total": len(edges),
        "counts": counts,
        "explicit_return_indexed_ceiling": explicit_indexed,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "--json":
        sys.stderr.write("usage: python receiver_census.py --json <payload.json>\n")
        return 2
    payload = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    result = census_receivers(
        Path(payload["root"]),
        list(payload["edges"]),
        list(payload.get("qnames") or []),
    )
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
