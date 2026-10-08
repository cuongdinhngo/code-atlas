"""Runtime module loads the standard library spells (task 373): what a call loads, read from syntax.

``runpy.run_path``, ``importlib.util.spec_from_file_location`` and ``exec`` of a file's text load a
module by path; ``importlib.import_module`` and ``__import__`` by dotted name. A path built from the
file's own directory (``os.path.dirname(__file__)``, ``Path(__file__).parent``) and literals names a
file exactly, as 353 reads PHP's ``__DIR__ . '/x.php'``. Standard library only (R2.1).
"""

from __future__ import annotations

import ast
import posixpath
from collections.abc import Callable

Canon = Callable[[ast.expr], str | None]

PATH_LOADERS = {"runpy.run_path": 0, "importlib.util.spec_from_file_location": 1}
NAME_LOADERS = frozenset({"importlib.import_module", "__import__"})
_IDENTITY = frozenset({"os.path.abspath", "os.path.realpath", "os.path.normpath", "pathlib.Path"})


def callee_names(tree: ast.Module) -> dict[str, str]:
    """Local name → the dotted standard name an import binds it to (``ip`` → ``importlib``)."""
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    out[alias.asname] = alias.name
                else:
                    head = alias.name.split(".", 1)[0]
                    out[head] = head
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                if alias.name != "*":
                    out[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return out


def canonical(func: ast.expr, names: dict[str, str]) -> str | None:
    """The dotted standard name a callee spells, through the file's import aliases."""
    parts: list[str] = []
    cur: ast.expr = func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return None
    parts.append(names.get(cur.id, cur.id))
    return ".".join(reversed(parts))


def _is_file(expr: ast.expr, canon: Canon) -> bool:
    """``__file__``, or a call that only normalises it (``abspath``, ``Path(…).resolve()``)."""
    if isinstance(expr, ast.Name):
        return expr.id == "__file__"
    inner = _unwrap(expr, canon)
    return inner is not None and _is_file(inner, canon)


def _unwrap(expr: ast.expr, canon: Canon) -> ast.expr | None:
    """The one argument of a call that does not move the path, or the receiver of ``.resolve()``."""
    if not isinstance(expr, ast.Call) or expr.keywords:
        return None
    if canon(expr.func) in _IDENTITY and len(expr.args) == 1:
        return expr.args[0]
    if (
        isinstance(expr.func, ast.Attribute)
        and expr.func.attr in ("resolve", "absolute")
        and not expr.args
    ):
        return expr.func.value
    return None


def _levels_up(expr: ast.expr, canon: Canon) -> int | None:
    """How far above the file's own directory a directory expression sits; None if it is not one."""
    if isinstance(expr, ast.Call) and canon(expr.func) == "os.path.dirname" and len(expr.args) == 1:
        arg = expr.args[0]
        if _is_file(arg, canon):
            return 0
        up = _levels_up(arg, canon)
        return None if up is None else up + 1
    if isinstance(expr, ast.Attribute) and expr.attr == "parent":
        if _is_file(expr.value, canon):
            return 0
        up = _levels_up(expr.value, canon)
        return None if up is None else up + 1
    inner = _unwrap(expr, canon)
    return None if inner is None else _levels_up(inner, canon)


def _relative(expr: ast.expr, canon: Canon) -> str | None:
    """The path ``expr`` builds relative to the file's directory; None when a part is computed."""
    up = _levels_up(expr, canon)
    if up is not None:
        return "/".join([".."] * up) or "."
    if isinstance(expr, ast.Call) and canon(expr.func) == "os.path.join" and expr.args:
        head = _relative(expr.args[0], canon)
        tail = [
            a.value
            for a in expr.args[1:]
            if isinstance(a, ast.Constant) and isinstance(a.value, str)
        ]
        if head is None or len(tail) != len(expr.args) - 1:
            return None
        return posixpath.join(head, *tail)
    if isinstance(expr, ast.BinOp) and isinstance(expr.right, ast.Constant):
        literal = expr.right.value
        head = _relative(expr.left, canon)
        if head is None or not isinstance(literal, str):
            return None
        if isinstance(expr.op, ast.Div):
            return posixpath.join(head, literal)
        if isinstance(expr.op, ast.Add) and literal.startswith("/"):
            return head + literal
        return None
    if isinstance(expr, ast.JoinedStr) and len(expr.values) == 2:
        first, rest = expr.values
        if isinstance(first, ast.FormattedValue) and isinstance(rest, ast.Constant):
            head = _relative(first.value, canon)
            literal = rest.value
            if head is not None and isinstance(literal, str) and literal.startswith("/"):
                return head + literal
    return None


def file_relative_target(expr: ast.expr, canon: Canon, from_qpath: str) -> str | None:
    """The repo-relative file a ``__file__``-relative path names, or None (computed, or outside)."""
    rel = _relative(expr, canon)
    if rel is None:
        return None
    target = posixpath.normpath(posixpath.join(posixpath.dirname(from_qpath), rel))
    if target in (".", "..") or target.startswith(("../", "/")) or target.endswith("/"):
        return None
    return target


def exec_file_path(call: ast.Call, canon: Canon) -> tuple[bool, ast.expr | None]:
    """``(reads_a_file, path)`` for ``exec``: ``exec(open(p).read())``, ``exec(compile(…))``,
    ``exec(p.read_text())``; ``path`` is None when the file is read through a variable."""
    if canon(call.func) != "exec" or not call.args:
        return False, None
    source = call.args[0]
    if isinstance(source, ast.Call) and canon(source.func) == "compile" and source.args:
        source = source.args[0]
    if not isinstance(source, ast.Call) or not isinstance(source.func, ast.Attribute):
        return False, None
    reader = source.func
    if reader.attr == "read_text":
        return True, reader.value
    if reader.attr != "read":
        return False, None
    opened = reader.value
    if isinstance(opened, ast.Call) and canon(opened.func) == "open" and opened.args:
        return True, opened.args[0]
    return True, None
