"""Walk a ``.py`` file with stdlib ``ast`` and emit contract nodes/edges (task 020 tier 1a)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from src.imports import import_target_raw, resolve_import

MEMBER_SEP = "::"


def to_posix(path: str) -> str:
    return path.replace("\\", "/")


def module_name(qpath: str) -> str:
    """Repo-relative path → dotted module (``a/b/__init__.py`` → ``a.b``, ``a/b.py`` → ``a.b``)."""
    p = to_posix(qpath)
    if p.endswith("/__init__.py"):
        p = p[: -len("/__init__.py")]
    elif p.endswith(".py"):
        p = p[: -len(".py")]
    return p.replace("/", ".") if p else ""


def member(container: str, name: str) -> str:
    return f"{container}{MEMBER_SEP}{name}"


def dotted(container: str, name: str) -> str:
    return f"{container}.{name}" if container else name


def _decorator_names(node: ast.AST) -> list[str]:
    names: list[str] = []
    for deco in getattr(node, "decorator_list", []) or []:
        if isinstance(deco, ast.Name):
            names.append(deco.id)
        elif isinstance(deco, ast.Attribute):
            names.append(deco.attr)
        elif isinstance(deco, ast.Call):
            if isinstance(deco.func, ast.Name):
                names.append(deco.func.id)
            elif isinstance(deco.func, ast.Attribute):
                names.append(deco.func.attr)
    return names


def _method_modifiers(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    mods: list[str] = []
    if isinstance(node, ast.AsyncFunctionDef):
        mods.append("async")
    for name in _decorator_names(node):
        if name in ("staticmethod", "classmethod", "property") and name not in mods:
            mods.append(name)
    return mods


def _function_modifiers(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    return ["async"] if isinstance(node, ast.AsyncFunctionDef) else []


def _is_upper_const(name: str) -> bool:
    return name.isupper() and any(c.isalpha() for c in name)


def parse_file(path: str, declarations_only: bool = False) -> dict[str, Any]:
    qpath = to_posix(path)
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return {"path": qpath, "ok": False, "error": f"cannot read file: {exc}"}

    try:
        tree = ast.parse(text, filename=qpath)
    except SyntaxError as exc:
        msg = exc.msg or "invalid syntax"
        return {"path": qpath, "ok": False, "error": f"syntax error: {msg}"}

    # ast.Module has no end_lineno; File/Namespace spans cover the source text (PHP/TS do the same).
    line_end = max(len(text.splitlines()), 1)
    mod = module_name(qpath)
    is_package_init = qpath.endswith("/__init__.py") or qpath == "__init__.py"
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    nodes.append(
        {
            "kind": "File",
            "name": Path(qpath).name,
            "qualified_name": qpath,
            "file_path": qpath,
            "line_start": 1,
            "line_end": line_end,
        }
    )

    # Graph container for module-level symbols: Namespace for a package __init__, else the File.
    root_container = qpath
    if is_package_init and mod:
        pkg_name = mod.rsplit(".", 1)[-1]
        nodes.append(
            {
                "kind": "Namespace",
                "name": pkg_name,
                "qualified_name": mod,
                "file_path": qpath,
                "line_start": 1,
                "line_end": line_end,
            }
        )
        edges.append(
            {
                "kind": "CONTAINS",
                "source_qname": qpath,
                "target_raw": mod,
                "file_path": qpath,
                "line": 1,
            }
        )
        root_container = mod

    # Same-file name → qname map (ambiguous names fall back to bare).
    declared: dict[str, str | None] = {}
    method_qnames: set[str] = set()
    class_bases: dict[str, list[str]] = {}

    def remember(name: str, qname: str) -> None:
        if name in declared:
            declared[name] = None
        else:
            declared[name] = qname

    def collect(stmt: ast.AST, class_qname: str | None, func_qname: str | None) -> None:
        if isinstance(stmt, ast.ClassDef):
            qn = (
                member(class_qname, stmt.name)
                if class_qname is not None
                else dotted(mod, stmt.name)
            )
            remember(stmt.name, qn)
            bases: list[str] = []
            for base in stmt.bases:
                if isinstance(base, ast.Name):
                    bases.append(resolve_name_early(base.id, qn))
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            class_bases[qn] = bases
            for child in stmt.body:
                collect(child, qn, None)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if class_qname is not None:
                qn = member(class_qname, stmt.name)
                method_qnames.add(qn)
            elif func_qname is not None:
                qn = member(func_qname, stmt.name)
            else:
                qn = dotted(mod, stmt.name)
            remember(stmt.name, qn)
            for child in stmt.body:
                collect(child, class_qname, qn)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets: list[ast.expr] = []
            if isinstance(stmt, ast.Assign):
                targets = list(stmt.targets)
            elif isinstance(stmt, ast.AnnAssign) and stmt.target is not None:
                targets = [stmt.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    if class_qname is not None:
                        remember(target.id, member(class_qname, target.id))
                    elif _is_upper_const(target.id):
                        remember(target.id, dotted(mod, target.id))

    def resolve_name_early(name: str, _current_class: str) -> str:
        # During collect, prior declarations in ``declared`` are already visible.
        local = declared.get(name)
        return local if local else dotted(mod, name)

    for stmt in tree.body:
        collect(stmt, None, None)

    def resolve_name(name: str) -> str:
        local = declared.get(name)
        if local:
            return local
        if name in declared:
            return name
        return name

    def add_node(
        kind: str,
        name: str,
        qname: str,
        node: ast.AST,
        *,
        modifiers: list[str] | None = None,
    ) -> None:
        row: dict[str, Any] = {
            "kind": kind,
            "name": name,
            "qualified_name": qname,
            "file_path": qpath,
            "line_start": getattr(node, "lineno", 1) or 1,
            "line_end": getattr(node, "end_lineno", None) or getattr(node, "lineno", 1) or 1,
        }
        if modifiers:
            row["modifiers"] = modifiers
        nodes.append(row)

    def add_edge(
        kind: str,
        source: str,
        target_raw: str,
        node: ast.AST,
        tier: str | None = None,
    ) -> None:
        row: dict[str, Any] = {
            "kind": kind,
            "source_qname": source,
            "target_raw": target_raw,
            "file_path": qpath,
            "line": getattr(node, "lineno", 1) or 1,
        }
        if tier:
            row["confidence_tier"] = tier
        edges.append(row)

    def emit_imports(node: ast.Import | ast.ImportFrom) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = import_target_raw(
                    module=alias.name, level=0, from_qpath=qpath
                )
                add_edge("IMPORTS", qpath, target, node)
                if alias.asname:
                    # ALIASES is FQN-shaped: prefer the dotted module over the file path.
                    real = (
                        module_name(target)
                        if target.endswith(".py") or target.endswith("/__init__.py")
                        else target
                    )
                    add_edge("ALIASES", dotted(mod, alias.asname), real, node)
            return
        # ImportFrom
        level = node.level or 0
        module = node.module
        # One IMPORTS edge per statement to the module (or the first named relative leaf).
        if level > 0 and module is None and node.names:
            # `from . import x, y` — one IMPORTS per name (each may be its own module).
            for alias in node.names:
                if alias.name == "*":
                    continue
                target = import_target_raw(
                    module=None, level=level, from_qpath=qpath, name=alias.name
                )
                add_edge("IMPORTS", qpath, target, node)
                if alias.asname:
                    add_edge("ALIASES", dotted(mod, alias.asname), target, node)
            return
        target = import_target_raw(module=module, level=level, from_qpath=qpath)
        add_edge("IMPORTS", qpath, target, node)
        for alias in node.names:
            if alias.name == "*" or not alias.asname:
                continue
            # `from a import b as y` — alias points at the imported name under the module.
            resolved_mod = resolve_import(module=module, level=level, from_qpath=qpath)
            if resolved_mod:
                # Prefer symbol qname under the defining module when we know the file.
                real = dotted(module_name(resolved_mod), alias.name)
            elif module:
                real = dotted(module, alias.name)
            else:
                real = alias.name
            add_edge("ALIASES", dotted(mod, alias.asname), real, node)

    def emit_call(node: ast.Call, scope: str, enclosing_class: str | None) -> None:
        func = node.func
        if isinstance(func, ast.Name):
            # ``super()`` alone is not a call edge; ``super().m()`` is handled via Attribute.
            if func.id == "super":
                return
            add_edge("CALLS", scope, resolve_name(func.id), node)
            return
        if isinstance(func, ast.Attribute):
            method = func.attr
            recv = func.value
            # self.m() / cls.m() with a known enclosing class → same-file Method when present.
            if (
                isinstance(recv, ast.Name)
                and recv.id in ("self", "cls")
                and enclosing_class is not None
            ):
                target = member(enclosing_class, method)
                if target in method_qnames:
                    add_edge("CALLS", scope, target, node)
                else:
                    add_edge("CALLS", scope, method, node, "HEURISTIC")
                return
            # super().m() — prefer a same-file base Method; else HEURISTIC bare name.
            if (
                isinstance(recv, ast.Call)
                and isinstance(recv.func, ast.Name)
                and recv.func.id == "super"
                and enclosing_class is not None
            ):
                for base in class_bases.get(enclosing_class, []):
                    target = member(base, method)
                    if target in method_qnames:
                        add_edge("CALLS", scope, target, node)
                        return
                add_edge("CALLS", scope, method, node, "HEURISTIC")
                return
            # obj.m() — method name known, receiver not: HEURISTIC ceiling (emit-do-not-gate).
            add_edge("CALLS", scope, method, node, "HEURISTIC")
            return
        add_edge("CALLS", scope, "(dynamic)", node, "DYNAMIC")

    def walk_body(
        body: list[ast.stmt],
        container: str,
        scope: str,
        enclosing_class: str | None,
    ) -> None:
        for stmt in body:
            walk_stmt(stmt, container, scope, enclosing_class)

    def walk_stmt(
        stmt: ast.stmt,
        container: str,
        scope: str,
        enclosing_class: str | None,
    ) -> None:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            emit_imports(stmt)
            return

        if isinstance(stmt, ast.ClassDef):
            if enclosing_class is None and container in (qpath, mod):
                qn = dotted(mod, stmt.name)
            elif enclosing_class is not None:
                qn = member(enclosing_class, stmt.name)
            else:
                qn = dotted(mod, stmt.name)
            add_node("Class", stmt.name, qn, stmt)
            add_edge("CONTAINS", container, qn, stmt)
            for base in stmt.bases:
                if isinstance(base, ast.Name):
                    add_edge("EXTENDS", qn, resolve_name(base.id), base)
                elif isinstance(base, ast.Attribute):
                    add_edge("EXTENDS", qn, base.attr, base)
            walk_body(stmt.body, qn, qn, qn)
            return

        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if enclosing_class is not None:
                kind = "Method"
                qn = member(enclosing_class, stmt.name)
                mods = _method_modifiers(stmt)
            elif container in (qpath, mod):
                kind = "Function"
                qn = dotted(mod, stmt.name)
                mods = _function_modifiers(stmt)
            else:
                # Nested function — Function CONTAINS inside parent.
                kind = "Function"
                qn = member(container, stmt.name)
                mods = _function_modifiers(stmt)
            add_node(kind, stmt.name, qn, stmt, modifiers=mods or None)
            add_edge("CONTAINS", container, qn, stmt)
            if not declarations_only:
                walk_body(stmt.body, qn, qn, enclosing_class)
            return

        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets: list[ast.expr] = []
            if isinstance(stmt, ast.Assign):
                targets = list(stmt.targets)
            elif stmt.target is not None:
                targets = [stmt.target]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if enclosing_class is not None:
                    qn = member(enclosing_class, target.id)
                    add_node("Property", target.id, qn, stmt)
                    add_edge("CONTAINS", enclosing_class, qn, stmt)
                elif container in (qpath, mod) and _is_upper_const(target.id):
                    qn = dotted(mod, target.id)
                    add_node("Const", target.id, qn, stmt)
                    add_edge("CONTAINS", container, qn, stmt)
            if not declarations_only and isinstance(stmt, ast.Assign) and stmt.value:
                _walk_expr(stmt.value, scope, enclosing_class)
            elif not declarations_only and isinstance(stmt, ast.AnnAssign) and stmt.value:
                _walk_expr(stmt.value, scope, enclosing_class)
            return

        if not declarations_only:
            for child in ast.iter_child_nodes(stmt):
                if isinstance(child, ast.stmt):
                    walk_stmt(child, container, scope, enclosing_class)
                else:
                    _walk_expr(child, scope, enclosing_class)

    def _walk_expr(expr: ast.AST, scope: str, enclosing_class: str | None) -> None:
        if isinstance(expr, ast.Call):
            emit_call(expr, scope, enclosing_class)
        for child in ast.iter_child_nodes(expr):
            _walk_expr(child, scope, enclosing_class)

    for stmt in tree.body:
        walk_stmt(stmt, root_container, root_container, None)

    return {"path": qpath, "ok": True, "nodes": nodes, "edges": edges}
